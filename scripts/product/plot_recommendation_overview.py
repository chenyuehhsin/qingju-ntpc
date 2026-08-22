#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
from pathlib import Path


PROJECT_CACHE_DIR = Path(tempfile.gettempdir()) / "qingju_ntpc_cache"
os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_CACHE_DIR / "xdg"))
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_CACHE_DIR / "matplotlib"))

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

from plot_recommendation_mode_views import (
    CANDIDATE_LOCATIONS_CSV,
    LIVABILITY_CSV,
    MODE_COLORS,
    MODE_COPY,
    MODE_ORDER,
    MODE_SOFT_COLORS,
    OUTPUT_DIR,
    PREFERENCE_CSV,
    PROJECT_ROOT,
    add_rounded_rect,
    configure_matplotlib,
    living_area,
    load_boundaries,
    load_data,
    minutes,
    money,
)


OVERVIEW_PNG = OUTPUT_DIR / "00_recommendation_overview.png"
OVERVIEW_SVG = OUTPUT_DIR / "00_recommendation_overview.svg"

OVERVIEW_LABEL_OFFSETS = {
    "淡水站": (-16, 18),
    "汐止車站": (-26, 8),
    "板橋站": (14, -20),
    "樹林車站": (-18, -20),
    "大坪林站": (16, -8),
}


def load_overview_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, float | str]]:
    recommendations = pd.read_csv(PREFERENCE_CSV)
    livability = pd.read_csv(LIVABILITY_CSV)
    locations = pd.read_csv(CANDIDATE_LOCATIONS_CSV)

    life_quality_rows = recommendations[recommendations["preference_mode"] == "生活品質型"].copy()
    if len(life_quality_rows) != 16:
        raise RuntimeError(f"Expected 16 生活品質型 rows, found {len(life_quality_rows)}.")

    candidates = locations.merge(
        life_quality_rows[
            [
                "candidate_name",
                "rent",
                "commute_minutes",
                "rent_saving_vs_neihu",
                "livability_index",
            ]
        ],
        on="candidate_name",
        how="left",
        validate="one_to_one",
    )
    candidates = candidates.merge(
        livability[["candidate_name", "equal_weight_livability_index"]],
        on="candidate_name",
        how="left",
        validate="one_to_one",
    )
    candidates["livability_index"] = candidates["livability_index"].fillna(candidates["equal_weight_livability_index"])

    missing_metrics = candidates[
        candidates[["rent", "commute_minutes", "rent_saving_vs_neihu", "livability_index"]].isna().any(axis=1)
    ]["candidate_name"].tolist()
    if missing_metrics:
        raise RuntimeError(f"Missing overview metrics for candidates: {missing_metrics}")

    top3, destination = load_data()
    top1 = top3[top3["rank"] == 1].copy()
    if len(top1) != 4:
        raise RuntimeError(f"Expected four mode Top 1 rows, found {len(top1)}.")

    return candidates, top3, top1, destination


def draw_header(ax: plt.Axes) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.02, 0.72, "青聚新北 MVP", fontsize=11, color="#6A787D", weight="bold", va="center")
    ax.text(0.02, 0.34, "四模式推薦總覽", fontsize=24, color="#223139", weight="bold", va="center")
    ax.text(0.245, 0.34, "已評估 16 個候選生活圈", fontsize=9.8, color="#6A787D", va="center")

    chips = [("工作地", "港墘站"), ("交通方式", "大眾運輸"), ("租屋型態", "獨立套房")]
    x = 0.52
    for label, value in chips:
        add_rounded_rect(ax, (x, 0.44), 0.13, 0.34, "#FFFFFF", "#D9E0E2", linewidth=0.8, radius=0.025)
        ax.text(x + 0.015, 0.65, label, fontsize=7.8, color="#7A878B", va="center")
        ax.text(x + 0.015, 0.53, value, fontsize=10.2, color="#25343A", weight="bold", va="center")
        x += 0.145


