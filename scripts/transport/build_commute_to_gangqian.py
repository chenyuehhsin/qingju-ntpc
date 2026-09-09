#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.transport.test_tdx_api import get_access_token, require_credentials


USER_AGENT = "qingju-ntpc-hackathon/0.1 (transport commute MVP)"
TDX_BASIC_BASE_URL = "https://tdx.transportdata.tw/api/basic/v2"
TDX_MAAS_ROUTING_URL = "https://tdx.transportdata.tw/api/maas/routing"

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "transport"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "transport"
OUTPUTS_DIR = PROJECT_ROOT / "outputs" / "transport"
STATION_CACHE_DIR = INTERIM_DIR / "tdx_station_data"
RESPONSE_DIR = INTERIM_DIR / "tdx_maas_responses"

CANDIDATE_LOCATIONS_PATH = PROCESSED_DIR / "candidate_locations.csv"
COMMUTE_OUTPUT_PATH = PROCESSED_DIR / "commute_to_gangqian.csv"
METADATA_OUTPUT_PATH = OUTPUTS_DIR / "commute_to_gangqian_metadata.json"

# The current project date is 2026-08-21, a Friday. Use the next Monday
# morning so the API query is a reproducible weekday commute scenario.
DEPARTURE_TIME = "2026-08-24T08:00:00"

STATION_ENDPOINTS = {
    "TRTC": f"{TDX_BASIC_BASE_URL}/Rail/Metro/Station/TRTC",
    "TRA": f"{TDX_BASIC_BASE_URL}/Rail/TRA/Station",
}

DESTINATION = {
    "candidate_name": "港墘站",
    "name": "港墘站",
    "station_name": "港墘",
    "operator_id": "TRTC",
}

CANDIDATES = [
    {"candidate_name": "汐止車站", "station_name": "汐止", "operator_id": "TRA"},
    {"candidate_name": "頂溪站", "station_name": "頂溪", "operator_id": "TRTC"},
    {"candidate_name": "景安站", "station_name": "景安", "operator_id": "TRTC"},
    {"candidate_name": "大坪林站", "station_name": "大坪林", "operator_id": "TRTC"},
    {"candidate_name": "板橋站", "station_name": "板橋", "operator_id": "TRTC"},
    {"candidate_name": "三重站", "station_name": "三重", "operator_id": "TRTC"},
    {"candidate_name": "新莊站", "station_name": "新莊", "operator_id": "TRTC"},
    {"candidate_name": "蘆洲站", "station_name": "蘆洲", "operator_id": "TRTC"},
]

ROUTING_PARAMS = {
    "gc": "1",
    "top": "5",
    "transit": "3,4,5,6,7,8,9",
    "transfer_time": "5,60",
    "depart": DEPARTURE_TIME,
    "first_mile_mode": "0",
    "first_mile_time": "10",
    "last_mile_mode": "0",
    "last_mile_time": "10",
}

MAX_ROUTE_RETRIES = 2
SECONDS_BETWEEN_ROUTE_REQUESTS = 12


def request_json(url: str, access_token: str, timeout: int = 60) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            raise RuntimeError(f"TDX returned non-JSON content type: {content_type}")
        return json.loads(body)


def fetch_station_data(access_token: str) -> dict[str, list[dict[str, Any]]]:
    STATION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    station_data: dict[str, list[dict[str, Any]]] = {}
    for operator_id, url in STATION_ENDPOINTS.items():
        records = request_json(url, access_token, timeout=30)
        if not isinstance(records, list):
            raise RuntimeError(f"Station endpoint for {operator_id} did not return a list.")
        station_data[operator_id] = records
        cache_path = STATION_CACHE_DIR / f"{operator_id.lower()}_stations.json"
        cache_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return station_data


def station_name_zh(record: dict[str, Any]) -> str:
    name = record.get("StationName", {})
    return str(name.get("Zh_tw", "")).strip() if isinstance(name, dict) else ""


