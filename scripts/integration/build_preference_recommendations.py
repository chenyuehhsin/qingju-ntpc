#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_CSV = PROJECT_ROOT / "data" / "processed" / "integration" / "rent_commute_candidates_expanded.csv"
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
        ranked["rent_weight"] = mode["rent_weight"]
        ranked["commute_weight"] = mode["commute_weight"]
        ranked["preference_cost"] = (
            mode["rent_weight"] * ranked["normalized_rent"]
            + mode["commute_weight"] * ranked["normalized_commute"]
        )
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
            "official_median_rent",
            "commute_minutes",
            "transfer_count",
            "rent_saving_vs_neihu",
            "preference_cost",
            "normalized_rent",
            "normalized_commute",
            "rent_weight",
            "commute_weight",
        ]
    ].copy()


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


def build_summary_markdown(recommendations: pd.DataFrame, pareto: pd.DataFrame) -> str:
    lines = [
        "# Preference Recommendation Summary",
        "",
        "範圍：第一版 MVP 推薦模式，只使用 Rent x Commute Pareto-efficient candidates。",
        "",
        "Normalization：`official_median_rent` 與 `commute_minutes` 都在 Pareto frontier 內做 min-max normalization。兩者皆為越低越好。`preference_cost` 是 normalized rent 與 normalized commute 的加權和，cost 越低排名越前。",
        "",
        "這些權重只是 MVP 的使用者偏好設定，不是客觀最佳權重。",
        "",
        "Pareto candidates 即使沒有成為 Top 1，也會保留在推薦池中。例如樹林車站仍保留，因為它在 rent x commute 下仍是 Pareto-efficient。",
        "",
    ]

    for mode in [item["preference_mode"] for item in PREFERENCE_MODES]:
        subset = recommendations[recommendations["preference_mode"] == mode].sort_values("rank")
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

    lines += [
        "",
        "## Outputs",
        "",
        f"- Input: `{INPUT_CSV.relative_to(PROJECT_ROOT)}`",
        f"- Recommendations: `{OUTPUT_CSV.relative_to(PROJECT_ROOT)}`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    pareto = load_pareto_candidates()
    recommendations = build_recommendations(pareto)
    run_sanity_check(recommendations)

    recommendations.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    OUTPUT_MD.write_text(build_summary_markdown(recommendations, pareto), encoding="utf-8")

    print(f"Wrote {OUTPUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {OUTPUT_MD.relative_to(PROJECT_ROOT)}")
    for mode in [item["preference_mode"] for item in PREFERENCE_MODES]:
        top = recommendations[
            (recommendations["preference_mode"] == mode) & (recommendations["rank"] == 1)
        ].iloc[0]
        print(f"{mode} Top 1: {top['candidate_name']} ({top['preference_cost']:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
