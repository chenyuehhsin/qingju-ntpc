#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.transport.build_commute_to_gangqian import (
    DEPARTURE_TIME,
    DESTINATION,
    RESPONSE_DIR,
    ROUTING_PARAMS,
    TDX_BASIC_BASE_URL,
    TDX_MAAS_ROUTING_URL,
    build_commute_rows,
    find_station,
    request_json,
    station_row,
)
from scripts.transport.test_tdx_api import get_access_token, require_credentials


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "transport"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "transport"
OUTPUTS_DIR = PROJECT_ROOT / "outputs" / "transport"
STATION_CACHE_DIR = INTERIM_DIR / "tdx_station_data"

CANDIDATE_LOCATIONS_PATH = PROCESSED_DIR / "candidate_locations_expanded.csv"
COMMUTE_OUTPUT_PATH = PROCESSED_DIR / "commute_to_gangqian_expanded.csv"
METADATA_OUTPUT_PATH = OUTPUTS_DIR / "commute_to_gangqian_expanded_metadata.json"

STATION_ENDPOINTS = {
    "TRTC": f"{TDX_BASIC_BASE_URL}/Rail/Metro/Station/TRTC",
    "TRA": f"{TDX_BASIC_BASE_URL}/Rail/TRA/Station",
    "TYMC": f"{TDX_BASIC_BASE_URL}/Rail/Metro/Station/TYMC",
    "NWT_BUS_STATION": f"{TDX_BASIC_BASE_URL}/Bus/Station/City/NewTaipei",
}

CANDIDATES = [
    {
        "candidate_name": "汐止車站",
        "district": "汐止區",
        "station_name": "汐止",
        "operator_id": "TRA",
        "slug": "xizhi_station",
        "selection_reason": "TRA station anchoring Xizhi's main rail commute corridor.",
    },
    {
        "candidate_name": "頂溪站",
        "district": "永和區",
        "station_name": "頂溪",
        "operator_id": "TRTC",
        "slug": "dingxi_station",
        "selection_reason": "Central Yonghe MRT station on the Zhonghe-Xinlu line.",
    },
    {
        "candidate_name": "景安站",
        "district": "中和區",
        "station_name": "景安",
        "operator_id": "TRTC",
        "slug": "jingan_station",
        "selection_reason": "Major Zhonghe interchange area with MRT access.",
    },
    {
        "candidate_name": "大坪林站",
        "district": "新店區",
        "station_name": "大坪林",
        "operator_id": "TRTC",
        "slug": "dapinglin_station",
        "selection_reason": "Representative Xindian MRT station with direct urban access.",
    },
    {
        "candidate_name": "板橋站",
        "district": "板橋區",
        "station_name": "板橋",
        "operator_id": "TRTC",
        "slug": "banqiao_station",
        "selection_reason": "Primary Banqiao multimodal hub represented by its MRT station coordinate.",
    },
    {
        "candidate_name": "三重站",
        "district": "三重區",
        "station_name": "三重",
        "operator_id": "TRTC",
        "slug": "sanchong_station",
        "selection_reason": "Representative Sanchong MRT station on the Zhonghe-Xinlu line.",
    },
    {
        "candidate_name": "新莊站",
        "district": "新莊區",
        "station_name": "新莊",
        "operator_id": "TRTC",
        "slug": "xinzhuang_station",
        "selection_reason": "Established MRT node in the older Xinzhuang urban core.",
    },
    {
        "candidate_name": "蘆洲站",
        "district": "蘆洲區",
        "station_name": "蘆洲",
        "operator_id": "TRTC",
        "slug": "luzhou_station",
        "selection_reason": "Terminal MRT node and representative Luzhou transit anchor.",
    },
    {
        "candidate_name": "土城站",
        "district": "土城區",
        "station_name": "土城",
        "operator_id": "TRTC",
        "slug": "tucheng_station",
        "selection_reason": "MRT station named for and located in Tucheng, suitable as the district's transit anchor.",
    },
    {
        "candidate_name": "泰山站",
        "district": "泰山區",
        "station_name": "泰山站",
        "operator_id": "TYMC",
        "slug": "taishan_station",
        "selection_reason": "Taoyuan Airport MRT A5 station in Taishan, the clearest rail node for the district.",
    },
    {
        "candidate_name": "林口站",
        "district": "林口區",
        "station_name": "林口站",
        "operator_id": "TYMC",
        "slug": "linkou_station",
        "selection_reason": "Taoyuan Airport MRT A9 station and the main rail node for Linkou new town.",
    },
    {
        "candidate_name": "淡水站",
        "district": "淡水區",
        "station_name": "淡水",
        "operator_id": "TRTC",
        "slug": "tamsui_station",
        "selection_reason": "Terminal MRT station and highest-recognition Tamsui transit node.",
    },
    {
        "candidate_name": "三峽北大特區",
        "district": "三峽區",
        "station_name": "臺北大學正門",
        "operator_id": "NWT_BUS_STATION",
        "station_uid": "NWT3282",
        "slug": "sanxia_ntpu_main_gate",
        "selection_reason": "TDX bus station at NTPU main gate, representing the dense Sanxia Beida residential area with many bus routes.",
    },
    {
        "candidate_name": "樹林車站",
        "district": "樹林區",
        "station_name": "樹林",
        "operator_id": "TRA",
        "slug": "shulin_station",
        "selection_reason": "TRA station and main rail anchor for Shulin.",
    },
    {
        "candidate_name": "五股區公所",
        "district": "五股區",
        "station_name": "五股區公所(五股公有市場)",
        "operator_id": "NWT_BUS_STATION",
        "station_uid": "NWT74479",
        "slug": "wugu_district_office",
        "selection_reason": "TDX bus station at Wugu District Office / public market, representing the district center.",
    },
    {
        "candidate_name": "鶯歌車站",
        "district": "鶯歌區",
        "station_name": "鶯歌",
        "operator_id": "TRA",
        "slug": "yingge_station",
        "selection_reason": "TRA station and main rail anchor for Yingge.",
    },
]