def find_station(
    station_data: dict[str, list[dict[str, Any]]],
    station_name: str,
    operator_id: str,
) -> dict[str, Any]:
    matches = [
        record
        for record in station_data.get(operator_id, [])
        if station_name_zh(record) == station_name
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one {operator_id} station named {station_name}, found {len(matches)}."
        )
    return matches[0]


def station_row(
    station_data: dict[str, list[dict[str, Any]]],
    item: dict[str, str],
) -> dict[str, Any]:
    record = find_station(station_data, item["station_name"], item["operator_id"])
    position = record.get("StationPosition", {})
    lat = position.get("PositionLat") if isinstance(position, dict) else None
    lon = position.get("PositionLon") if isinstance(position, dict) else None
    if lat is None or lon is None:
        raise RuntimeError(f"Station {item['station_name']} does not include lat/lon.")
    return {
        "candidate_name": item.get("candidate_name", item["station_name"]),
        "district": record.get("LocationTown", ""),
        "station_name": station_name_zh(record),
        "station_operator": item["operator_id"],
        "station_uid": record.get("StationUID", ""),
        "station_id": record.get("StationID", ""),
        "lat": lat,
        "lon": lon,
        "source_endpoint": STATION_ENDPOINTS[item["operator_id"]],
        "source_update_time": record.get("SrcUpdateTime", ""),
        "tdx_update_time": record.get("UpdateTime", ""),
    }


def write_candidate_locations(rows: list[dict[str, Any]]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "candidate_name",
        "district",
        "station_name",
        "station_operator",
        "station_uid",
        "station_id",
        "lat",
        "lon",
        "source_endpoint",
        "source_update_time",
        "tdx_update_time",
    ]
    with CANDIDATE_LOCATIONS_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def route_request_url(origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float) -> str:
    params = {
        **ROUTING_PARAMS,
        "origin": f"{origin_lat:.6f},{origin_lon:.6f}",
        "destination": f"{dest_lat:.6f},{dest_lon:.6f}",
    }
    return f"{TDX_MAAS_ROUTING_URL}?{urllib.parse.urlencode(params)}"


def choose_fastest_transit_route(response: dict[str, Any]) -> dict[str, Any] | None:
    routes = response.get("data", {}).get("routes", [])
    if not isinstance(routes, list):
        return None
    transit_routes = [
        route
        for route in routes
        if isinstance(route, dict)
        and route.get("travel_time") is not None
        and any(section.get("type") == "transit" for section in route.get("sections", []))
    ]
    if not transit_routes:
        return None
    return min(transit_routes, key=lambda route: route.get("travel_time", math.inf))


def route_output_fields(route: dict[str, Any]) -> dict[str, Any]:
    travel_time = int(route["travel_time"])
    return {
        "commute_minutes": round(travel_time / 60, 1),
        "transfer_count": route.get("transfers", ""),
        "route_summary": summarize_route(route),
        "query_status": "success",
        "route_start_time": route.get("start_time", ""),
        "route_end_time": route.get("end_time", ""),
        "travel_time_seconds": travel_time,
    }


def parse_success_response(response: dict[str, Any]) -> dict[str, Any] | None:
    if response.get("result") != "success":
        return None
    route = choose_fastest_transit_route(response)
    if route is None:
        return None
    return route_output_fields(route)


def summarize_route(route: dict[str, Any]) -> str:
    summaries: list[str] = []
    for section in route.get("sections", []):
        if not isinstance(section, dict) or section.get("type") != "transit":
            continue
        transport = section.get("transport", {})
        if not isinstance(transport, dict):
            continue
        mode = str(transport.get("mode") or transport.get("category") or "transit")
        name = str(transport.get("name") or transport.get("shortName") or "").strip()
        departure_place = section.get("departure", {}).get("place", {}).get("name", "")
        arrival_place = section.get("arrival", {}).get("place", {}).get("name", "")
        label = f"{mode} {name}".strip()
        if departure_place and arrival_place:
            label = f"{label} ({departure_place}->{arrival_place})"
        summaries.append(label)
    return " | ".join(summaries)


