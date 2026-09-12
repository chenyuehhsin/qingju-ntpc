#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.transport.build_commute_to_gangqian import TDX_BASIC_BASE_URL, request_json  # noqa: E402
from scripts.transport.test_tdx_api import get_access_token, require_credentials  # noqa: E402


RAW_METRO_DIR = PROJECT_ROOT / "data" / "raw" / "transport" / "metro"
RAW_BIKE_DIR = PROJECT_ROOT / "data" / "raw" / "transport" / "bike"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "transport"
OUTPUTS_DIR = PROJECT_ROOT / "outputs" / "transport"
CATALOG_PATH = PROJECT_ROOT / "data" / "data_catalog.csv"

METRO_STATIONS_CSV = PROCESSED_DIR / "metro_stations.csv"
METRO_LINES_GEOJSON = PROCESSED_DIR / "metro_lines.geojson"
YOUBIKE_STATIONS_CSV = PROCESSED_DIR / "youbike_stations.csv"
METADATA_PATH = OUTPUTS_DIR / "housing_transport_layers_metadata.json"

CATALOG_COLUMNS = [
    "dataset_id",
    "filename",
    "original_filename",
    "category",
    "source_org",
    "source_url",
    "download_date",
    "data_period",
    "geographic_scope",
    "format",
    "description",
    "raw_or_derived",
    "notes",
]

METRO_ENDPOINTS = {
    "station": f"{TDX_BASIC_BASE_URL}/Rail/Metro/Station/TRTC",
    "line": f"{TDX_BASIC_BASE_URL}/Rail/Metro/Line/TRTC",
    "station_of_line": f"{TDX_BASIC_BASE_URL}/Rail/Metro/StationOfLine/TRTC",
    "shape": f"{TDX_BASIC_BASE_URL}/Rail/Metro/Shape/TRTC",
}
BIKE_ENDPOINTS = {
    "taipei": f"{TDX_BASIC_BASE_URL}/Bike/Station/City/Taipei",
    "new_taipei": f"{TDX_BASIC_BASE_URL}/Bike/Station/City/NewTaipei",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch TDX metro and YouBike static layers for Housing maps and build processed files."
    )
    parser.add_argument(
        "--download-date",
        default=date.today().isoformat(),
        help="Download date for filenames and catalog records in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Fetch new raw JSON even when a raw file for the same download date already exists.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=4,
        help="Maximum attempts per TDX endpoint, including the first attempt.",
    )
    return parser.parse_args()


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for version in range(2, 1000):
        candidate = path.with_name(f"{path.stem}_v{version}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find an unused filename for {path}")


def existing_raw_path(directory: Path, stem: str, download_date: str) -> Path | None:
    candidates = sorted(directory.glob(f"{stem}_{download_date}*.json"), key=lambda path: path.stat().st_mtime)
    return candidates[-1] if candidates else None