def draw_summary_cards(ax: plt.Axes, top1: pd.DataFrame) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    card_width = 0.232
    gap = 0.016
    rows_by_mode = {row["preference_mode"]: row for _, row in top1.iterrows()}
    for index, mode in enumerate(MODE_ORDER):
        row = rows_by_mode[mode]
        x = 0.0 + index * (card_width + gap)
        color = MODE_COLORS[mode]
        soft = MODE_SOFT_COLORS[mode]
        add_rounded_rect(ax, (x, 0.04), card_width, 0.88, soft, color, linewidth=1.0, radius=0.024)
        ax.scatter([x + 0.024], [0.70], s=120, color=color, edgecolor="#FFFFFF", linewidth=1.1, transform=ax.transAxes)
        ax.text(x + 0.048, 0.76, mode, fontsize=9.5, color=color, weight="bold", va="center")
        ax.text(x + 0.048, 0.60, living_area(row["candidate_name"]), fontsize=12.0, color="#233239", weight="bold", va="center")
        ax.text(x + 0.048, 0.43, f"{money(row['rent'])} NTD", fontsize=9.6, color="#243238", weight="bold")
        ax.text(x + 0.048, 0.29, minutes(row["commute_minutes"]), fontsize=9.6, color="#243238", weight="bold")
        livability_label = f"生活機能 {float(row['livability_index']):.3f}"
        ax.text(
            x + card_width - 0.018,
            0.42,
            livability_label,
            fontsize=7.7,
            color=color if mode == "生活品質型" else "#6D7A7F",
            weight="bold" if mode == "生活品質型" else "normal",
            ha="right",
        )
        ax.text(x + 0.048, 0.16, MODE_COPY[mode], fontsize=7.4, color="#5F6F75", va="center")


def candidate_role(candidate_name: str, top3: pd.DataFrame) -> str:
    rows = top3[top3["candidate_name"] == candidate_name]
    if rows.empty:
        return "evaluated"
    if (rows["rank"] == 1).any():
        return "recommended"
    return "top3"


def top_modes_for_candidate(candidate_name: str, top3: pd.DataFrame, rank: int | None = None) -> list[str]:
    rows = top3[top3["candidate_name"] == candidate_name]
    if rank is not None:
        rows = rows[rows["rank"] == rank]
    mode_rank = {mode: index for index, mode in enumerate(MODE_ORDER)}
    return sorted(rows["preference_mode"].tolist(), key=lambda mode: mode_rank[mode])


def draw_city_labels(ax: plt.Axes) -> None:
    for city_name, x, y in [("新北市", 121.405, 25.095), ("臺北市", 121.555, 25.045)]:
        txt = ax.text(x, y, city_name, fontsize=10.5, color="#52646B", weight="bold", ha="center", va="center", zorder=8)
        txt.set_path_effects([pe.withStroke(linewidth=3.0, foreground="#FFFFFF")])


def draw_candidate_label(ax: plt.Axes, row: pd.Series, label: str, color: str, rank: int | None) -> None:
    offset = OVERVIEW_LABEL_OFFSETS.get(row["candidate_name"], (12, 8))
    annotation = ax.annotate(
        label,
        xy=(float(row["lon"]), float(row["lat"])),
        xytext=offset,
        textcoords="offset points",
        ha="right" if offset[0] < 0 else "left",
        va="center",
        fontsize=8.5 if rank == 1 else 7.8,
        color="#243238",
        bbox={
            "boxstyle": "round,pad=0.22",
            "fc": "#FFFFFF",
            "ec": color if rank == 1 else "#CBD4D7",
            "alpha": 0.94,
            "lw": 1.0 if rank == 1 else 0.75,
        },
        arrowprops={"arrowstyle": "-", "color": color, "lw": 0.7, "alpha": 0.48, "shrinkA": 0, "shrinkB": 5},
        zorder=10 if rank == 1 else 8,
    )
    annotation.set_path_effects([pe.withStroke(linewidth=2.2, foreground="#FFFFFF")])


