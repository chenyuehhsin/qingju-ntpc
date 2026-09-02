from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_cleaner import STANDARD_DISTRICTS  # noqa: E402
from src.sources.population_source import PopulationSourceAdapter  # noqa: E402
from src.sources.taiwanjobs_source import JobSourceAdapter  # noqa: E402
from src.trend_metrics import (  # noqa: E402
    absolute_change,
    clean_json_value,
    demand_growth_signal,
    forecast_readiness,
    percent_change,
    trend_label,
)


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
HISTORY_DIR = PROJECT_ROOT / "data" / "history"
WEBSITE_DATA_DIR = PROJECT_ROOT / "website" / "data"
CURRENT_CSV = PROCESSED_DIR / "youth_employment_map.csv"
CURRENT_JSON = WEBSITE_DATA_DIR / "youth_employment_map.json"
HISTORY_CSV = PROCESSED_DIR / "youth_employment_history.csv"
CATEGORY_HISTORY_CSV = PROCESSED_DIR / "job_category_history.csv"
HISTORY_JSON = WEBSITE_DATA_DIR / "youth_employment_history.json"
HISTORY_MANIFEST = HISTORY_DIR / "history_manifest.json"

SNAPSHOT_COLUMNS = [
    "snapshot_month",
    "district",
    "youth_population_18_35",
    "job_postings",
    "job_openings",
    "jobs_per_1000_youth",
    "avg_salary",
    "median_salary",
    "company_count",
    "top_job_category",
    "top_occupation",
    "top_industry",
    "opportunity_score",
    "salary_score",
    "job_diversity_score",
    "employment_stability_score",
    "youth_employment_opportunity_index",
    "index_reliability_score",
    "index_reliability_level",
    "population_source_file",
    "jobs_source_file",
    "snapshot_as_of",
    "population_reference_month",
    "population_downloaded_at",
    "jobs_reference_date",
    "jobs_snapshot_as_of",
    "jobs_downloaded_at",
    "previous_available_period",
    "period_gap_months",
    "population_data_freshness_status",
    "population_lag_months",
    "jobs_data_freshness_status",
    "jobs_lag_months",
    "source_date",
    "snapshot_created_at",
    "processed_at",
    "pipeline_version",
]

HISTORY_COLUMNS = [
    *SNAPSHOT_COLUMNS,
    "job_postings_mom_pct",
    "job_openings_mom_pct",
    "salary_mom_pct",
    "jobs_per_1000_youth_mom_pct",
    "index_mom_change",
    "job_opportunity_trend",
    "demand_growth_signal",
]

CATEGORY_COLUMNS = [
    "snapshot_month",
    "district",
    "category",
    "job_postings",
    "job_openings",
    "median_salary",
    "company_count",
    "source_date",
    "snapshot_created_at",
    "pipeline_version",
    "job_postings_mom_pct",
    "job_openings_mom_pct",
    "salary_mom_pct",
    "absolute_openings_change",
    "demand_growth_signal",
]


def valid_month(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value))


def run_current_validation() -> None:
    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "validate_youth_employment_data.py")],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        raise SystemExit("Current processed data validation failed.")


def roc_month_to_gregorian(filename: str) -> str | None:
    match = re.search(r"_(\d{3})(\d{2})_", filename)
    if not match:
        return None
    year = int(match.group(1)) + 1911
    month = int(match.group(2))
    if 1 <= month <= 12:
        return f"{year:04d}-{month:02d}"
    return None


def compact_date_to_month(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    match = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}"
    return None


def compact_date_to_iso_date(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    match = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2}).*", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    return None


def month_lag(snapshot_month: str, reference_month: str | None) -> int | None:
    if not reference_month or not valid_month(snapshot_month) or not valid_month(reference_month):
        return None
    sy, sm = [int(part) for part in snapshot_month.split("-")]
    ry, rm = [int(part) for part in reference_month.split("-")]
    return (sy - ry) * 12 + (sm - rm)


def freshness_status(lag: int | None) -> str:
    if lag is None:
        return "Unknown"
    if lag <= 1:
        return "Fresh"
    return "Lagged"


