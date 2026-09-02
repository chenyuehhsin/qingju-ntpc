from __future__ import annotations

import math

import pandas as pd

INDEX_WEIGHTS: dict[str, float] = {
    "opportunity": 0.40,
    "salary": 0.25,
    "diversity": 0.20,
    "stability": 0.15,
}

INDEX_SCORE_COLUMNS: dict[str, str] = {
    "opportunity": "opportunity_score",
    "salary": "salary_score",
    "diversity": "job_diversity_score",
    "stability": "employment_stability_score",
}

SENSITIVITY_SCENARIOS: dict[str, dict[str, float]] = {
    "baseline": INDEX_WEIGHTS,
    "scenario_b": {"opportunity": 0.50, "salary": 0.20, "diversity": 0.15, "stability": 0.15},
    "scenario_c": {"opportunity": 0.30, "salary": 0.35, "diversity": 0.20, "stability": 0.15},
    "scenario_d": {"opportunity": 0.30, "salary": 0.20, "diversity": 0.30, "stability": 0.20},
}

RELIABILITY_CONFIG: dict[str, object] = {
    "sample_thresholds": {
        "job_postings": 240,
        "job_openings": 800,
        "salary_sample_size": 150,
        "diversity_sample_size": 240,
        "stability_sample_size": 220,
        "youth_denominator": 5000,
    },
    "level_thresholds": {
        "high": 80,
        "medium": 60,
    },
    "dimension_weights": INDEX_WEIGHTS,
    "opportunity_components": {
        "job_postings": 0.55,
        "job_openings": 0.35,
        "youth_denominator": 0.10,
    },
    "coverage_component_weight": 0.30,
}


def jobs_per_1000_youth(job_openings: object, youth_population: object) -> float | pd.NA:
    openings = pd.to_numeric(pd.Series([job_openings]), errors="coerce").iloc[0]
    youth = pd.to_numeric(pd.Series([youth_population]), errors="coerce").iloc[0]
    if pd.isna(openings) or pd.isna(youth) or youth <= 0:
        return pd.NA
    return float(openings) / float(youth) * 1000


def aggregate_rate(job_openings: pd.Series, youth_population: pd.Series) -> float | pd.NA:
    openings_total = pd.to_numeric(job_openings, errors="coerce").sum(min_count=1)
    youth_total = pd.to_numeric(youth_population, errors="coerce").sum(min_count=1)
    return jobs_per_1000_youth(openings_total, youth_total)


def coverage_percentage(values: pd.Series) -> float | pd.NA:
    total = len(values)
    if total == 0:
        return pd.NA
    clean = values.dropna()
    clean = clean[clean.astype(str).str.strip() != ""]
    return float(len(clean) / total * 100)


def percentile_score(values: pd.Series) -> pd.Series:
    """Return 0-100 percentile-rank scores, so one extreme value does not dominate."""
    numeric = pd.to_numeric(values, errors="coerce")
    result = pd.Series(pd.NA, index=values.index, dtype="Float64")
    valid = numeric.dropna()
    if valid.empty:
        return result
    if len(valid) == 1:
        result.loc[valid.index] = 100.0
        return result
    ranks = valid.rank(method="average", ascending=True)
    result.loc[valid.index] = (ranks - 1) / (len(valid) - 1) * 100
    return result


def normalized_shannon_entropy(categories: pd.Series) -> float | pd.NA:
    clean = categories.dropna()
    clean = clean[clean.astype(str).str.strip() != ""]
    if clean.empty:
        return pd.NA
    counts = clean.astype(str).value_counts()
    if len(counts) == 1:
        return 0.0
    probabilities = counts / counts.sum()
    entropy = -sum(float(p) * math.log(float(p)) for p in probabilities)
    return float(entropy / math.log(len(counts)) * 100)


def employment_stability_score(work_types: pd.Series) -> float | pd.NA:
    clean = work_types.dropna().astype(str).str.strip()
    clean = clean[clean != ""]
    if clean.empty or "全職" not in set(clean):
        return pd.NA
    return float((clean == "全職").sum() / len(clean) * 100)


def composite_index(row: pd.Series, weights: dict[str, float] | None = None) -> tuple[float | pd.NA, float, str]:
    active_weights = weights or INDEX_WEIGHTS
    available: list[tuple[str, float, float]] = []
    for dimension, weight in active_weights.items():
        score = pd.to_numeric(pd.Series([row.get(INDEX_SCORE_COLUMNS[dimension])]), errors="coerce").iloc[0]
        if pd.notna(score):
            available.append((dimension, weight, float(score)))

    if not available:
        return pd.NA, 0.0, ""

    available_weight = sum(weight for _dimension, weight, _score in available)
    score = sum(score * (weight / available_weight) for _dimension, weight, score in available)
    dimensions = ";".join(dimension for dimension, _weight, _score in available)
    return float(score), float(available_weight * 100), dimensions


def count_present(values: pd.Series) -> int:
    clean = values.dropna()
    clean = clean[clean.astype(str).str.strip() != ""]
    return int(len(clean))


def sample_reliability(sample_size: object, threshold: float) -> float | pd.NA:
    n = pd.to_numeric(pd.Series([sample_size]), errors="coerce").iloc[0]
    if pd.isna(n) or n < 0:
        return pd.NA
    if threshold <= 0:
        return pd.NA
    return float(min(1.0, math.log1p(float(n)) / math.log1p(float(threshold))) * 100)


