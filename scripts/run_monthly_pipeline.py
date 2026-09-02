from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_cleaner import STANDARD_DISTRICTS  # noqa: E402
from src.sources.population_source import PopulationSourceAdapter  # noqa: E402
from src.sources.taiwanjobs_source import JobSourceAdapter  # noqa: E402
from src.trend_metrics import clean_json_value, forecast_readiness  # noqa: E402


HISTORY_DIR = PROJECT_ROOT / "data" / "history"
RAW_SNAPSHOT_DIR = PROJECT_ROOT / "data" / "raw_snapshots"
STAGING_DIR = PROJECT_ROOT / "data" / "staging"
REPORT_DIR = PROJECT_ROOT / "reports" / "pipeline_runs"
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def valid_month(month: str) -> bool:
    return bool(MONTH_RE.fullmatch(month))


def month_from_datetime(value: str | None) -> str | None:
    if not value:
        return None
    match = re.match(r"^(\d{4})-(\d{2})", value)
    return f"{match.group(1)}-{match.group(2)}" if match else None


def month_lag(snapshot_month: str, reference_month: str | None) -> int | None:
    if not reference_month or not valid_month(snapshot_month) or not valid_month(reference_month):
        return None
    sy, sm = [int(part) for part in snapshot_month.split("-")]
    ry, rm = [int(part) for part in reference_month.split("-")]
    return (sy - ry) * 12 + (sm - rm)


def freshness_status(snapshot_month: str, reference_month: str | None) -> dict[str, Any]:
    lag = month_lag(snapshot_month, reference_month)
    if lag is None:
        return {"status": "Unknown", "lag_months": None}
    if lag <= 1:
        return {"status": "Fresh", "lag_months": lag}
    return {"status": "Lagged", "lag_months": lag}


def existing_periods() -> list[str]:
    if not HISTORY_DIR.exists():
        return []
    return sorted(path.name for path in HISTORY_DIR.iterdir() if path.is_dir() and valid_month(path.name))


def previous_available_period(month: str, periods: list[str]) -> str | None:
    previous = [period for period in periods if period < month]
    return previous[-1] if previous else None