def infer_source_date(payload: dict) -> dict:
    population_sources = payload.get("provenance", {}).get("population_sources", [])
    population_months = sorted(
        {
            month
            for source in population_sources
            for month in [roc_month_to_gregorian(str(source))]
            if month
        }
    )
    jobs = [job for district_jobs in payload.get("jobs_by_district", {}).values() for job in district_jobs]
    job_update_months = sorted({month for job in jobs for month in [compact_date_to_month(job.get("updated_at"))] if month})
    job_reference_dates = sorted({date for job in jobs for date in [compact_date_to_iso_date(job.get("updated_at"))] if date})
    job_deadline_months = sorted({month for job in jobs for month in [compact_date_to_month(job.get("deadline"))] if month})
    downloads = [
        source.get("downloaded_at")
        for source in payload.get("provenance", {}).get("taiwanjobs_manifest", {}).get("sources", [])
        if source.get("downloaded_at")
    ]
    return {
        "population_source_month": population_months[-1] if population_months else None,
        "population_reference_month": population_months[-1] if population_months else None,
        "population_downloaded_at": None,
        "job_updated_month_min": job_update_months[0] if job_update_months else None,
        "job_updated_month_max": job_update_months[-1] if job_update_months else None,
        "job_deadline_month_min": job_deadline_months[0] if job_deadline_months else None,
        "job_deadline_month_max": job_deadline_months[-1] if job_deadline_months else None,
        "jobs_reference_date": job_reference_dates[-1] if job_reference_dates else None,
        "jobs_snapshot_as_of": max(downloads) if downloads else None,
        "jobs_downloaded_at": max(downloads) if downloads else None,
        "taiwanjobs_downloaded_at_min": min(downloads) if downloads else None,
        "taiwanjobs_downloaded_at_max": max(downloads) if downloads else None,
        "note": "processed_at is excluded from source_date inference.",
    }


def source_date_text(source_date: dict) -> str:
    return json.dumps(clean_json_value(source_date), ensure_ascii=False, sort_keys=True)


def monthly_salary_midpoint(job: dict) -> float | None:
    if not str(job.get("salary_text") or "").startswith("月薪"):
        return None
    low = pd.to_numeric(pd.Series([job.get("salary_min")]), errors="coerce").iloc[0]
    high = pd.to_numeric(pd.Series([job.get("salary_max")]), errors="coerce").iloc[0]
    if pd.notna(low) and pd.notna(high):
        return float((low + high) / 2)
    if pd.notna(low):
        return float(low)
    if pd.notna(high):
        return float(high)
    return None


def build_category_snapshot(payload: dict, snapshot_month: str, created_at: str, source_date: str) -> pd.DataFrame:
    rows: list[dict] = []
    for district in STANDARD_DISTRICTS:
        jobs = payload.get("jobs_by_district", {}).get(district, [])
        categories = sorted({job.get("category") for job in jobs if job.get("category")})
        for category in categories:
            category_jobs = [job for job in jobs if job.get("category") == category]
            salaries = [value for value in (monthly_salary_midpoint(job) for job in category_jobs) if value is not None]
            rows.append(
                {
                    "snapshot_month": snapshot_month,
                    "district": district,
                    "category": category,
                    "job_postings": len(category_jobs),
                    "job_openings": sum(int(job.get("openings") or 0) for job in category_jobs),
                    "median_salary": float(pd.Series(salaries).median()) if salaries else pd.NA,
                    "company_count": len({job.get("company") for job in category_jobs if job.get("company")}),
                    "source_date": source_date,
                    "snapshot_created_at": created_at,
                    "pipeline_version": "trend_snapshot_v1",
                }
            )
    return pd.DataFrame(rows)


