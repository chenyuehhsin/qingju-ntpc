#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import sys
import time
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.transport.build_commute_to_gangqian import (  # noqa: E402
    DEPARTURE_TIME,
    MAX_ROUTE_RETRIES,
    RESPONSE_DIR,
    ROUTING_PARAMS,
    SECONDS_BETWEEN_ROUTE_REQUESTS,
    TDX_BASIC_BASE_URL,
    TDX_MAAS_ROUTING_URL,
    parse_success_response,
    request_json,
    route_request_url,
)
from scripts.transport.test_tdx_api import get_access_token, require_credentials  # noqa: E402


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "transport"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "transport"
OUTPUTS_DIR = PROJECT_ROOT / "outputs" / "transport"
STATION_CACHE_DIR = INTERIM_DIR / "tdx_station_data"

CANDIDATE_LOCATIONS_PATH = PROCESSED_DIR / "candidate_locations_expanded.csv"
COMMUTE_OUTPUT_PATH = PROCESSED_DIR / "commute_by_workplace.csv"
METADATA_OUTPUT_PATH = OUTPUTS_DIR / "commute_by_workplace_metadata.json"

STATION_ENDPOINTS = {
    "TRTC": f"{TDX_BASIC_BASE_URL}/Rail/Metro/Station/TRTC",
}
FIXED_SOURCE_ENDPOINTS = {
    "OSM_NOMINATIM_CACHE": "data/interim/geocoding/nominatim_workplace_cache.json",
    "TYMC": "data/interim/transport/tdx_station_data/tymc_stations.json",
    "TRA": "data/interim/transport/tdx_station_data/tra_stations.json",
    "NWT_BUS": "data/interim/transport/tdx_station_data/nwt_bus_station_stations.json",
}
NEAR_ROUTE_FALLBACK_DISTANCE_KM = 2.0
WALKING_SPEED_KMPH = 4.8

WORKPLACES = [
    {
        "workplace_id": "gangqian_neihu",
        "workplace_name": "港墘站",
        "workplace_district": "內湖",
        "station_name": "港墘",
        "operator_id": "TRTC",
        "station_uid": "TRTC-BR17",
        "slug": "gangqian",
    },
    {
        "workplace_id": "taipei_city_hall_xinyi",
        "workplace_name": "市政府站",
        "workplace_district": "信義",
        "station_name": "市政府",
        "operator_id": "TRTC",
        "station_uid": "TRTC-BL18",
        "slug": "taipei_city_hall",
    },
    {
        "workplace_id": "taipei_main_zhongzheng",
        "workplace_name": "台北車站",
        "workplace_district": "中正",
        "station_name": "台北車站",
        "operator_id": "TRTC",
        "station_uid": "TRTC-BL12",
        "slug": "taipei_main",
    },
    {
        "workplace_id": "nangang_nangang",
        "workplace_name": "南港站",
        "workplace_district": "南港",
        "station_name": "南港",
        "operator_id": "TRTC",
        "station_uid": "TRTC-BL22",
        "slug": "nangang",
    },
    {
        "workplace_id": "xinban_special_district",
        "workplace_name": "新板特區",
        "workplace_district": "板橋",
        "station_name": "新府路",
        "operator_id": "OSM_NOMINATIM_CACHE",
        "station_uid": "nominatim:新北市板橋區新府路",
        "station_id": "",
        "lat": 25.0138307,
        "lon": 121.4618983,
        "slug": "xinban_special_district",
    },
    {
        "workplace_id": "xinzhuang_fuduxin",
        "workplace_name": "新莊副都心",
        "workplace_district": "新莊",
        "station_name": "新莊副都心站",
        "operator_id": "TYMC",
        "station_uid": "TYMC-A4",
        "station_id": "A4",
        "lat": 25.05924,
        "lon": 121.44561,
        "slug": "xinzhuang_fuduxin",
    },
    {
        "workplace_id": "xizhi_science_park",
        "workplace_name": "汐止科學園區",
        "workplace_district": "汐止",
        "station_name": "汐科站",
        "operator_id": "TRA",
        "station_uid": "TRA-0970",
        "station_id": "0970",
        "lat": 25.06406,
        "lon": 121.65233,
        "slug": "xizhi_science_park",
    },
    {
        "workplace_id": "zhonghe_tech_park",
        "workplace_name": "中和科技園區",
        "workplace_district": "中和",
        "station_name": "橋和站",
        "operator_id": "NWT_BUS",
        "station_uid": "NWT72482",
        "station_id": "72482",
        "lat": 25.007043,
        "lon": 121.496375,
        "slug": "zhonghe_tech_park",
    },
    {
        "workplace_id": "tucheng_industrial_park",
        "workplace_name": "土城產業園區",
        "workplace_district": "土城",
        "station_name": "土城工業區",
        "operator_id": "NWT_BUS",
        "station_uid": "NWT10070",
        "station_id": "10070",
        "lat": 24.962537,
        "lon": 121.425079,
        "slug": "tucheng_industrial_park",
    },
]


