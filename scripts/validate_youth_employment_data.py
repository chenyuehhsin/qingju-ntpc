from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_cleaner import STANDARD_DISTRICTS  # noqa: E402
from src.data_loader import PROCESSED_CSV, read_processed  # noqa: E402
from src.metrics import INDEX_SCORE_COLUMNS, INDEX_WEIGHTS, RELIABILITY_CONFIG, SENSITIVITY_SCENARIOS  # noqa: E402


REQUIRED_COLUMNS = [
    "district",
    "youth_population_18_35",
    "job_postings",
    "job_openings",
    "jobs_per_1000_youth",
]

INDEX_COLUMNS = [
    "opportunity_score",
    "salary_score",
    "job_diversity_score",
    "employment_stability_score",
    "youth_employment_opportunity_index",
    "index_coverage",
    "index_available_dimensions",
]

RELIABILITY_COLUMNS = [
    "salary_valid_count",
    "category_valid_count",
    "work_type_valid_count",
    "salary_sample_size",
    "diversity_sample_size",
    "stability_sample_size",
    "opportunity_reliability",
    "salary_reliability",
    "diversity_reliability",
    "stability_reliability",
    "index_reliability_score",
    "index_reliability_level",
    "baseline_index",
    "scenario_b_index",
    "scenario_c_index",
    "scenario_d_index",
    "baseline_rank",
    "scenario_b_rank",
    "scenario_c_rank",
    "scenario_d_rank",
    "rank_min",
    "rank_max",
    "rank_range",
    "index_rank_stability",
]


def check(condition: bool, severity: str, message: str, findings: list[tuple[str, str]]) -> None:
    if condition:
        print(f"PASS: {message}")
    else:
        print(f"{severity}: {message}")
        findings.append((severity, message))


def valid_score_range(series: pd.Series) -> bool:
    numeric = pd.to_numeric(series, errors="coerce")
    return not ((numeric < 0) | (numeric > 100)).any()


def expected_index(row: pd.Series) -> tuple[float | None, float, str]:
    dimensions: list[tuple[str, float, float]] = []
    for dimension, column in INDEX_SCORE_COLUMNS.items():
        value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
        if pd.notna(value):
            dimensions.append((dimension, INDEX_WEIGHTS[dimension], float(value)))

    if not dimensions:
        return None, 0.0, ""

    weight_sum = sum(weight for _dimension, weight, _score in dimensions)
    score = sum(score * (weight / weight_sum) for _dimension, weight, score in dimensions)
    return float(score), float(weight_sum * 100), ";".join(dimension for dimension, _weight, _score in dimensions)


def expected_index_with_weights(row: pd.Series, weights: dict[str, float]) -> float | None:
    dimensions: list[tuple[float, float]] = []
    for dimension, weight in weights.items():
        value = pd.to_numeric(pd.Series([row.get(INDEX_SCORE_COLUMNS[dimension])]), errors="coerce").iloc[0]
        if pd.notna(value):
            dimensions.append((float(value), weight))
    if not dimensions:
        return None
    weight_sum = sum(weight for _score, weight in dimensions)
    return float(sum(score * (weight / weight_sum) for score, weight in dimensions))