def safe_response_filename(candidate_name: str) -> str:
    mapping = {
        "汐止車站": "xizhi_station",
        "頂溪站": "dingxi_station",
        "景安站": "jingan_station",
        "大坪林站": "dapinglin_station",
        "板橋站": "banqiao_station",
        "三重站": "sanchong_station",
        "新莊站": "xinzhuang_station",
        "蘆洲站": "luzhou_station",
    }
    return f"{mapping[candidate_name]}_to_gangqian.json"


def build_commute_rows(
    access_token: str,
    candidate_rows: list[dict[str, Any]],
    destination_row: dict[str, Any],
) -> list[dict[str, Any]]:
    RESPONSE_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for candidate in candidate_rows:
        response_file = RESPONSE_DIR / safe_response_filename(str(candidate["candidate_name"]))
        row = {
            "candidate_name": candidate["candidate_name"],
            "district": candidate["district"],
            "lat": candidate["lat"],
            "lon": candidate["lon"],
            "destination": DESTINATION["name"],
            "destination_lat": destination_row["lat"],
            "destination_lon": destination_row["lon"],
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
        url = route_request_url(
            float(candidate["lat"]),
            float(candidate["lon"]),
            float(destination_row["lat"]),
            float(destination_row["lon"]),
        )
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
                rows.append(row)
                continue

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
            response_file.write_text(
                json.dumps(response, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            if response.get("result") != "success":
                row["error_message"] = json.dumps(response.get("error", response), ensure_ascii=False)
            else:
                output_fields = parse_success_response(response)
                if output_fields is None:
                    row["error_message"] = "TDX returned success but no usable transit route."
                else:
                    row.update(output_fields)
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            row["error_message"] = f"HTTP {exc.code}: {message[:500]}"
            response_file.write_text(
                json.dumps({"http_status": exc.code, "body": message}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except (urllib.error.URLError, TimeoutError, RuntimeError, ValueError) as exc:
            row["error_message"] = str(exc)
            response_file.write_text(
                json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        rows.append(row)
        time.sleep(SECONDS_BETWEEN_ROUTE_REQUESTS)
    return rows


def write_commute_rows(rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "candidate_name",
        "district",
        "lat",
        "lon",
        "destination",
        "destination_lat",
        "destination_lon",
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


def write_metadata(destination_row: dict[str, Any], commute_rows: list[dict[str, Any]]) -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "departure_time": DEPARTURE_TIME,
        "departure_timezone": "Asia/Taipei",
        "destination": destination_row,
        "routing_endpoint": TDX_MAAS_ROUTING_URL,
        "routing_parameters": ROUTING_PARAMS,
        "station_endpoints": STATION_ENDPOINTS,
        "station_cache_dir": str(STATION_CACHE_DIR.relative_to(PROJECT_ROOT)),
        "maas_response_dir": str(RESPONSE_DIR.relative_to(PROJECT_ROOT)),
        "route_selection": "Fastest route among returned routes with at least one transit section.",
        "candidate_count": len(commute_rows),
        "success_count": sum(1 for row in commute_rows if row["query_status"] == "success"),
        "failure_count": sum(1 for row in commute_rows if row["query_status"] != "success"),
    }
    METADATA_OUTPUT_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    client_id, client_secret = require_credentials()
    access_token = get_access_token(client_id, client_secret)

    station_data = fetch_station_data(access_token)
    candidate_rows = [station_row(station_data, item) for item in CANDIDATES]
    destination_row = station_row(station_data, DESTINATION)

    write_candidate_locations(candidate_rows)
    commute_rows = build_commute_rows(access_token, candidate_rows, destination_row)
    write_commute_rows(commute_rows)
    write_metadata(destination_row, commute_rows)

    print(f"Wrote {CANDIDATE_LOCATIONS_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {COMMUTE_OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {METADATA_OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    print(
        "Route query status: "
        f"{sum(1 for row in commute_rows if row['query_status'] == 'success')} success, "
        f"{sum(1 for row in commute_rows if row['query_status'] != 'success')} failed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
