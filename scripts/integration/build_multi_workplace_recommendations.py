#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

COMMUTE_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "commute_by_workplace.csv"
CANDIDATE_LOCATIONS_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "candidate_locations_expanded.csv"
HOUSING_BENCHMARK_CSV = (
    PROJECT_ROOT / "data" / "processed" / "housing" / "moi_independent_suite_rent_benchmark.csv"
)
LIVABILITY_CSV = PROJECT_ROOT / "data" / "processed" / "livability" / "livability_by_candidate.csv"
RENT_COMMUTE_OUTPUT_CSV = (
    PROJECT_ROOT / "data" / "processed" / "integration" / "rent_commute_candidates_by_workplace.csv"
)
RECOMMENDATION_OUTPUT_CSV = (
    PROJECT_ROOT / "data" / "processed" / "integration" / "preference_recommendations_by_workplace.csv"
)
VALIDATION_OUTPUT_MD = PROJECT_ROOT / "outputs" / "product" / "multi_workplace_validation.md"

EXPECTED_CANDIDATE_COUNT = 16
EXPECTED_WORKPLACE_COUNT = 4
NEIHU_BASELINE_RENT = 19_500
NEIHU_CITY = "臺北市"
NEIHU_DISTRICT = "內湖區"

PREFERENCE_MODES = [
    {"preference_mode": "省租型", "rent_weight": 0.7, "commute_weight": 0.3},
    {"preference_mode": "平衡型", "rent_weight": 0.5, "commute_weight": 0.5},
    {"preference_mode": "通勤型", "rent_weight": 0.3, "commute_weight": 0.7},
]
LIFE_QUALITY_MODE = {
    "preference_mode": "生活品質型",
    "livability_weight": 0.6,
    "rent_weight": 0.2,
    "commute_weight": 0.2,
}
MODE_ORDER = ["省租型", "平衡型", "通勤型", "生活品質型"]
WORKPLACE_ORDER = [
    "gangqian_neihu",
    "taipei_city_hall_xinyi",
    "taipei_main_zhongzheng",
    "nangang_nangang",
]


def normalize_min_max(series: pd.Series) -> pd.Series:
    min_value = series.min()
    max_value = series.max()
    value_range = max_value - min_value
    if value_range == 0:
        return pd.Series(0.0, index=series.index)
    return (series - min_value) / value_range


def add_pareto_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    efficient: list[bool] = []
    dominated_by: list[str] = []
    for idx, row in result.iterrows():
        others = result.drop(index=idx)
        dominates = (
            (others["official_median_rent"] <= row["official_median_rent"])
            & (others["commute_minutes"] <= row["commute_minutes"])
            & (
                (others["official_median_rent"] < row["official_median_rent"])
                | (others["commute_minutes"] < row["commute_minutes"])
            )
        )
        dominators = others.loc[dominates].sort_values(
            ["commute_minutes", "official_median_rent", "candidate_name"]
        )["candidate_name"].tolist()
        efficient.append(len(dominators) == 0)
        dominated_by.append("; ".join(dominators))
    result["is_pareto_efficient"] = efficient
    result["dominated_by"] = dominated_by
    return result