def read_existing(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    return pd.read_csv(path, encoding="utf-8-sig")


def add_history_changes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=HISTORY_COLUMNS)
    result = df.copy()
    result = result.sort_values(["district", "snapshot_month"]).reset_index(drop=True)
    periods = sorted(result["snapshot_month"].dropna().astype(str).unique().tolist())
    previous_by_period = {
        period: periods[index - 1] if index > 0 else pd.NA
        for index, period in enumerate(periods)
    }
    result["previous_available_period"] = result["snapshot_month"].astype(str).map(previous_by_period)
    result["period_gap_months"] = [
        month_lag(current, previous) if isinstance(previous, str) else pd.NA
        for current, previous in zip(result["snapshot_month"].astype(str), result["previous_available_period"])
    ]
    for column in ["job_postings", "job_openings", "avg_salary", "median_salary", "jobs_per_1000_youth", "youth_employment_opportunity_index", "company_count"]:
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="coerce")
    grouped = result.groupby("district", sort=False)
    result["job_postings_mom_pct"] = [
        percent_change(current, previous)
        for current, previous in zip(result["job_postings"], grouped["job_postings"].shift(1))
    ]
    result["job_openings_mom_pct"] = [
        percent_change(current, previous)
        for current, previous in zip(result["job_openings"], grouped["job_openings"].shift(1))
    ]
    result["salary_mom_pct"] = [
        percent_change(current, previous)
        for current, previous in zip(result["median_salary"], grouped["median_salary"].shift(1))
    ]
    result["jobs_per_1000_youth_mom_pct"] = [
        percent_change(current, previous)
        for current, previous in zip(result["jobs_per_1000_youth"], grouped["jobs_per_1000_youth"].shift(1))
    ]
    result["index_mom_change"] = [
        absolute_change(current, previous)
        for current, previous in zip(result["youth_employment_opportunity_index"], grouped["youth_employment_opportunity_index"].shift(1))
    ]
    result["job_opportunity_trend"] = result["job_openings_mom_pct"].map(trend_label)
    result["demand_growth_signal"] = [
        demand_growth_signal(openings, postings, company)
        for openings, postings, company in zip(
            result["job_openings_mom_pct"],
            result["job_postings_mom_pct"],
            [percent_change(current, previous) for current, previous in zip(result["company_count"], grouped["company_count"].shift(1))],
        )
    ]
    return result[[column for column in HISTORY_COLUMNS if column in result.columns]]


def add_category_changes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=CATEGORY_COLUMNS)
    result = df.copy()
    result = result.sort_values(["district", "category", "snapshot_month"]).reset_index(drop=True)
    for column in ["job_postings", "job_openings", "median_salary", "company_count"]:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    grouped = result.groupby(["district", "category"], sort=False)
    result["job_postings_mom_pct"] = [
        percent_change(current, previous)
        for current, previous in zip(result["job_postings"], grouped["job_postings"].shift(1))
    ]
    result["job_openings_mom_pct"] = [
        percent_change(current, previous)
        for current, previous in zip(result["job_openings"], grouped["job_openings"].shift(1))
    ]
    result["salary_mom_pct"] = [
        percent_change(current, previous)
        for current, previous in zip(result["median_salary"], grouped["median_salary"].shift(1))
    ]
    result["absolute_openings_change"] = [
        absolute_change(current, previous)
        for current, previous in zip(result["job_openings"], grouped["job_openings"].shift(1))
    ]
    company_pct = [percent_change(current, previous) for current, previous in zip(result["company_count"], grouped["company_count"].shift(1))]
    result["demand_growth_signal"] = [
        demand_growth_signal(openings, postings, company)
        for openings, postings, company in zip(result["job_openings_mom_pct"], result["job_postings_mom_pct"], company_pct)
    ]
    return result[[column for column in CATEGORY_COLUMNS if column in result.columns]]


