#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
from pathlib import Path


PROJECT_CACHE_DIR = Path(tempfile.gettempdir()) / "qingju_ntpc_cache"
os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_CACHE_DIR / "xdg"))
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_CACHE_DIR / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.ticker as mticker
import pandas as pd
from matplotlib import pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMMUTE_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "commute_to_gangqian.csv"
HOUSING_BENCHMARK_CSV = (
    PROJECT_ROOT / "data" / "processed" / "housing" / "moi_independent_suite_rent_benchmark.csv"
)
OUTPUT_CSV = PROJECT_ROOT / "data" / "processed" / "integration" / "rent_commute_candidates.csv"
OUTPUT_FIG = PROJECT_ROOT / "outputs" / "integration" / "01_rent_commute_scatter.png"
OUTPUT_MD = PROJECT_ROOT / "outputs" / "integration" / "rent_commute_analysis.md"

EXPECTED_CANDIDATE_COUNT = 8
NEIHU_BASELINE_RENT = 19_500
NEIHU_CITY = "臺北市"
NEIHU_DISTRICT = "內湖區"

LABEL_OFFSETS = {
    "板橋站": (-4, 10),
    "汐止車站": (8, -2),
    "大坪林站": (8, 8),
    "三重站": (8, -16),
    "頂溪站": (8, 6),
    "蘆洲站": (8, 6),
    "新莊站": (8, 6),
    "景安站": (8, -14),
}


def configure_matplotlib() -> None:
    candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            fm.fontManager.addfont(candidate)
            prop = fm.FontProperties(fname=candidate)
            plt.rcParams["font.family"] = prop.get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 160


def format_money(value: float | int) -> str:
    return f"{float(value):,.0f}"


def format_minutes(value: float) -> str:
    return f"{float(value):.1f}"


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    commute = pd.read_csv(COMMUTE_CSV)
    housing = pd.read_csv(HOUSING_BENCHMARK_CSV)

    if len(commute) != EXPECTED_CANDIDATE_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_CANDIDATE_COUNT} commute candidates, got {len(commute)}.")

    duplicate_candidates = commute[commute["candidate_name"].duplicated()]["candidate_name"].tolist()
    if duplicate_candidates:
        raise RuntimeError(f"Duplicate commute candidates found: {duplicate_candidates}")

    failed_queries = commute[commute["query_status"] != "success"]
    if not failed_queries.empty:
        details = failed_queries[["candidate_name", "district", "query_status", "error_message"]].to_dict("records")
        raise RuntimeError(f"Commute inputs include non-success rows: {details}")

    neihu = housing[(housing["city"] == NEIHU_CITY) & (housing["district"] == NEIHU_DISTRICT)]
    if len(neihu) != 1:
        raise RuntimeError(f"Expected one Neihu benchmark row, found {len(neihu)}.")
    observed_neihu = int(neihu.iloc[0]["rent_median"])
    if observed_neihu != NEIHU_BASELINE_RENT:
        raise RuntimeError(
            f"Neihu benchmark mismatch: expected {NEIHU_BASELINE_RENT}, found {observed_neihu}."
        )

    return commute, housing


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
        dominators = others.loc[dominates, "candidate_name"].sort_values().tolist()
        efficient.append(len(dominators) == 0)
        dominated_by.append("; ".join(dominators))

    result["is_pareto_efficient"] = efficient
    result["dominated_by"] = dominated_by
    return result


def build_dataset() -> pd.DataFrame:
    commute, housing = load_inputs()

    ntpc_housing = (
        housing[housing["city"] == "新北市"][["city", "district", "rent_median"]]
        .rename(columns={"city": "official_benchmark_city", "rent_median": "official_median_rent"})
        .copy()
    )
    if ntpc_housing["district"].duplicated().any():
        duplicates = ntpc_housing[ntpc_housing["district"].duplicated()]["district"].tolist()
        raise RuntimeError(f"Duplicate New Taipei benchmark districts found: {duplicates}")

    merged = commute.merge(ntpc_housing, on="district", how="left", validate="many_to_one")
    unmatched = merged[merged["official_median_rent"].isna()]
    if not unmatched.empty:
        details = unmatched[["candidate_name", "district"]].to_dict("records")
        raise RuntimeError(f"Housing benchmark join failed for candidates: {details}")
    if len(merged) != EXPECTED_CANDIDATE_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_CANDIDATE_COUNT} joined candidates, got {len(merged)}.")

    merged["official_median_rent"] = merged["official_median_rent"].astype(int)
    merged["rent_saving_vs_neihu"] = NEIHU_BASELINE_RENT - merged["official_median_rent"]
    merged = add_pareto_columns(merged)
    merged = merged.sort_values(["commute_minutes", "official_median_rent", "candidate_name"])

    return merged[
        [
            "candidate_name",
            "district",
            "official_benchmark_city",
            "official_median_rent",
            "commute_minutes",
            "transfer_count",
            "rent_saving_vs_neihu",
            "is_pareto_efficient",
            "dominated_by",
            "destination",
            "departure_time",
            "route_summary",
        ]
    ].copy()


