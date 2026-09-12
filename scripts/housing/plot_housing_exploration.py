from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd

from common import INTERIM_HOUSING, OUTPUT_HOUSING, PROCESSED_HOUSING, RENTAL_CSV, ensure_output_dirs


RENT_BY_DISTRICT = PROCESSED_HOUSING / "rent_by_district.csv"
CLEAN_CSV = INTERIM_HOUSING / "ntpc_rental_independent_suite_clean.csv"
SUMMARY_MD = OUTPUT_HOUSING / "housing_exploration_summary.md"


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
    plt.rcParams["figure.dpi"] = 140


def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()


def figure_1(df: pd.DataFrame) -> None:
    ntpc = df[df["city"] == "新北市"].sort_values("official_median_rent")
    neihu = df[(df["city"] == "臺北市") & (df["district"] == "內湖區")].iloc[0]
    plt.figure(figsize=(9, 8))
    plt.barh(ntpc["district"], ntpc["official_median_rent"], color="#4C78A8")
    plt.axvline(neihu["official_median_rent"], color="#C44E52", linestyle="--", linewidth=1.8)
    plt.text(
        neihu["official_median_rent"] + 200,
        len(ntpc) - 0.5,
        "Taipei Neihu baseline",
        color="#C44E52",
        va="center",
        fontsize=9,
    )
    plt.xlabel("Official median monthly rent (NTD)")
    plt.ylabel("New Taipei district")
    plt.title("Independent Suite Official Median Rent by District (MOI 2026-03)")
    plt.grid(axis="x", alpha=0.25)
    savefig(OUTPUT_HOUSING / "01_median_rent_by_district.png")


def figure_2(df: pd.DataFrame) -> None:
    ntpc = df[df["city"] == "新北市"].copy()
    plt.figure(figsize=(8, 6))
    plt.scatter(ntpc["official_median_rent"], ntpc["official_median_unit_price"], color="#4C78A8", s=48)
    for _, row in ntpc.iterrows():
        plt.annotate(row["district"], (row["official_median_rent"], row["official_median_unit_price"]), xytext=(4, 3), textcoords="offset points", fontsize=8)
    plt.xlabel("Official median monthly rent (NTD)")
    plt.ylabel("Official median unit rent (NTD / ping)")
    plt.title("Official Total Rent vs Unit Rent, Independent Suites (MOI 2026-03)")
    plt.grid(alpha=0.25)
    savefig(OUTPUT_HOUSING / "02_rent_vs_unit_price.png")


def figure_3(df: pd.DataFrame) -> None:
    ntpc = df[(df["city"] == "新北市") & df["transaction_median_rent"].notna()].copy()
    lim_min = min(ntpc["official_median_rent"].min(), ntpc["transaction_median_rent"].min()) * 0.9
    lim_max = max(ntpc["official_median_rent"].max(), ntpc["transaction_median_rent"].max()) * 1.1
    plt.figure(figsize=(7, 7))
    plt.scatter(ntpc["official_median_rent"], ntpc["transaction_median_rent"], color="#59A14F", s=48)
    plt.plot([lim_min, lim_max], [lim_min, lim_max], color="#777777", linestyle="--", linewidth=1.5)
    for _, row in ntpc.iterrows():
        plt.annotate(row["district"], (row["official_median_rent"], row["transaction_median_rent"]), xytext=(4, 3), textcoords="offset points", fontsize=8)
    plt.xlim(lim_min, lim_max)
    plt.ylim(lim_min, lim_max)
    plt.xlabel("Official median rent (NTD)")
    plt.ylabel("Transaction-derived median rent (NTD)")
    plt.title("Individual Records vs Official Benchmark")
    plt.grid(alpha=0.25)
    savefig(OUTPUT_HOUSING / "03_transactions_vs_official.png")