def write_history_json(history: pd.DataFrame, category_history: pd.DataFrame) -> None:
    months = sorted(history["snapshot_month"].dropna().astype(str).unique()) if not history.empty else []
    latest_month = months[-1] if months else None
    current = history[history["snapshot_month"] == latest_month].copy() if latest_month else pd.DataFrame()
    overview_rows = []
    for month, month_df in history.groupby("snapshot_month", sort=True):
        youth_total = pd.to_numeric(month_df["youth_population_18_35"], errors="coerce").sum(min_count=1)
        openings_total = pd.to_numeric(month_df["job_openings"], errors="coerce").sum(min_count=1)
        postings_total = pd.to_numeric(month_df["job_postings"], errors="coerce").sum(min_count=1)
        salary = pd.to_numeric(month_df["median_salary"], errors="coerce").dropna()
        overview_rows.append(
            {
                "snapshot_month": month,
                "total_youth_population": youth_total,
                "total_job_postings": postings_total,
                "total_job_openings": openings_total,
                "jobs_per_1000_youth": float(openings_total) / float(youth_total) * 1000 if pd.notna(openings_total) and pd.notna(youth_total) and youth_total > 0 else None,
                "median_salary": float(salary.median()) if not salary.empty else None,
            }
        )

    current_category = category_history[category_history["snapshot_month"] == latest_month].copy() if latest_month and not category_history.empty else pd.DataFrame()
    if not current_category.empty:
        current_category["job_openings"] = pd.to_numeric(current_category["job_openings"], errors="coerce")
        current_category["absolute_openings_change"] = pd.to_numeric(current_category["absolute_openings_change"], errors="coerce")
        category_current_demand = current_category.groupby("category", as_index=False)["job_openings"].sum().sort_values("job_openings", ascending=False)
        category_increase = (
            current_category.dropna(subset=["absolute_openings_change"])
            .groupby("category", as_index=False)["absolute_openings_change"]
            .sum()
            .sort_values("absolute_openings_change", ascending=False)
        )
        category_decrease = category_increase.sort_values("absolute_openings_change", ascending=True)
    else:
        category_current_demand = pd.DataFrame()
        category_increase = pd.DataFrame()
        category_decrease = pd.DataFrame()

    readiness = forecast_readiness(len(months))
    manifest = {
        "available_periods": months,
        "period_count": len(months),
        "latest_period": latest_month,
        "forecast_readiness": readiness,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_MANIFEST.write_text(json.dumps(clean_json_value(manifest), ensure_ascii=False, indent=2), encoding="utf-8")
    payload = {
        "title": "新北市青年就業歷史快照",
        "periods": months,
        "latest_snapshot": latest_month,
        "history_manifest": manifest,
        "forecast_readiness": readiness,
        "records": clean_json_value(history.to_dict(orient="records")),
        "category_history": clean_json_value(category_history.to_dict(orient="records")),
        "overall_trend": clean_json_value(overview_rows),
        "category_trends": {
            "current_demand_top": clean_json_value(category_current_demand.head(10).to_dict(orient="records")) if not category_current_demand.empty else [],
            "demand_increase_top": clean_json_value(category_increase.head(10).to_dict(orient="records")) if not category_increase.empty else [],
            "demand_decrease_top": clean_json_value(category_decrease.head(10).to_dict(orient="records")) if not category_decrease.empty else [],
        },
    }
    WEBSITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def create_snapshot(month: str, force: bool) -> None:
    if not valid_month(month):
        raise SystemExit("--month must use YYYY-MM format.")
    run_current_validation()
    snapshot_dir = HISTORY_DIR / month
    snapshot_csv = snapshot_dir / "youth_employment_map.csv"
    snapshot_metadata = snapshot_dir / "metadata.json"
    snapshot_source_manifest = snapshot_dir / "source_manifest.json"
    if snapshot_dir.exists() and not force:
        raise SystemExit(f"Snapshot already exists: {snapshot_dir}. Use --force to replace it explicitly.")

    df = pd.read_csv(CURRENT_CSV, encoding="utf-8-sig")
    df = df[df["district"].isin(STANDARD_DISTRICTS)].copy()
    if sorted(df["district"].tolist()) != sorted(STANDARD_DISTRICTS) or len(df) != 29:
        raise SystemExit("Current processed data must contain exactly 29 New Taipei districts.")

    payload = json.loads(CURRENT_JSON.read_text(encoding="utf-8"))
    created_at = datetime.now().isoformat(timespec="seconds")
    source_date = infer_source_date(payload)
    source_date_serialized = source_date_text(source_date)

    snapshot = df.copy()
    snapshot.insert(0, "snapshot_month", month)
    snapshot["snapshot_as_of"] = created_at
    snapshot["population_reference_month"] = source_date.get("population_reference_month")
    snapshot["population_downloaded_at"] = source_date.get("population_downloaded_at")
    snapshot["jobs_reference_date"] = source_date.get("jobs_reference_date")
    snapshot["jobs_snapshot_as_of"] = source_date.get("jobs_snapshot_as_of")
    snapshot["jobs_downloaded_at"] = source_date.get("jobs_downloaded_at")
    population_lag = month_lag(month, source_date.get("population_reference_month"))
    jobs_snapshot_month = compact_date_to_month(str(source_date.get("jobs_snapshot_as_of") or "").replace("-", "")[:8])
    jobs_lag = month_lag(month, jobs_snapshot_month)
    snapshot["previous_available_period"] = pd.NA
    snapshot["period_gap_months"] = pd.NA
    snapshot["population_data_freshness_status"] = freshness_status(population_lag)
    snapshot["population_lag_months"] = population_lag
    snapshot["jobs_data_freshness_status"] = freshness_status(jobs_lag)
    snapshot["jobs_lag_months"] = jobs_lag
    snapshot["source_date"] = source_date_serialized
    snapshot["snapshot_created_at"] = created_at
    snapshot["pipeline_version"] = "trend_snapshot_v1"
    snapshot = snapshot[[column for column in SNAPSHOT_COLUMNS if column in snapshot.columns]]

    category_snapshot = build_category_snapshot(payload, month, created_at, source_date_serialized)

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot.to_csv(snapshot_csv, index=False, encoding="utf-8-sig")
    snapshot_metadata.write_text(
        json.dumps(
            clean_json_value(
                {
                    "snapshot_month": month,
                    "snapshot_created_at": created_at,
                    "source_date": source_date,
                    "pipeline_version": "trend_snapshot_v1",
                    "district_count": int(len(snapshot)),
                    "category_rows": int(len(category_snapshot)),
                    "note": "This snapshot was created from validated processed data. Raw data was not modified.",
                }
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    population_adapter = PopulationSourceAdapter()
    job_adapter = JobSourceAdapter()
    source_manifest = {
        "snapshot_month": month,
        "snapshot_as_of": created_at,
        "population_reference_month": source_date.get("population_reference_month"),
        "population_downloaded_at": source_date.get("population_downloaded_at"),
        "jobs_reference_date": source_date.get("jobs_reference_date"),
        "jobs_snapshot_as_of": source_date.get("jobs_snapshot_as_of"),
        "jobs_downloaded_at": source_date.get("jobs_downloaded_at"),
        "processed_at": sorted(set(df["processed_at"].dropna()))[-1] if "processed_at" in df and df["processed_at"].notna().any() else None,
        "sources": {
            "population": population_adapter.get_provenance(population_adapter.source_paths()),
            "jobs": job_adapter.get_provenance(job_adapter.source_paths()),
        },
    }
    snapshot_source_manifest.write_text(
        json.dumps(clean_json_value(source_manifest), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    existing_history = read_existing(HISTORY_CSV, HISTORY_COLUMNS)
    existing_history = existing_history[existing_history["snapshot_month"].astype(str) != month] if not existing_history.empty and force else existing_history
    combined_history = pd.concat([existing_history, snapshot], ignore_index=True)
    combined_history = add_history_changes(combined_history)
    combined_history.to_csv(HISTORY_CSV, index=False, encoding="utf-8-sig")

    existing_category = read_existing(CATEGORY_HISTORY_CSV, CATEGORY_COLUMNS)
    existing_category = existing_category[existing_category["snapshot_month"].astype(str) != month] if not existing_category.empty and force else existing_category
    combined_category = pd.concat([existing_category, category_snapshot], ignore_index=True)
    combined_category = add_category_changes(combined_category)
    combined_category.to_csv(CATEGORY_HISTORY_CSV, index=False, encoding="utf-8-sig")
    write_history_json(combined_history, combined_category)

    print(f"Wrote {snapshot_csv}")
    print(f"Wrote {snapshot_metadata}")
    print(f"Wrote {snapshot_source_manifest}")
    print(f"Wrote {HISTORY_CSV}")
    print(f"Wrote {CATEGORY_HISTORY_CSV}")
    print(f"Wrote {HISTORY_JSON}")
    print(f"Wrote {HISTORY_MANIFEST}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a monthly youth employment snapshot.")
    parser.add_argument("--month", required=True, help="Snapshot month in YYYY-MM format.")
    parser.add_argument("--force", action="store_true", help="Explicitly replace an existing snapshot month.")
    args = parser.parse_args()
    create_snapshot(args.month, args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