def write_raw_json(directory: Path, stem: str, records: Any, download_date: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = unique_path(directory / f"{stem}_{download_date}.json")
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def request_json_with_retries(url: str, access_token: str, max_retries: int) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return request_json(url, access_token, timeout=60)
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code != 429 or attempt == max_retries:
                raise
            retry_after = exc.headers.get("Retry-After")
            try:
                sleep_seconds = max(5.0, float(retry_after)) if retry_after else 8.0 * attempt
            except ValueError:
                sleep_seconds = 8.0 * attempt
            time.sleep(sleep_seconds)
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt == max_retries:
                raise
            time.sleep(4.0 * attempt)
    if last_error is not None:
        raise last_error
    raise RuntimeError("TDX request failed without an exception.")


def fetch_required(
    name: str,
    url: str,
    access_token: str,
    directory: Path,
    stem: str,
    download_date: str,
    refresh: bool,
    max_retries: int,
) -> tuple[Any, Path]:
    if not refresh:
        existing = existing_raw_path(directory, stem, download_date)
        if existing is not None:
            records = json.loads(existing.read_text(encoding="utf-8"))
            if not isinstance(records, list):
                raise RuntimeError(f"Existing raw file for {name} did not contain a JSON list: {relative(existing)}")
            return records, existing

    records = request_json_with_retries(url, access_token, max_retries)
    if not isinstance(records, list):
        raise RuntimeError(f"{name} endpoint did not return a JSON list.")
    path = write_raw_json(directory, stem, records, download_date)
    return records, path


def fetch_optional_shape(
    access_token: str,
    download_date: str,
    refresh: bool,
    max_retries: int,
) -> tuple[list[dict[str, Any]], Path | None, dict[str, str]]:
    url = METRO_ENDPOINTS["shape"]
    if not refresh:
        existing = existing_raw_path(RAW_METRO_DIR, "tdx_trtc_metro_shape", download_date)
        if existing is not None:
            records = json.loads(existing.read_text(encoding="utf-8"))
            if not isinstance(records, list):
                return [], None, {"status": "unavailable", "error": f"Existing Shape raw file is not a JSON list: {relative(existing)}"}
            return records, existing, {"status": "reused", "error": ""}
    try:
        records = request_json_with_retries(url, access_token, max_retries)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        return [], None, {"status": "unavailable", "error": f"HTTP {exc.code}: {body}"}
    except urllib.error.URLError as exc:
        return [], None, {"status": "unavailable", "error": f"network error: {exc.reason}"}
    if not isinstance(records, list):
        return [], None, {"status": "unavailable", "error": "Shape endpoint did not return a JSON list."}
    path = write_raw_json(RAW_METRO_DIR, "tdx_trtc_metro_shape", records, download_date)
    return records, path, {"status": "fetched", "error": ""}


def localized(record: dict[str, Any], key: str, locale: str) -> str:
    value = record.get(key, {})
    if isinstance(value, dict):
        return str(value.get(locale, "") or "").strip()
    return str(value or "").strip()


def nested_text(value: Any, locale: str) -> str:
    if isinstance(value, dict):
        return str(value.get(locale, "") or "").strip()
    return str(value or "").strip()


def position(record: dict[str, Any], key: str = "StationPosition") -> tuple[float | None, float | None]:
    value = record.get(key, {})
    if not isinstance(value, dict):
        return None, None
    lat = value.get("PositionLat")
    lon = value.get("PositionLon")
    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None, None


def build_station_line_lookup(station_of_line: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    lookup: dict[str, dict[str, list[str]]] = {}
    for line in station_of_line:
        line_id = str(line.get("LineID", "") or "").strip()
        line_name_zh = localized(line, "LineName", "Zh_tw")
        stations = line.get("Stations", [])
        if not isinstance(stations, list):
            continue
        for station in stations:
            if not isinstance(station, dict):
                continue
            station_uid = str(station.get("StationUID", "") or "").strip()
            station_id = str(station.get("StationID", "") or "").strip()
            for key in [station_uid, station_id]:
                if not key:
                    continue
                row = lookup.setdefault(key, {"line_ids": [], "line_names_zh": []})
                if line_id and line_id not in row["line_ids"]:
                    row["line_ids"].append(line_id)
                if line_name_zh and line_name_zh not in row["line_names_zh"]:
                    row["line_names_zh"].append(line_name_zh)
    return lookup


def write_metro_stations(
    stations: list[dict[str, Any]],
    station_of_line: list[dict[str, Any]],
    source_url: str,
) -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    lookup = build_station_line_lookup(station_of_line)
    fieldnames = [
        "station_uid",
        "station_id",
        "station_name_zh",
        "station_name_en",
        "line_ids",
        "line_names_zh",
        "location_city",
        "location_town",
        "lat",
        "lon",
        "station_address_zh",
        "station_address_en",
        "src_update_time",
        "tdx_update_time",
        "source_url",
    ]
    rows: list[dict[str, Any]] = []
    for record in stations:
        lat, lon = position(record)
        station_uid = str(record.get("StationUID", "") or "").strip()
        station_id = str(record.get("StationID", "") or "").strip()
        line_info = lookup.get(station_uid) or lookup.get(station_id) or {"line_ids": [], "line_names_zh": []}
        rows.append(
            {
                "station_uid": station_uid,
                "station_id": station_id,
                "station_name_zh": localized(record, "StationName", "Zh_tw"),
                "station_name_en": localized(record, "StationName", "En"),
                "line_ids": "|".join(line_info["line_ids"]),
                "line_names_zh": "|".join(line_info["line_names_zh"]),
                "location_city": record.get("LocationCity", ""),
                "location_town": record.get("LocationTown", ""),
                "lat": "" if lat is None else f"{lat:.8f}",
                "lon": "" if lon is None else f"{lon:.8f}",
                "station_address_zh": localized(record, "StationAddress", "Zh_tw"),
                "station_address_en": localized(record, "StationAddress", "En"),
                "src_update_time": record.get("SrcUpdateTime", ""),
                "tdx_update_time": record.get("UpdateTime", ""),
                "source_url": source_url,
            }
        )
    with METRO_STATIONS_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def parse_shape_geometry(record: dict[str, Any]) -> dict[str, Any] | None:
    for key in ["Geometry", "geometry"]:
        value = record.get(key)
        if isinstance(value, dict) and value.get("type") and "coordinates" in value:
            return value
        if isinstance(value, str) and value.strip():
            try:
                from shapely import wkt
                from shapely.geometry import mapping
            except ImportError as exc:
                raise RuntimeError("shapely is required to parse TDX Shape WKT geometry.") from exc
            return mapping(wkt.loads(value))
    return None


def line_key(record: dict[str, Any]) -> str:
    for key in ["LineID", "LineUID", "ShapeID", "ShapeUID"]:
        value = str(record.get(key, "") or "").strip()
        if value:
            return value
    return ""


def write_metro_lines(
    lines: list[dict[str, Any]],
    shapes: list[dict[str, Any]],
    line_source_url: str,
    shape_source_url: str,
    shape_status: dict[str, str],
) -> tuple[int, int, str]:
    line_lookup = {line_key(record): record for record in lines if line_key(record)}
    features: list[dict[str, Any]] = []
    parsed_geometry_count = 0

    if shapes:
        for shape in shapes:
            geometry = parse_shape_geometry(shape)
            if geometry is None:
                continue
            parsed_geometry_count += 1
            key = line_key(shape)
            line = line_lookup.get(key, {})
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": metro_line_properties(shape, line, line_source_url, shape_source_url, "shape_geometry"),
                }
            )

    if not features:
        for line in lines:
            features.append(
                {
                    "type": "Feature",
                    "geometry": None,
                    "properties": metro_line_properties(
                        line,
                        line,
                        line_source_url,
                        shape_source_url,
                        f"no_geometry_{shape_status['status']}",
                    ),
                }
            )

    geojson = {
        "type": "FeatureCollection",
        "name": "metro_lines",
        "metadata": {
            "shape_status": shape_status["status"],
            "shape_error": shape_status["error"],
            "note": "Geometry is sourced from TDX Shape/TRTC only when available; null geometries are not fabricated.",
        },
        "features": features,
    }
    METRO_LINES_GEOJSON.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(features), parsed_geometry_count, shape_status["status"]