def station_name_zh(record: dict[str, Any]) -> str:
    name = record.get("StationName", {})
    return str(name.get("Zh_tw", "")).strip() if isinstance(name, dict) else ""


def load_station_cache() -> dict[str, list[dict[str, Any]]]:
    station_data: dict[str, list[dict[str, Any]]] = {}
    for operator_id in STATION_ENDPOINTS:
        cache_path = STATION_CACHE_DIR / f"{operator_id.lower()}_stations.json"
        if not cache_path.exists():
            raise FileNotFoundError(
                f"Missing TDX station cache: {cache_path.relative_to(PROJECT_ROOT)}. "
                "Run the existing station pipeline first."
            )
        records = json.loads(cache_path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise RuntimeError(f"Station cache for {operator_id} did not contain a list.")
        station_data[operator_id] = records
    return station_data


def workplace_station_row(station_data: dict[str, list[dict[str, Any]]], item: dict[str, str]) -> dict[str, Any]:
    if "lat" in item and "lon" in item:
        return {
            "workplace_id": item["workplace_id"],
            "workplace_name": item["workplace_name"],
            "workplace_district": item["workplace_district"],
            "workplace_station_name": item["station_name"],
            "workplace_station_operator": item["operator_id"],
            "workplace_station_uid": item["station_uid"],
            "workplace_station_id": item.get("station_id", ""),
            "workplace_lat": item["lat"],
            "workplace_lon": item["lon"],
            "workplace_source_endpoint": FIXED_SOURCE_ENDPOINTS[item["operator_id"]],
            "workplace_source_update_time": "",
            "workplace_tdx_update_time": "",
            "slug": item["slug"],
        }
    records = station_data[item["operator_id"]]
    matches = [record for record in records if str(record.get("StationUID", "")) == item["station_uid"]]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one station UID {item['station_uid']}, found {len(matches)}.")
    record = matches[0]
    if station_name_zh(record) != item["station_name"]:
        raise RuntimeError(
            f"Station UID {item['station_uid']} expected {item['station_name']}, found {station_name_zh(record)}."
        )
    position = record.get("StationPosition", {})
    lat = position.get("PositionLat") if isinstance(position, dict) else None
    lon = position.get("PositionLon") if isinstance(position, dict) else None
    if lat is None or lon is None:
        raise RuntimeError(f"Station {item['station_name']} does not include lat/lon.")
    return {
        "workplace_id": item["workplace_id"],
        "workplace_name": item["workplace_name"],
        "workplace_district": item["workplace_district"],
        "workplace_station_name": station_name_zh(record),
        "workplace_station_operator": item["operator_id"],
        "workplace_station_uid": record.get("StationUID", ""),
        "workplace_station_id": record.get("StationID", ""),
        "workplace_lat": lat,
        "workplace_lon": lon,
        "workplace_source_endpoint": STATION_ENDPOINTS[item["operator_id"]],
        "workplace_source_update_time": record.get("SrcUpdateTime", ""),
        "workplace_tdx_update_time": record.get("UpdateTime", ""),
        "slug": item["slug"],
    }


def safe_response_filename(candidate_slug: str, workplace_slug: str) -> str:
    return f"{candidate_slug}_to_{workplace_slug}.json"


def load_candidates() -> list[dict[str, Any]]:
    df = list(csv.DictReader(CANDIDATE_LOCATIONS_PATH.open(encoding="utf-8")))
    if len(df) != 16:
        raise RuntimeError(f"Expected 16 candidate rows, found {len(df)}.")
    if len({row["candidate_name"] for row in df}) != 16:
        raise RuntimeError("Candidate location table contains duplicate candidate_name values.")
    return df


def candidate_slug(candidate_name: str) -> str:
    mapping = {
        "汐止車站": "xizhi_station",
        "頂溪站": "dingxi_station",
        "景安站": "jingan_station",
        "大坪林站": "dapinglin_station",
        "板橋站": "banqiao_station",
        "三重站": "sanchong_station",
        "新莊站": "xinzhuang_station",
        "蘆洲站": "luzhou_station",
        "土城站": "tucheng_station",
        "泰山站": "taishan_station",
        "林口站": "linkou_station",
        "淡水站": "tamsui_station",
        "三峽北大特區": "sanxia_ntpu_main_gate",
        "樹林車站": "shulin_station",
        "五股區公所": "wugu_district_office",
        "鶯歌車站": "yingge_station",
    }
    try:
        return mapping[candidate_name]
    except KeyError as exc:
        raise RuntimeError(f"Missing response-cache slug for candidate {candidate_name}.") from exc


def route_cache_has_success(path: Path) -> bool:
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


def near_route_fallback_fields(candidate: dict[str, Any], workplace: dict[str, Any]) -> dict[str, Any] | None:
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


def access_token_if_needed(candidates: list[dict[str, Any]], workplaces: list[dict[str, Any]]) -> str:
    for workplace in workplaces:
        for candidate in candidates:
            response_file = RESPONSE_DIR / safe_response_filename(candidate_slug(candidate["candidate_name"]), workplace["slug"])
            if route_cache_has_success(response_file):
                continue
            if near_route_fallback_fields(candidate, workplace):
                continue
            break
        else:
            continue
        break
    else:
        return ""
    client_id, client_secret = require_credentials()
    return get_access_token(client_id, client_secret)


def build_row(
    access_token: str,
    candidate: dict[str, Any],
    workplace: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    response_file = RESPONSE_DIR / safe_response_filename(candidate_slug(candidate["candidate_name"]), workplace["slug"])
    had_success_cache = route_cache_has_success(response_file)
    row = {
        "workplace_id": workplace["workplace_id"],
        "workplace_name": workplace["workplace_name"],
        "workplace_district": workplace["workplace_district"],
        "workplace_lat": workplace["workplace_lat"],
        "workplace_lon": workplace["workplace_lon"],
        "workplace_station_operator": workplace["workplace_station_operator"],
        "workplace_station_uid": workplace["workplace_station_uid"],
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

    cached_response: dict[str, Any] | None = None
    if response_file.exists():
        try:
            cached_response = json.loads(response_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached_response = None
    if cached_response:
        cached_fields = parse_success_response(cached_response)
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
        row["error_message"] = "Missing TDX access token and no successful cache exists."
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
        if response.get("result") != "success":
            row["error_message"] = json.dumps(response.get("error", response), ensure_ascii=False)
        else:
            fields = parse_success_response(response)
            if fields is None:
                fallback_fields = near_route_fallback_fields(candidate, workplace)
                if fallback_fields:
                    row.update(fallback_fields)
                else:
                    row["error_message"] = "TDX returned success but no usable transit route."
            else:
                row.update(fields)
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        row["error_message"] = f"HTTP {exc.code}: {message[:500]}"
        response_file.write_text(
            json.dumps({"http_status": exc.code, "body": message}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (urllib.error.URLError, TimeoutError, RuntimeError, ValueError) as exc:
        row["error_message"] = str(exc)
        response_file.write_text(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2), encoding="utf-8")
    return row, not had_success_cache


def build_commute_rows(
    candidates: list[dict[str, Any]],
    workplaces: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    RESPONSE_DIR.mkdir(parents=True, exist_ok=True)
    access_token = access_token_if_needed(candidates, workplaces)

    rows: list[dict[str, Any]] = []
    for workplace in workplaces:
        for candidate in candidates:
            row, queried_api = build_row(access_token, candidate, workplace)
            rows.append(row)
            if row["query_status"] != "success":
                print(
                    f"Route failed: {candidate['candidate_name']} -> {workplace['workplace_name']}: "
                    f"{row['error_message']}",
                    file=sys.stderr,
                )
            if queried_api:
                time.sleep(SECONDS_BETWEEN_ROUTE_REQUESTS)
    return rows


def write_commute_rows(rows: list[dict[str, Any]]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "workplace_id",
        "workplace_name",
        "workplace_district",
        "workplace_lat",
        "workplace_lon",
        "workplace_station_operator",
        "workplace_station_uid",
        "candidate_name",
        "district",
        "lat",
        "lon",
        "departure_time",
        "commute_minutes",
        "transfer_count",
        "route_summary",
        "query_status",
        "error_message",
        "route_start_time",
        "route_end_time",
        "travel_time_seconds",
        "maas_response_file",
    ]
    with COMMUTE_OUTPUT_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_metadata(workplaces: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "departure_time": DEPARTURE_TIME,
        "departure_timezone": "Asia/Taipei",
        "workplaces": [
            {key: value for key, value in workplace.items() if key != "slug"}
            for workplace in workplaces
        ],
        "routing_endpoint": TDX_MAAS_ROUTING_URL,
        "routing_parameters": ROUTING_PARAMS,
        "station_endpoints": STATION_ENDPOINTS,
        "station_cache_dir": str(STATION_CACHE_DIR.relative_to(PROJECT_ROOT)),
        "maas_response_dir": str(RESPONSE_DIR.relative_to(PROJECT_ROOT)),
        "route_selection": "Fastest route among returned routes with at least one transit section.",
        "candidate_count": len({row["candidate_name"] for row in rows}),
        "workplace_count": len({row["workplace_id"] for row in rows}),
        "row_count": len(rows),
        "success_count": sum(1 for row in rows if row["query_status"] == "success"),
        "failure_count": sum(1 for row in rows if row["query_status"] != "success"),
    }
    METADATA_OUTPUT_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    station_data = load_station_cache()
    workplaces = [workplace_station_row(station_data, item) for item in WORKPLACES]
    candidates = load_candidates()
    rows = build_commute_rows(candidates, workplaces)
    write_commute_rows(rows)
    write_metadata(workplaces, rows)

    print(f"Wrote {COMMUTE_OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {METADATA_OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    for workplace in workplaces:
        subset = [row for row in rows if row["workplace_id"] == workplace["workplace_id"]]
        print(
            f"{workplace['workplace_name']}: "
            f"{sum(1 for row in subset if row['query_status'] == 'success')}/{len(subset)} success"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
