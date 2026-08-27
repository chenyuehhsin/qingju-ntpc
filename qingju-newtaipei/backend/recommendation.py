"""依使用者預算與職類產生可解釋的行政區推薦。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .districts import normalize_district


UNLIMITED_CATEGORY = "不限職類"
MIN_RENTAL_CASES = 10


def build_category_metrics(jobs: pd.DataFrame) -> pd.DataFrame:
    """依行政區、第一職類彙整職缺筆數與刊登求才人數。"""
    required = {"district", "CJOB_NAME1", "JOB_PERSON"}
    missing = required - set(jobs.columns)
    if missing:
        raise KeyError(f"職缺資料缺少欄位：{sorted(missing)}")

    work = jobs.copy()
    work["district"] = work["district"].map(normalize_district)
    work["job_category"] = work["CJOB_NAME1"].astype("string").str.strip()
    work["category_hiring_count"] = pd.to_numeric(
        work["JOB_PERSON"].astype("string").str.replace(",", "", regex=False),
        errors="coerce",
    )
    work = work[work["district"].notna() & work["job_category"].notna() & work["job_category"].ne("")]

    return (
        work.groupby(["district", "job_category"], as_index=False)
        .agg(
            category_job_postings=("CJOB_NAME1", "size"),
            category_hiring_count=("category_hiring_count", lambda values: values.sum(min_count=1)),
        )
    )


def _log_score(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").fillna(0).clip(lower=0)
    maximum = numeric.max()
    if maximum <= 0:
        return pd.Series(0.0, index=values.index)
    return np.log1p(numeric) / np.log1p(maximum) * 100


def _evidence_level(rental_count: object) -> str:
    if pd.isna(rental_count) or float(rental_count) < 10:
        return "低"
    if float(rental_count) < 100:
        return "中"
    return "高"


def recommend_districts(
    district_summary: pd.DataFrame,
    category_metrics: pd.DataFrame,
    budget: int,
    job_category: str,
    top_n: int = 3,
) -> tuple[pd.DataFrame, dict]:
    """以預算、職類及資料量排序；交通與工作地點刻意不納入。"""
    if budget <= 0:
        raise ValueError("租屋預算必須大於 0")

    data = district_summary.copy()
    data = data[data["median_rent"].notna()].copy()
    districts_with_housing_data = len(data)
    rental_count = pd.to_numeric(data["rental_count"], errors="coerce")
    enough_evidence = rental_count.ge(MIN_RENTAL_CASES)
    excluded_low_sample_count = int((~enough_evidence).sum())
    data = data[enough_evidence].copy()

    if job_category == UNLIMITED_CATEGORY:
        data["matched_job_postings"] = pd.to_numeric(data["job_postings"], errors="coerce")
        data["matched_hiring_count"] = pd.to_numeric(data["hiring_count"], errors="coerce")
    else:
        selected = category_metrics[category_metrics["job_category"].eq(job_category)].copy()
        selected = selected.rename(
            columns={
                "category_job_postings": "matched_job_postings",
                "category_hiring_count": "matched_hiring_count",
            }
        )
        data = data.merge(
            selected[["district", "matched_job_postings", "matched_hiring_count"]],
            on="district",
            how="left",
            validate="one_to_one",
        )

    data[["matched_job_postings", "matched_hiring_count"]] = data[
        ["matched_job_postings", "matched_hiring_count"]
    ].fillna(0)
    data["budget_gap"] = budget - data["median_rent"]
    data["within_budget"] = data["budget_gap"].ge(0)
    data["has_job_match"] = data["matched_job_postings"].gt(0)
    data["criteria_met_count"] = data["within_budget"].astype(int) + data["has_job_match"].astype(int)
    data["match_status"] = np.select(
        [
            data["within_budget"] & data["has_job_match"],
            data["within_budget"] & ~data["has_job_match"],
            ~data["within_budget"] & data["has_job_match"],
        ],
        ["符合預算與職類", "符合預算，職類機會不足", "職類有機會，但超出預算"],
        default="預算與職類皆不符合",
    )

    # 租金等於預算為 50 分；愈低於預算分數愈高，超過兩倍預算為 0 分。
    data["affordability_score"] = ((2 - data["median_rent"] / budget) * 50).clip(0, 100)
    hiring_score = _log_score(data["matched_hiring_count"])
    posting_score = _log_score(data["matched_job_postings"])
    data["job_match_score"] = hiring_score * 0.65 + posting_score * 0.35
    data["evidence_score"] = _log_score(data["rental_count"])
    data["recommendation_score"] = (
        data["affordability_score"] * 0.55
        + data["job_match_score"] * 0.40
        + data["evidence_score"] * 0.05
    )
    data["evidence_level"] = data["rental_count"].map(_evidence_level)

    def explain(row: pd.Series) -> str:
        if row["within_budget"]:
            housing = f"租金中位數低於預算 NT${row['budget_gap']:,.0f}"
        else:
            housing = f"租金中位數超出預算 NT${-row['budget_gap']:,.0f}"
        category_label = "全部職類" if job_category == UNLIMITED_CATEGORY else job_category
        jobs = (
            f"{category_label}有 {row['matched_job_postings']:,.0f} 筆職缺，"
            f"刊登求才 {row['matched_hiring_count']:,.0f} 人"
        )
        return f"{housing}；{jobs}"

    data["recommendation_reason"] = data.apply(explain, axis=1)
    data = data.sort_values(
        ["criteria_met_count", "recommendation_score", "rental_count"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    data["recommendation_rank"] = data.index + 1

    metadata = {
        "affordable_district_count": int(data["within_budget"].sum()),
        "districts_with_housing_data": int(districts_with_housing_data),
        "districts_scored": int(len(data)),
        "excluded_low_sample_count": excluded_low_sample_count,
        "fully_matched_count": int((data["criteria_met_count"] == 2).sum()),
        "weights": {"affordability": 0.55, "job_match": 0.40, "evidence": 0.05},
        "transport_included": False,
    }
    return data.head(top_n).copy(), metadata

