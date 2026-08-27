from pathlib import Path
import json
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.recommendation import build_category_metrics, recommend_districts
from backend.visualization import load_geojson, make_choropleth, make_scatter


def main() -> None:
    summary = pd.read_csv(ROOT / "data/processed/district_summary.csv", encoding="utf-8-sig")
    jobs = pd.read_csv(
        ROOT / "data/raw/new_taipei_jobs.csv",
        encoding="utf-8-sig",
        usecols=["district", "CJOB_NAME1", "JOB_PERSON"],
    )
    recommendations, metadata = recommend_districts(
        summary,
        build_category_metrics(jobs),
        budget=20_000,
        job_category="不限職類",
    )
    assert len(recommendations) == 3
    assert recommendations["district"].nunique() == 3
    assert metadata["transport_included"] is False

    geojson = load_geojson(ROOT / "data/processed/new_taipei_districts.geojson")
    profile = json.loads((ROOT / "data/processed/data_profile.json").read_text(encoding="utf-8"))
    assert make_choropleth(summary, geojson, "💼 工作機會").data
    assert make_choropleth(summary, geojson, "🏠 租屋成本").data
    assert make_scatter(summary, profile["thresholds"]).data
    print("PASS: recommendation and map smoke tests")


if __name__ == "__main__":
    main()
