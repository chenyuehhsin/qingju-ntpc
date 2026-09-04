from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_loader import (  # noqa: E402
    CANDIDATE_LOCATIONS_CSV,
    LIVABILITY_CSV,
    MODE_ORDER,
    living_area,
)
from scripts.integration.build_multi_workplace_recommendations import (  # noqa: E402
    LIFE_QUALITY_MODE,
    NEIHU_BASELINE_RENT,
    PREFERENCE_MODES,
    add_pareto_columns,
    build_life_quality_recommendations,
    build_rent_commute_recommendations,
    recommendation_columns,
)
from scripts.transport.build_commute_to_gangqian import (  # noqa: E402
    DEPARTURE_TIME,
    MAX_ROUTE_RETRIES,
    SECONDS_BETWEEN_ROUTE_REQUESTS,
    parse_success_response,
    request_json,
    route_request_url,
)
from scripts.transport.build_commute_by_workplace import candidate_slug  # noqa: E402
from scripts.transport.test_tdx_api import get_access_token, require_credentials  # noqa: E402


HOUSING_BENCHMARK_CSV = PROJECT_ROOT / "data" / "processed" / "housing" / "moi_independent_suite_rent_benchmark.csv"
GEOCODE_CACHE_PATH = PROJECT_ROOT / "data" / "interim" / "geocoding" / "nominatim_workplace_cache.json"
CUSTOM_MAAS_DIR = PROJECT_ROOT / "data" / "interim" / "transport" / "tdx_maas_responses_custom_workplace"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
GEOCODING_SOURCE = "OpenStreetMap Nominatim"
USER_AGENT = "qingju-ntpc-hackathon/0.1 (custom workplace geocoding; contact: local-mvp)"
GEOCODING_FAILURE_MESSAGE = "無法定位此地址，請嘗試移除樓層、公司名稱或改用附近交通節點。"
NEAR_ROUTE_FALLBACK_DISTANCE_KM = 2.0
WALKING_SPEED_KMPH = 4.8


def normalize_address(address: str) -> str:
    return " ".join(address.strip().split())


def remove_floor_info(address: str) -> str:
    normalized = normalize_address(address)
    floor_patterns = [
        r"(?<=號)\s*(?:地下)?\d+\s*(?:樓|[Ff])(?:\s*(?:之|-|－)\s*\d+)?(?:\s*室)?$",
        r"\s+(?:地下)?\d+\s*(?:樓|[Ff])(?:\s*(?:之|-|－)\s*\d+)?(?:\s*室)?$",
    ]
    result = normalized
    for pattern in floor_patterns:
        result = re.sub(pattern, "", result).strip()
    return normalize_address(result)


def remove_village_level(address: str) -> str:
    normalized = normalize_address(address)
    result = re.sub(r"([區鎮鄉市])[^區鎮鄉市路街大道段巷弄號]{1,12}里", r"\1", normalized, count=1)
    return normalize_address(result)


def geocode_query_candidates(address: str) -> list[dict[str, str]]:
    original = normalize_address(address)
    candidates = [
        {
            "query_strategy": "original_address",
            "normalized_address": original,
        }
    ]
    no_floor = remove_floor_info(original)
    if no_floor != original:
        candidates.append(
            {
                "query_strategy": "remove_floor_info",
                "normalized_address": no_floor,
            }
        )
    no_village = remove_village_level(no_floor)
    if no_village != no_floor:
        candidates.append(
            {
                "query_strategy": "remove_floor_info_and_village",
                "normalized_address": no_village,
            }
        )

    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized_address = candidate["normalized_address"]
        if normalized_address and normalized_address not in seen:
            deduped.append(candidate)
            seen.add(normalized_address)
    return deduped


def load_json_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def geocode_address(address: str) -> dict[str, Any]:
    original = normalize_address(address)
    if not original:
        raise ValueError("請輸入工作地址。")

    cache = load_json_cache(GEOCODE_CACHE_PATH)
    query_candidates = geocode_query_candidates(original)
    for sequence, candidate in enumerate(query_candidates, start=1):
        normalized = candidate["normalized_address"]
        strategy = candidate["query_strategy"]
        record = geocode_single_query(original, normalized, strategy, sequence, cache)
        if record.get("status") == "success":
            record["original_address"] = original
            record["normalized_address"] = normalized
            record["query_strategy"] = strategy
            record["query_sequence"] = sequence
            record["fallback_queries"] = query_candidates
            return record

    raise RuntimeError(GEOCODING_FAILURE_MESSAGE)