def validate_inputs(commute: pd.DataFrame, housing: pd.DataFrame, livability: pd.DataFrame) -> None:
    required_commute = {
        "workplace_id",
        "workplace_name",
        "workplace_district",
        "workplace_lat",
        "workplace_lon",
        "candidate_name",
        "district",
        "commute_minutes",
        "transfer_count",
        "route_summary",
        "query_status",
    }
    missing_commute = required_commute - set(commute.columns)
    if missing_commute:
        raise RuntimeError(f"Commute table missing columns: {sorted(missing_commute)}")
    failed = commute[commute["query_status"] != "success"]
    if not failed.empty:
        details = failed[["workplace_name", "candidate_name", "error_message"]].to_dict("records")
        raise RuntimeError(f"Commute table includes failed routes: {details}")
    if commute.groupby("workplace_id")["candidate_name"].nunique().min() != EXPECTED_CANDIDATE_COUNT:
        counts = commute.groupby("workplace_id")["candidate_name"].nunique().to_dict()
        raise RuntimeError(f"Expected 16 commute rows for every workplace, found {counts}.")
    if commute["workplace_id"].nunique() != EXPECTED_WORKPLACE_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_WORKPLACE_COUNT} workplaces, found {commute['workplace_id'].nunique()}.")

    neihu = housing[(housing["city"] == NEIHU_CITY) & (housing["district"] == NEIHU_DISTRICT)]
    if len(neihu) != 1 or int(neihu.iloc[0]["rent_median"]) != NEIHU_BASELINE_RENT:
        raise RuntimeError("Neihu rent baseline is not the expected 19,500 NTD/month benchmark.")
    if len(livability) != EXPECTED_CANDIDATE_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_CANDIDATE_COUNT} livability rows, found {len(livability)}.")


def build_rent_commute_by_workplace() -> pd.DataFrame:
    commute = pd.read_csv(COMMUTE_CSV)
    locations = pd.read_csv(CANDIDATE_LOCATIONS_CSV)
    housing = pd.read_csv(HOUSING_BENCHMARK_CSV)
    livability = pd.read_csv(LIVABILITY_CSV)
    validate_inputs(commute, housing, livability)

    location_fields = locations[
        [
            "candidate_name",
            "station_name",
            "station_operator",
            "station_uid",
            "station_id",
            "source_endpoint",
            "selection_reason",
            "route_count_at_station",
        ]
    ].copy()
    commute = commute.merge(location_fields, on="candidate_name", how="left", validate="many_to_one")

    ntpc_housing = (
        housing[housing["city"] == "新北市"][["city", "district", "rent_median"]]
        .rename(columns={"city": "official_benchmark_city", "rent_median": "official_median_rent"})
        .copy()
    )
    merged = commute.merge(ntpc_housing, on="district", how="left", validate="many_to_one")
    unmatched = merged[merged["official_median_rent"].isna()]
    if not unmatched.empty:
        details = unmatched[["candidate_name", "district"]].drop_duplicates().to_dict("records")
        raise RuntimeError(f"Housing benchmark join failed for candidates: {details}")

    merged["official_median_rent"] = merged["official_median_rent"].astype(int)
    merged["rent_saving_vs_neihu"] = NEIHU_BASELINE_RENT - merged["official_median_rent"]

    rows = []
    for _, subset in merged.groupby("workplace_id", sort=False):
        rows.append(add_pareto_columns(subset))
    result = pd.concat(rows, ignore_index=True)
    return result[
        [
            "workplace_id",
            "workplace_name",
            "workplace_district",
            "workplace_lat",
            "workplace_lon",
            "candidate_name",
            "district",
            "lat",
            "lon",
            "station_name",
            "station_operator",
            "station_uid",
            "station_id",
            "official_benchmark_city",
            "official_median_rent",
            "commute_minutes",
            "transfer_count",
            "rent_saving_vs_neihu",
            "is_pareto_efficient",
            "dominated_by",
            "selection_reason",
            "route_count_at_station",
            "departure_time",
            "route_summary",
            "source_endpoint",
            "maas_response_file",
        ]
    ].sort_values(["workplace_id", "commute_minutes", "official_median_rent", "candidate_name"])


