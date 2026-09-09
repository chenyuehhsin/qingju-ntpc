#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.livability.build_livability_poi import (  # noqa: E402
    POI_CATEGORIES,
    RAW_CACHE_DIR,
    element_matches_category,
    safe_slug,
)

INPUT_CSV = PROJECT_ROOT / "data" / "processed" / "integration" / "rent_commute_candidates_expanded.csv"
LIVABILITY_CSV = PROJECT_ROOT / "data" / "processed" / "livability" / "livability_by_candidate.csv"
OUTPUT_CSV = PROJECT_ROOT / "data" / "processed" / "integration" / "preference_recommendations.csv"
OUTPUT_MD = PROJECT_ROOT / "outputs" / "integration" / "preference_recommendation_summary.md"

PREFERENCE_MODES = [
    {"preference_mode": "省租型", "rent_weight": 0.7, "commute_weight": 0.3},
    {"preference_mode": "平衡型", "rent_weight": 0.5, "commute_weight": 0.5},
    {"preference_mode": "通勤型", "rent_weight": 0.3, "commute_weight": 0.7},
]

EXPECTED_TOP_1 = {
    "省租型": "淡水站",
    "平衡型": "汐止車站",
    "通勤型": "板橋站",
}

LIFE_QUALITY_MODE = {
    "preference_mode": "生活品質型",
    "livability_weight": 0.6,
    "rent_weight": 0.2,
    "commute_weight": 0.2,
}
EXPECTED_CANDIDATE_COUNT = 16
LIVABILITY_RADIUS_METERS = 800
LIVABILITY_SAMPLE_CANDIDATES = ["板橋站", "大坪林站", "五股區公所"]


def format_money(value: float | int) -> str:
    return f"{float(value):,.0f}"


def format_minutes(value: float) -> str:
    return f"{float(value):.1f}"


def normalize_min_max(series: pd.Series) -> pd.Series:
    min_value = series.min()
    max_value = series.max()
    value_range = max_value - min_value
    if value_range == 0:
        return pd.Series(0.0, index=series.index)
    return (series - min_value) / value_range


def load_pareto_candidates() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV)
    required = {
        "candidate_name",
        "district",
        "official_median_rent",
        "commute_minutes",
        "transfer_count",
        "rent_saving_vs_neihu",
        "is_pareto_efficient",
    }
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(f"Input is missing required columns: {sorted(missing)}")

    pareto = df[df["is_pareto_efficient"] == True].copy()  # noqa: E712
    if len(pareto) < 3:
        raise RuntimeError(f"Expected at least 3 Pareto-efficient candidates, found {len(pareto)}.")

    pareto["normalized_rent"] = normalize_min_max(pareto["official_median_rent"])
    pareto["normalized_commute"] = normalize_min_max(pareto["commute_minutes"])
    return pareto