def draw_map(
    ax: plt.Axes,
    candidates: pd.DataFrame,
    top3: pd.DataFrame,
    destination: dict[str, float | str],
    towns: gpd.GeoDataFrame,
    cities: gpd.GeoDataFrame,
) -> None:
    ax.set_facecolor("#F7F8F7")
    dest_lon = float(destination["destination_lon"])
    dest_lat = float(destination["destination_lat"])

    towns.plot(ax=ax, color="#F4F6F5", edgecolor="#DDE3E5", linewidth=0.32, zorder=0)
    target_towns = towns[towns["TOWNNAME"].isin(set(candidates["district"].tolist()) | {"內湖區"})]
    target_towns.plot(ax=ax, color="#EDF3F2", edgecolor="#CDD7DA", linewidth=0.50, zorder=1)
    for city_name, edgecolor, linewidth in [("新北市", "#7B8B74", 1.8), ("臺北市", "#6B7F8A", 1.7)]:
        cities[cities["COUNTYNAME"] == city_name].boundary.plot(ax=ax, color=edgecolor, linewidth=linewidth, zorder=3)

    evaluated = candidates[candidates["candidate_name"].map(lambda name: candidate_role(name, top3) == "evaluated")]
    top3_options = candidates[candidates["candidate_name"].map(lambda name: candidate_role(name, top3) == "top3")]
    recommended = candidates[candidates["candidate_name"].map(lambda name: candidate_role(name, top3) == "recommended")]

    ax.scatter(
        evaluated["lon"],
        evaluated["lat"],
        s=34,
        color="#AEB8BA",
        alpha=0.58,
        edgecolor="#FFFFFF",
        linewidth=0.45,
        zorder=4,
    )
    for _, row in top3_options.iterrows():
        modes = top_modes_for_candidate(row["candidate_name"], top3)
        color = MODE_COLORS[modes[0]]
        ax.scatter(
            [float(row["lon"])],
            [float(row["lat"])],
            s=260,
            color=color,
            alpha=0.16,
            edgecolor="none",
            zorder=5,
        )
        ax.scatter(
            [float(row["lon"])],
            [float(row["lat"])],
            s=76,
            color=color,
            alpha=0.68,
            edgecolor="#FFFFFF",
            linewidth=1.0,
            zorder=6,
        )

    for _, row in recommended.iterrows():
        modes = top_modes_for_candidate(row["candidate_name"], top3, rank=1)
        primary_color = MODE_COLORS[modes[0]]
        ax.scatter(
            [float(row["lon"])],
            [float(row["lat"])],
            s=780,
            color=primary_color,
            alpha=0.20,
            edgecolor="none",
            zorder=6,
        )
        ax.scatter(
            [float(row["lon"])],
            [float(row["lat"])],
            s=150,
            color=primary_color,
            alpha=1.0,
            edgecolor="#FFFFFF",
            linewidth=1.35,
            zorder=7,
        )
        if len(modes) > 1:
            ax.scatter(
                [float(row["lon"])],
                [float(row["lat"])],
                s=218,
                facecolor="none",
                edgecolor=MODE_COLORS[modes[1]],
                linewidth=2.0,
                zorder=8,
            )
        ax.text(
            float(row["lon"]),
            float(row["lat"]),
            "1",
            ha="center",
            va="center",
            fontsize=8.3,
            color="#FFFFFF",
            weight="bold",
            zorder=9,
        )

    for _, row in top3_options.iterrows():
        modes = top_modes_for_candidate(row["candidate_name"], top3)
        color = MODE_COLORS[modes[0]]
        label = f"{living_area(row['candidate_name'])}\nTop-3 option"
        draw_candidate_label(ax, row, label, color, rank=None)

    for _, row in recommended.iterrows():
        modes = top_modes_for_candidate(row["candidate_name"], top3, rank=1)
        label = f"{' / '.join(modes)}\n{living_area(row['candidate_name'])}"
        draw_candidate_label(ax, row, label, MODE_COLORS[modes[0]], rank=1)

    ax.scatter(
        [dest_lon],
        [dest_lat],
        s=195,
        marker="*",
        color="#C45B65",
        edgecolor="#742C34",
        linewidth=0.9,
        zorder=9,
    )
    workplace = ax.annotate(
        "Workplace anchor\n港墘站",
        xy=(dest_lon, dest_lat),
        xytext=(-18, 20),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=8.8,
        color="#742C34",
        bbox={"boxstyle": "round,pad=0.24", "fc": "#FFFFFF", "ec": "#C45B65", "alpha": 0.95, "lw": 0.9},
        arrowprops={"arrowstyle": "-", "color": "#C45B65", "lw": 0.75, "shrinkA": 0, "shrinkB": 5},
        zorder=10,
    )
    workplace.set_path_effects([pe.withStroke(linewidth=2.2, foreground="white")])

    draw_city_labels(ax)
    min_lon = min(candidates["lon"].min(), dest_lon)
    max_lon = max(candidates["lon"].max(), dest_lon)
    min_lat = min(candidates["lat"].min(), dest_lat)
    max_lat = max(candidates["lat"].max(), dest_lat)
    ax.set_xlim(min_lon - 0.070, max_lon + 0.080)
    ax.set_ylim(min_lat - 0.050, max_lat + 0.035)
    ax.set_axis_off()
    ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor="#4E8F77", markeredgecolor="#FFFFFF", markersize=8.5, label="Recommended"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor="#8EB6D0", markeredgecolor="#FFFFFF", alpha=0.72, markersize=7.0, label="Other Top-3 options"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor="#AEB8BA", markeredgecolor="#FFFFFF", alpha=0.70, markersize=5.8, label="Other evaluated candidates"),
            Line2D([0], [0], marker="*", color="none", markerfacecolor="#C45B65", markeredgecolor="#742C34", markersize=11, label="港墘站"),
            Line2D([0], [0], color="#7B8B74", lw=1.8, label="新北市外框"),
            Line2D([0], [0], color="#6B7F8A", lw=1.7, label="臺北市外框"),
        ],
        loc="upper right",
        frameon=True,
        facecolor="#FFFFFF",
        edgecolor="#D6DDE0",
        fontsize=7.8,
    )


