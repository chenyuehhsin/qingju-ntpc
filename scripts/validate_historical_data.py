from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_cleaner import STANDARD_DISTRICTS  # noqa: E402
from src.trend_metrics import absolute_change, percent_change, trend_label  # noqa: E402


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
HISTORY_DIR = PROJECT_ROOT / "data" / "history"
HISTORY_CSV = PROCESSED_DIR / "youth_employment_history.csv"
CATEGORY_HISTORY_CSV = PROCESSED_DIR / "job_category_history.csv"

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
REQUIRED_HISTORY_COLUMNS = {
    "snapshot_month",
    "district",
    "youth_population_18_35",
    "job_postings",
    "job_openings",
    "jobs_per_1000_youth",
    "avg_salary",
    "median_salary",
    "company_count",
    "youth_employment_opportunity_index",
    "index_reliability_score",
    "snapshot_as_of",
    "population_reference_month",
    "jobs_reference_date",
    "jobs_snapshot_as_of",
    "previous_available_period",
    "period_gap_months",
    "population_data_freshness_status",
    "jobs_data_freshness_status",
    "source_date",
    "snapshot_created_at",
    "pipeline_version",
}
REQUIRED_CATEGORY_COLUMNS = {
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
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)
    print(f"FAIL: {message}")


def pass_check(message: str) -> None:
    print(f"PASS: {message}")


def check_month(value: object) -> bool:
    return bool(MONTH_RE.fullmatch(str(value)))


def check_non_negative(df: pd.DataFrame, columns: list[str], errors: list[str]) -> None:
    for column in columns:
        values = pd.to_numeric(df[column], errors="coerce")
        if (values.dropna() < 0).any():
            fail(errors, f"{column} has negative values")
        else:
            pass_check(f"{column} has no negative values")


def validate_history(errors: list[str]) -> pd.DataFrame:
    if not HISTORY_CSV.exists():
        fail(errors, f"missing {HISTORY_CSV}")
        return pd.DataFrame()
    df = pd.read_csv(HISTORY_CSV, encoding="utf-8-sig")
    missing = sorted(REQUIRED_HISTORY_COLUMNS - set(df.columns))
    if missing:
        fail(errors, f"history missing columns: {missing}")
    else:
        pass_check("history required columns present")

    invalid_months = sorted({str(value) for value in df["snapshot_month"].dropna() if not check_month(value)})
    if invalid_months:
        fail(errors, f"invalid snapshot_month values: {invalid_months}")
    else:
        pass_check("snapshot_month values are valid YYYY-MM")

    duplicate_count = int(df.duplicated(["snapshot_month", "district"]).sum())
    if duplicate_count:
        fail(errors, f"duplicate snapshot_month + district rows: {duplicate_count}")
    else:
        pass_check("snapshot_month + district is unique")

    illegal = sorted(set(df["district"]) - set(STANDARD_DISTRICTS))
    if illegal:
        fail(errors, f"illegal districts: {illegal}")
    else:
        pass_check("all districts are legal")

    for month, month_df in df.groupby("snapshot_month"):
        missing_districts = sorted(set(STANDARD_DISTRICTS) - set(month_df["district"]))
        extra = sorted(set(month_df["district"]) - set(STANDARD_DISTRICTS))
        if len(month_df) != 29 or missing_districts or extra:
            fail(errors, f"{month} does not contain exactly 29 districts; missing={missing_districts}; extra={extra}")
        else:
            pass_check(f"{month} contains exactly 29 districts")

    check_non_negative(df, ["youth_population_18_35", "job_postings", "job_openings"], errors)

    metadata_missing = df[
        df["source_date"].isna()
        | (df["source_date"].astype(str).str.strip() == "")
        | df["snapshot_created_at"].isna()
        | (df["snapshot_created_at"].astype(str).str.strip() == "")
        | df["pipeline_version"].isna()
        | (df["pipeline_version"].astype(str).str.strip() == "")
    ]
    if len(metadata_missing):
        fail(errors, f"source metadata missing rows: {len(metadata_missing)}")
    else:
        pass_check("source metadata exists for history rows")

    months = sorted(df["snapshot_month"].astype(str).unique())
    if months != list(df.sort_values(["snapshot_month", "district"])["snapshot_month"].drop_duplicates()):
        pass_check("history months are sortable chronologically")
    else:
        pass_check("history chronological order is valid")

    validate_mom(df, errors)
    validate_previous_periods(df, errors)
    validate_snapshot_files(months, errors)
    return df


def month_lag(current: str, previous: str | None) -> int | None:
    if previous is None or pd.isna(previous) or not check_month(current) or not check_month(previous):
        return None
    cy, cm = [int(part) for part in str(current).split("-")]
    py, pm = [int(part) for part in str(previous).split("-")]
    return (cy - py) * 12 + (cm - pm)