def metro_line_properties(
    shape: dict[str, Any],
    line: dict[str, Any],
    line_source_url: str,
    shape_source_url: str,
    geometry_status: str,
) -> dict[str, Any]:
    line_name = line.get("LineName") if isinstance(line.get("LineName"), dict) else shape.get("LineName", {})
    return {
        "line_uid": shape.get("LineUID") or line.get("LineUID", ""),
        "line_id": shape.get("LineID") or line.get("LineID", ""),
        "line_name_zh": nested_text(line_name, "Zh_tw"),
        "line_name_en": nested_text(line_name, "En"),
        "shape_uid": shape.get("ShapeUID", ""),
        "shape_id": shape.get("ShapeID", ""),
        "line_color": line.get("LineColor", ""),
        "src_update_time": shape.get("SrcUpdateTime") or line.get("SrcUpdateTime", ""),
        "tdx_update_time": shape.get("UpdateTime") or line.get("UpdateTime", ""),
        "geometry_status": geometry_status,
        "line_source_url": line_source_url,
        "shape_source_url": shape_source_url,
    }


def write_youbike_stations(records_by_city: dict[str, list[dict[str, Any]]]) -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "city",
        "station_uid",
        "station_id",
        "station_name_zh",
        "station_name_en",
        "lat",
        "lon",
        "station_address_zh",
        "station_address_en",
        "bikes_capacity",
        "service_type",
        "src_update_time",
        "tdx_update_time",
        "source_url",
    ]
    rows: list[dict[str, Any]] = []
    for city, records in records_by_city.items():
        for record in records:
            lat, lon = position(record)
            rows.append(
                {
                    "city": city,
                    "station_uid": record.get("StationUID", ""),
                    "station_id": record.get("StationID", ""),
                    "station_name_zh": localized(record, "StationName", "Zh_tw"),
                    "station_name_en": localized(record, "StationName", "En"),
                    "lat": "" if lat is None else f"{lat:.8f}",
                    "lon": "" if lon is None else f"{lon:.8f}",
                    "station_address_zh": localized(record, "StationAddress", "Zh_tw"),
                    "station_address_en": localized(record, "StationAddress", "En"),
                    "bikes_capacity": record.get("BikesCapacity", ""),
                    "service_type": record.get("ServiceType", ""),
                    "src_update_time": record.get("SrcUpdateTime", ""),
                    "tdx_update_time": record.get("UpdateTime", ""),
                    "source_url": BIKE_ENDPOINTS[city],
                }
            )
    with YOUBIKE_STATIONS_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def relative(path: Path | None) -> str:
    if path is None:
        return ""
    return path.relative_to(PROJECT_ROOT).as_posix()