def geocode_single_query(
    original_address: str,
    normalized_address: str,
    query_strategy: str,
    query_sequence: int,
    cache: dict[str, Any],
) -> dict[str, Any]:
    cached = cache.get(normalized_address)
    if cached:
        record = dict(cached)
        record.setdefault("original_address", original_address)
        record.setdefault("normalized_address", normalized_address)
        record.setdefault("query_strategy", query_strategy)
        record.setdefault("query_sequence", query_sequence)
        return record

    params = urllib.parse.urlencode(
        {
            "format": "jsonv2",
            "q": normalized_address,
            "countrycodes": "tw",
            "limit": "1",
            "addressdetails": "1",
        }
    )
    request = urllib.request.Request(
        f"{NOMINATIM_URL}?{params}",
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            results = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Geocoding failed: {exc}") from exc

    if not isinstance(results, list) or not results:
        cache[normalized_address] = {
            "status": "failed",
            "query": normalized_address,
            "original_address": original_address,
            "normalized_address": normalized_address,
            "query_strategy": query_strategy,
            "query_sequence": query_sequence,
            "source": GEOCODING_SOURCE,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "error_message": "No geocoding result returned.",
        }
        write_json_cache(GEOCODE_CACHE_PATH, cache)
        return cache[normalized_address]

    first = results[0]
    lat = float(first["lat"])
    lon = float(first["lon"])
    if not (21.5 <= lat <= 26.5 and 119.0 <= lon <= 123.0):
        cache[normalized_address] = {
            "status": "failed",
            "query": normalized_address,
            "original_address": original_address,
            "normalized_address": normalized_address,
            "query_strategy": query_strategy,
            "query_sequence": query_sequence,
            "source": GEOCODING_SOURCE,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "error_message": "Geocoding result is outside Taiwan bounds; refusing to use guessed coordinates.",
            "raw": first,
        }
        write_json_cache(GEOCODE_CACHE_PATH, cache)
        return cache[normalized_address]

    record = {
        "status": "success",
        "query": normalized_address,
        "original_address": original_address,
        "normalized_address": normalized_address,
        "query_strategy": query_strategy,
        "query_sequence": query_sequence,
        "source": GEOCODING_SOURCE,
        "source_url": NOMINATIM_URL,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "display_name": first.get("display_name", normalized_address),
        "lat": lat,
        "lon": lon,
        "raw": first,
    }
    cache[normalized_address] = record
    write_json_cache(GEOCODE_CACHE_PATH, cache)
    return record


def workplace_id_for(address: str, lat: float, lon: float) -> str:
    digest = hashlib.sha1(f"{normalize_address(address)}|{lat:.6f}|{lon:.6f}".encode("utf-8")).hexdigest()[:12]
    return f"custom_{digest}"


def route_cache_file(candidate_name: str, workplace_id: str) -> Path:
    return CUSTOM_MAAS_DIR / workplace_id / f"{candidate_slug(candidate_name)}_to_custom_workplace.json"


def route_cache_success(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return parse_success_response(payload) is not None


def haversine_km(origin_lat: float, origin_lon: float, destination_lat: float, destination_lon: float) -> float:
    radius_km = 6371.0088
    lat1 = math.radians(origin_lat)
    lat2 = math.radians(destination_lat)
    delta_lat = math.radians(destination_lat - origin_lat)
    delta_lon = math.radians(destination_lon - origin_lon)
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def near_route_fallback_fields(candidate: pd.Series, workplace: dict[str, Any]) -> dict[str, Any] | None:
    distance_km = haversine_km(
        float(candidate["lat"]),
        float(candidate["lon"]),
        float(workplace["workplace_lat"]),
        float(workplace["workplace_lon"]),
    )
    if distance_km > NEAR_ROUTE_FALLBACK_DISTANCE_KM:
        return None
    minutes = max(5.0, round(distance_km / WALKING_SPEED_KMPH * 60, 1))
    travel_seconds = int(round(minutes * 60))
    return {
        "commute_minutes": minutes,
        "transfer_count": 0,
        "route_summary": f"Near workplace fallback: {distance_km:.1f} km walking connection used because TDX returned no usable public-transit route.",
        "query_status": "success",
        "error_message": "",
        "travel_time_seconds": travel_seconds,
    }


def access_token_if_needed(candidates: pd.DataFrame, workplace: dict[str, Any]) -> str:
    workplace_id = str(workplace["workplace_id"])
    needs_api = False
    for _, candidate in candidates.iterrows():
        path = route_cache_file(candidate["candidate_name"], workplace_id)
        if route_cache_success(path):
            continue
        if near_route_fallback_fields(candidate, workplace):
            continue
        needs_api = True
        break
    if not needs_api:
        return ""
    client_id, client_secret = require_credentials()
    return get_access_token(client_id, client_secret)


def build_route_row(
    access_token: str,
    candidate: pd.Series,
    workplace: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    response_file = route_cache_file(str(candidate["candidate_name"]), str(workplace["workplace_id"]))
    response_file.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "workplace_id": workplace["workplace_id"],
        "workplace_name": workplace["workplace_name"],
        "workplace_district": workplace["workplace_district"],
        "workplace_lat": workplace["workplace_lat"],
        "workplace_lon": workplace["workplace_lon"],
        "candidate_name": candidate["candidate_name"],
        "district": candidate["district"],
        "lat": candidate["lat"],
        "lon": candidate["lon"],
        "departure_time": DEPARTURE_TIME,
        "commute_minutes": "",
        "transfer_count": "",
        "route_summary": "",
        "query_status": "failed",
        "error_message": "",
        "route_start_time": "",
        "route_end_time": "",
        "travel_time_seconds": "",
        "maas_response_file": str(response_file.relative_to(PROJECT_ROOT)),
    }

    if response_file.exists():
        try:
            cached_payload = json.loads(response_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached_payload = None
        if cached_payload:
            cached_fields = parse_success_response(cached_payload)
            if cached_fields:
                row.update(cached_fields)
                return row, False
            fallback_fields = near_route_fallback_fields(candidate, workplace)
            if fallback_fields:
                row.update(fallback_fields)
                return row, False

    if not access_token:
        fallback_fields = near_route_fallback_fields(candidate, workplace)
        if fallback_fields:
            row.update(fallback_fields)
            return row, False
        row["error_message"] = "Missing TDX access token and no successful route cache exists."
        return row, False

    url = route_request_url(
        float(candidate["lat"]),
        float(candidate["lon"]),
        float(workplace["workplace_lat"]),
        float(workplace["workplace_lon"]),
    )
    try:
        response: dict[str, Any] | None = None
        for attempt in range(MAX_ROUTE_RETRIES + 1):
            try:
                if attempt > 0:
                    time.sleep(60)
                response = request_json(url, access_token, timeout=90)
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt >= MAX_ROUTE_RETRIES:
                    raise
                exc.read()
        if response is None:
            raise RuntimeError("TDX routing returned no response.")
        response_file.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
        fields = parse_success_response(response)
        if fields is None:
            fallback_fields = near_route_fallback_fields(candidate, workplace)
            if fallback_fields:
                row.update(fallback_fields)
            else:
                row["error_message"] = "TDX returned no usable public-transit route."
        else:
            row.update(fields)
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        row["error_message"] = f"HTTP {exc.code}: {message[:500]}"
        response_file.write_text(json.dumps({"http_status": exc.code, "body": message}, ensure_ascii=False, indent=2), encoding="utf-8")
    except (urllib.error.URLError, TimeoutError, RuntimeError, ValueError) as exc:
        row["error_message"] = str(exc)
        response_file.write_text(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), encoding="utf-8")
    return row, True


def build_custom_commute(workplace: dict[str, Any]) -> pd.DataFrame:
    candidates = pd.read_csv(CANDIDATE_LOCATIONS_CSV)
    if len(candidates) != 16:
        raise RuntimeError(f"Expected 16 candidate locations, found {len(candidates)}.")
    access_token = access_token_if_needed(candidates, workplace)

    rows: list[dict[str, Any]] = []
    for _, candidate in candidates.iterrows():
        row, queried_api = build_route_row(access_token, candidate, workplace)
        rows.append(row)
        if queried_api:
            time.sleep(SECONDS_BETWEEN_ROUTE_REQUESTS)
    commute = pd.DataFrame(rows)
    failed = commute[commute["query_status"] != "success"]
    if not failed.empty:
        details = failed[["candidate_name", "error_message"]].to_dict("records")
        raise RuntimeError(f"TDX route failures: {details}")
    return commute


def build_custom_rent_commute(commute: pd.DataFrame) -> pd.DataFrame:
    locations = pd.read_csv(CANDIDATE_LOCATIONS_CSV)
    housing = pd.read_csv(HOUSING_BENCHMARK_CSV)

    location_fields = locations[
        [
            "candidate_name",
            "station_name",
            "station_operator",
            "station_uid",
            "station_id",
            "source_endpoint",
            "selection_reason",
            "route_count_at_station",
        ]
    ].copy()
    merged = commute.merge(location_fields, on="candidate_name", how="left", validate="one_to_one")
    ntpc_housing = (
        housing[housing["city"] == "新北市"][["city", "district", "rent_median"]]
        .rename(columns={"city": "official_benchmark_city", "rent_median": "official_median_rent"})
        .copy()
    )
    merged = merged.merge(ntpc_housing, on="district", how="left", validate="many_to_one")
    if merged["official_median_rent"].isna().any():
        missing = merged[merged["official_median_rent"].isna()][["candidate_name", "district"]].to_dict("records")
        raise RuntimeError(f"Housing benchmark join failed: {missing}")
    merged["official_median_rent"] = merged["official_median_rent"].astype(int)
    merged["rent_saving_vs_neihu"] = NEIHU_BASELINE_RENT - merged["official_median_rent"]
    merged = add_pareto_columns(merged)
    return merged


def build_custom_dashboard_data(address: str, geocode: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    workplace_id = workplace_id_for(address, float(geocode["lat"]), float(geocode["lon"]))
    workplace = {
        "workplace_id": workplace_id,
        "workplace_name": "我的工作地",
        "workplace_district": "自訂地址",
        "workplace_lat": float(geocode["lat"]),
        "workplace_lon": float(geocode["lon"]),
        "workplace_address": normalize_address(address),
        "geocoding_source": geocode["source"],
        "geocoding_display_name": geocode["display_name"],
    }
    commute = build_custom_commute(workplace)
    rent_commute = build_custom_rent_commute(commute)

    rent_commute_recommendations = build_rent_commute_recommendations(rent_commute)
    life_quality_recommendations = build_life_quality_recommendations(rent_commute)
    recommendations = recommendation_columns(
        pd.concat([rent_commute_recommendations, life_quality_recommendations], ignore_index=True, sort=False)
    )

    livability = pd.read_csv(LIVABILITY_CSV)
    livability_columns = [
        "candidate_name",
        "equal_weight_livability_index",
        "total_poi_count",
        "food_count",
        "shopping_count",
        "medical_count",
        "recreation_count",
        "culture_count",
    ]
    candidates = rent_commute.merge(
        livability[[column for column in livability_columns if column in livability.columns]],
        on="candidate_name",
        how="left",
        validate="one_to_one",
    )
    candidates["rent"] = candidates["official_median_rent"]
    candidates["livability_index"] = candidates["equal_weight_livability_index"]
    candidates["living_area"] = candidates["candidate_name"].map(living_area)

    recommendations = recommendations.merge(
        candidates[
            [
                "candidate_name",
                "living_area",
                "livability_index",
                "total_poi_count",
                *[
                    column
                    for column in livability_columns
                    if column.endswith("_count") and column != "total_poi_count" and column in candidates.columns
                ],
                "route_summary",
            ]
        ],
        on="candidate_name",
        how="left",
        validate="many_to_one",
        suffixes=("", "_from_candidates"),
    )
    recommendations["livability_index"] = recommendations["livability_index"].fillna(
        recommendations["livability_index_from_candidates"]
    )
    for column in ["total_poi_count", "food_count", "shopping_count", "medical_count", "recreation_count", "culture_count"]:
        from_candidates = f"{column}_from_candidates"
        if from_candidates not in recommendations.columns:
            continue
        if column in recommendations.columns:
            recommendations[column] = recommendations[column].fillna(recommendations[from_candidates])
        else:
            recommendations[column] = recommendations[from_candidates]
    recommendations = recommendations.drop(
        columns=[column for column in recommendations.columns if column.endswith("_from_candidates")]
    )
    top3 = recommendations[recommendations["rank"] <= 3].copy()
    destination = {
        "workplace_id": workplace_id,
        "workplace_name": "我的工作地",
        "workplace_district": "自訂地址",
        "destination": "我的工作地",
        "destination_lat": float(geocode["lat"]),
        "destination_lon": float(geocode["lon"]),
        "workplace_address": normalize_address(address),
        "geocoding_source": geocode["source"],
        "geocoding_display_name": geocode["display_name"],
    }
    _validate_custom_outputs(candidates, recommendations, top3)
    return candidates, recommendations, top3, destination


def _validate_custom_outputs(candidates: pd.DataFrame, recommendations: pd.DataFrame, top3: pd.DataFrame) -> None:
    if len(candidates) != 16:
        raise RuntimeError(f"Expected 16 candidates, found {len(candidates)}.")
    for mode in MODE_ORDER:
        rows = top3[top3["preference_mode"] == mode]
        if len(rows) != 3:
            raise RuntimeError(f"Expected Top 3 for {mode}, found {len(rows)}.")
    if len(recommendations[recommendations["preference_mode"] == "生活品質型"]) != 16:
        raise RuntimeError("Expected 16 rows for 生活品質型 recommendations.")


def top1_summary(recommendations: pd.DataFrame) -> dict[str, str]:
    return {
        mode: recommendations[(recommendations["preference_mode"] == mode) & (recommendations["rank"] == 1)].iloc[0]["candidate_name"]
        for mode in MODE_ORDER
    }


__all__ = [
    "GEOCODING_SOURCE",
    "build_custom_dashboard_data",
    "geocode_address",
    "top1_summary",
]