def figure_4(df: pd.DataFrame) -> None:
    ntpc = df[df["city"] == "新北市"].sort_values("official_median_rent").copy()
    x = range(len(ntpc))
    width = 0.26
    plt.figure(figsize=(13, 6))
    plt.bar([i - width for i in x], ntpc["official_median_rent"], width=width, label="Official median", color="#4C78A8")
    plt.bar(x, ntpc["transaction_median_rent"], width=width, label="All transaction median", color="#59A14F")
    plt.bar([i + width for i in x], ntpc["non_social_median_rent"], width=width, label="Non-social transaction median", color="#F28E2B")
    plt.xticks(list(x), ntpc["district"], rotation=55, ha="right")
    plt.ylabel("Median monthly rent (NTD)")
    plt.title("Social Housing / Rental Management Effect on Transaction Median")
    plt.legend()
    plt.grid(axis="y", alpha=0.25)
    savefig(OUTPUT_HOUSING / "04_social_housing_effect.png")


def money(value: object) -> str:
    if pd.isna(value):
        return "NA"
    return f"{float(value):,.0f}"


def percent(value: object) -> str:
    if pd.isna(value):
        return "NA"
    return f"{float(value):.1%}"


def build_summary(df: pd.DataFrame, clean: pd.DataFrame) -> None:
    ntpc = df[df["city"] == "新北市"].copy()
    ntpc_sorted = ntpc.sort_values("official_median_rent")
    low = ntpc_sorted.head(5)
    high = ntpc_sorted.tail(5).sort_values("official_median_rent", ascending=False)
    neihu = df[(df["city"] == "臺北市") & (df["district"] == "內湖區")].iloc[0]

    corr = ntpc[["official_median_rent", "official_median_unit_price"]].corr().iloc[0, 1]
    target_districts = ["汐止區", "新店區", "中和區", "永和區", "板橋區"]
    comparison = ntpc[ntpc["district"].isin(target_districts)].copy()
    comparison["difference_vs_neihu"] = comparison["official_median_rent"] - neihu["official_median_rent"]

    discrepancy = ntpc[ntpc["transaction_median_rent"].notna()].copy()
    discrepancy["abs_rent_difference"] = discrepancy["rent_difference"].abs()
    discrepancy_top = discrepancy.sort_values("abs_rent_difference", ascending=False).head(5)

    transaction_period = f"{clean['rental_date'].min()} to {clean['rental_date'].max()}"
    social_counts = clean["social_housing_flag"].value_counts()
    social_share = (clean["social_housing_flag"] == "社宅 / 包租代管").mean()

    lines = [
        "# Housing Exploration Summary",
        "",
        "Scope: independent suites only.",
        "",
        "Sources:",
        "",
        "- New Taipei rental transaction individual records: `data/raw/housing/ntpc_rental_transactions_2026-08-21.csv`",
        "- MOI rent total quartiles PDF: `data/raw/housing/moi_rent_total_quartiles_2026-03.pdf`",
        "- MOI rent unit-price quartiles PDF: `data/raw/housing/moi_rent_unit_price_quartiles_2026-03.pdf`",
        "",
        f"Transaction-derived period observed in cleaned records: {transaction_period}.",
        "Official benchmark statistic period: 2026-03.",
        "",
        "## Q1. Lower / Higher Official Median Rents",
        "",
        "Lowest New Taipei official median rents:",
        "",
    ]
    for _, row in low.iterrows():
        lines.append(f"- {row['district']}: {money(row['official_median_rent'])} NTD")
    lines += ["", "Highest New Taipei official median rents:", ""]
    for _, row in high.iterrows():
        lines.append(f"- {row['district']}: {money(row['official_median_rent'])} NTD")

    lines += [
        "",
        "## Q2. Total Rent vs Unit Rent",
        "",
        f"Across the 20 extracted New Taipei districts, official median total rent and official median unit rent have Pearson correlation {corr:.2f}. Lower total rent often aligns with lower unit rent, but not always.",
        "",
        "Notable example: 泰山區 has low official median total rent but high unit rent, which suggests smaller unit sizes may be part of the total-rent story.",
        "",
        "## Q3. Neihu Baseline",
        "",
        f"Taipei Neihu official median rent baseline: {money(neihu['official_median_rent'])} NTD; official median unit rent: {money(neihu['official_median_unit_price'])} NTD/ping.",
        "",
    ]
    for _, row in comparison.sort_values("official_median_rent").iterrows():
        lines.append(
            f"- {row['district']}: {money(row['official_median_rent'])} NTD, "
            f"{money(row['difference_vs_neihu'])} NTD vs Neihu"
        )

    lines += [
        "",
        "## Q4. Individual Records vs Official Benchmark",
        "",
        "Largest rent-median differences. These are differences, not errors by themselves:",
        "",
    ]
    for _, row in discrepancy_top.iterrows():
        direction = "higher" if row["rent_difference"] > 0 else "lower"
        lines.append(
            f"- {row['district']}: transaction median is {money(abs(row['rent_difference']))} NTD {direction} than official; "
            f"transaction sample={int(row['transaction_record_count'])}, social housing share={percent(row['social_housing_share'])}"
        )

    lines += [
        "",
        "Possible explanation / hypothesis for larger differences:",
        "",
        "- The official benchmark and individual records may use different effective periods.",
        "- The individual-record sample has very high social housing / rental-management share in many districts.",
        "- District-level samples differ in size.",
        "- Unit size, building age, and floor composition may differ across sources even within independent suites.",
        "",
        "## Q5. Readiness for Rent x Commute-Time Analysis",
        "",
        "The housing side is usable for a first rent x commute-time exploration, with caution: official benchmark rows cover 20 New Taipei districts plus the Neihu baseline, while individual transaction rows are heavily shaped by social housing / rental-management cases.",
        "",
        "Official unit rent and transaction unit price are not directly compared in this report because their units differ: MOI official unit rent is presented as NTD/ping, while the raw transaction CSV field is NTD/square meter.",
        "",
        "Minimum next-step input table:",
        "",
        "```text",
        "district / candidate location",
        "lat",
        "lon",
        "official_median_rent",
        "official_median_unit_price_ping",
        "commute_minutes_to_neihu",
        "transfer_count",
        "```",
        "",
        "## Social Housing Structure",
        "",
        f"Cleaned independent-suite transaction rows: {len(clean):,}.",
        f"社宅 / 包租代管 share: {percent(social_share)}.",
        "",
    ]
    for key, value in social_counts.items():
        lines.append(f"- {key}: {int(value):,}")

    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate housing exploration figures and summary.")
    parser.add_argument(
        "--only",
        nargs="+",
        choices=["figure1", "figure2", "figure3", "figure4", "summary"],
        help="Generate only selected outputs. Defaults to all outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_output_dirs()
    configure_matplotlib()
    df = pd.read_csv(RENT_BY_DISTRICT)
    clean = pd.read_csv(CLEAN_CSV)

    selected = set(args.only or ["figure1", "figure2", "figure3", "figure4", "summary"])
    output_by_task = {
        "figure1": "01_median_rent_by_district.png",
        "figure2": "02_rent_vs_unit_price.png",
        "figure3": "03_transactions_vs_official.png",
        "figure4": "04_social_housing_effect.png",
        "summary": "housing_exploration_summary.md",
    }
    if "figure1" in selected:
        figure_1(df)
    if "figure2" in selected:
        figure_2(df)
    if "figure3" in selected:
        figure_3(df)
    if "figure4" in selected:
        figure_4(df)
    if "summary" in selected:
        build_summary(df, clean)

    for task in ["figure1", "figure2", "figure3", "figure4", "summary"]:
        if task in selected:
            print(f"Wrote {OUTPUT_HOUSING / output_by_task[task]}")


if __name__ == "__main__":
    main()
