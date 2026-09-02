from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_cleaner import STANDARD_DISTRICTS  # noqa: E402


def main() -> int:
    website_data = PROJECT_ROOT / "website" / "data"
    history_path = website_data / "youth_employment_history.json"
    processed_path = PROJECT_ROOT / "data" / "processed" / "youth_employment_map.csv"
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else {}
    df = pd.read_csv(processed_path, encoding="utf-8-sig") if processed_path.exists() else pd.DataFrame()
    records = df[df["district"].isin(STANDARD_DISTRICTS)] if "district" in df else pd.DataFrame()
    latest = history.get("latest_snapshot") or history.get("history_manifest", {}).get("latest_period")
    latest_rows = [row for row in history.get("records", []) if row.get("snapshot_month") == latest]
    first = latest_rows[0] if latest_rows else {}
    build_info = {
        "pipeline_version": first.get("pipeline_version") or "demo_readiness_v1",
        "snapshot_month": latest,
        "district_count": int(len(records)),
        "validation_status": "passed" if len(records) == 29 else "failed",
        "population_reference_month": first.get("population_reference_month"),
        "jobs_reference_date": first.get("jobs_reference_date"),
        "jobs_snapshot_as_of": first.get("jobs_snapshot_as_of"),
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "demo_mode_supported": True,
    }
    website_data.mkdir(parents=True, exist_ok=True)
    (website_data / "build_info.json").write_text(json.dumps(build_info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote website/data/build_info.json ({build_info['validation_status']})")
    return 0 if build_info["validation_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
