#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


PROJECT_CACHE_DIR = Path(tempfile.gettempdir()) / "qingju_ntpc_cache"
os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_CACHE_DIR / "xdg"))
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_CACHE_DIR / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.patheffects as pe
import matplotlib.ticker as mticker
import pandas as pd
from matplotlib import pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOUSING_BENCHMARK_CSV = (
    PROJECT_ROOT / "data" / "processed" / "housing" / "moi_independent_suite_rent_benchmark.csv"
)
CANDIDATE_LOCATIONS_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "candidate_locations_expanded.csv"
RENT_COMMUTE_BY_WORKPLACE_CSV = (
    PROJECT_ROOT / "data" / "processed" / "integration" / "rent_commute_candidates_by_workplace.csv"
)
LIVABILITY_CSV = PROJECT_ROOT / "data" / "processed" / "livability" / "livability_by_candidate.csv"
RENTAL_CLEAN_CSV = PROJECT_ROOT / "data" / "interim" / "housing" / "ntpc_rental_independent_suite_clean.csv"

OUTPUT_CSV = PROJECT_ROOT / "data" / "processed" / "policy" / "policy_lens_v0.csv"
OUTPUT_FIG = PROJECT_ROOT / "outputs" / "policy" / "01_housing_accessibility_pressure.png"
OUTPUT_SUMMARY = PROJECT_ROOT / "outputs" / "policy" / "policy_lens_v0_summary.md"
OUTPUT_METADATA = PROJECT_ROOT / "outputs" / "policy" / "policy_lens_v0_metadata.json"

EXPECTED_CANDIDATE_COUNT = 16
POLICY_LINKED_FLAG = "社宅 / 包租代管"
WORKPLACE_ORDER = [
    "gangqian_neihu",
    "taipei_city_hall_xinyi",
    "taipei_main_zhongzheng",
    "nangang_nangang",
    "xinban_special_district",
    "xinzhuang_fuduxin",
    "xizhi_science_park",
    "zhonghe_tech_park",
    "tucheng_industrial_park",
]

LABEL_OFFSETS = {
    "林口站": (10, 9),
    "蘆洲站": (10, -8),
    "五股區公所": (10, 10),
    "大坪林站": (10, 8),
    "新莊站": (10, -8),
    "淡水站": (-12, 8),
    "三峽北大特區": (-12, -10),
    "樹林車站": (10, -8),
    "汐止車站": (10, 9),
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


def money(value: float | int) -> str:
    return f"{float(value):,.0f}"


def minutes(value: float | int) -> str:
    return f"{float(value):.1f}"


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def validate_inputs(
    housing: pd.DataFrame,
    locations: pd.DataFrame,
    rent_commute: pd.DataFrame,
    livability: pd.DataFrame,
    rentals: pd.DataFrame,
) -> list[dict[str, str]]:
    if len(locations) != EXPECTED_CANDIDATE_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_CANDIDATE_COUNT} candidate locations, found {len(locations)}.")
    if locations["candidate_name"].nunique() != EXPECTED_CANDIDATE_COUNT:
        raise RuntimeError("Candidate locations include duplicated candidate_name values.")

    required_workplaces = set(WORKPLACE_ORDER)
    observed_workplaces = set(rent_commute["workplace_id"])
    missing_workplaces = sorted(required_workplaces - observed_workplaces)
    if missing_workplaces:
        raise RuntimeError(f"Missing workplace commute data: {missing_workplaces}")
    failed = rent_commute[rent_commute["commute_minutes"].isna()]
    if not failed.empty:
        details = failed[["workplace_id", "candidate_name"]].to_dict("records")
        raise RuntimeError(f"Commute inputs include missing commute_minutes: {details}")

    counts = rent_commute.groupby("workplace_id")["candidate_name"].nunique()
    incomplete = counts[counts != EXPECTED_CANDIDATE_COUNT]
    if not incomplete.empty:
        raise RuntimeError(f"Expected 16 candidates for every workplace, found {incomplete.to_dict()}.")

    required_housing = {"city", "district", "contract_count", "rent_median"}
    missing_housing = required_housing - set(housing.columns)
    if missing_housing:
        raise RuntimeError(f"Housing benchmark missing columns: {sorted(missing_housing)}")

    required_livability = {"candidate_name", "equal_weight_livability_index"}
    missing_livability = required_livability - set(livability.columns)
    if missing_livability:
        raise RuntimeError(f"Livability table missing columns: {sorted(missing_livability)}")

    required_rentals = {"district", "social_housing_flag"}
    missing_rentals = required_rentals - set(rentals.columns)
    if missing_rentals:
        raise RuntimeError(f"Rental clean table missing columns: {sorted(missing_rentals)}")

    workplaces = (
        rent_commute[["workplace_id", "workplace_name", "workplace_district"]]
        .drop_duplicates()
        .copy()
    )
    workplaces["_order"] = workplaces["workplace_id"].map({value: index for index, value in enumerate(WORKPLACE_ORDER)})
    workplaces = workplaces.sort_values("_order").drop(columns=["_order"])
    return workplaces.to_dict("records")


