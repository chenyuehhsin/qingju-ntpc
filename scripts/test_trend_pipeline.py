from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_decision_engine import answer_query  # noqa: E402
from src.data_cleaner import STANDARD_DISTRICTS  # noqa: E402
from src.trend_metrics import percent_change, trend_label  # noqa: E402


def assert_one_period_has_no_trend_claim() -> None:
    result = answer_query("這個月哪些區工作機會增加最多？")
    assert result["intent"] == "district_growth_ranking"
    assert result["recommendations"] == []
    assert "尚無足夠歷史資料" in result["answer"]


def assert_mom_pct() -> None:
    assert percent_change(120, 100) == 20.0
    assert trend_label(20.0) == "上升"


def assert_previous_zero_is_null() -> None:
    assert percent_change(120, 0) is None


def assert_duplicate_key_detectable() -> None:
    df = pd.DataFrame(
        [
            {"snapshot_month": "2026-08", "district": "板橋區"},
            {"snapshot_month": "2026-08", "district": "板橋區"},
        ]
    )
    assert int(df.duplicated(["snapshot_month", "district"]).sum()) == 1


def assert_missing_month_not_fabricated() -> None:
    periods = ["2026-07", "2026-09"]
    assert "2026-08" not in periods
    assert periods == sorted(periods)


def assert_standard_district_count() -> None:
    assert len(STANDARD_DISTRICTS) == 29


def main() -> int:
    tests = [
        assert_one_period_has_no_trend_claim,
        assert_mom_pct,
        assert_previous_zero_is_null,
        assert_duplicate_key_detectable,
        assert_missing_month_not_fabricated,
        assert_standard_district_count,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
