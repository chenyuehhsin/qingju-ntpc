#!/usr/bin/env python3
"""Build exact New Taipei 18--35 population statistics from RIS ODRP014."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "population"
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "population" / "ntpc_district_youth_18_35.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "population"
METADATA_PATH = OUTPUT_DIR / "ntpc_district_youth_18_35_metadata.json"
VILLAGE_MAPPING_PATH = OUTPUT_DIR / "ntpc_village_to_district_mapping.csv"
DATA_CATALOG = PROJECT_ROOT / "data" / "data_catalog.csv"

API_TEMPLATE = "https://www.ris.gov.tw/rs-opendata/api/v1/datastore/ODRP014/{yyyymm}"
COUNTY = "新北市"
SOURCE_ORG = "Ministry of the Interior Department of Household Registration"
YOUTH_AGES = range(18, 36)
DISTRICT_PATTERN = re.compile(r"^新北市(?P<district>.+區)$")
EXPECTED_DISTRICTS = frozenset(
    {
        "板橋區", "三重區", "中和區", "永和區", "新莊區", "新店區", "樹林區", "鶯歌區", "三峽區", "淡水區",
        "汐止區", "瑞芳區", "土城區", "蘆洲區", "五股區", "泰山區", "林口區", "深坑區", "石碇區", "坪林區",
        "三芝區", "石門區", "八里區", "平溪區", "雙溪區", "貢寮區", "金山區", "萬里區", "烏來區",
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yyyymm", help="ROC year/month, e.g. 11507. Defaults to latest available month.")
    parser.add_argument("--as-of-date", default=date.today().isoformat(), help="Detection start date in YYYY-MM-DD.")
    parser.add_argument("--lookback-months", type=int, default=24)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_month = parse_source_month(args.yyyymm) if args.yyyymm else find_latest_month(args.as_of_date, args.lookback_months)
    responses = fetch_all_pages(source_month)
    records, response_qa = validate_response_completeness(responses, source_month)
    rows, village_rows, aggregation_qa = aggregate(records, source_month)
    write_csv(PROCESSED_PATH, rows, processed_fieldnames())
    write_csv(VILLAGE_MAPPING_PATH, village_rows, village_mapping_fieldnames())
    raw_paths = write_raw_responses(source_month, responses)
    metadata = build_metadata(source_month, responses, raw_paths, response_qa, aggregation_qa, rows, village_rows)
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_catalog(source_month, raw_paths)
    print(json.dumps(metadata["qa"], ensure_ascii=False, indent=2))


def parse_source_month(value: str) -> tuple[str, int, int, int]:
    if not re.fullmatch(r"\d{5}", value):
        raise ValueError("yyyymm must be a five-digit ROC year/month, e.g. 11507")
    roc_year, month = int(value[:3]), int(value[3:])
    if not 1 <= month <= 12:
        raise ValueError("month must be between 01 and 12")
    return value, roc_year, roc_year + 1911, month


def find_latest_month(as_of_date: str, lookback_months: int) -> tuple[str, int, int, int]:
    cursor = datetime.strptime(as_of_date, "%Y-%m-%d").date().replace(day=1)
    for _ in range(lookback_months):
        source_month = (f"{cursor.year - 1911:03d}{cursor.month:02d}", cursor.year - 1911, cursor.year, cursor.month)
        response = fetch_page(source_month[0], 1)
        if is_success(response):
            return source_month
        cursor = previous_month(cursor)
    raise RuntimeError(f"No complete ODRP014 data found within {lookback_months} months")


def previous_month(value: date) -> date:
    return date(value.year - 1, 12, 1) if value.month == 1 else date(value.year, value.month - 1, 1)


def source_url(yyyymm: str, page: int | None = None) -> str:
    parameters: dict[str, str | int] = {"COUNTY": COUNTY}
    if page is not None:
        parameters["page"] = page
    return f"{API_TEMPLATE.format(yyyymm=yyyymm)}?{urlencode(parameters)}"


def fetch_page(yyyymm: str, page: int) -> dict[str, Any]:
    request = Request(source_url(yyyymm, page), headers={"User-Agent": "qingju-ntpc-population-pipeline/1.0"})
    try:
        with urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"ODRP014 request failed for {yyyymm} page {page}: {exc}") from exc


def fetch_all_pages(source_month: tuple[str, int, int, int]) -> list[dict[str, Any]]:
    first = fetch_page(source_month[0], 1)
    if not is_success(first):
        raise RuntimeError(f"ODRP014 returned no usable data for {source_month[0]}: {first.get('responseMessage')}")
    total_pages = positive_int(first.get("totalPage"), "totalPage")
    return [first, *(fetch_page(source_month[0], page) for page in range(2, total_pages + 1))]


def is_success(response: dict[str, Any]) -> bool:
    return response.get("responseCode") == "OD-0101-S" and isinstance(response.get("responseData"), list)


def validate_response_completeness(
    responses: list[dict[str, Any]], source_month: tuple[str, int, int, int]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected_pages = positive_int(responses[0].get("totalPage"), "totalPage")
    if len(responses) != expected_pages:
        raise RuntimeError(f"Retrieved {len(responses)} pages but API declared {expected_pages}")
    required_fields = {"statistic_yyymm", "district_code", "site_id", "village", "people_total"}
    required_fields.update(f"people_age_{age:03d}_{sex}" for age in YOUTH_AGES for sex in ("m", "f"))
    records: list[dict[str, Any]] = []
    page_details: list[dict[str, Any]] = []
    for expected_page, response in enumerate(responses, start=1):
        if not is_success(response):
            raise RuntimeError(f"API page {expected_page} did not return a success response")
        if positive_int(response.get("page"), "page") != expected_page:
            raise RuntimeError(f"Expected API page {expected_page}, received {response.get('page')!r}")
        if positive_int(response.get("totalPage"), "totalPage") != expected_pages:
            raise RuntimeError("API totalPage changed during pagination")
        page_records = response["responseData"]
        declared_size = positive_int(response.get("pageDataSize"), "pageDataSize")
        if len(page_records) != declared_size:
            raise RuntimeError(f"Page {expected_page} has {len(page_records)} records but declares {declared_size}")
        for record in page_records:
            if not isinstance(record, dict):
                raise RuntimeError(f"Page {expected_page} contains a non-object record")
            missing = required_fields - record.keys()
            if missing:
                raise RuntimeError(f"Page {expected_page} missing required fields: {sorted(missing)}")
            if str(record["statistic_yyymm"]) != source_month[0]:
                raise RuntimeError(f"Unexpected statistic_yyymm {record['statistic_yyymm']!r}")
        records.extend(page_records)
        page_details.append({"page": expected_page, "page_data_size": declared_size, "url": source_url(source_month[0], expected_page)})
    return records, {
        "api_declared_total_pages": expected_pages,
        "api_declared_total_data_size": responses[0].get("totalDataSize"),
        "retrieved_page_count": len(responses),
        "retrieved_record_count": len(records),
        "retrieved_record_count_equals_page_data_sizes": len(records) == sum(item["page_data_size"] for item in page_details),
        "api_total_data_size_note": "ODRP014 returns the national totalDataSize even with COUNTY filtering; page count and pageDataSize are the response-completeness checks.",
        "pages": page_details,
        "required_schema_fields_present": True,
    }


def aggregate(
    records: list[dict[str, Any]], source_month: tuple[str, int, int, int]
) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"village_count": 0, "total_population": 0, "youth": 0, "male": 0, "female": 0})
    village_rows: list[dict[str, str]] = []
    village_ids: set[str] = set()
    district_codes: dict[str, set[str]] = defaultdict(set)
    source_youth_total = 0
    source_population_total = 0
    for record in records:
        district = district_from_site_id(str(record["site_id"]))
        if district not in EXPECTED_DISTRICTS:
            raise RuntimeError(f"Unexpected New Taipei district in source: {district!r}")
        village_id = str(record["district_code"]).strip()
        if not village_id:
            raise RuntimeError("Blank district_code in source")
        if village_id in village_ids:
            raise RuntimeError(f"Duplicate village district_code in source: {village_id}")
        village_ids.add(village_id)
        total_population = nonnegative_int(record["people_total"], f"people_total for {village_id}")
        male = sum(nonnegative_int(record[f"people_age_{age:03d}_m"], f"age {age} male for {village_id}") for age in YOUTH_AGES)
        female = sum(nonnegative_int(record[f"people_age_{age:03d}_f"], f"age {age} female for {village_id}") for age in YOUTH_AGES)
        youth = male + female
        district_code = village_id[:-3]
        if not district_code:
            raise RuntimeError(f"Invalid village district_code: {village_id}")
        district_codes[district].add(district_code)
        totals[district]["village_count"] += 1
        totals[district]["total_population"] += total_population
        totals[district]["youth"] += youth
        totals[district]["male"] += male
        totals[district]["female"] += female
        source_youth_total += youth
        source_population_total += total_population
        village_rows.append({
            "source_month": source_month[0], "district_code": village_id, "district_code_prefix": district_code,
            "site_id": str(record["site_id"]), "village": str(record["village"]), "district": district,
        })
    source_districts = set(totals)
    missing, unexpected = EXPECTED_DISTRICTS - source_districts, source_districts - EXPECTED_DISTRICTS
    if missing or unexpected or len(source_districts) != 29:
        raise RuntimeError(f"District completeness failed; missing={sorted(missing)}, unexpected={sorted(unexpected)}")
    rows = [district_row(district, totals[district], source_month) for district in sorted(EXPECTED_DISTRICTS)]
    district_youth_total = sum(row["youth_18_35_count"] for row in rows)
    district_population_total = sum(row["total_population"] for row in rows)
    if district_youth_total != source_youth_total or district_population_total != source_population_total:
        raise RuntimeError("District aggregation totals do not reconcile to the source village totals")
    return rows, sorted(village_rows, key=lambda row: row["district_code"]), {
        "expected_district_count": 29,
        "district_count": len(source_districts),
        "missing_districts": sorted(missing),
        "unexpected_districts": sorted(unexpected),
        "duplicate_districts": [],
        "village_record_count": len(records),
        "unique_village_district_code_count": len(village_ids),
        "duplicate_village_district_codes": [],
        "village_records_accounted_for": len(village_rows) == len(records),
        "district_code_prefixes_by_district": {district: sorted(codes) for district, codes in sorted(district_codes.items())},
        "source_youth_18_35_count": source_youth_total,
        "district_youth_18_35_count": district_youth_total,
        "district_youth_equals_source_youth": district_youth_total == source_youth_total,
        "source_total_population": source_population_total,
        "district_total_population": district_population_total,
        "district_total_population_equals_source_total": district_population_total == source_population_total,
    }


def district_from_site_id(value: str) -> str:
    match = DISTRICT_PATTERN.fullmatch(value.strip())
    if not match:
        raise RuntimeError(f"site_id is not a New Taipei district identifier: {value!r}")
    return match.group("district")


def district_row(district: str, values: dict[str, int], source_month: tuple[str, int, int, int]) -> dict[str, Any]:
    yyyymm, roc_year, year, month = source_month
    return {
        "city": COUNTY,
        "district": district,
        "source_month": yyyymm,
        "source_period": f"{roc_year}年{month:02d}月 / {year}-{month:02d}",
        "source_url": source_url(yyyymm),
        "source_dataset": "ODRP014 village household and single-age population",
        "village_count": values["village_count"],
        "total_population": values["total_population"],
        "youth_18_35_count": values["youth"],
        "youth_18_35_share": f"{values['youth'] / values['total_population']:.10f}",
        "youth_18_35_male": values["male"],
        "youth_18_35_female": values["female"],
        "exact_age_definition": "sum people_age_018_m/f through people_age_035_m/f, inclusive",
    }


def write_raw_responses(source_month: tuple[str, int, int, int], responses: list[dict[str, Any]]) -> list[Path]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for page, response in enumerate(responses, start=1):
        path = RAW_DIR / f"ris_odrp014_{source_month[0]}_ntpc_page_{page:03d}.json"
        serialized = json.dumps(response, ensure_ascii=False, indent=2) + "\n"
        if path.exists():
            if path.read_text(encoding="utf-8") != serialized:
                raise RuntimeError(f"Refusing to overwrite immutable raw file with different content: {path}")
        else:
            path.write_text(serialized, encoding="utf-8")
        paths.append(path)
    return paths


def build_metadata(
    source_month: tuple[str, int, int, int], responses: list[dict[str, Any]], raw_paths: list[Path], response_qa: dict[str, Any], aggregation_qa: dict[str, Any], rows: list[dict[str, Any]], village_rows: list[dict[str, str]]
) -> dict[str, Any]:
    yyyymm, roc_year, year, month = source_month
    return {
        "pipeline": "scripts/population/build_ntpc_district_youth_population.py",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": {
            "organization": SOURCE_ORG,
            "dataset_id": "ODRP014",
            "dataset_name": "村里戶數、單一年齡人口（新增區域代碼）",
            "source_url": source_url(yyyymm),
            "source_month": yyyymm,
            "source_period": f"{roc_year}年{month:02d}月 / {year}-{month:02d}",
            "geographic_scope": "新北市村里，依戶政司 district_code、site_id、village 欄位彙整為 29 區",
            "raw_response_files": [raw_file_metadata(path) for path in raw_paths],
        },
        "exact_18_35_method": {
            "age_range": [18, 35],
            "inclusive": True,
            "formula": "sum(age 18..35 of people_age_{age:03d}_m + people_age_{age:03d}_f)",
            "denominator": "sum(people_total) from the same ODRP014 month and village records",
            "share_formula": "youth_18_35_count / total_population",
        },
        "outputs": {
            "district_csv": str(PROCESSED_PATH.relative_to(PROJECT_ROOT)),
            "village_mapping_csv": str(VILLAGE_MAPPING_PATH.relative_to(PROJECT_ROOT)),
            "district_row_count": len(rows),
            "village_mapping_row_count": len(village_rows),
        },
        "api_schema": {
            "field_count": len(responses[0]["responseData"][0]),
            "field_names": list(responses[0]["responseData"][0]),
            "required_fields": sorted(required_schema_fields()),
        },
        "qa": {"response_completeness": response_qa, "aggregation": aggregation_qa},
    }


def raw_file_metadata(path: Path) -> dict[str, str]:
    return {"path": str(path.relative_to(PROJECT_ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def required_schema_fields() -> set[str]:
    fields = {"statistic_yyymm", "district_code", "site_id", "village", "people_total"}
    fields.update(f"people_age_{age:03d}_{sex}" for age in YOUTH_AGES for sex in ("m", "f"))
    return fields


def processed_fieldnames() -> list[str]:
    return ["city", "district", "source_month", "source_period", "source_url", "source_dataset", "village_count", "total_population", "youth_18_35_count", "youth_18_35_share", "youth_18_35_male", "youth_18_35_female", "exact_age_definition"]


def village_mapping_fieldnames() -> list[str]:
    return ["source_month", "district_code", "district_code_prefix", "site_id", "village", "district"]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def update_catalog(source_month: tuple[str, int, int, int], raw_paths: list[Path]) -> None:
    fieldnames = ["dataset_id", "filename", "original_filename", "category", "source_org", "source_url", "download_date", "data_period", "geographic_scope", "format", "description", "raw_or_derived", "notes"]
    with DATA_CATALOG.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    yyyymm, roc_year, year, month = source_month
    period = f"{roc_year}年{month:02d}月 / {year}-{month:02d}"
    replacement = {
        f"ris_odrp014_ntpc_{yyyymm}": {"dataset_id": f"ris_odrp014_ntpc_{yyyymm}", "filename": ";".join(str(path.relative_to(PROJECT_ROOT)) for path in raw_paths), "original_filename": f"ODRP014/{yyyymm}", "category": "population", "source_org": SOURCE_ORG, "source_url": source_url(yyyymm), "download_date": date.today().isoformat(), "data_period": period, "geographic_scope": "New Taipei City village-level", "format": "json", "description": "Unmodified paginated RIS ODRP014 responses filtered to New Taipei City.", "raw_or_derived": "raw", "notes": "Fetched by scripts/population/build_ntpc_district_youth_population.py; each API page is stored separately and immutable."},
        f"ntpc_district_youth_18_35_{yyyymm}_exact": {"dataset_id": f"ntpc_district_youth_18_35_{yyyymm}_exact", "filename": str(PROCESSED_PATH.relative_to(PROJECT_ROOT)), "original_filename": "", "category": "population", "source_org": f"Derived from {SOURCE_ORG}", "source_url": source_url(yyyymm), "download_date": date.today().isoformat(), "data_period": period, "geographic_scope": "New Taipei City 29 districts", "format": "csv", "description": "Exact 18-35 population, total population denominator, and youth share aggregated from village-level ODRP014.", "raw_or_derived": "derived", "notes": "Generated by scripts/population/build_ntpc_district_youth_population.py; QA metadata and reproducible village-to-district mapping are under outputs/population/."},
    }
    existing_ids = {row["dataset_id"] for row in rows}
    normalized = [{name: row.get(name, "") for name in fieldnames} for row in rows]
    normalized = [replacement.get(row["dataset_id"], row) for row in normalized]
    normalized.extend(row for dataset_id, row in replacement.items() if dataset_id not in existing_ids)
    with DATA_CATALOG.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(normalized)


def positive_int(value: Any, field: str) -> int:
    parsed = nonnegative_int(value, field)
    if parsed < 1:
        raise RuntimeError(f"{field} must be positive, got {value!r}")
    return parsed


def nonnegative_int(value: Any, field: str) -> int:
    text = str(value).strip().replace(",", "")
    if not re.fullmatch(r"\d+", text):
        raise RuntimeError(f"{field} must be a non-negative integer, got {value!r}")
    return int(text)


if __name__ == "__main__":
    main()