def draw_comparison(ax: plt.Axes, top1: pd.DataFrame) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    add_rounded_rect(ax, (0.0, 0.10), 1.0, 0.78, "#FFFFFF", "#DDE5E6", linewidth=0.8, radius=0.022)
    ax.text(0.025, 0.72, "四模式 Top 1 比較", fontsize=10.6, color="#243238", weight="bold", va="center")
    rows_by_mode = {row["preference_mode"]: row for _, row in top1.iterrows()}
    x_positions = [0.025, 0.275, 0.525, 0.755]
    for x, mode in zip(x_positions, MODE_ORDER):
        row = rows_by_mode[mode]
        color = MODE_COLORS[mode]
        ax.scatter([x], [0.42], s=92, color=color, edgecolor="#FFFFFF", linewidth=1.0, transform=ax.transAxes)
        livability = f" | livability {float(row['livability_index']):.3f}" if mode == "生活品質型" else ""
        line = f"{mode}｜{living_area(row['candidate_name']).replace('生活圈', '')}｜{money(row['rent'])}｜{minutes(row['commute_minutes'])}{livability}"
        ax.text(x + 0.025, 0.42, line, fontsize=8.8, color="#334249", va="center", transform=ax.transAxes)


def plot_overview() -> tuple[Path, Path]:
    configure_matplotlib()
    towns, cities = load_boundaries()
    candidates, top3, top1, destination = load_overview_data()

    fig = plt.figure(figsize=(14.5, 8.8), facecolor="#F7F6F1")
    header_ax = fig.add_axes([0.045, 0.865, 0.91, 0.105])
    cards_ax = fig.add_axes([0.055, 0.705, 0.90, 0.13])
    map_ax = fig.add_axes([0.055, 0.220, 0.90, 0.455])
    comparison_ax = fig.add_axes([0.055, 0.060, 0.90, 0.120])

    draw_header(header_ax)
    draw_summary_cards(cards_ax, top1)
    draw_map(map_ax, candidates, top3, destination, towns, cities)
    draw_comparison(comparison_ax, top1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OVERVIEW_PNG, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(OVERVIEW_SVG, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return OVERVIEW_PNG, OVERVIEW_SVG


def main() -> int:
    candidates, top3, top1, _ = load_overview_data()
    unlabeled = sorted(
        set(candidates["candidate_name"])
        - set(top3["candidate_name"])
    )
    png, svg = plot_overview()
    print(f"Evaluated candidates shown: {len(candidates)}")
    print("Top 1 by mode:")
    for mode in MODE_ORDER:
        row = top1[top1["preference_mode"] == mode].iloc[0]
        print(f"{mode}: {row['candidate_name']}")
    print("Unlabeled evaluated candidates: " + ", ".join(unlabeled))
    print(f"Wrote {png.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {svg.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