def coverage_factor(coverage: object) -> float | pd.NA:
    value = pd.to_numeric(pd.Series([coverage]), errors="coerce").iloc[0]
    if pd.isna(value):
        return pd.NA
    return float(max(0.0, min(100.0, float(value))))


def weighted_known(values: list[tuple[object, float]]) -> float | pd.NA:
    clean: list[tuple[float, float]] = []
    for value, weight in values:
        numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        if pd.notna(numeric):
            clean.append((float(numeric), weight))
    if not clean:
        return pd.NA
    weight_sum = sum(weight for _value, weight in clean)
    return float(sum(value * weight for value, weight in clean) / weight_sum)


def reliability_level(score: object) -> str | pd.NA:
    numeric = pd.to_numeric(pd.Series([score]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return pd.NA
    thresholds = RELIABILITY_CONFIG["level_thresholds"]
    if float(numeric) >= thresholds["high"]:
        return "High"
    if float(numeric) >= thresholds["medium"]:
        return "Medium"
    return "Low"


def add_reliability_scores(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    thresholds = RELIABILITY_CONFIG["sample_thresholds"]
    opportunity_components = RELIABILITY_CONFIG["opportunity_components"]
    coverage_weight = float(RELIABILITY_CONFIG["coverage_component_weight"])

    result["opportunity_reliability"] = [
        weighted_known(
            [
                (sample_reliability(row.get("job_postings"), thresholds["job_postings"]), opportunity_components["job_postings"]),
                (sample_reliability(row.get("job_openings"), thresholds["job_openings"]), opportunity_components["job_openings"]),
                (sample_reliability(row.get("youth_population_18_35"), thresholds["youth_denominator"]), opportunity_components["youth_denominator"]),
            ]
        )
        for _idx, row in result.iterrows()
    ]
    result["salary_reliability"] = [
        weighted_known(
            [
                (sample_reliability(row.get("salary_sample_size"), thresholds["salary_sample_size"]), 1 - coverage_weight),
                (coverage_factor(row.get("salary_data_coverage")), coverage_weight),
            ]
        )
        for _idx, row in result.iterrows()
    ]
    result["diversity_reliability"] = [
        weighted_known(
            [
                (sample_reliability(row.get("diversity_sample_size"), thresholds["diversity_sample_size"]), 1 - coverage_weight),
                (coverage_factor(row.get("category_data_coverage")), coverage_weight),
            ]
        )
        for _idx, row in result.iterrows()
    ]
    result["stability_reliability"] = [
        weighted_known(
            [
                (sample_reliability(row.get("stability_sample_size"), thresholds["stability_sample_size"]), 1 - coverage_weight),
                (coverage_factor(row.get("work_type_data_coverage")), coverage_weight),
            ]
        )
        for _idx, row in result.iterrows()
    ]

    result["index_reliability_score"] = [
        weighted_known(
            [
                (row.get("opportunity_reliability"), INDEX_WEIGHTS["opportunity"]),
                (row.get("salary_reliability"), INDEX_WEIGHTS["salary"]),
                (row.get("diversity_reliability"), INDEX_WEIGHTS["diversity"]),
                (row.get("stability_reliability"), INDEX_WEIGHTS["stability"]),
            ]
        )
        for _idx, row in result.iterrows()
    ]
    result["index_reliability_level"] = result["index_reliability_score"].map(reliability_level)
    return result


def ranked_series(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    result = pd.Series(pd.NA, index=values.index, dtype="Int64")
    ranked = numeric.dropna().sort_values(ascending=False, kind="mergesort")
    for rank, idx in enumerate(ranked.index, start=1):
        result.loc[idx] = rank
    return result


def add_sensitivity_analysis(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for scenario, weights in SENSITIVITY_SCENARIOS.items():
        scores = result.apply(lambda row: composite_index(row, weights)[0], axis=1)
        result[f"{scenario}_index"] = scores
        result[f"{scenario}_rank"] = ranked_series(scores)

    result["baseline_rank"] = result["baseline_rank"].astype("Int64")
    scenario_rank_columns = ["baseline_rank", "scenario_b_rank", "scenario_c_rank", "scenario_d_rank"]
    result["rank_min"] = result[scenario_rank_columns].min(axis=1, skipna=True)
    result["rank_max"] = result[scenario_rank_columns].max(axis=1, skipna=True)
    result["rank_range"] = result["rank_max"] - result["rank_min"]
    max_range = max(len(result.dropna(subset=["youth_employment_opportunity_index"])) - 1, 1)
    result["index_rank_stability"] = (1 - pd.to_numeric(result["rank_range"], errors="coerce") / max_range) * 100
    return result


def add_opportunity_index_scores(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["opportunity_score"] = percentile_score(result["jobs_per_1000_youth"])
    result["salary_score"] = percentile_score(result["median_salary"])

    composites = result.apply(composite_index, axis=1, result_type="expand")
    result["youth_employment_opportunity_index"] = composites[0]
    result["index_coverage"] = composites[1]
    result["index_available_dimensions"] = composites[2]
    result = add_reliability_scores(result)
    result = add_sensitivity_analysis(result)
    return result