def fetch_station_data(access_token: str) -> dict[str, list[dict[str, Any]]]:
    STATION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    station_data: dict[str, list[dict[str, Any]]] = {}
    for operator_id, url in STATION_ENDPOINTS.items():
        cache_path = STATION_CACHE_DIR / f"{operator_id.lower()}_stations.json"
        if cache_path.exists():
            records = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            records = request_json(url, access_token, timeout=60)
            cache_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        if not isinstance(records, list):
            raise RuntimeError(f"Station endpoint for {operator_id} did not return a list.")
        station_data[operator_id] = records
    return station_data


def find_bus_station(
    station_data: dict[str, list[dict[str, Any]]],
    station_uid: str,
) -> dict[str, Any]:
    matches = [
        record
        for record in station_data["NWT_BUS_STATION"]
        if str(record.get("StationUID", "")) == station_uid
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one New Taipei bus station UID {station_uid}, found {len(matches)}.")
    return matches[0]


def bus_station_name_zh(record: dict[str, Any]) -> str:
    name = record.get("StationName", {})
    return str(name.get("Zh_tw", "")).strip() if isinstance(name, dict) else ""


def bus_station_row(
    station_data: dict[str, list[dict[str, Any]]],
    item: dict[str, str],
) -> dict[str, Any]:
    record = find_bus_station(station_data, item["station_uid"])
    position = record.get("StationPosition", {})
    lat = position.get("PositionLat") if isinstance(position, dict) else None
    lon = position.get("PositionLon") if isinstance(position, dict) else None
    if lat is None or lon is None:
        raise RuntimeError(f"Bus station {item['station_name']} does not include lat/lon.")
    record_name = bus_station_name_zh(record)
    if record_name != item["station_name"]:
        raise RuntimeError(
            f"Bus station UID {item['station_uid']} expected {item['station_name']}, found {record_name}."
        )
    return {
        "candidate_name": item["candidate_name"],
        "district": item["district"],
        "station_name": record_name,
        "station_operator": item["operator_id"],
        "station_uid": record.get("StationUID", ""),
        "station_id": record.get("StationID", ""),
        "lat": lat,
        "lon": lon,
        "source_endpoint": STATION_ENDPOINTS[item["operator_id"]],
        "source_update_time": "",
        "tdx_update_time": record.get("UpdateTime", ""),
        "selection_reason": item["selection_reason"],
        "route_count_at_station": len(record.get("Stops", [])),
    }


def rail_station_row(
    station_data: dict[str, list[dict[str, Any]]],
    item: dict[str, str],
) -> dict[str, Any]:
    record = find_station(station_data, item["station_name"], item["operator_id"])
    position = record.get("StationPosition", {})
    lat = position.get("PositionLat") if isinstance(position, dict) else None
    lon = position.get("PositionLon") if isinstance(position, dict) else None
    if lat is None or lon is None:
        raise RuntimeError(f"Station {item['station_name']} does not include lat/lon.")
    row = {
        "candidate_name": item["candidate_name"],
        "district": record.get("LocationTown", ""),
        "station_name": item["station_name"],
        "station_operator": item["operator_id"],
        "station_uid": record.get("StationUID", ""),
        "station_id": record.get("StationID", ""),
        "lat": lat,
        "lon": lon,
        "source_endpoint": STATION_ENDPOINTS[item["operator_id"]],
        "source_update_time": record.get("SrcUpdateTime", ""),
        "tdx_update_time": record.get("UpdateTime", ""),
    }
    if row["district"] != item["district"]:
        raise RuntimeError(
            f"{item['candidate_name']} district mismatch: expected {item['district']}, found {row['district']}."
        )
    row["selection_reason"] = item["selection_reason"]
    row["route_count_at_station"] = ""
    return row


def candidate_row(
    station_data: dict[str, list[dict[str, Any]]],
    item: dict[str, str],
) -> dict[str, Any]:
    if item["operator_id"] == "NWT_BUS_STATION":
        return bus_station_row(station_data, item)
    return rail_station_row(station_data, item)


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
        "selection_reason",
        "route_count_at_station",
    ]
    with CANDIDATE_LOCATIONS_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def safe_response_filename(candidate_name: str) -> str:
    slug_by_name = {item["candidate_name"]: item["slug"] for item in CANDIDATES}
    return f"{slug_by_name[candidate_name]}_to_gangqian.json"


