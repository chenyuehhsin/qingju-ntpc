from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ai_decision_engine import answer_query, parse_constraints  # noqa: E402


def assert_salary_floor() -> None:
    result = answer_query("月薪至少40000")
    jobs = result["matching_jobs"]
    assert result["intent"] == "personalized_recommendation"
    for job in jobs:
        assert job.get("salary_min") is not None
        assert int(job["salary_min"]) >= 40000


def assert_full_time_filter() -> None:
    result = answer_query("全職")
    jobs = result["matching_jobs"]
    assert result["intent"] == "personalized_recommendation"
    assert jobs
    assert all(job.get("work_type") == "全職" for job in jobs)


def assert_xinzhuang_parse() -> None:
    constraints = parse_constraints("我住新莊，想找資訊相關工作")
    assert constraints["preferred_district"] == "新莊區"


def assert_low_reliability_warning() -> None:
    result = answer_query("平溪為什麼 Index 很高，但系統提醒我要小心？")
    assert result["intent"] == "explain_district"
    assert "資料可靠度偏低" in result["answer"]
    assert result["district_explanation"]["district"] == "平溪區"


def assert_no_fabricated_results() -> None:
    result = answer_query("我想找火星採礦工程師月薪至少999萬")
    assert result["intent"] == "personalized_recommendation"
    assert result["recommendations"] == []
    assert "目前沒有找到符合條件的職缺" in result["answer"]


def assert_data_freshness_evidence() -> None:
    result = answer_query("這是幾月資料？")
    assert result["intent"] == "data_freshness"
    assert result["temporal_evidence"]["latest_snapshot"] == "2026-08"
    assert result["temporal_evidence"]["population_reference_month"] == "2026-07"
    assert "2026-08" in result["answer"]


def main() -> int:
    tests = [
        assert_salary_floor,
        assert_full_time_filter,
        assert_xinzhuang_parse,
        assert_low_reliability_warning,
        assert_no_fabricated_results,
        assert_data_freshness_evidence,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