def read_catalog_records() -> list[dict[str, str]]:
    if not CATALOG_PATH.exists():
        return []
    with CATALOG_PATH.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != CATALOG_COLUMNS:
            raise RuntimeError(f"Unexpected data catalog columns: {reader.fieldnames}")
        return list(reader)


def write_catalog_records(records: list[dict[str, str]]) -> None:
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CATALOG_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CATALOG_COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def upsert_catalog(new_records: list[dict[str, str]]) -> None:
    existing = read_catalog_records()
    by_dataset_id = {record["dataset_id"]: record for record in existing}
    order = [record["dataset_id"] for record in existing]
    for record in new_records:
        if record["dataset_id"] not in by_dataset_id:
            order.append(record["dataset_id"])
        by_dataset_id[record["dataset_id"]] = record
    write_catalog_records([by_dataset_id[dataset_id] for dataset_id in order])


def catalog_record(
    path: Path,
    category: str,
    source_org: str,
    source_url: str,
    download_date: str,
    data_period: str,
    geographic_scope: str,
    file_format: str,
    description: str,
    raw_or_derived: str,
    notes: str,
) -> dict[str, str]:
    relative_path = relative(path)
    return {
        "dataset_id": path.stem,
        "filename": relative_path,
        "original_filename": "",
        "category": category,
        "source_org": source_org,
        "source_url": source_url,
        "download_date": download_date,
        "data_period": data_period,
        "geographic_scope": geographic_scope,
        "format": file_format,
        "description": description,
        "raw_or_derived": raw_or_derived,
        "notes": notes,
    }


