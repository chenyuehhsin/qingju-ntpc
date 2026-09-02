from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import scripts.run_monthly_pipeline as pipeline  # noqa: E402
from src.data_cleaner import STANDARD_DISTRICTS  # noqa: E402
from src.sources.base import validate_required_fields  # noqa: E402
from src.sources.population_source import PopulationSourceAdapter  # noqa: E402
from src.sources.taiwanjobs_source import JobSourceAdapter  # noqa: E402


def assert_current_sources_validate() -> None:
    population = PopulationSourceAdapter()
    jobs = JobSourceAdapter()
    population_result = population.validate_raw(population.source_paths())
    job_result = jobs.validate_raw(jobs.source_paths())
    assert population_result.ok, population_result.errors
    assert job_result.ok, job_result.errors
    assert population_result.row_count and population_result.row_count > 0
    assert job_result.row_count and job_result.row_count > 0


def assert_existing_snapshot_requires_force() -> None:
    report = pipeline.preflight("2026-08", force=False)
    assert any("snapshot already exists" in error for error in report["errors"])
    assert report["would_create_snapshot"] is False


def assert_lagged_population_month_is_preserved() -> None:
    report = pipeline.preflight("2026-09", force=True)
    population = report["sources"]["population"]
    assert population["reference_month"] == "2026-07"
    assert population["freshness"]["status"] == "Lagged"
    assert population["freshness"]["lag_months"] == 2


def assert_missing_required_source_field_fails() -> None:
    result = validate_required_fields(["site_id", "people_age_018_m"], ["site_id", "statistic_yyymm"], "fixture")
    assert not result.ok
    assert "statistic_yyymm" in result.errors[0]


def assert_missing_district_detectable() -> None:
    rows = pd.DataFrame({"district": STANDARD_DISTRICTS[:-1]})
    missing = sorted(set(STANDARD_DISTRICTS) - set(rows["district"]))
    assert missing == [STANDARD_DISTRICTS[-1]]


def assert_previous_period_gap_uses_previous_available_period() -> None:
    periods = ["2026-08"]
    assert pipeline.previous_available_period("2026-10", periods) == "2026-08"
    assert pipeline.month_lag("2026-10", "2026-08") == 2


def assert_failed_halfway_does_not_create_official_history_snapshot() -> None:
    original_preflight = pipeline.preflight
    original_stage_raw_sources = pipeline.stage_raw_sources
    original_write_report = pipeline.write_report
    month = "2099-01"

    def fake_preflight(_month: str, *, force: bool = False) -> dict:
        return {
            "target_snapshot": _month,
            "latest_existing_snapshot": "2026-08",
            "available_periods": ["2026-08"],
            "previous_available_period": "2026-08",
            "period_gap_months": 869,
            "would_create_snapshot": True,
            "source_unavailable": False,
            "errors": [],
            "warnings": [],
            "will_produce_mom": True,
        }

    def fake_stage_raw_sources(_month: str, *, force: bool = False) -> dict:
        return {"staging": pipeline.STAGING_DIR / _month, "source_manifest": {"snapshot_month": _month, "sources": {}}}

    try:
        pipeline.preflight = fake_preflight
        pipeline.stage_raw_sources = fake_stage_raw_sources
        pipeline.write_report = lambda _month, _report: None
        report = pipeline.run_pipeline(month, force=True, fail_after_stage=True)
        assert report["status"] == "failed"
        assert report.get("snapshot_created") is False
        assert not (PROJECT_ROOT / "data" / "history" / month / "youth_employment_map.csv").exists()
    finally:
        pipeline.preflight = original_preflight
        pipeline.stage_raw_sources = original_stage_raw_sources
        pipeline.write_report = original_write_report


def assert_dry_run_does_not_create_missing_month() -> None:
    target = PROJECT_ROOT / "data" / "history" / "2026-09"
    before = target.exists()
    report = pipeline.run_pipeline("2026-09", dry_run=True, force=True)
    assert report["status"] == "dry_run_complete"
    assert report["snapshot_created"] is False
    assert target.exists() is before


def main() -> int:
    tests = [
        assert_current_sources_validate,
        assert_existing_snapshot_requires_force,
        assert_lagged_population_month_is_preserved,
        assert_missing_required_source_field_fails,
        assert_missing_district_detectable,
        assert_previous_period_gap_uses_previous_available_period,
        assert_failed_halfway_does_not_create_official_history_snapshot,
        assert_dry_run_does_not_create_missing_month,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