def plot_scatter(df: pd.DataFrame) -> None:
    configure_matplotlib()

    pareto = df[df["is_pareto_efficient"]].sort_values("commute_minutes")
    dominated = df[~df["is_pareto_efficient"]]

    fig, ax = plt.subplots(figsize=(9.2, 5.8))
    ax.scatter(
        dominated["commute_minutes"],
        dominated["official_median_rent"],
        s=58,
        color="#6F7C85",
        alpha=0.9,
        label="Dominated candidate",
        zorder=2,
    )
    ax.scatter(
        pareto["commute_minutes"],
        pareto["official_median_rent"],
        s=95,
        color="#D95F02",
        edgecolor="#202020",
        linewidth=0.8,
        label="Pareto-efficient",
        zorder=4,
    )
    if len(pareto) >= 2:
        ax.plot(
            pareto["commute_minutes"],
            pareto["official_median_rent"],
            color="#D95F02",
            linewidth=1.8,
            alpha=0.85,
            zorder=3,
        )

    for _, row in df.iterrows():
        offset = LABEL_OFFSETS.get(row["candidate_name"], (7, 7))
        ax.annotate(
            row["candidate_name"],
            (row["commute_minutes"], row["official_median_rent"]),
            xytext=offset,
            textcoords="offset points",
            fontsize=9,
            color="#222222",
            ha="right" if offset[0] < 0 else "left",
            va="center",
        )

    ax.axhline(NEIHU_BASELINE_RENT, color="#B23A48", linestyle="--", linewidth=1.5)
    ax.text(
        df["commute_minutes"].min(),
        NEIHU_BASELINE_RENT + 250,
        f"Neihu rent baseline: {format_money(NEIHU_BASELINE_RENT)} NTD/month",
        color="#B23A48",
        fontsize=9,
        va="bottom",
    )

    ax.set_xlabel("One-way public-transit commute to Gangqian Station (minutes)")
    ax.set_ylabel("Official median monthly rent (NTD)")
    ax.set_title("Rent x Commute Trade-off for Candidate Living Areas", fontsize=13, pad=10)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    ax.grid(alpha=0.22)
    ax.legend(frameon=False, loc="upper right")
    ax.set_xlim(df["commute_minutes"].min() - 2, df["commute_minutes"].max() + 4)
    ax.set_ylim(min(df["official_median_rent"].min(), NEIHU_BASELINE_RENT) - 900, NEIHU_BASELINE_RENT + 1_300)
    fig.tight_layout()

    OUTPUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_FIG, bbox_inches="tight")
    plt.close(fig)


def build_analysis_markdown(df: pd.DataFrame) -> str:
    lowest_rent = df.sort_values(["official_median_rent", "commute_minutes", "candidate_name"]).iloc[0]
    shortest_commute = df.sort_values(["commute_minutes", "official_median_rent", "candidate_name"]).iloc[0]
    pareto = df[df["is_pareto_efficient"]].sort_values(["commute_minutes", "official_median_rent"])
    dominated = df[~df["is_pareto_efficient"]].sort_values(["commute_minutes", "official_median_rent"])

    lines = [
        "# Rent x Commute Analysis",
        "",
        "Scope: 8 candidate living-area nodes joined to New Taipei official independent-suite rent benchmarks by district.",
        "",
        f"Neihu rent baseline: {format_money(NEIHU_BASELINE_RENT)} NTD/month. This is a reference line only and is not included in Pareto calculations.",
        "",
        "## Main Findings",
        "",
        f"- Lowest rent candidate: {lowest_rent['candidate_name']} ({lowest_rent['district']}), {format_money(lowest_rent['official_median_rent'])} NTD/month, {format_minutes(lowest_rent['commute_minutes'])} minutes.",
        f"- Shortest commute candidate: {shortest_commute['candidate_name']} ({shortest_commute['district']}), {format_minutes(shortest_commute['commute_minutes'])} minutes, {format_money(shortest_commute['official_median_rent'])} NTD/month.",
        "- Pareto-efficient candidates: "
        + ", ".join(
            f"{row['candidate_name']} ({format_money(row['official_median_rent'])} NTD, {format_minutes(row['commute_minutes'])} min)"
            for _, row in pareto.iterrows()
        )
        + ".",
        "",
        "## Dominated Candidates",
        "",
    ]

    for _, row in dominated.iterrows():
        lines.append(f"- {row['candidate_name']}: dominated by {row['dominated_by']}.")

    lines += [
        "",
        "## Interpretation",
        "",
        "Rent x commute shows a meaningful but narrow trade-off at the frontier: Banqiao is the fastest option but costs 2,000 NTD/month more than Xizhi, while Xizhi is 4.0 minutes slower and has the lowest rent among these candidates.",
        "",
        "The remaining six candidates do not add frontier choices under the current two-objective definition because at least one other candidate is both cheaper and no slower, or cheaper and faster.",
        "",
        "These 8 candidates are sufficient to continue a first recommendation-model prototype because the join is complete and the two core numeric dimensions are available. They are not yet sufficient for a robust final model; later steps should add non-rent housing attributes, accessibility beyond Gangqian, and neighborhood-quality variables.",
        "",
        "## Inputs And Outputs",
        "",
        f"- Input housing benchmark: `{HOUSING_BENCHMARK_CSV.relative_to(PROJECT_ROOT)}`",
        f"- Input commute table: `{COMMUTE_CSV.relative_to(PROJECT_ROOT)}`",
        f"- Integrated table: `{OUTPUT_CSV.relative_to(PROJECT_ROOT)}`",
        f"- Scatter plot: `{OUTPUT_FIG.relative_to(PROJECT_ROOT)}`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    df = build_dataset()
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    plot_scatter(df)
    OUTPUT_MD.write_text(build_analysis_markdown(df), encoding="utf-8")

    pareto_names = df.loc[df["is_pareto_efficient"], "candidate_name"].tolist()
    dominated_count = int((~df["is_pareto_efficient"]).sum())

    print(f"Wrote {OUTPUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {OUTPUT_FIG.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {OUTPUT_MD.relative_to(PROJECT_ROOT)}")
    print(f"Joined candidates: {len(df)} / {EXPECTED_CANDIDATE_COUNT}")
    print(f"Pareto-efficient candidates: {', '.join(pareto_names)}")
    print(f"Dominated candidates: {dominated_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