def write_metadata(metadata: dict[str, Any]) -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    client_id, client_secret = require_credentials()
    access_token = get_access_token(client_id, client_secret)

    metro_station, metro_station_path = fetch_required(
        "Taipei Metro stations",
        METRO_ENDPOINTS["station"],
        access_token,
        RAW_METRO_DIR,
        "tdx_trtc_metro_station",
        args.download_date,
        args.refresh,
        args.max_retries,
    )
    metro_line, metro_line_path = fetch_required(
        "Taipei Metro lines",
        METRO_ENDPOINTS["line"],
        access_token,
        RAW_METRO_DIR,
        "tdx_trtc_metro_line",
        args.download_date,
        args.refresh,
        args.max_retries,
    )
    metro_station_of_line, metro_station_of_line_path = fetch_required(
        "Taipei Metro station-of-line",
        METRO_ENDPOINTS["station_of_line"],
        access_token,
        RAW_METRO_DIR,
        "tdx_trtc_metro_station_of_line",
        args.download_date,
        args.refresh,
        args.max_retries,
    )
    metro_shape, metro_shape_path, shape_status = fetch_optional_shape(
        access_token,
        args.download_date,
        args.refresh,
        args.max_retries,
    )

    bike_taipei, bike_taipei_path = fetch_required(
        "Taipei YouBike stations",
        BIKE_ENDPOINTS["taipei"],
        access_token,
        RAW_BIKE_DIR,
        "tdx_taipei_youbike_station",
        args.download_date,
        args.refresh,
        args.max_retries,
    )
    bike_new_taipei, bike_new_taipei_path = fetch_required(
        "New Taipei YouBike stations",
        BIKE_ENDPOINTS["new_taipei"],
        access_token,
        RAW_BIKE_DIR,
        "tdx_new_taipei_youbike_station",
        args.download_date,
        args.refresh,
        args.max_retries,
    )

    metro_station_count = write_metro_stations(metro_station, metro_station_of_line, METRO_ENDPOINTS["station"])
    metro_line_feature_count, metro_line_geometry_count, shape_result = write_metro_lines(
        metro_line,
        metro_shape,
        METRO_ENDPOINTS["line"],
        METRO_ENDPOINTS["shape"],
        shape_status,
    )
    youbike_count = write_youbike_stations({"taipei": bike_taipei, "new_taipei": bike_new_taipei})

    generated_at = datetime.now(timezone.utc).isoformat()
    metadata = {
        "generated_at_utc": generated_at,
        "download_date": args.download_date,
        "raw_files": {
            "metro_station": relative(metro_station_path),
            "metro_line": relative(metro_line_path),
            "metro_station_of_line": relative(metro_station_of_line_path),
            "metro_shape": relative(metro_shape_path),
            "youbike_taipei": relative(bike_taipei_path),
            "youbike_new_taipei": relative(bike_new_taipei_path),
        },
        "processed_files": {
            "metro_stations": relative(METRO_STATIONS_CSV),
            "metro_lines": relative(METRO_LINES_GEOJSON),
            "youbike_stations": relative(YOUBIKE_STATIONS_CSV),
        },
        "api_counts": {
            "metro_station": len(metro_station),
            "metro_line": len(metro_line),
            "metro_station_of_line": len(metro_station_of_line),
            "metro_shape": len(metro_shape),
            "youbike_taipei": len(bike_taipei),
            "youbike_new_taipei": len(bike_new_taipei),
        },
        "processed_counts": {
            "metro_stations": metro_station_count,
            "metro_line_features": metro_line_feature_count,
            "metro_line_features_with_geometry": metro_line_geometry_count,
            "youbike_stations": youbike_count,
        },
        "shape_status": shape_status,
        "notes": [
            "YouBike station endpoint only is fetched; real-time availability endpoints are intentionally not queried.",
            "Metro route geometry is included only when TDX Shape/TRTC returns parseable geometry.",
        ],
    }
    write_metadata(metadata)

    catalog_records = [
        catalog_record(
            metro_station_path,
            "transport",
            "TDX Transport Data eXchange",
            METRO_ENDPOINTS["station"],
            args.download_date,
            f"TDX API snapshot requested on {args.download_date}",
            "Taipei City and New Taipei City",
            "json",
            "Raw Taipei Metro TRTC station records from TDX.",
            "raw",
            "Generated by scripts/transport/build_housing_transport_layers.py; raw contents must not be edited in place.",
        ),
        catalog_record(
            metro_line_path,
            "transport",
            "TDX Transport Data eXchange",
            METRO_ENDPOINTS["line"],
            args.download_date,
            f"TDX API snapshot requested on {args.download_date}",
            "Taipei City and New Taipei City",
            "json",
            "Raw Taipei Metro TRTC line records from TDX.",
            "raw",
            "Generated by scripts/transport/build_housing_transport_layers.py; raw contents must not be edited in place.",
        ),
        catalog_record(
            metro_station_of_line_path,
            "transport",
            "TDX Transport Data eXchange",
            METRO_ENDPOINTS["station_of_line"],
            args.download_date,
            f"TDX API snapshot requested on {args.download_date}",
            "Taipei City and New Taipei City",
            "json",
            "Raw Taipei Metro TRTC station-of-line records from TDX.",
            "raw",
            "Generated by scripts/transport/build_housing_transport_layers.py; raw contents must not be edited in place.",
        ),
        catalog_record(
            bike_taipei_path,
            "transport",
            "TDX Transport Data eXchange",
            BIKE_ENDPOINTS["taipei"],
            args.download_date,
            f"TDX API snapshot requested on {args.download_date}",
            "Taipei City",
            "json",
            "Raw Taipei YouBike station records from TDX static station endpoint.",
            "raw",
            "Generated by scripts/transport/build_housing_transport_layers.py; real-time availability is intentionally not fetched.",
        ),
        catalog_record(
            bike_new_taipei_path,
            "transport",
            "TDX Transport Data eXchange",
            BIKE_ENDPOINTS["new_taipei"],
            args.download_date,
            f"TDX API snapshot requested on {args.download_date}",
            "New Taipei City",
            "json",
            "Raw New Taipei YouBike station records from TDX static station endpoint.",
            "raw",
            "Generated by scripts/transport/build_housing_transport_layers.py; real-time availability is intentionally not fetched.",
        ),
        catalog_record(
            METRO_STATIONS_CSV,
            "transport",
            "Derived from TDX Transport Data eXchange",
            "; ".join([METRO_ENDPOINTS["station"], METRO_ENDPOINTS["station_of_line"]]),
            args.download_date,
            f"TDX API snapshot requested on {args.download_date}",
            "Taipei City and New Taipei City",
            "csv",
            "Processed Taipei Metro TRTC station table with coordinates and line memberships.",
            "derived",
            f"Generated by scripts/transport/build_housing_transport_layers.py from {relative(metro_station_path)} and {relative(metro_station_of_line_path)}.",
        ),
        catalog_record(
            METRO_LINES_GEOJSON,
            "transport",
            "Derived from TDX Transport Data eXchange",
            "; ".join([METRO_ENDPOINTS["line"], METRO_ENDPOINTS["shape"]]),
            args.download_date,
            f"TDX API snapshot requested on {args.download_date}",
            "Taipei City and New Taipei City",
            "geojson",
            "Processed Taipei Metro TRTC line GeoJSON; geometry is included only when TDX Shape is available.",
            "derived",
            f"Generated by scripts/transport/build_housing_transport_layers.py; Shape status: {shape_result}.",
        ),
        catalog_record(
            YOUBIKE_STATIONS_CSV,
            "transport",
            "Derived from TDX Transport Data eXchange",
            "; ".join([BIKE_ENDPOINTS["taipei"], BIKE_ENDPOINTS["new_taipei"]]),
            args.download_date,
            f"TDX API snapshot requested on {args.download_date}",
            "Taipei City and New Taipei City",
            "csv",
            "Processed YouBike station table for Taipei and New Taipei static stations.",
            "derived",
            "Generated by scripts/transport/build_housing_transport_layers.py; does not include real-time availability.",
        ),
    ]
    if metro_shape_path is not None:
        catalog_records.append(
            catalog_record(
                metro_shape_path,
                "transport",
                "TDX Transport Data eXchange",
                METRO_ENDPOINTS["shape"],
                args.download_date,
                f"TDX API snapshot requested on {args.download_date}",
                "Taipei City and New Taipei City",
                "json",
                "Raw Taipei Metro TRTC shape records from TDX.",
                "raw",
                "Generated by scripts/transport/build_housing_transport_layers.py; raw contents must not be edited in place.",
            )
        )
    upsert_catalog(catalog_records)

    print("TDX Housing transport layer fetch complete.")
    print(f"metro_station_api_records={len(metro_station)}")
    print(f"metro_line_api_records={len(metro_line)}")
    print(f"metro_station_of_line_api_records={len(metro_station_of_line)}")
    print(f"metro_shape_api_records={len(metro_shape)}")
    print(f"metro_shape_status={shape_status['status']}")
    if shape_status["error"]:
        print(f"metro_shape_error={shape_status['error']}")
    print(f"youbike_taipei_api_records={len(bike_taipei)}")
    print(f"youbike_new_taipei_api_records={len(bike_new_taipei)}")
    print(f"processed_metro_stations={metro_station_count}")
    print(f"processed_metro_line_features={metro_line_feature_count}")
    print(f"processed_metro_line_features_with_geometry={metro_line_geometry_count}")
    print(f"processed_youbike_stations={youbike_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