def expected_reliability_level(score: object) -> str | None:
    numeric = pd.to_numeric(pd.Series([score]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    thresholds = RELIABILITY_CONFIG["level_thresholds"]
    if float(numeric) >= thresholds["high"]:
        return "High"
    if float(numeric) >= thresholds["medium"]:
        return "Medium"
    return "Low"


def main() -> int:
    if not PROCESSED_CSV.exists():
        print(f"ERROR: Missing processed CSV: {PROCESSED_CSV}")
        return 1

    df = read_processed(PROCESSED_CSV)
    findings: list[tuple[str, str]] = []

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    check(not missing_columns, "ERROR", f"required columns present; missing={missing_columns}", findings)

    if missing_columns:
        return 1

    check(len(df) == 29, "ERROR", f"dataset has 29 districts; actual={len(df)}", findings)
    check(not df["district"].duplicated().any(), "ERROR", "district is not duplicated", findings)

    illegal = sorted(set(df["district"].dropna()) - set(STANDARD_DISTRICTS))
    check(not illegal, "ERROR", f"all district names are legal; illegal={illegal}", findings)

    missing_districts = [district for district in STANDARD_DISTRICTS if district not in set(df["district"])]
    check(not missing_districts, "ERROR", f"all standard districts exist; missing={missing_districts}", findings)

    youth = pd.to_numeric(df["youth_population_18_35"], errors="coerce")
    openings = pd.to_numeric(df["job_openings"], errors="coerce")
    rate = pd.to_numeric(df["jobs_per_1000_youth"], errors="coerce")

    check(not (youth < 0).any(), "ERROR", "youth_population_18_35 has no negative values", findings)
    check(not (openings < 0).any(), "ERROR", "job_openings has no negative values", findings)
    check(not (rate < 0).any(), "ERROR", "jobs_per_1000_youth has no negative values", findings)
    check(not (rate > 1000).any(), "WARN", "jobs_per_1000_youth is <= 1000 where known", findings)

    missing_summary = df[REQUIRED_COLUMNS].isna().sum()
    missing_dict = {column: int(count) for column, count in missing_summary.items() if count}
    check(not missing_dict, "WARN", f"required metric fields have no missing values; missing={missing_dict}", findings)

    missing_index_columns = [column for column in INDEX_COLUMNS if column not in df.columns]
    check(not missing_index_columns, "ERROR", f"index columns present; missing={missing_index_columns}", findings)

    if not missing_index_columns:
        for column in INDEX_COLUMNS:
            if column == "index_available_dimensions":
                continue
            check(valid_score_range(df[column]), "ERROR", f"{column} values are within 0-100 where known", findings)

        for source_column, score_column in [
            ("jobs_per_1000_youth", "opportunity_score"),
            ("median_salary", "salary_score"),
        ]:
            if source_column in df.columns:
                source_missing = pd.to_numeric(df[source_column], errors="coerce").isna()
                score_present_when_source_missing = pd.to_numeric(df.loc[source_missing, score_column], errors="coerce").notna()
                check(
                    not score_present_when_source_missing.any(),
                    "ERROR",
                    f"{score_column} stays null when {source_column} is missing",
                    findings,
                )

        index_errors = []
        dimension_errors = []
        coverage_errors = []
        for idx, row in df.iterrows():
            expected_score, expected_coverage, expected_dimensions = expected_index(row)
            actual_score = pd.to_numeric(pd.Series([row["youth_employment_opportunity_index"]]), errors="coerce").iloc[0]
            actual_coverage = pd.to_numeric(pd.Series([row["index_coverage"]]), errors="coerce").iloc[0]
            actual_dimensions = "" if pd.isna(row["index_available_dimensions"]) else str(row["index_available_dimensions"])

            if expected_score is None:
                if pd.notna(actual_score):
                    index_errors.append(str(row["district"]))
            elif pd.isna(actual_score) or abs(float(actual_score) - expected_score) > 1e-6:
                index_errors.append(str(row["district"]))

            if pd.isna(actual_coverage) or abs(float(actual_coverage) - expected_coverage) > 1e-6:
                coverage_errors.append(str(row["district"]))

            if actual_dimensions != expected_dimensions:
                dimension_errors.append(str(row["district"]))

        check(not index_errors, "ERROR", f"final index matches normalized weights; mismatches={index_errors}", findings)
        check(not coverage_errors, "ERROR", f"index_coverage matches available raw weights; mismatches={coverage_errors}", findings)
        check(not dimension_errors, "ERROR", f"index_available_dimensions matches non-null sub-scores; mismatches={dimension_errors}", findings)

    missing_reliability_columns = [column for column in RELIABILITY_COLUMNS if column not in df.columns]
    check(not missing_reliability_columns, "ERROR", f"reliability columns present; missing={missing_reliability_columns}", findings)

    scenario_weight_errors = [
        scenario for scenario, weights in SENSITIVITY_SCENARIOS.items() if abs(sum(weights.values()) - 1.0) > 1e-9
    ]
    check(not scenario_weight_errors, "ERROR", f"sensitivity scenario weights sum to 1; errors={scenario_weight_errors}", findings)

    if not missing_reliability_columns:
        reliability_score_columns = [
            "opportunity_reliability",
            "salary_reliability",
            "diversity_reliability",
            "stability_reliability",
            "index_reliability_score",
            "index_rank_stability",
        ]
        for column in reliability_score_columns:
            check(valid_score_range(df[column]), "ERROR", f"{column} values are within 0-100 where known", findings)

        sample_columns = [
            "salary_valid_count",
            "category_valid_count",
            "work_type_valid_count",
            "salary_sample_size",
            "diversity_sample_size",
            "stability_sample_size",
            "job_postings",
            "job_openings",
        ]
        for column in sample_columns:
            values = pd.to_numeric(df[column], errors="coerce")
            check(not (values < 0).any(), "ERROR", f"{column} sample values are non-negative", findings)

        baseline_mismatch = []
        scenario_mismatch = []
        level_mismatch = []
        rank_stability_mismatch = []
        for _idx, row in df.iterrows():
            baseline = pd.to_numeric(pd.Series([row["baseline_index"]]), errors="coerce").iloc[0]
            actual_index = pd.to_numeric(pd.Series([row["youth_employment_opportunity_index"]]), errors="coerce").iloc[0]
            expected_baseline = expected_index_with_weights(row, SENSITIVITY_SCENARIOS["baseline"])
            if expected_baseline is None or pd.isna(baseline) or pd.isna(actual_index) or abs(float(baseline) - expected_baseline) > 1e-6 or abs(float(actual_index) - expected_baseline) > 1e-6:
                baseline_mismatch.append(str(row["district"]))

            for scenario in ["scenario_b", "scenario_c", "scenario_d"]:
                actual = pd.to_numeric(pd.Series([row[f"{scenario}_index"]]), errors="coerce").iloc[0]
                expected = expected_index_with_weights(row, SENSITIVITY_SCENARIOS[scenario])
                if expected is None or pd.isna(actual) or abs(float(actual) - expected) > 1e-6:
                    scenario_mismatch.append(f"{row['district']}:{scenario}")

            expected_level = expected_reliability_level(row["index_reliability_score"])
            actual_level = None if pd.isna(row["index_reliability_level"]) else str(row["index_reliability_level"])
            if expected_level != actual_level:
                level_mismatch.append(str(row["district"]))

            expected_stability = (1 - float(row["rank_range"]) / 28) * 100
            actual_stability = pd.to_numeric(pd.Series([row["index_rank_stability"]]), errors="coerce").iloc[0]
            if pd.isna(actual_stability) or abs(float(actual_stability) - expected_stability) > 1e-6:
                rank_stability_mismatch.append(str(row["district"]))

        check(not baseline_mismatch, "ERROR", f"baseline scenario equals v1 index; mismatches={baseline_mismatch}", findings)
        check(not scenario_mismatch, "ERROR", f"sensitivity scenario scores match weights; mismatches={scenario_mismatch}", findings)
        check(not level_mismatch, "ERROR", f"reliability level mapping is correct; mismatches={level_mismatch}", findings)
        check(not rank_stability_mismatch, "ERROR", f"rank stability matches rank_range; mismatches={rank_stability_mismatch}", findings)

    error_count = sum(1 for severity, _ in findings if severity == "ERROR")
    warn_count = sum(1 for severity, _ in findings if severity == "WARN")
    print(f"Validation complete: {error_count} error(s), {warn_count} warning(s)")
    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
