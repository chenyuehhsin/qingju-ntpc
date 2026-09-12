"""Audit real available employment months, never train or fabricate forecasts."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def audit(root=ROOT):
    path = root / "data/processed/employment/new_taipei_employment_summary.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    dates = sorted({r["source_snapshot_date"] for r in rows if r["source_snapshot_date"]})
    months = sorted({d[:7] for d in dates})
    return {
        "status": "not_ready", "available_months": months, "snapshot_dates": dates,
        "verified_monthly_series_count": 0,
        "evidence_files": [path.relative_to(root).as_posix()],
        "minimum_data_requirement": {"exploratory_gate": "12 comparable consecutive monthly snapshots plus rolling validation",
                                     "seasonality_goal": "24–36 months; still requires coverage/stability audit and baseline evaluation",
                                     "basis": "Proposed project collection gates, not an AWS requirement or guarantee of sufficiency"},
        "candidate_target": "district × stable occupation category monthly unique postings / hiring demand proxy, not confirmed vacancies",
        "candidate_features": ["lagged postings and hiring counts", "seasonality", "salary sample coverage", "source coverage", "same-period youth population with availability lag"],
        "data_gaps": ["One employment snapshot is not a monthly time series.",
                      "Summary has only top_job_category, no complete district/category panel.",
                      "Cross-month occupation taxonomy, deduplication and district coverage are unverified.",
                      "Annual age-proxy unemployment series cannot replace monthly district/category job demand.",
                      "Raw employment file is excluded from Git; no reproducible historical archive is available in this checkout."],
        "recommended_collection_plan": ["Archive immutable monthly source responses, fetch dates, reference periods and hashes.",
                                        "Record taxonomy version, job IDs, district mapping, missing and late records.",
                                        "Build comparable district/category panels; distinguish zero from missing.",
                                        "Use chronological holdout and rolling-origin backtests against seasonal/naive baselines before SageMaker deployment."],
        "forecast_contract": {"prediction": None, "uncertainty": None, "training_period": None, "model_version": None, "prediction_is_fact": False},
    }


if __name__ == "__main__":
    report = audit()
    (ROOT / "docs/FORECAST_READINESS_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