def validate_previous_periods(df: pd.DataFrame, errors: list[str]) -> None:
    periods = sorted(df["snapshot_month"].astype(str).unique())
    expected = {period: periods[index - 1] if index > 0 else None for index, period in enumerate(periods)}
    mismatches = []
    for _idx, row in df.iterrows():
        period = str(row["snapshot_month"])
        expected_previous = expected[period]
        actual_previous = None if pd.isna(row.get("previous_available_period")) else str(row.get("previous_available_period"))
        if expected_previous != actual_previous:
            mismatches.append((period, row["district"], expected_previous, actual_previous))
            continue
        expected_gap = month_lag(period, expected_previous)
        actual_gap = row.get("period_gap_months")
        if expected_gap is None and pd.isna(actual_gap):
            continue
        if expected_gap is not None and (pd.isna(actual_gap) or int(actual_gap) != expected_gap):
            mismatches.append((period, row["district"], expected_gap, actual_gap))
    if mismatches:
        fail(errors, f"previous period metadata mismatches: {mismatches[:5]}")
    else:
        pass_check("previous_available_period and period_gap_months are correct")


def validate_mom(df: pd.DataFrame, errors: list[str]) -> None:
    if df.empty:
        return
    sorted_df = df.sort_values(["district", "snapshot_month"]).copy()
    grouped = sorted_df.groupby("district", sort=False)
    checks = [
        ("job_postings", "job_postings_mom_pct", percent_change),
        ("job_openings", "job_openings_mom_pct", percent_change),
        ("median_salary", "salary_mom_pct", percent_change),
        ("jobs_per_1000_youth", "jobs_per_1000_youth_mom_pct", percent_change),
        ("youth_employment_opportunity_index", "index_mom_change", absolute_change),
    ]
    mismatches: list[str] = []
    division_by_zero_rows = 0
    for value_col, change_col, func in checks:
        if change_col not in sorted_df.columns:
            continue
        previous = grouped[value_col].shift(1)
        for idx, (current, prev, actual) in enumerate(zip(sorted_df[value_col], previous, sorted_df[change_col])):
            expected = func(current, prev)
            if pd.notna(prev) and float(pd.to_numeric(pd.Series([prev]), errors="coerce").iloc[0]) == 0 and "pct" in change_col:
                division_by_zero_rows += 1
            if expected is None and pd.isna(actual):
                continue
            if expected is None and pd.notna(actual):
                mismatches.append(f"{change_col} row {idx} expected null got {actual}")
            elif expected is not None and (pd.isna(actual) or abs(float(actual) - expected) > 0.0001):
                mismatches.append(f"{change_col} row {idx} expected {expected} got {actual}")
    if mismatches:
        fail(errors, f"MoM calculation mismatches: {mismatches[:5]}")
    else:
        pass_check("MoM calculations are correct")
    pass_check(f"previous=0 percentage changes are null-safe; rows_checked={division_by_zero_rows}")

    if "job_opportunity_trend" in sorted_df.columns and "job_openings_mom_pct" in sorted_df.columns:
        bad = []
        for idx, (pct, label) in enumerate(zip(sorted_df["job_openings_mom_pct"], sorted_df["job_opportunity_trend"])):
            expected = trend_label(pct)
            if expected is None and pd.isna(label):
                continue
            if expected != label:
                bad.append(idx)
        if bad:
            fail(errors, f"trend label mismatches: {bad[:5]}")
        else:
            pass_check("trend labels match configured thresholds")


def validate_snapshot_files(months: list[str], errors: list[str]) -> None:
    for month in months:
        snapshot_dir = HISTORY_DIR / month
        metadata = snapshot_dir / "metadata.json"
        csv_path = snapshot_dir / "youth_employment_map.csv"
        if not snapshot_dir.exists() or not metadata.exists() or not csv_path.exists():
            fail(errors, f"snapshot files missing for {month}")
            continue
        try:
            info = json.loads(metadata.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            fail(errors, f"metadata.json is invalid for {month}")
            continue
        if info.get("snapshot_month") != month:
            fail(errors, f"metadata snapshot_month mismatch for {month}")
        else:
            pass_check(f"snapshot metadata exists for {month}")


def validate_category_history(errors: list[str]) -> pd.DataFrame:
    if not CATEGORY_HISTORY_CSV.exists():
        fail(errors, f"missing {CATEGORY_HISTORY_CSV}")
        return pd.DataFrame()
    df = pd.read_csv(CATEGORY_HISTORY_CSV, encoding="utf-8-sig")
    missing = sorted(REQUIRED_CATEGORY_COLUMNS - set(df.columns))
    if missing:
        fail(errors, f"category history missing columns: {missing}")
    else:
        pass_check("category history required columns present")
    duplicate_count = int(df.duplicated(["snapshot_month", "district", "category"]).sum())
    if duplicate_count:
        fail(errors, f"duplicate snapshot_month + district + category rows: {duplicate_count}")
    else:
        pass_check("snapshot_month + district + category is unique")
    illegal = sorted(set(df["district"]) - set(STANDARD_DISTRICTS))
    if illegal:
        fail(errors, f"category history illegal districts: {illegal}")
    else:
        pass_check("category history districts are legal")
    invalid_months = sorted({str(value) for value in df["snapshot_month"].dropna() if not check_month(value)})
    if invalid_months:
        fail(errors, f"category history invalid months: {invalid_months}")
    else:
        pass_check("category history months are valid")
    check_non_negative(df, ["job_postings", "job_openings"], errors)
    return df


def main() -> int:
    errors: list[str] = []
    history = validate_history(errors)
    validate_category_history(errors)
    if not history.empty:
        periods = sorted(history["snapshot_month"].astype(str).unique())
        print(f"Historical periods: {periods}")
    print(f"Historical validation complete: {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