def rental_policy_counts(rentals: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        rentals.groupby("district", dropna=False)
        .agg(
            total_rental_record_count=("social_housing_flag", "size"),
            policy_linked_record_count=(
                "social_housing_flag",
                lambda values: int((values == POLICY_LINKED_FLAG).sum()),
            ),
        )
        .reset_index()
    )
    grouped["policy_linked_record_share"] = (
        grouped["policy_linked_record_count"] / grouped["total_rental_record_count"]
    )
    return grouped


def assign_quadrants(df: pd.DataFrame, rent_median: float, commute_median: float) -> pd.Series:
    high_rent = df["official_median_rent"] >= rent_median
    long_commute = df["commute_accessibility_minutes"] >= commute_median
    return pd.Series(
        [
            _quadrant_label(is_high_rent, is_long_commute)
            for is_high_rent, is_long_commute in zip(high_rent, long_commute)
        ],
        index=df.index,
    )


def _quadrant_label(high_rent: bool, long_commute: bool) -> str:
    if high_rent and long_commute:
        return "高租金 × 長通勤"
    if not high_rent and long_commute:
        return "低租金 × 長通勤"
    if high_rent and not long_commute:
        return "高租金 × 短通勤"
    return "低租金 × 短通勤"


def build_policy_dataset() -> tuple[pd.DataFrame, dict[str, object]]:
    housing = pd.read_csv(HOUSING_BENCHMARK_CSV)
    locations = pd.read_csv(CANDIDATE_LOCATIONS_CSV)
    rent_commute = pd.read_csv(RENT_COMMUTE_BY_WORKPLACE_CSV)
    livability = pd.read_csv(LIVABILITY_CSV)
    rentals = pd.read_csv(RENTAL_CLEAN_CSV)
    workplaces = validate_inputs(housing, locations, rent_commute, livability, rentals)

    rent_commute = rent_commute[rent_commute["workplace_id"].isin(WORKPLACE_ORDER)].copy()
    accessibility = (
        rent_commute.groupby(["candidate_name", "district"], as_index=False)
        .agg(
            commute_accessibility_minutes=("commute_minutes", "median"),
            commute_accessibility_workplace_count=("workplace_id", "nunique"),
            commute_accessibility_min_minutes=("commute_minutes", "min"),
            commute_accessibility_max_minutes=("commute_minutes", "max"),
        )
        .copy()
    )

    ntpc_housing = (
        housing[housing["city"] == "新北市"][["district", "contract_count", "rent_median"]]
        .rename(
            columns={
                "contract_count": "official_contract_count",
                "rent_median": "official_median_rent",
            }
        )
        .copy()
    )
    rental_counts = rental_policy_counts(rentals)

    result = (
        locations[["candidate_name", "district", "lat", "lon"]]
        .merge(ntpc_housing, on="district", how="left", validate="many_to_one")
        .merge(accessibility, on=["candidate_name", "district"], how="left", validate="one_to_one")
        .merge(
            livability[["candidate_name", "equal_weight_livability_index"]],
            on="candidate_name",
            how="left",
            validate="one_to_one",
        )
        .merge(rental_counts, on="district", how="left", validate="many_to_one")
    )
    result = result.rename(columns={"equal_weight_livability_index": "livability_index"})
    if len(result) != EXPECTED_CANDIDATE_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_CANDIDATE_COUNT} policy rows, found {len(result)}.")

    required_output = [
        "official_median_rent",
        "official_contract_count",
        "commute_accessibility_minutes",
        "livability_index",
        "total_rental_record_count",
        "policy_linked_record_count",
        "policy_linked_record_share",
        "lat",
        "lon",
    ]
    missing_values = result[result[required_output].isna().any(axis=1)]
    if not missing_values.empty:
        details = missing_values[["candidate_name", "district"]].to_dict("records")
        raise RuntimeError(f"Policy dataset has missing required values: {details}")

    rent_median = float(result["official_median_rent"].median())
    commute_median = float(result["commute_accessibility_minutes"].median())
    result["policy_quadrant"] = assign_quadrants(result, rent_median, commute_median)
    result["policy_lens_note"] = "policy screening diagnostic; not a formal priority ranking"
    result = result.sort_values(
        ["policy_quadrant", "commute_accessibility_minutes", "official_median_rent", "candidate_name"]
    )

    metadata = {
        "created_at": pd.Timestamp.now(tz="Asia/Taipei").isoformat(),
        "candidate_count": int(len(result)),
        "workplace_count": int(len(WORKPLACE_ORDER)),
        "workplaces_used": workplaces,
        "commute_accessibility_definition": "median commute_minutes across existing workplace presets",
        "rent_quadrant_threshold": rent_median,
        "commute_quadrant_threshold": commute_median,
        "policy_linked_record_definition": f"social_housing_flag == {POLICY_LINKED_FLAG}",
        "limitations": [
            "District-level MOI independent-suite rent benchmark is not station-area live rent.",
            "Commute is representative candidate node to existing workplace anchor public-transit proxy.",
            "Livability is an OSM 800m POI proxy, not complete quality of life.",
            "Policy-linked rental share is rental registration sample structure, not market share or supply rate.",
            "Rental records do not include tenant age.",
            "Policy v0 is screening, not causal analysis or formal policy prioritization.",
        ],
    }
    return result[
        [
            "candidate_name",
            "district",
            "official_median_rent",
            "official_contract_count",
            "commute_accessibility_minutes",
            "commute_accessibility_workplace_count",
            "commute_accessibility_min_minutes",
            "commute_accessibility_max_minutes",
            "livability_index",
            "policy_linked_record_count",
            "total_rental_record_count",
            "policy_linked_record_share",
            "lat",
            "lon",
            "policy_quadrant",
            "policy_lens_note",
        ]
    ], metadata