def build_rent_commute_recommendations(rent_commute: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for workplace_id, workplace_rows in rent_commute.groupby("workplace_id", sort=False):
        pareto = workplace_rows[workplace_rows["is_pareto_efficient"] == True].copy()  # noqa: E712
        if len(pareto) < 3:
            raise RuntimeError(f"{workplace_id} has fewer than three Pareto-efficient candidates.")
        pareto["normalized_rent"] = normalize_min_max(pareto["official_median_rent"])
        pareto["normalized_commute"] = normalize_min_max(pareto["commute_minutes"])
        for mode in PREFERENCE_MODES:
            ranked = pareto.copy()
            ranked["preference_mode"] = mode["preference_mode"]
            ranked["rent"] = ranked["official_median_rent"]
            ranked["rent_weight"] = mode["rent_weight"]
            ranked["commute_weight"] = mode["commute_weight"]
            ranked["preference_cost"] = (
                ranked["rent_weight"] * ranked["normalized_rent"]
                + ranked["commute_weight"] * ranked["normalized_commute"]
            )
            ranked["preference_score"] = 1 - ranked["preference_cost"]
            ranked = ranked.sort_values(
                ["preference_cost", "commute_minutes", "official_median_rent", "candidate_name"]
            ).reset_index(drop=True)
            ranked["rank"] = ranked.index + 1
            rows.append(ranked)
    result = pd.concat(rows, ignore_index=True)
    return result


def build_life_quality_recommendations(rent_commute: pd.DataFrame) -> pd.DataFrame:
    livability = pd.read_csv(LIVABILITY_CSV)
    rows: list[pd.DataFrame] = []
    for _, workplace_rows in rent_commute.groupby("workplace_id", sort=False):
        ranked = workplace_rows.merge(
            livability[
                [
                    "candidate_name",
                    "food_count",
                    "shopping_count",
                    "recreation_count",
                    "culture_count",
                    "medical_count",
                    "total_poi_count",
                    "equal_weight_livability_index",
                ]
            ],
            on="candidate_name",
            how="left",
            validate="one_to_one",
        )
        ranked["normalized_rent"] = normalize_min_max(ranked["official_median_rent"])
        ranked["normalized_commute"] = normalize_min_max(ranked["commute_minutes"])
        ranked["normalized_livability"] = normalize_min_max(ranked["equal_weight_livability_index"])
        ranked["livability_cost"] = 1 - ranked["normalized_livability"]
        ranked["preference_mode"] = LIFE_QUALITY_MODE["preference_mode"]
        ranked["rent"] = ranked["official_median_rent"]
        ranked["rent_weight"] = LIFE_QUALITY_MODE["rent_weight"]
        ranked["commute_weight"] = LIFE_QUALITY_MODE["commute_weight"]
        ranked["livability_weight"] = LIFE_QUALITY_MODE["livability_weight"]
        ranked["preference_cost"] = (
            ranked["rent_weight"] * ranked["normalized_rent"]
            + ranked["commute_weight"] * ranked["normalized_commute"]
            + ranked["livability_weight"] * ranked["livability_cost"]
        )
        ranked["preference_score"] = 1 - ranked["preference_cost"]
        ranked = ranked.sort_values(
            [
                "preference_cost",
                "equal_weight_livability_index",
                "commute_minutes",
                "official_median_rent",
                "candidate_name",
            ],
            ascending=[True, False, True, True, True],
        ).reset_index(drop=True)
        ranked["rank"] = ranked.index + 1
        ranked["livability_index"] = ranked["equal_weight_livability_index"]
        rows.append(ranked)
    return pd.concat(rows, ignore_index=True)


def recommendation_columns(recommendations: pd.DataFrame) -> pd.DataFrame:
    optional = [
        "livability_index",
        "food_count",
        "shopping_count",
        "recreation_count",
        "culture_count",
        "medical_count",
        "total_poi_count",
        "normalized_livability",
        "livability_cost",
        "livability_weight",
    ]
    base = [
        "workplace_id",
        "workplace_name",
        "workplace_district",
        "workplace_lat",
        "workplace_lon",
        "preference_mode",
        "rank",
        "candidate_name",
        "district",
        "lat",
        "lon",
        "rent",
        "official_median_rent",
        "commute_minutes",
        "transfer_count",
        "rent_saving_vs_neihu",
        "preference_cost",
        "preference_score",
        "normalized_rent",
        "normalized_commute",
        "rent_weight",
        "commute_weight",
        "is_pareto_efficient",
        "dominated_by",
        "route_summary",
    ]
    columns = base + [column for column in optional if column in recommendations.columns]
    return recommendations[columns].copy()


def write_validation(recommendations: pd.DataFrame, rent_commute: pd.DataFrame) -> None:
    lines = [
        "# Multi-Workplace Validation",
        "",
        "Scenario: public transit, weekday 08:00 Asia/Taipei, independent-suite rent benchmark.",
        "",
        "| workplace | commute rows | 省租型 Top 1 | 平衡型 Top 1 | 通勤型 Top 1 | 生活品質型 Top 1 |",
        "|---|---:|---|---|---|---|",
    ]
    workplace_order = (
        rent_commute[["workplace_id", "workplace_name", "workplace_district"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    workplace_order["_order"] = workplace_order["workplace_id"].map(
        {workplace_id: index for index, workplace_id in enumerate(WORKPLACE_ORDER)}
    )
    workplace_order = workplace_order.sort_values("_order").drop(columns=["_order"])
    for _, workplace in workplace_order.iterrows():
        subset = recommendations[recommendations["workplace_id"] == workplace["workplace_id"]]
        top1 = {
            mode: subset[(subset["preference_mode"] == mode) & (subset["rank"] == 1)].iloc[0]["candidate_name"]
            for mode in MODE_ORDER
        }
        commute_count = len(rent_commute[rent_commute["workplace_id"] == workplace["workplace_id"]])
        lines.append(
            f"| {workplace['workplace_name']}｜{workplace['workplace_district']} | {commute_count}/16 | "
            f"{top1['省租型']} | {top1['平衡型']} | {top1['通勤型']} | {top1['生活品質型']} |"
        )
    lines += [
        "",
        "Checks:",
        "",
        "- Every workplace has 16 successful candidate commute rows.",
        "- Rent and livability inputs are unchanged across workplaces.",
        "- Rent x Commute modes rank only each workplace's Pareto-efficient candidates.",
        "- 生活品質型 ranks all 16 candidates per workplace using the existing MVP weights.",
    ]
    VALIDATION_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    RENT_COMMUTE_OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    RECOMMENDATION_OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    rent_commute = build_rent_commute_by_workplace()
    rent_commute.to_csv(RENT_COMMUTE_OUTPUT_CSV, index=False, encoding="utf-8")

    rent_commute_recommendations = build_rent_commute_recommendations(rent_commute)
    life_quality_recommendations = build_life_quality_recommendations(rent_commute)
    recommendations = recommendation_columns(
        pd.concat([rent_commute_recommendations, life_quality_recommendations], ignore_index=True, sort=False)
    )
    recommendations["_workplace_order"] = recommendations["workplace_id"].map(
        {workplace_id: index for index, workplace_id in enumerate(WORKPLACE_ORDER)}
    )
    recommendations["_mode_order"] = recommendations["preference_mode"].map(
        {mode: index for index, mode in enumerate(MODE_ORDER)}
    )
    recommendations = recommendations.sort_values(["_workplace_order", "_mode_order", "rank"]).drop(
        columns=["_workplace_order", "_mode_order"]
    )
    recommendations.to_csv(RECOMMENDATION_OUTPUT_CSV, index=False, encoding="utf-8")
    write_validation(recommendations, rent_commute)

    print(f"Wrote {RENT_COMMUTE_OUTPUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {RECOMMENDATION_OUTPUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {VALIDATION_OUTPUT_MD.relative_to(PROJECT_ROOT)}")
    for workplace_id, subset in recommendations.groupby("workplace_id", sort=False):
        workplace_name = subset.iloc[0]["workplace_name"]
        tops = []
        for mode in MODE_ORDER:
            top = subset[(subset["preference_mode"] == mode) & (subset["rank"] == 1)].iloc[0]
            tops.append(f"{mode}={top['candidate_name']}")
        print(f"{workplace_name}: " + ", ".join(tops))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
