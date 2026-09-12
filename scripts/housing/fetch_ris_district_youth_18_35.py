#!/usr/bin/env python3
"""Fetch RIS single-age village population and aggregate NTPC 18-35 youth.

Raw API responses are stored under data/raw/population. Derived district-level
statistics are written to data/processed/housing.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "population"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "housing"
DATA_CATALOG = PROJECT_ROOT / "data" / "data_catalog.csv"
PROCESSED_OUTPUT = PROCESSED_DIR / "ntpc_district_youth_18_35.csv"

API_TEMPLATE = "https://www.ris.gov.tw/rs-opendata/api/v1/datastore/ODRP014/{yyyymm}"
SOURCE_ORG = "Ministry of the Interior Department of Household Registration"
YOUTH_MIN_AGE = 18
YOUTH_MAX_AGE = 35
EXPECTED_NTPC_DISTRICTS = 29


@dataclass(frozen=True)
class SourceMonth:
    yyyymm: str
    roc_year: int
    year: int
    month: int

    @property
    def data_period(self) -> str:
        return f"{self.roc_year}年{self.month:02d}月 / {self.year}-{self.month:02d}"

    @property
    def source_url(self) -> str:
        return API_TEMPLATE.format(yyyymm=self.yyyymm)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yyyymm",
        help="ROC year/month to fetch, for example 11507. If omitted, the latest available month is detected.",
    )
    parser.add_argument(
        "--as-of-date",
        default=date.today().isoformat(),
        help="Gregorian date used to start latest-month detection. Defaults to today.",
    )
    parser.add_argument(
        "--lookback-months",
        type=int,
        default=24,
        help="Maximum months to probe when detecting the latest available month.",
    )
    parser.add_argument("--force", action="store_true", help="Refetch even if the raw JSON cache already exists.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if args.yyyymm:
        source_month = source_month_from_yyyymm(args.yyyymm)
        raw_payload = load_or_fetch_month(source_month, force=args.force)
    else:
        source_month, raw_payload = find_latest_available_month(
            as_of_date=args.as_of_date,
            lookback_months=args.lookback_months,
            force=args.force,
        )

    raw_path = raw_output_path(source_month)
    processed_rows, summary = aggregate_ntpc_districts(raw_payload, source_month)
    write_processed_csv(processed_rows)
    update_data_catalog(source_month)

    print(f"source_month={source_month.yyyymm}")
    print(f"source_period={source_month.data_period}")
    print(f"raw_path={raw_path.relative_to(PROJECT_ROOT)}")
    print(f"processed_path={PROCESSED_OUTPUT.relative_to(PROJECT_ROOT)}")
    print(f"ntpc_village_rows={summary['ntpc_village_rows']}")
    print(f"ntpc_districts={summary['district_count']}/{EXPECTED_NTPC_DISTRICTS}")
    print(f"youth_count_total={summary['youth_count_total']}")
    print(f"district_total_population={summary['district_total_population']}")
    print(f"youth_share_complete={summary['youth_share_complete']}/{summary['district_count']}")
    if summary["missing_districts"]:
        print(f"missing_districts={','.join(summary['missing_districts'])}")


def find_latest_available_month(
    as_of_date: str,
    lookback_months: int,
    force: bool,
) -> tuple[SourceMonth, dict[str, Any]]:
    start = datetime.strptime(as_of_date, "%Y-%m-%d").date()
    year = start.year
    month = start.month
    errors: list[str] = []

    for _ in range(lookback_months):
        source_month = SourceMonth(
            yyyymm=f"{year - 1911:03d}{month:02d}",
            roc_year=year - 1911,
            year=year,
            month=month,
        )
        try:
            payload = load_or_fetch_month(source_month, force=force)
        except NoDataError:
            payload = None
        except (HTTPError, URLError, TimeoutError) as exc:
            errors.append(f"{source_month.yyyymm}: {exc}")
            payload = None
        if payload is not None:
            return source_month, payload
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    details = "; ".join(errors[:5])
    raise RuntimeError(f"No RIS ODRP014 data found within {lookback_months} months. {details}")


def load_or_fetch_month(source_month: SourceMonth, force: bool) -> dict[str, Any]:
    raw_path = raw_output_path(source_month)
    if raw_path.exists() and not force:
        return json.loads(raw_path.read_text(encoding="utf-8"))

    first_page = fetch_page(source_month, page=1)
    if not is_success_payload(first_page):
        raise NoDataError(first_page.get("responseMessage", "no data"))

    total_pages = int(first_page.get("totalPage") or 1)
    pages = [first_page]
    for page in range(2, total_pages + 1):
        payload = fetch_page(source_month, page=page)
        if not is_success_payload(payload):
            raise RuntimeError(f"RIS API returned non-success payload for {source_month.yyyymm} page {page}")
        pages.append(payload)

    raw_payload = {
        "metadata": {
            "dataset_id": f"ris_village_single_age_{source_month.yyyymm}",
            "source_org": SOURCE_ORG,
            "source_url": source_month.source_url,
            "api_template": API_TEMPLATE,
            "download_date": date.today().isoformat(),
            "source_month": source_month.yyyymm,
            "roc_year": source_month.roc_year,
            "year": source_month.year,
            "month": source_month.month,
            "data_period": source_month.data_period,
            "geographic_scope": "Taiwan village-level household and single-age population",
            "pages": total_pages,
            "total_data_size": int(first_page.get("totalDataSize") or 0),
            "exact_age_scope": f"{YOUTH_MIN_AGE}-{YOUTH_MAX_AGE}",
        },
        "pages": pages,
    }
    raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return raw_payload


def fetch_page(source_month: SourceMonth, page: int) -> dict[str, Any]:
    url = source_month.source_url
    if page > 1:
        url = f"{url}?{urlencode({'page': page})}"
    request = Request(url, headers={"User-Agent": "qingju-ntpc-data-pipeline/1.0"})
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def is_success_payload(payload: dict[str, Any]) -> bool:
    return payload.get("responseCode") == "OD-0101-S" and bool(payload.get("responseData"))


def raw_output_path(source_month: SourceMonth) -> Path:
    return RAW_DIR / f"ris_village_single_age_{source_month.yyyymm}.json"


def source_month_from_yyyymm(yyyymm: str) -> SourceMonth:
    if len(yyyymm) != 5 or not yyyymm.isdigit():
        raise ValueError("yyyymm must be a five-digit ROC year/month such as 11507")
    roc_year = int(yyyymm[:3])
    month = int(yyyymm[3:])
    if month < 1 or month > 12:
        raise ValueError("yyyymm month must be between 01 and 12")
    return SourceMonth(yyyymm=yyyymm, roc_year=roc_year, year=roc_year + 1911, month=month)


def aggregate_ntpc_districts(
    raw_payload: dict[str, Any],
    source_month: SourceMonth,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = [
        record
        for page in raw_payload.get("pages", [])
        for record in page.get("responseData", [])
        if isinstance(record, dict)
    ]
    district_totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "village_count": 0,
            "total_population": 0,
            "youth_18_35_count": 0,
            "youth_18_35_male": 0,
            "youth_18_35_female": 0,
        }
    )
    ntpc_village_rows = 0

    for record in records:
        site_id = first_present(record, ["site_id", "區域別"])
        if not site_id:
            continue
        site_text = str(site_id).strip()
        if not site_text.startswith("新北市") or site_text == "新北市":
            continue
        district = site_text.replace("新北市", "", 1)
        if not district:
            continue

        total_population = parse_int(first_present(record, ["people_total", "人口數"]))
        male_count = 0
        female_count = 0
        for age in range(YOUTH_MIN_AGE, YOUTH_MAX_AGE + 1):
            male_count += parse_int(first_present(record, [f"people_age_{age:03d}_m", f"{age}歲男"]))
            female_count += parse_int(first_present(record, [f"people_age_{age:03d}_f", f"{age}歲女"]))

        totals = district_totals[district]
        totals["village_count"] += 1
        totals["total_population"] += total_population
        totals["youth_18_35_male"] += male_count
        totals["youth_18_35_female"] += female_count
        totals["youth_18_35_count"] += male_count + female_count
        ntpc_village_rows += 1

    rows: list[dict[str, Any]] = []
    for district in sorted(district_totals):
        totals = district_totals[district]
        total_population = totals["total_population"]
        youth_count = totals["youth_18_35_count"]
        youth_share = youth_count / total_population if total_population else None
        rows.append(
            {
                "city": "新北市",
                "district": district,
                "source_month": source_month.yyyymm,
                "roc_year": source_month.roc_year,
                "year": source_month.year,
                "month": source_month.month,
                "data_period": source_month.data_period,
                "source_url": source_month.source_url,
                "source_org": SOURCE_ORG,
                "exact_age_scope": f"{YOUTH_MIN_AGE}-{YOUTH_MAX_AGE}",
                "source_geography": "village-level RIS ODRP014 aggregated to district",
                "village_count": totals["village_count"],
                "total_population": total_population,
                "youth_18_35_count": youth_count,
                "youth_18_35_share": f"{youth_share:.10f}" if youth_share is not None else "",
                "youth_18_35_male": totals["youth_18_35_male"],
                "youth_18_35_female": totals["youth_18_35_female"],
                "processing_note": (
                    "Exact sum of single-age male/female fields people_age_018_m through "
                    "people_age_035_f; no interpolation or 5-year age-bin estimation."
                ),
            }
        )

    expected = expected_ntpc_districts()
    districts = {row["district"] for row in rows}
    summary = {
        "ntpc_village_rows": ntpc_village_rows,
        "district_count": len(districts),
        "missing_districts": sorted(expected - districts),
        "youth_count_total": sum(row["youth_18_35_count"] for row in rows),
        "district_total_population": sum(row["total_population"] for row in rows),
        "youth_share_complete": sum(1 for row in rows if row["youth_18_35_share"] != ""),
    }
    if len(districts) != EXPECTED_NTPC_DISTRICTS:
        raise RuntimeError(f"Expected {EXPECTED_NTPC_DISTRICTS} NTPC districts, got {len(districts)}")
    if summary["missing_districts"]:
        raise RuntimeError(f"Missing NTPC districts: {', '.join(summary['missing_districts'])}")
    return rows, summary


def first_present(record: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        if name in record:
            return record[name]
    return None


def parse_int(value: Any) -> int:
    if value is None:
        return 0
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "nan", "NaN", "None"}:
        return 0
    return int(float(text))


def expected_ntpc_districts() -> set[str]:
    return {
        "板橋區",
        "三重區",
        "中和區",
        "永和區",
        "新莊區",
        "新店區",
        "土城區",
        "蘆洲區",
        "樹林區",
        "鶯歌區",
        "三峽區",
        "淡水區",
        "汐止區",
        "瑞芳區",
        "五股區",
        "泰山區",
        "林口區",
        "深坑區",
        "石碇區",
        "坪林區",
        "三芝區",
        "石門區",
        "八里區",
        "平溪區",
        "雙溪區",
        "貢寮區",
        "金山區",
        "萬里區",
        "烏來區",
    }


def write_processed_csv(rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "city",
        "district",
        "source_month",
        "roc_year",
        "year",
        "month",
        "data_period",
        "source_url",
        "source_org",
        "exact_age_scope",
        "source_geography",
        "village_count",
        "total_population",
        "youth_18_35_count",
        "youth_18_35_share",
        "youth_18_35_male",
        "youth_18_35_female",
        "processing_note",
    ]
    with PROCESSED_OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def update_data_catalog(source_month: SourceMonth) -> None:
    fieldnames = [
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
    rows: list[dict[str, str]] = []
    if DATA_CATALOG.exists():
        with DATA_CATALOG.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [{field: row.get(field, "") for field in fieldnames} for row in reader]

    raw_dataset_id = f"ris_village_single_age_{source_month.yyyymm}"
    processed_dataset_id = f"ntpc_district_youth_18_35_{source_month.yyyymm}"
    replacement_rows = {
        raw_dataset_id: {
            "dataset_id": raw_dataset_id,
            "filename": str(raw_output_path(source_month).relative_to(PROJECT_ROOT)),
            "original_filename": f"ODRP014/{source_month.yyyymm}",
            "category": "population",
            "source_org": SOURCE_ORG,
            "source_url": source_month.source_url,
            "download_date": date.today().isoformat(),
            "data_period": source_month.data_period,
            "geographic_scope": "Taiwan village-level household and single-age population",
            "format": "json",
            "description": "RIS village-level households and single-age male/female population with district codes.",
            "raw_or_derived": "raw",
            "notes": "Fetched by scripts/housing/fetch_ris_district_youth_18_35.py; raw API page responses are preserved inside the JSON cache.",
        },
        processed_dataset_id: {
            "dataset_id": processed_dataset_id,
            "filename": str(PROCESSED_OUTPUT.relative_to(PROJECT_ROOT)),
            "original_filename": "",
            "category": "housing",
            "source_org": f"Derived from {SOURCE_ORG}",
            "source_url": source_month.source_url,
            "download_date": date.today().isoformat(),
            "data_period": source_month.data_period,
            "geographic_scope": "New Taipei City 29 districts",
            "format": "csv",
            "description": "District-level exact 18-35 youth population, youth share, and total population aggregated from RIS village single-age data.",
            "raw_or_derived": "derived",
            "notes": "Generated by scripts/housing/fetch_ris_district_youth_18_35.py; exact ages 18-35 from single-age male/female fields; no interpolation or 5-year age-bin estimation.",
        },
    }

    existing_ids = {row["dataset_id"] for row in rows}
    rows = [replacement_rows.get(row["dataset_id"], row) for row in rows]
    for dataset_id, row in replacement_rows.items():
        if dataset_id not in existing_ids:
            rows.append(row)

    with DATA_CATALOG.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class NoDataError(RuntimeError):
    """Raised when the RIS API reports that a month has no available data."""


if __name__ == "__main__":
    main()