def build_expanded_commute_rows(
    access_token: str,
    candidate_rows: list[dict[str, Any]],
    destination_row: dict[str, Any],
) -> list[dict[str, Any]]:
    original_safe_response_filename = build_commute_rows.__globals__["safe_response_filename"]
    build_commute_rows.__globals__["safe_response_filename"] = safe_response_filename
    try:
        return build_commute_rows(access_token, candidate_rows, destination_row)
    finally:
        build_commute_rows.__globals__["safe_response_filename"] = original_safe_response_filename


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
        "candidate_selection": [
            {
                "candidate_name": item["candidate_name"],
                "district": item["district"],
                "station_name": item["station_name"],
                "operator_id": item["operator_id"],
                "selection_reason": item["selection_reason"],
            }
            for item in CANDIDATES
        ],
    }
    METADATA_OUTPUT_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    client_id, client_secret = require_credentials()
    access_token = get_access_token(client_id, client_secret)

    station_data = fetch_station_data(access_token)
    candidate_rows = [candidate_row(station_data, item) for item in CANDIDATES]
    destination_row = station_row(
        station_data,
        {
            "candidate_name": DESTINATION["candidate_name"],
            "station_name": DESTINATION["station_name"],
            "operator_id": DESTINATION["operator_id"],
        },
    )

    write_candidate_locations(candidate_rows)
    commute_rows = build_expanded_commute_rows(access_token, candidate_rows, destination_row)
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