def label_candidates(df: pd.DataFrame) -> set[str]:
    high_pressure = set(df[df["policy_quadrant"] == "高租金 × 長通勤"]["candidate_name"])
    long_affordable = set(
        df[df["policy_quadrant"] == "低租金 × 長通勤"]
        .sort_values("commute_accessibility_minutes", ascending=False)
        .head(2)["candidate_name"]
    )
    favorable = set(
        df[df["policy_quadrant"] == "低租金 × 短通勤"]
        .sort_values(["commute_accessibility_minutes", "official_median_rent"])
        .head(2)["candidate_name"]
    )
    return high_pressure | long_affordable | favorable


def plot_policy_pressure(df: pd.DataFrame, metadata: dict[str, object]) -> None:
    configure_matplotlib()
    rent_threshold = float(metadata["rent_quadrant_threshold"])
    commute_threshold = float(metadata["commute_quadrant_threshold"])

    fig, ax = plt.subplots(figsize=(11.6, 7.2))
    fig.patch.set_facecolor("#F7F6F1")
    ax.set_facecolor("#FBFCFA")

    scatter = ax.scatter(
        df["commute_accessibility_minutes"],
        df["official_median_rent"],
        c=df["livability_index"],
        cmap="viridis",
        s=118,
        alpha=0.92,
        edgecolor="#FFFFFF",
        linewidth=1.2,
        zorder=3,
    )

    ax.axvline(commute_threshold, color="#8B989D", linewidth=1.1, linestyle=(0, (4, 4)), zorder=1)
    ax.axhline(rent_threshold, color="#8B989D", linewidth=1.1, linestyle=(0, (4, 4)), zorder=1)

    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    quadrant_style = {"fontsize": 9.2, "color": "#5F6F75", "weight": "bold", "alpha": 0.82}
    ax.text(x_max - 1.0, y_max - 450, "高租金 × 長通勤\npotential pressure", ha="right", va="top", **quadrant_style)
    ax.text(x_min + 1.0, y_max - 450, "高租金 × 短通勤\naccessible, higher cost", ha="left", va="top", **quadrant_style)
    ax.text(x_max - 1.0, y_min + 1200, "低租金 × 長通勤\naffordable, less accessible", ha="right", va="bottom", **quadrant_style)
    ax.text(x_min + 1.0, y_min + 1200, "低租金 × 短通勤\nrelatively favorable", ha="left", va="bottom", **quadrant_style)

    for _, row in df[df["candidate_name"].isin(label_candidates(df))].iterrows():
        offset = LABEL_OFFSETS.get(row["candidate_name"], (8, 8))
        annotation = ax.annotate(
            row["candidate_name"],
            xy=(row["commute_accessibility_minutes"], row["official_median_rent"]),
            xytext=offset,
            textcoords="offset points",
            ha="right" if offset[0] < 0 else "left",
            va="center",
            fontsize=8.8,
            color="#26343A",
            bbox={"boxstyle": "round,pad=0.22", "fc": "#FFFFFF", "ec": "#D7E0E2", "lw": 0.8, "alpha": 0.92},
            arrowprops={"arrowstyle": "-", "color": "#9AA6AA", "lw": 0.7, "alpha": 0.55},
            zorder=4,
        )
        annotation.set_path_effects([pe.withStroke(linewidth=2.4, foreground="#FFFFFF")])

    ax.set_title("Housing × Transit Accessibility Pressure Screening", fontsize=17, weight="bold", color="#233239", pad=14)
    ax.set_xlabel("Commute accessibility minutes\nmedian across 9 workplace presets, higher = less accessible", color="#39484E")
    ax.set_ylabel("Official independent-suite median rent (NTD/month)", color="#39484E")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda value, _: f"{value:,.0f}"))
    ax.grid(True, color="#E5EBEC", linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_color("#D9E0E2")

    colorbar = fig.colorbar(scatter, ax=ax, pad=0.018)
    colorbar.set_label("Livability proxy: OSM 800m POI index", color="#39484E")
    colorbar.outline.set_edgecolor("#D9E0E2")

    fig.text(
        0.105,
        0.025,
        "Policy v0 screening only. Rent is district-level MOI benchmark; commute is node-to-anchor public transit; livability is OSM POI proxy.",
        fontsize=8.5,
        color="#66757B",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    OUTPUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_FIG, dpi=220)
    plt.close(fig)


def markdown_list(values: list[str]) -> str:
    if not values:
        return "- none"
    return "\n".join(f"- {value}" for value in values)


def candidate_brief(row: pd.Series) -> str:
    return (
        f"{row['candidate_name']}（{row['district']}）："
        f"租金 {money(row['official_median_rent'])}，"
        f"可達性 {minutes(row['commute_accessibility_minutes'])} min，"
        f"生活機能 {float(row['livability_index']):.3f}，"
        f"policy-linked share {percent(float(row['policy_linked_record_share']))} "
        f"({int(row['policy_linked_record_count'])}/{int(row['total_rental_record_count'])})"
    )


def write_summary(df: pd.DataFrame, metadata: dict[str, object]) -> None:
    high_long = df[df["policy_quadrant"] == "高租金 × 長通勤"].sort_values(
        ["official_median_rent", "commute_accessibility_minutes"], ascending=[False, False]
    )
    low_long = df[df["policy_quadrant"] == "低租金 × 長通勤"].sort_values(
        "commute_accessibility_minutes", ascending=False
    )
    favorable = df[df["policy_quadrant"] == "低租金 × 短通勤"].sort_values(
        ["commute_accessibility_minutes", "official_median_rent"]
    )
    high_livability_pressure = high_long.sort_values("livability_index", ascending=False).head(2)
    low_livability_favorable = favorable.sort_values("livability_index").head(2)
    share_high = df.sort_values("policy_linked_record_share", ascending=False).head(5)
    share_low = df.sort_values("policy_linked_record_share", ascending=True).head(5)
    small_samples = df[df["total_rental_record_count"] < 50].sort_values("total_rental_record_count")

    lines = [
        "# Policy Lens v0 Summary",
        "",
        "Purpose: screen candidate New Taipei living areas that may warrant further housing-policy attention from a Youth Bureau lens.",
        "This is a diagnostic view, not a formal policy priority ranking and not a policy prescription.",
        "",
        "## Method",
        "",
        f"- Candidates: {len(df)} existing MVP living-area nodes.",
        f"- Commute accessibility: median `commute_minutes` across {metadata['workplace_count']} existing workplace presets.",
        f"- Rent threshold: overall candidate median = {money(metadata['rent_quadrant_threshold'])} NTD/month.",
        f"- Commute threshold: overall candidate median = {minutes(metadata['commute_quadrant_threshold'])} minutes.",
        "- Livability: OSM 800m POI equal-weight index used as a life-function proxy.",
        "- Policy-linked rental share: share of cleaned independent-suite rental registration sample with `social_housing_flag == 社宅 / 包租代管`.",
        "",
        "## 1. 高租金 × 長通勤",
        "",
        markdown_list([candidate_brief(row) for _, row in high_long.iterrows()]),
        "",
        "These candidates combine above-median district rent benchmark and above-median median commute to existing workplace anchors.",
        "",
        "## 2. 低租金 × 長通勤",
        "",
        markdown_list([candidate_brief(row) for _, row in low_long.iterrows()]),
        "",
        "These may look affordable on district rent benchmark but are less accessible under the current public-transit anchor set.",
        "",
        "## 3. Better Rent × Transit Trade-Off",
        "",
        markdown_list([candidate_brief(row) for _, row in favorable.iterrows()]),
        "",
        "These fall in the lower-rent and shorter-commute quadrant under the v0 thresholds.",
        "",
        "## 4. Livability Exceptions",
        "",
        "High-pressure quadrant but relatively strong livability proxy:",
        "",
        markdown_list([candidate_brief(row) for _, row in high_livability_pressure.iterrows()]),
        "",
        "Favorable rent/commute quadrant but weaker livability proxy:",
        "",
        markdown_list([candidate_brief(row) for _, row in low_livability_favorable.iterrows()]),
        "",
        "This suggests POI-based life-function can complicate a simple rent/commute diagnosis.",
        "",
        "## 5. Policy-Linked Rental Record Share",
        "",
        "Highest shares in candidate districts:",
        "",
        markdown_list([candidate_brief(row) for _, row in share_high.iterrows()]),
        "",
        "Lowest shares in candidate districts:",
        "",
        markdown_list([candidate_brief(row) for _, row in share_low.iterrows()]),
        "",
        "Important interpretation limit: this is only the share within the cleaned rental registration sample. It is not market share, not youth rental share, and not the true district social-housing or sublease-management supply rate.",
        "",
        "Small sample districts to treat carefully:",
        "",
        markdown_list([candidate_brief(row) for _, row in small_samples.iterrows()]),
        "",
        "## 6. Hypotheses Only",
        "",
        "- High rent and long commute may indicate housing-accessibility pressure, but this does not prove unmet youth demand.",
        "- Low rent and long commute may indicate affordability/accessibility trade-off, but not necessarily poor welfare outcomes.",
        "- Higher livability proxy reflects POI counts around one representative node, not complete neighborhood quality.",
        "- Policy-linked rental share reflects observed rental-registration sample structure, not actual policy coverage.",
        "- The data has no tenant age, so none of the rental records can be called youth rental cases.",
        "",
        "## 7. Missing Data Before Social Housing / Subsidy Discussion",
        "",
        "- Existing and planned social-housing units by location, unit type, and eligibility.",
        "- Rental subsidy application, approval, waiting, and unmet-demand data by age group and district.",
        "- Youth population, workplace distribution, income, and household formation data at finer geography.",
        "- Real listing rents or transaction microdata closer to station-area buffers.",
        "- Door-to-door commute estimates and off-peak/weekend accessibility.",
        "- Land/public-asset availability and policy feasibility constraints.",
    ]
    OUTPUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_METADATA.parent.mkdir(parents=True, exist_ok=True)
    df, metadata = build_policy_dataset()
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    OUTPUT_METADATA.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    plot_policy_pressure(df, metadata)
    write_summary(df, metadata)

    print(f"Wrote {OUTPUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {OUTPUT_FIG.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {OUTPUT_SUMMARY.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {OUTPUT_METADATA.relative_to(PROJECT_ROOT)}")
    print(f"Candidates: {len(df)}")
    print(f"Workplaces used: {metadata['workplace_count']}")
    print("Quadrants:")
    for quadrant, count in df["policy_quadrant"].value_counts().sort_index().items():
        print(f"- {quadrant}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