def backup_existing(path: Path) -> Path:
    backup = path.with_name(f"{path.name}.backup-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    shutil.move(str(path), str(backup))
    return backup


def run_command(args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(args, cwd=PROJECT_ROOT, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(args),
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def write_report(month: str, report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / f"{month}.json").write_text(json.dumps(clean_json_value(report), ensure_ascii=False, indent=2), encoding="utf-8")


def preflight(month: str, *, force: bool = False) -> dict[str, Any]:
    population = PopulationSourceAdapter()
    jobs = JobSourceAdapter()
    periods = existing_periods()
    previous = previous_available_period(month, periods)
    population_paths = population.source_paths()
    job_paths = jobs.source_paths()
    population_validation = population.validate_raw(population_paths)
    job_validation = jobs.validate_raw(job_paths)
    population_reference_month = population.extract_reference_date(population_paths)
    jobs_snapshot_as_of = jobs.get_provenance(job_paths).get("snapshot_as_of")
    jobs_snapshot_month = month_from_datetime(jobs_snapshot_as_of)
    target_exists = (HISTORY_DIR / month).exists()
    raw_target_exists = (RAW_SNAPSHOT_DIR / month).exists()
    errors: list[str] = []
    warnings: list[str] = []

    if not valid_month(month):
        errors.append("target month must use YYYY-MM")
    if len(STANDARD_DISTRICTS) != 29:
        errors.append("STANDARD_DISTRICTS must contain exactly 29 districts")
    if target_exists and not force:
        errors.append(f"snapshot already exists: data/history/{month}")
    if raw_target_exists and not force:
        errors.append(f"raw snapshot already exists: data/raw_snapshots/{month}")
    if not population_validation.ok:
        errors.extend(population_validation.errors)
    if not job_validation.ok:
        errors.extend(job_validation.errors)
    warnings.extend(population_validation.warnings[:10])
    warnings.extend(job_validation.warnings[:10])

    source_unavailable = False
    if population_reference_month and month_lag(month, population_reference_month) is not None and month_lag(month, population_reference_month) > 1:
        source_unavailable = True
        warnings.append(f"population source appears lagged for {month}: latest reference month is {population_reference_month}")
    if jobs_snapshot_month and jobs_snapshot_month < month:
        source_unavailable = True
        warnings.append(f"job source appears unavailable for {month}: latest downloaded snapshot is {jobs_snapshot_month}")

    return {
        "target_snapshot": month,
        "latest_existing_snapshot": periods[-1] if periods else None,
        "available_periods": periods,
        "previous_available_period": previous,
        "period_gap_months": month_lag(month, previous) if previous else None,
        "district_count": len(STANDARD_DISTRICTS),
        "output_paths": {
            "staging": str((STAGING_DIR / month).relative_to(PROJECT_ROOT)),
            "history": str((HISTORY_DIR / month).relative_to(PROJECT_ROOT)),
            "raw_snapshot": str((RAW_SNAPSHOT_DIR / month).relative_to(PROJECT_ROOT)),
            "pipeline_report": str((REPORT_DIR / f"{month}.json").relative_to(PROJECT_ROOT)),
        },
        "sources": {
            "population": {
                "reference_month": population_reference_month,
                "freshness": freshness_status(month, population_reference_month),
                "row_count": population_validation.row_count,
                "planned_files": [str(path.relative_to(PROJECT_ROOT)) for path in population_paths],
            },
            "jobs": {
                "jobs_snapshot_as_of": jobs_snapshot_as_of,
                "download_snapshot_month": jobs_snapshot_month,
                "freshness": freshness_status(month, jobs_snapshot_month),
                "row_count": job_validation.row_count,
                "planned_files": [str(path.relative_to(PROJECT_ROOT)) for path in job_paths],
            },
        },
        "will_produce_mom": previous is not None,
        "would_create_snapshot": not errors and not source_unavailable,
        "source_unavailable": source_unavailable,
        "errors": errors,
        "warnings": warnings,
        "forecast_readiness_after_run": forecast_readiness(len(set([*periods, month]))),
    }


def stage_raw_sources(month: str, *, force: bool = False) -> dict[str, Any]:
    staging = STAGING_DIR / month
    if staging.exists():
        shutil.rmtree(staging)
    population = PopulationSourceAdapter()
    jobs = JobSourceAdapter()
    population_paths = population.fetch(staging / "raw_snapshots" / month / "population", force=force)
    job_paths = jobs.fetch(staging / "raw_snapshots" / month / "jobs", force=force)
    population_validation = population.validate_raw(population_paths)
    job_validation = jobs.validate_raw(job_paths)
    if not population_validation.ok or not job_validation.ok:
        raise RuntimeError("; ".join([*population_validation.errors, *job_validation.errors]))
    return {
        "staging": staging,
        "source_manifest": {
            "snapshot_month": month,
            "snapshot_as_of": datetime.now().isoformat(timespec="seconds"),
            "sources": {
                "population": population.get_provenance(population_paths),
                "jobs": jobs.get_provenance(job_paths),
            },
        },
    }


def commit_raw_snapshot(month: str, staging: Path, *, force: bool = False) -> Path:
    source = staging / "raw_snapshots" / month
    target = RAW_SNAPSHOT_DIR / month
    if target.exists():
        if not force:
            raise FileExistsError(f"raw snapshot already exists: {target}")
        backup_existing(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))
    return target


def run_pipeline(month: str, *, dry_run: bool = False, force: bool = False, fail_after_stage: bool = False) -> dict[str, Any]:
    started_at = datetime.now().isoformat(timespec="seconds")
    report = {
        "run_started_at": started_at,
        "run_completed_at": None,
        "status": "running",
        "snapshot_month": month,
        "steps": [],
        "errors": [],
        "warnings": [],
    }
    plan = preflight(month, force=force)
    report["preflight"] = plan
    report["warnings"].extend(plan["warnings"])
    if dry_run:
        report["status"] = "dry_run_complete"
        report["run_completed_at"] = datetime.now().isoformat(timespec="seconds")
        report["snapshot_created"] = False
        return report
    if plan["errors"] or plan["source_unavailable"]:
        report["status"] = "failed"
        report["errors"].extend(plan["errors"])
        if plan["source_unavailable"]:
            report["errors"].append("source unavailable / not yet published for target snapshot")
        report["run_completed_at"] = datetime.now().isoformat(timespec="seconds")
        write_report(month, report)
        return report

    try:
        stage_info = stage_raw_sources(month, force=force)
        report["steps"].append({"step": "stage_raw_sources", "status": "ok"})
        if fail_after_stage:
            raise RuntimeError("simulated failure after staging")
        commands = [
            [sys.executable, "scripts/build_youth_employment_map.py"],
            [sys.executable, "scripts/export_website_data.py"],
            [sys.executable, "scripts/validate_youth_employment_data.py"],
        ]
        for command in commands:
            result = run_command(command)
            report["steps"].append({"step": result["command"], "status": "ok" if result["returncode"] == 0 else "failed"})
            if result["returncode"] != 0:
                raise RuntimeError(f"command failed: {result['command']}")
        raw_target = commit_raw_snapshot(month, stage_info["staging"], force=force)
        report["raw_snapshot"] = str(raw_target.relative_to(PROJECT_ROOT))
        source_manifest_path = HISTORY_DIR / month / "source_manifest.json"
        (HISTORY_DIR / month).mkdir(parents=True, exist_ok=True)
        source_manifest_path.write_text(json.dumps(clean_json_value(stage_info["source_manifest"]), ensure_ascii=False, indent=2), encoding="utf-8")
        snapshot_command = [sys.executable, "scripts/create_monthly_snapshot.py", "--month", month]
        if force:
            snapshot_command.append("--force")
        snapshot_result = run_command(snapshot_command)
        report["steps"].append({"step": snapshot_result["command"], "status": "ok" if snapshot_result["returncode"] == 0 else "failed"})
        if snapshot_result["returncode"] != 0:
            raise RuntimeError("snapshot creation failed")
        validation_result = run_command([sys.executable, "scripts/validate_historical_data.py"])
        report["steps"].append({"step": validation_result["command"], "status": "ok" if validation_result["returncode"] == 0 else "failed"})
        if validation_result["returncode"] != 0:
            raise RuntimeError("historical validation failed")
        report["snapshot_created"] = True
        report["previous_period"] = plan["previous_available_period"]
        report["MoM_available"] = plan["will_produce_mom"]
        report["status"] = "success"
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append(str(exc))
        history_target = HISTORY_DIR / month
        if not (history_target / "youth_employment_map.csv").exists():
            report["snapshot_created"] = False
        if (STAGING_DIR / month).exists():
            shutil.rmtree(STAGING_DIR / month)
    report["run_completed_at"] = datetime.now().isoformat(timespec="seconds")
    write_report(month, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run monthly ingestion and snapshot pipeline.")
    parser.add_argument("--month", required=True, help="Target analytical snapshot label in YYYY-MM format.")
    parser.add_argument("--dry-run", action="store_true", help="Run preflight and print planned actions without writing files.")
    parser.add_argument("--force", action="store_true", help="Explicitly replace an existing target month.")
    parser.add_argument("--fail-after-stage", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    report = run_pipeline(args.month, dry_run=args.dry_run, force=args.force, fail_after_stage=args.fail_after_stage)
    print(json.dumps(clean_json_value(report), ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"success", "dry_run_complete"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