def build_recommendations(pareto: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for mode in PREFERENCE_MODES:
        ranked = pareto.copy()
        ranked["preference_mode"] = mode["preference_mode"]
        ranked["rent"] = ranked["official_median_rent"]
        ranked["rent_weight"] = mode["rent_weight"]
        ranked["commute_weight"] = mode["commute_weight"]
        ranked["preference_cost"] = (
            mode["rent_weight"] * ranked["normalized_rent"]
            + mode["commute_weight"] * ranked["normalized_commute"]
        )
        ranked["preference_score"] = 1 - ranked["preference_cost"]
        ranked = ranked.sort_values(
            ["preference_cost", "commute_minutes", "official_median_rent", "candidate_name"]
        ).reset_index(drop=True)
        ranked["rank"] = ranked.index + 1
        rows.append(ranked)

    result = pd.concat(rows, ignore_index=True)
    return result[
        [
            "preference_mode",
            "rank",
            "candidate_name",
            "district",
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
        ]
    ].copy()


def load_life_quality_candidates() -> pd.DataFrame:
    rent_commute = pd.read_csv(INPUT_CSV)
    livability = pd.read_csv(LIVABILITY_CSV)
    required_rent = {
        "candidate_name",
        "district",
        "official_median_rent",
        "commute_minutes",
        "transfer_count",
        "rent_saving_vs_neihu",
        "is_pareto_efficient",
        "dominated_by",
    }
    required_livability = {
        "candidate_name",
        "radius_meters",
        "food_count",
        "shopping_count",
        "recreation_count",
        "culture_count",
        "medical_count",
        "total_poi_count",
        "equal_weight_livability_index",
    }
    missing_rent = required_rent - set(rent_commute.columns)
    missing_livability = required_livability - set(livability.columns)
    if missing_rent or missing_livability:
        raise RuntimeError(
            f"Missing input columns: rent={sorted(missing_rent)}, livability={sorted(missing_livability)}"
        )
    if len(rent_commute) != EXPECTED_CANDIDATE_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_CANDIDATE_COUNT} rent/commute rows, got {len(rent_commute)}.")
    if len(livability) != EXPECTED_CANDIDATE_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_CANDIDATE_COUNT} livability rows, got {len(livability)}.")
    if set(livability["radius_meters"].unique()) != {LIVABILITY_RADIUS_METERS}:
        raise RuntimeError(f"Not all livability rows use {LIVABILITY_RADIUS_METERS}m radius.")

    merged = rent_commute.merge(
        livability[
            [
                "candidate_name",
                "radius_meters",
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
    missing = merged[merged["equal_weight_livability_index"].isna()]["candidate_name"].tolist()
    if missing:
        raise RuntimeError(f"Missing livability rows for candidates: {missing}")
    return merged


def build_life_quality_recommendations(candidates: pd.DataFrame) -> pd.DataFrame:
    ranked = candidates.copy()
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
    return ranked[
        [
            "preference_mode",
            "rank",
            "candidate_name",
            "district",
            "rent",
            "official_median_rent",
            "commute_minutes",
            "transfer_count",
            "rent_saving_vs_neihu",
            "livability_index",
            "food_count",
            "shopping_count",
            "recreation_count",
            "culture_count",
            "medical_count",
            "total_poi_count",
            "preference_cost",
            "preference_score",
            "normalized_rent",
            "normalized_commute",
            "normalized_livability",
            "livability_cost",
            "rent_weight",
            "commute_weight",
            "livability_weight",
            "is_pareto_efficient",
            "dominated_by",
        ]
    ].copy()


def scan_livability_cache_for_duplicates(candidate_name: str) -> dict[str, object]:
    cache_path = RAW_CACHE_DIR / f"{safe_slug(candidate_name)}.json"
    if not cache_path.exists():
        raise RuntimeError(f"Missing raw Overpass cache for {candidate_name}: {cache_path}")
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    elements = payload.get("overpass_response", {}).get("elements", [])
    category_ids = {category_name: set() for category_name in POI_CATEGORIES}
    multi_category_elements: list[dict[str, object]] = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags", {})
        if not isinstance(tags, dict):
            continue
        element_id = f"{element.get('type')}:{element.get('id')}"
        matches = [
            category_name
            for category_name in POI_CATEGORIES
            if element_matches_category(tags, category_name)
        ]
        for category_name in matches:
            category_ids[category_name].add(element_id)
        if len(matches) > 1:
            multi_category_elements.append(
                {
                    "element_id": element_id,
                    "categories": matches,
                    "name": tags.get("name", ""),
                    "amenity": tags.get("amenity", ""),
                    "shop": tags.get("shop", ""),
                    "leisure": tags.get("leisure", ""),
                    "tourism": tags.get("tourism", ""),
                }
            )
    category_counts = {f"{category_name}_count": len(ids) for category_name, ids in category_ids.items()}
    return {
        "candidate_name": candidate_name,
        "cache_file": str(cache_path.relative_to(PROJECT_ROOT)),
        "element_count": len(elements),
        "category_counts": category_counts,
        "multi_category_duplicate_count": len(multi_category_elements),
        "multi_category_examples": multi_category_elements[:5],
    }


def run_livability_sanity_check(livability: pd.DataFrame) -> dict[str, object]:
    radius_values = sorted(livability["radius_meters"].dropna().unique().tolist())
    sample_audits = [
        scan_livability_cache_for_duplicates(candidate_name)
        for candidate_name in LIVABILITY_SAMPLE_CANDIDATES
    ]
    all_audits = [
        scan_livability_cache_for_duplicates(candidate_name)
        for candidate_name in livability["candidate_name"].tolist()
    ]
    total_multi_category_duplicates = sum(
        int(audit["multi_category_duplicate_count"]) for audit in all_audits
    )
    if radius_values != [LIVABILITY_RADIUS_METERS]:
        raise RuntimeError(f"Livability radius sanity check failed: {radius_values}")
    if total_multi_category_duplicates:
        raise RuntimeError(
            f"Found {total_multi_category_duplicates} OSM elements matching multiple POI categories."
        )
    return {
        "category_definition": {
            category_name: {
                "label": definition["label"],
                "tags": {key: sorted(values) for key, values in definition["tags"].items()},
            }
            for category_name, definition in POI_CATEGORIES.items()
        },
        "radius_values": radius_values,
        "sample_audits": sample_audits,
        "total_multi_category_duplicates": total_multi_category_duplicates,
        "raw_cache_files_checked": len(all_audits),
    }


def run_sanity_check(recommendations: pd.DataFrame) -> None:
    actual_top_1 = (
        recommendations.sort_values(["preference_mode", "rank"])
        .groupby("preference_mode")["candidate_name"]
        .first()
        .to_dict()
    )
    mismatches = {
        mode: {"expected": expected, "actual": actual_top_1.get(mode)}
        for mode, expected in EXPECTED_TOP_1.items()
        if actual_top_1.get(mode) != expected
    }
    if mismatches:
        raise RuntimeError(
            "Sanity check failed; verify normalization and scoring direction. "
            f"Mismatches: {mismatches}"
        )


def build_summary_markdown(
    rent_commute_recommendations: pd.DataFrame,
    pareto: pd.DataFrame,
    life_quality_recommendations: pd.DataFrame,
    sanity: dict[str, object],
) -> str:
    lines = [
        "# Preference Recommendation Summary",
        "",
        "範圍：第一版 MVP 推薦模式。省租型、平衡型、通勤型維持只使用 Rent x Commute Pareto-efficient candidates；生活品質型重新評估全部 16 個候選生活圈。",
        "",
        "Normalization：省租型、平衡型、通勤型的 `official_median_rent` 與 `commute_minutes` 都在 Pareto frontier 內做 min-max normalization。生活品質型則在 16 個候選點內 normalize rent、commute、livability。cost 越低排名越前。",
        "",
        "這些權重只是 MVP 的使用者偏好設定，不是客觀最佳權重。",
        "",
        "Pareto candidates 即使沒有成為 Top 1，也會保留在推薦池中。例如樹林車站仍保留，因為它在 rent x commute 下仍是 Pareto-efficient。",
        "",
    ]

    for mode in [item["preference_mode"] for item in PREFERENCE_MODES]:
        subset = rent_commute_recommendations[
            rent_commute_recommendations["preference_mode"] == mode
        ].sort_values("rank")
        top_1 = subset.iloc[0]
        top_3 = subset.head(3)
        weights = PREFERENCE_MODES[[item["preference_mode"] for item in PREFERENCE_MODES].index(mode)]

        lines += [
            f"## {mode}",
            "",
            f"Top 1: {top_1['candidate_name']} ({top_1['district']}), cost={top_1['preference_cost']:.3f}, rent={format_money(top_1['official_median_rent'])} NTD, commute={format_minutes(top_1['commute_minutes'])} min.",
            "",
            "Top 3:",
            "",
        ]
        for _, row in top_3.iterrows():
            lines.append(
                f"- #{int(row['rank'])} {row['candidate_name']}: cost={row['preference_cost']:.3f}, "
                f"rent={format_money(row['official_median_rent'])} NTD, "
                f"commute={format_minutes(row['commute_minutes'])} min"
            )

        explanation = {
            "省租型": "租金權重最高，因此淡水站因 normalized rent 最低而排名第一，即使它在 Top 3 中通勤時間最長。",
            "平衡型": "租金與通勤權重相同，因此汐止車站以低於 frontier 中段的租金，加上接近板橋的通勤時間取得第一。",
            "通勤型": "通勤權重最高，因此板橋站因 frontier 中最短通勤時間而排名第一。",
        }[mode]
        lines += [
            "",
            f"排序原因：{explanation} 使用權重：rent={weights['rent_weight']:.1f}, commute={weights['commute_weight']:.1f}。",
            "",
        ]

    lines += [
        "## Pareto Pool Used",
        "",
        "| candidate | district | normalized_rent | normalized_commute |",
        "|---|---|---:|---:|",
    ]
    for _, row in pareto.sort_values(["commute_minutes", "official_median_rent"]).iterrows():
        lines.append(
            f"| {row['candidate_name']} | {row['district']} | "
            f"{row['normalized_rent']:.3f} | {row['normalized_commute']:.3f} |"
        )

    life_top_3 = life_quality_recommendations.sort_values("rank").head(3)
    competitive_dominated = life_quality_recommendations[
        (life_quality_recommendations["rank"] <= 6)
        & (life_quality_recommendations["is_pareto_efficient"] == False)  # noqa: E712
    ].copy()

    lines += [
        "",
        "## 生活品質型",
        "",
        "生活品質型會重新評估全部 16 個候選生活圈，不沿用 Rent x Commute 的 2D Pareto filter。",
        "",
        "MVP preference weights: livability=0.6, rent=0.2, commute=0.2。這是生活品質型的 MVP 使用者偏好設定，不是客觀最佳權重。",
        "",
        "`livability_index` 是以 OpenStreetMap POI 生活機能作為生活品質 proxy，不是客觀完整生活品質指標。",
        "",
        "Scoring: rent 與 commute 為越低越好，livability 為越高越好；`preference_cost = 0.2 * normalized_rent + 0.2 * normalized_commute + 0.6 * (1 - normalized_livability)`，cost 越低排名越前。",
        "",
        "Top 3:",
        "",
    ]
    for _, row in life_top_3.iterrows():
        lines.append(
            f"- #{int(row['rank'])} {row['candidate_name']}: cost={row['preference_cost']:.3f}, "
            f"score={row['preference_score']:.3f}, rent={format_money(row['official_median_rent'])} NTD, "
            f"commute={format_minutes(row['commute_minutes'])} min, livability_index={row['livability_index']:.3f}"
        )

    lines += [
        "",
        "排序原因：板橋站的 livability proxy 最高且通勤最短，因此在生活品質型拿到第一；大坪林站雖然在 Rent x Commute 中被汐止車站 dominated，但 POI 生活機能非常高，因此升到第二；樹林車站則同時有較高 livability proxy 與較低租金，排名第三。",
        "",
        "加入 livability 後重新具有競爭力的 Rent x Commute dominated candidates:",
        "",
    ]
    for _, row in competitive_dominated.iterrows():
        lines.append(
            f"- {row['candidate_name']}: 生活品質型 rank #{int(row['rank'])}, "
            f"livability_index={row['livability_index']:.3f}, 原 dominated_by={row['dominated_by']}"
        )

    lines += [
        "",
        "## Livability Sanity Check",
        "",
        f"- POI radius values: {sanity['radius_values']} meters; all candidates use {LIVABILITY_RADIUS_METERS}m.",
        f"- Raw cache files checked for duplicate category matches: {sanity['raw_cache_files_checked']}.",
        f"- Multi-category duplicate element count: {sanity['total_multi_category_duplicates']}.",
        "",
        "POI query/tag definition:",
        "",
    ]
    category_definition = sanity["category_definition"]
    assert isinstance(category_definition, dict)
    for category_name, definition in category_definition.items():
        tags = definition["tags"]
        tag_parts = []
        for key, values in tags.items():
            tag_parts.append(f"{key}={ '|'.join(values) }")
        lines.append(f"- {definition['label']} ({category_name}): " + ", ".join(tag_parts))

    lines += [
        "",
        "Sample classification audits:",
        "",
    ]
    for audit in sanity["sample_audits"]:
        category_counts = audit["category_counts"]
        lines.append(
            f"- {audit['candidate_name']}: elements={audit['element_count']}, "
            f"food={category_counts['food_count']}, shopping={category_counts['shopping_count']}, "
            f"recreation={category_counts['recreation_count']}, culture={category_counts['culture_count']}, "
            f"medical={category_counts['medical_count']}, multi-category duplicates={audit['multi_category_duplicate_count']}"
        )

    lines += [
        "",
        "## 生活品質型全 16 排名",
        "",
        "| rank | candidate | rent | commute | livability_index | cost | score | rent_commute_pareto |",
        "|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for _, row in life_quality_recommendations.sort_values("rank").iterrows():
        lines.append(
            f"| {int(row['rank'])} | {row['candidate_name']} | {format_money(row['official_median_rent'])} | "
            f"{format_minutes(row['commute_minutes'])} | {row['livability_index']:.3f} | "
            f"{row['preference_cost']:.3f} | {row['preference_score']:.3f} | "
            f"{'yes' if row['is_pareto_efficient'] else 'no'} |"
        )

    lines += [
        "",
        "## Outputs",
        "",
        f"- Input: `{INPUT_CSV.relative_to(PROJECT_ROOT)}`",
        f"- Livability input: `{LIVABILITY_CSV.relative_to(PROJECT_ROOT)}`",
        f"- Recommendations: `{OUTPUT_CSV.relative_to(PROJECT_ROOT)}`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    pareto = load_pareto_candidates()
    rent_commute_recommendations = build_recommendations(pareto)
    run_sanity_check(rent_commute_recommendations)

    life_quality_candidates = load_life_quality_candidates()
    livability_sanity = run_livability_sanity_check(
        life_quality_candidates[
            [
                "candidate_name",
                "radius_meters",
                "food_count",
                "shopping_count",
                "recreation_count",
                "culture_count",
                "medical_count",
                "total_poi_count",
                "equal_weight_livability_index",
            ]
        ].copy()
    )
    life_quality_recommendations = build_life_quality_recommendations(life_quality_candidates)

    recommendations = pd.concat(
        [rent_commute_recommendations, life_quality_recommendations],
        ignore_index=True,
        sort=False,
    )
    recommendations.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    OUTPUT_MD.write_text(
        build_summary_markdown(
            rent_commute_recommendations,
            pareto,
            life_quality_recommendations,
            livability_sanity,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {OUTPUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {OUTPUT_MD.relative_to(PROJECT_ROOT)}")
    for mode in [item["preference_mode"] for item in PREFERENCE_MODES] + [LIFE_QUALITY_MODE["preference_mode"]]:
        top = recommendations[
            (recommendations["preference_mode"] == mode) & (recommendations["rank"] == 1)
        ].iloc[0]
        print(f"{mode} Top 1: {top['candidate_name']} ({top['preference_cost']:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
