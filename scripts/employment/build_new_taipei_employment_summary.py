#!/usr/bin/env python3
"""Aggregate the immutable New Taipei TaiwanJobs snapshot by district."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = PROJECT_ROOT / "data" / "raw" / "employment" / "new_taipei_jobs.csv"
OUTPUT_CSV = PROJECT_ROOT / "data" / "processed" / "employment" / "new_taipei_employment_summary.csv"
SNAPSHOT_DATE = "2026-08-25"


def _top_category(values: pd.Series) -> str:
    counts = values.dropna().astype(str).str.strip().value_counts()
    return "" if counts.empty else str(counts.index[0])


def build_summary() -> pd.DataFrame:
    jobs = pd.read_csv(RAW_CSV, encoding="utf-8-sig", keep_default_na=False)
    required = {
        "district",
        "CJOB_NAME1",
        "JOB_PERSON",
        "SALARYCD",
        "NT_L",
        "NT_U",
        "COMPNAME",
    }
    missing = required - set(jobs.columns)
    if missing:
        raise RuntimeError(f"Employment raw data is missing columns: {sorted(missing)}")

    jobs["JOB_PERSON"] = pd.to_numeric(jobs["JOB_PERSON"], errors="coerce")
    jobs["salary_lower"] = pd.to_numeric(
        jobs["NT_L"].astype(str).str.replace(",", "", regex=False), errors="coerce"
    )
    jobs["salary_upper"] = pd.to_numeric(
        jobs["NT_U"].astype(str).str.replace(",", "", regex=False), errors="coerce"
    )
    monthly = jobs.loc[
        jobs["SALARYCD"].isin(["月薪", "部分工時(月薪)"])
        & jobs["salary_lower"].gt(0)
        & jobs["salary_upper"].gt(0)
    ].copy()
    monthly["salary_midpoint"] = (monthly["salary_lower"] + monthly["salary_upper"]) / 2

    summary = jobs.groupby("district", as_index=False).agg(
        job_postings=("district", "size"),
        hiring_count=("JOB_PERSON", "sum"),
        company_count=("COMPNAME", lambda values: values.astype(str).str.strip().replace("", pd.NA).nunique()),
        top_job_category=("CJOB_NAME1", _top_category),
    )
    salary = monthly.groupby("district", as_index=False)["salary_midpoint"].median().rename(
        columns={"salary_midpoint": "median_salary"}
    )
    summary = summary.merge(salary, on="district", how="left", validate="one_to_one")
    summary["source_file"] = "data/raw/employment/new_taipei_jobs.csv"
    summary["source_organization"] = "TaiwanJobs"
    summary["source_snapshot_date"] = SNAPSHOT_DATE
    return summary[
        [
            "district",
            "job_postings",
            "hiring_count",
            "company_count",
            "median_salary",
            "top_job_category",
            "source_file",
            "source_organization",
            "source_snapshot_date",
        ]
    ].sort_values("district").reset_index(drop=True)


def main() -> None:
    result = build_summary()
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"Wrote {OUTPUT_CSV.relative_to(PROJECT_ROOT)} rows={len(result)}")


if __name__ == "__main__":
    main()
