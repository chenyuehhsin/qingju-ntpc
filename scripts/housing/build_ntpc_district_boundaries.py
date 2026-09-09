#!/usr/bin/env python3
"""Build a Git-trackable New Taipei 29-district GeoJSON from NLSC boundaries."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "housing" / "boundaries"
ZIP_PATH = INTERIM_DIR / "nlsc_town_boundary_twd97.zip"
EXTRACT_DIR = INTERIM_DIR / "nlsc_town_boundary_twd97"
SHAPEFILE_STEM = "TOWN_MOI_1120317"
SHAPEFILE_PATH = EXTRACT_DIR / f"{SHAPEFILE_STEM}.shp"
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "geography" / "ntpc_district_boundaries.geojson"
METADATA_PATH = PROJECT_ROOT / "outputs" / "geography" / "ntpc_district_boundaries_metadata.json"
DATA_CATALOG = PROJECT_ROOT / "data" / "data_catalog.csv"

SOURCE_URL = "https://maps.nlsc.gov.tw/download/%E9%84%89%E9%8E%AE%E5%B8%82%E5%8D%80%E7%95%8C%E7%B7%9A(TWD97%E7%B6%93%E7%B7%AF%E5%BA%A6).zip"
SOURCE_ORG = "National Land Surveying and Mapping Center / Ministry of the Interior"
SOURCE_DATE = "2023-03-17"
SOURCE_CRS = "EPSG:3824"
OUTPUT_CRS = "EPSG:4326"
COUNTY_NAME = "新北市"
REQUIRED_SIDECARS = (".shp", ".shx", ".dbf", ".prj")
EXPECTED_DISTRICTS = frozenset(
    {
        "板橋區", "三重區", "中和區", "永和區", "新莊區", "新店區", "樹林區", "鶯歌區", "三峽區", "淡水區",
        "汐止區", "瑞芳區", "土城區", "蘆洲區", "五股區", "泰山區", "林口區", "深坑區", "石碇區", "坪林區",
        "三芝區", "石門區", "八里區", "平溪區", "雙溪區", "貢寮區", "金山區", "萬里區", "烏來區",
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-download", action="store_true", help="Require an existing raw ZIP instead of downloading it.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_raw_zip(skip_download=args.skip_download)
    ensure_shapefile_components()
    build_geojson()
    metadata = validate_and_describe_geojson()
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    register_processed_dataset()
    print(json.dumps(metadata["validation"], ensure_ascii=False, indent=2))


def ensure_raw_zip(skip_download: bool) -> None:
    if ZIP_PATH.exists():
        if ZIP_PATH.stat().st_size == 0 or not zipfile.is_zipfile(ZIP_PATH):
            raise RuntimeError(f"Existing raw ZIP is empty or invalid: {ZIP_PATH}")
        return
    if skip_download:
        raise FileNotFoundError(f"Raw boundary ZIP is missing: {ZIP_PATH}")
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    request = Request(SOURCE_URL, headers={"User-Agent": "qingju-ntpc-boundary-pipeline/1.0"})
    try:
        with urlopen(request, timeout=120) as response:
            payload = response.read()
        if not payload:
            raise RuntimeError("NLSC boundary download returned an empty response")
        ZIP_PATH.write_bytes(payload)
    except URLError:
        temporary_path = ZIP_PATH.with_suffix(".download")
        run_command(
            [
                "curl",
                "--fail",
                "--location",
                "--silent",
                "--show-error",
                "--max-time",
                "120",
                "--output",
                str(temporary_path),
                SOURCE_URL,
            ]
        )
        temporary_path.replace(ZIP_PATH)
    if not zipfile.is_zipfile(ZIP_PATH):
        raise RuntimeError(f"Downloaded file is not a valid ZIP: {ZIP_PATH}")


def ensure_shapefile_components() -> None:
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH) as archive:
        members = {Path(member).name: member for member in archive.namelist() if not member.endswith("/")}
        missing = [f"{SHAPEFILE_STEM}{suffix}" for suffix in REQUIRED_SIDECARS if f"{SHAPEFILE_STEM}{suffix}" not in members]
        if missing:
            raise RuntimeError(f"NLSC ZIP is missing required shapefile components: {missing}")
        for suffix in (*REQUIRED_SIDECARS, ".cpg"):
            name = f"{SHAPEFILE_STEM}{suffix}"
            member = members.get(name)
            if member is None:
                continue
            destination = EXTRACT_DIR / name
            content = archive.read(member)
            if destination.exists() and destination.read_bytes() != content:
                raise RuntimeError(f"Refusing to replace existing extracted boundary component: {destination}")
            if not destination.exists():
                destination.write_bytes(content)
    missing_after_extract = [path.name for path in shapefile_component_paths() if not path.exists()]
    if missing_after_extract:
        raise RuntimeError(f"Extracted boundary is incomplete: {missing_after_extract}")


def shapefile_component_paths() -> list[Path]:
    return [EXTRACT_DIR / f"{SHAPEFILE_STEM}{suffix}" for suffix in REQUIRED_SIDECARS]


def build_geojson() -> None:
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            "ogr2ogr",
            "-f",
            "GeoJSON",
            "-t_srs",
            OUTPUT_CRS,
            "-where",
            f"COUNTYNAME = '{COUNTY_NAME}'",
            "-lco",
            "RFC7946=YES",
            str(PROCESSED_PATH),
            str(SHAPEFILE_PATH),
        ]
    )


def validate_and_describe_geojson() -> dict[str, Any]:
    payload = json.loads(PROCESSED_PATH.read_text(encoding="utf-8"))
    features = payload.get("features")
    if payload.get("type") != "FeatureCollection" or not isinstance(features, list):
        raise RuntimeError("Processed boundary output is not a GeoJSON FeatureCollection")
    districts: list[dict[str, str | None]] = []
    names: list[str] = []
    for feature in features:
        properties = feature.get("properties") or {}
        name = str(properties.get("TOWNNAME", "")).strip()
        if not name or feature.get("geometry") is None:
            raise RuntimeError("Boundary feature is missing TOWNNAME or geometry")
        names.append(name)
        districts.append({"district": name, "code": district_code(properties)})
    district_set = set(names)
    missing, unexpected = sorted(EXPECTED_DISTRICTS - district_set), sorted(district_set - EXPECTED_DISTRICTS)
    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    if len(features) != 29 or missing or unexpected or duplicate_names:
        raise RuntimeError(
            "New Taipei district validation failed: "
            f"features={len(features)}, missing={missing}, unexpected={unexpected}, duplicates={duplicate_names}"
        )
    if any(item["code"] is None for item in districts):
        raise RuntimeError("Processed boundary output has no recognized district code field")
    return {
        "pipeline": str(Path(__file__).relative_to(PROJECT_ROOT)),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": {
            "organization": SOURCE_ORG,
            "source_url": SOURCE_URL,
            "source_date": SOURCE_DATE,
            "source_crs": SOURCE_CRS,
            "raw_zip": str(ZIP_PATH.relative_to(PROJECT_ROOT)),
            "raw_zip_sha256": sha256(ZIP_PATH),
            "shapefile": str(SHAPEFILE_PATH.relative_to(PROJECT_ROOT)),
            "required_components": [path.name for path in shapefile_component_paths()],
        },
        "output": {
            "path": str(PROCESSED_PATH.relative_to(PROJECT_ROOT)),
            "crs": OUTPUT_CRS,
            "size_bytes": PROCESSED_PATH.stat().st_size,
            "sha256": sha256(PROCESSED_PATH),
        },
        "validation": {
            "feature_count": len(features),
            "district_count": len(district_set),
            "district_names": sorted(names),
            "districts": sorted(districts, key=lambda item: str(item["district"])),
            "duplicate_district_names": duplicate_names,
            "missing_districts": missing,
            "unexpected_districts": unexpected,
            "all_29_districts_present": True,
        },
    }


def district_code(properties: dict[str, Any]) -> str | None:
    for field in ("TOWNID", "TOWNCODE", "TOWN_CODE", "TOWN_NO"):
        value = properties.get(field)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def run_command(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{completed.stderr.strip()}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def register_processed_dataset() -> None:
    dataset_id = "ntpc_district_boundaries_geojson_2023-03-17"
    existing = DATA_CATALOG.read_text(encoding="utf-8-sig")
    if any(line.startswith(f"{dataset_id},") for line in existing.splitlines()):
        return
    row = [
        dataset_id,
        str(PROCESSED_PATH.relative_to(PROJECT_ROOT)),
        "",
        "geography",
        f"Derived from {SOURCE_ORG}",
        SOURCE_URL,
        date.today().isoformat(),
        SOURCE_DATE,
        "New Taipei City 29 districts",
        "geojson",
        "New Taipei City district boundaries reprojected from the official NLSC/MOI township boundary shapefile.",
        "derived",
        "Generated by scripts/housing/build_ntpc_district_boundaries.py; validates 29 unique districts and preserves source district codes in GeoJSON properties.",
    ]
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerow(row)
    with DATA_CATALOG.open("a", encoding="utf-8", newline="") as handle:
        if existing and not existing.endswith(("\n", "\r")):
            handle.write("\n")
        handle.write(buffer.getvalue())


if __name__ == "__main__":
    main()
