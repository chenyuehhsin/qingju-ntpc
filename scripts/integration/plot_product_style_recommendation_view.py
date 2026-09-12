#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path


PROJECT_CACHE_DIR = Path(tempfile.gettempdir()) / "qingju_ntpc_cache"
os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_CACHE_DIR / "xdg"))
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_CACHE_DIR / "matplotlib"))

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREFERENCE_CSV = PROJECT_ROOT / "data" / "processed" / "integration" / "preference_recommendations.csv"
RENT_COMMUTE_CSV = PROJECT_ROOT / "data" / "processed" / "integration" / "rent_commute_candidates_expanded.csv"
CANDIDATE_LOCATIONS_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "candidate_locations_expanded.csv"
COMMUTE_EXPANDED_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "commute_to_gangqian_expanded.csv"

BOUNDARY_SHP = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "housing"
    / "boundaries"
    / "nlsc_town_boundary_twd97"
    / "TOWN_MOI_1120317.shp"
)
BOUNDARY_ZIP = PROJECT_ROOT / "data" / "interim" / "housing" / "boundaries" / "nlsc_town_boundary_twd97.zip"
BOUNDARY_EXTRACT_DIR = PROJECT_ROOT / "data" / "interim" / "housing" / "boundaries" / "nlsc_town_boundary_twd97"
BOUNDARY_SOURCE_URL = "https://maps.nlsc.gov.tw/download/%E9%84%89%E9%8E%AE%E5%B8%82%E5%8D%80%E7%95%8C%E7%B7%9A(TWD97%E7%B6%93%E7%B7%AF%E5%BA%A6).zip"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "integration"
OUTPUT_PNG = OUTPUT_DIR / "04_product_style_recommendation_view.png"
OUTPUT_SVG = OUTPUT_DIR / "04_product_style_recommendation_view.svg"

MODE_ORDER = ["通勤型", "平衡型", "省租型"]
MODE_TO_LIVING_AREA = {
    "通勤型": "板橋生活圈",
    "平衡型": "汐止生活圈",
    "省租型": "淡水生活圈",
}
MODE_DESCRIPTIONS = {
    "通勤型": "適合最重視上班時間的人",
    "平衡型": "租金與通勤取得較佳折衷",
    "省租型": "願意用較長通勤換取較低租金",
}
MODE_COLORS = {
    "通勤型": "#E9A15B",
    "平衡型": "#6FA8C9",
    "省租型": "#7FBF9A",
    "Pareto option": "#B9AED2",
}
MODE_SOFT_COLORS = {
    "通勤型": "#FFF2E4",
    "平衡型": "#EAF4FA",
    "省租型": "#EAF6EF",
    "Pareto option": "#F1EEF7",
}
PARETO_OPTION_NAME = "樹林車站"
PARETO_OPTION_AREA = "樹林生活圈"

MAP_LABEL_OFFSETS = {
    "淡水站": (-8, 20),
    "汐止車站": (16, 4),
    "板橋站": (14, -16),
    "樹林車站": (-18, -24),
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
    plt.rcParams["figure.dpi"] = 170


def ensure_boundary_data() -> None:
    if BOUNDARY_SHP.exists():
        return
    BOUNDARY_ZIP.parent.mkdir(parents=True, exist_ok=True)
    if not BOUNDARY_ZIP.exists() or BOUNDARY_ZIP.stat().st_size == 0:
        with urllib.request.urlopen(BOUNDARY_SOURCE_URL, timeout=60) as response:
            BOUNDARY_ZIP.write_bytes(response.read())
    if BOUNDARY_EXTRACT_DIR.exists():
        shutil.rmtree(BOUNDARY_EXTRACT_DIR)
    BOUNDARY_EXTRACT_DIR.mkdir(parents=True)
    with zipfile.ZipFile(BOUNDARY_ZIP) as zf:
        zf.extractall(BOUNDARY_EXTRACT_DIR)


def load_boundaries() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    ensure_boundary_data()
    shapefiles = list(BOUNDARY_EXTRACT_DIR.rglob("*.shp"))
    if not shapefiles:
        raise FileNotFoundError(f"No .shp files found in {BOUNDARY_EXTRACT_DIR}")
    shapefile = BOUNDARY_SHP if BOUNDARY_SHP.exists() else max(shapefiles, key=lambda path: path.stat().st_size)
    towns = gpd.read_file(shapefile, encoding="utf-8")
    if towns.crs is None:
        towns = towns.set_crs("EPSG:3824")
    towns = towns.to_crs("EPSG:4326")
    required = {"COUNTYNAME", "TOWNNAME", "geometry"}
    missing = required - set(towns.columns)
    if missing:
        raise RuntimeError(f"Boundary file is missing expected columns: {sorted(missing)}")
    towns = towns[towns["COUNTYNAME"].isin(["新北市", "臺北市"])].copy()
    cities = towns.dissolve(by="COUNTYNAME", as_index=False)
    return towns, cities


def money(value: float | int) -> str:
    return f"{float(value):,.0f}"


def minutes(value: float) -> str:
    return f"{float(value):.1f} min"


def load_points() -> tuple[pd.DataFrame, dict[str, float | str]]:
    preferences = pd.read_csv(PREFERENCE_CSV)
    rent_commute = pd.read_csv(RENT_COMMUTE_CSV)
    locations = pd.read_csv(CANDIDATE_LOCATIONS_CSV)
    commute = pd.read_csv(COMMUTE_EXPANDED_CSV)

    top_1 = preferences[preferences["rank"] == 1].copy()
    expected = {
        "省租型": "淡水站",
        "平衡型": "汐止車站",
        "通勤型": "板橋站",
    }
    actual = top_1.set_index("preference_mode")["candidate_name"].to_dict()
    mismatches = {
        mode: {"expected": expected_name, "actual": actual.get(mode)}
        for mode, expected_name in expected.items()
        if actual.get(mode) != expected_name
    }
    if mismatches:
        raise RuntimeError(f"Top 1 recommendation mismatch: {mismatches}")

    top_1["display_role"] = top_1["preference_mode"]
    top_1["living_area"] = top_1["preference_mode"].map(MODE_TO_LIVING_AREA)

    shulin = rent_commute[
        (rent_commute["candidate_name"] == PARETO_OPTION_NAME)
        & (rent_commute["is_pareto_efficient"] == True)  # noqa: E712
    ].copy()
    if len(shulin) != 1:
        raise RuntimeError(f"Expected one Pareto-efficient Shulin row, found {len(shulin)}.")
    shulin["preference_mode"] = ""
    shulin["display_role"] = "Pareto option"
    shulin["living_area"] = PARETO_OPTION_AREA

    keep_cols = [
        "preference_mode",
        "display_role",
        "living_area",
        "candidate_name",
        "district",
        "official_median_rent",
        "commute_minutes",
        "transfer_count",
        "rent_saving_vs_neihu",
    ]
    points = pd.concat([top_1[keep_cols], shulin[keep_cols]], ignore_index=True)
    points = points.merge(
        locations[["candidate_name", "lat", "lon", "station_name", "station_operator"]],
        on="candidate_name",
        how="left",
        validate="one_to_one",
    )
    missing_locations = points[points["lat"].isna() | points["lon"].isna()]["candidate_name"].tolist()
    if missing_locations:
        raise RuntimeError(f"Missing candidate coordinates: {missing_locations}")

    destination_rows = commute[["destination", "destination_lat", "destination_lon"]].drop_duplicates()
    if len(destination_rows) != 1:
        raise RuntimeError(f"Expected one destination coordinate row, found {len(destination_rows)}.")
    destination = destination_rows.iloc[0].to_dict()
    if destination["destination"] != "港墘站":
        raise RuntimeError(f"Expected destination 港墘站, found {destination['destination']}.")

    return points, destination


def add_rounded_rect(
    ax: plt.Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    facecolor: str,
    edgecolor: str,
    linewidth: float = 1.0,
    radius: float = 0.025,
    alpha: float = 1.0,
    zorder: int = 1,
) -> FancyBboxPatch:
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle=f"round,pad=0.008,rounding_size={radius}",
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
        alpha=alpha,
        transform=ax.transAxes,
        clip_on=False,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def draw_left_panel(ax: plt.Axes, points: pd.DataFrame) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.text(0.02, 0.965, "青聚新北", fontsize=11, color="#49636F", weight="bold", va="top")
    ax.text(0.02, 0.91, "推薦生活圈", fontsize=21, color="#223139", weight="bold", va="top")
    ax.text(
        0.02,
        0.855,
        "依 MVP 偏好模式，從 Pareto frontier 中挑選。",
        fontsize=8.7,
        color="#68777E",
        va="top",
        wrap=True,
    )

    y_positions = [0.675, 0.46, 0.245]
    by_mode = points[points["display_role"].isin(MODE_ORDER)].set_index("display_role")
    for mode, y in zip(MODE_ORDER, y_positions):
        row = by_mode.loc[mode]
        color = MODE_COLORS[mode]
        soft = MODE_SOFT_COLORS[mode]
        add_rounded_rect(ax, (0.02, y), 0.9, 0.165, "#FFFFFF", "#D8E0E3", linewidth=0.9, radius=0.025)
        add_rounded_rect(ax, (0.035, y + 0.109), 0.18, 0.037, soft, color, linewidth=0.8, radius=0.015)
        ax.text(0.125, y + 0.128, mode, ha="center", va="center", fontsize=9.2, color="#26353B", weight="bold")
        ax.scatter([0.055], [y + 0.071], s=125, color=color, edgecolor="#FFFFFF", linewidth=1.4, transform=ax.transAxes, zorder=5)
        ax.text(0.095, y + 0.083, row["living_area"], fontsize=13.2, color="#233139", weight="bold", va="center")
        ax.text(0.095, y + 0.047, row["candidate_name"], fontsize=8.8, color="#6A777D", va="center")
        ax.text(0.78, y + 0.092, f"{money(row['official_median_rent'])} NTD", fontsize=11.7, color="#233139", weight="bold", ha="right")
        ax.text(0.78, y + 0.047, minutes(row["commute_minutes"]), fontsize=12.4, color="#233139", weight="bold", ha="right")
        ax.text(0.795, y + 0.047, "to 港墘", fontsize=7.8, color="#6A777D", va="baseline")

    shulin = points[points["display_role"] == "Pareto option"].iloc[0]
    y = 0.065
    add_rounded_rect(ax, (0.02, y), 0.9, 0.12, "#FAFAFC", "#DDD8E8", linewidth=0.9, radius=0.025)
    ax.scatter(
        [0.055],
        [y + 0.062],
        s=95,
        color=MODE_COLORS["Pareto option"],
        edgecolor="#FFFFFF",
        linewidth=1.1,
        transform=ax.transAxes,
        zorder=5,
    )
    ax.text(0.095, y + 0.078, "其他 Pareto 選項", fontsize=8.9, color="#706789", weight="bold", va="center")
    ax.text(0.095, y + 0.044, shulin["living_area"], fontsize=11.7, color="#25333A", weight="bold", va="center")
    ax.text(
        0.78,
        y + 0.061,
        f"{money(shulin['official_median_rent'])} NTD | {minutes(shulin['commute_minutes'])}",
        fontsize=8.6,
        color="#4F5B61",
        ha="right",
        va="center",
    )


def add_map_label(ax: plt.Axes, row: pd.Series) -> None:
    role = row["display_role"]
    color = MODE_COLORS[role]
    label = f"{role}\n{row['living_area']}"
    offset = MAP_LABEL_OFFSETS.get(row["candidate_name"], (12, 10))
    annotation = ax.annotate(
        label,
        xy=(float(row["lon"]), float(row["lat"])),
        xytext=offset,
        textcoords="offset points",
        ha="right" if offset[0] < 0 else "left",
        va="center",
        fontsize=8.7,
        color="#243238",
        bbox={"boxstyle": "round,pad=0.22", "fc": "#FFFFFF", "ec": color, "alpha": 0.93, "lw": 0.9},
        arrowprops={"arrowstyle": "-", "color": color, "lw": 0.75, "alpha": 0.7, "shrinkA": 0, "shrinkB": 5},
        zorder=9,
    )
    annotation.set_path_effects([pe.withStroke(linewidth=2.2, foreground="white")])


def draw_map(
    ax: plt.Axes,
    points: pd.DataFrame,
    destination: dict[str, float | str],
    towns: gpd.GeoDataFrame,
    cities: gpd.GeoDataFrame,
) -> None:
    ax.set_facecolor("#F7F8F7")

    dest_lon = float(destination["destination_lon"])
    dest_lat = float(destination["destination_lat"])
    focus_towns = towns[towns["COUNTYNAME"].isin(["新北市", "臺北市"])].copy()
    focus_towns.plot(ax=ax, color="#F4F6F5", edgecolor="#DDE3E5", linewidth=0.35, zorder=0)
    target_towns = towns[towns["TOWNNAME"].isin(set(points["district"].tolist()) | {"內湖區"})]
    target_towns.plot(ax=ax, color="#EDF3F2", edgecolor="#CDD7DA", linewidth=0.55, zorder=1)

    city_styles = {
        "臺北市": {"edgecolor": "#6B7F8A", "linewidth": 1.65},
        "新北市": {"edgecolor": "#7B8B74", "linewidth": 1.75},
    }
    for city_name, style in city_styles.items():
        cities[cities["COUNTYNAME"] == city_name].boundary.plot(
            ax=ax,
            color=style["edgecolor"],
            linewidth=style["linewidth"],
            zorder=3,
        )

    for _, row in points.iterrows():
        ax.plot(
            [float(row["lon"]), dest_lon],
            [float(row["lat"]), dest_lat],
            color="#9EA7AA",
            linewidth=0.55,
            alpha=0.20,
            zorder=2,
        )

    for _, row in points.iterrows():
        role = row["display_role"]
        color = MODE_COLORS[role]
        ax.scatter(
            [float(row["lon"])],
            [float(row["lat"])],
            s=720 if role != "Pareto option" else 560,
            color=color,
            alpha=0.18 if role != "Pareto option" else 0.13,
            edgecolor="none",
            zorder=4,
        )
        ax.scatter(
            [float(row["lon"])],
            [float(row["lat"])],
            s=142 if role != "Pareto option" else 96,
            color=color,
            alpha=0.96 if role != "Pareto option" else 0.68,
            edgecolor="#FFFFFF",
            linewidth=1.4,
            zorder=6,
        )

    ax.scatter(
        [dest_lon],
        [dest_lat],
        s=200,
        marker="*",
        color="#C45B65",
        edgecolor="#742C34",
        linewidth=0.9,
        zorder=7,
    )

    for _, row in points.iterrows():
        add_map_label(ax, row)

    workplace = ax.annotate(
        "workplace anchor\n港墘站",
        xy=(dest_lon, dest_lat),
        xytext=(16, 16),
        textcoords="offset points",
        ha="left",
        va="bottom",
        fontsize=9.1,
        color="#742C34",
        bbox={"boxstyle": "round,pad=0.24", "fc": "#FFFFFF", "ec": "#C45B65", "alpha": 0.95, "lw": 0.95},
        arrowprops={"arrowstyle": "-", "color": "#C45B65", "lw": 0.85, "shrinkA": 0, "shrinkB": 5},
        zorder=9,
    )
    workplace.set_path_effects([pe.withStroke(linewidth=2.2, foreground="white")])

    city_labels = {
        "臺北市": (121.555, 25.045),
        "新北市": (121.405, 25.095),
    }
    for city_name, (x, y) in city_labels.items():
        txt = ax.text(
            x,
            y,
            city_name,
            fontsize=10.5,
            color="#51636A",
            weight="bold",
            ha="center",
            va="center",
            zorder=8,
        )
        txt.set_path_effects([pe.withStroke(linewidth=3.0, foreground="#FFFFFF")])

    min_lon = min(points["lon"].min(), dest_lon)
    max_lon = max(points["lon"].max(), dest_lon)
    min_lat = min(points["lat"].min(), dest_lat)
    max_lat = max(points["lat"].max(), dest_lat)
    ax.set_xlim(min_lon - 0.08, max_lon + 0.055)
    ax.set_ylim(min_lat - 0.052, max_lat + 0.038)
    ax.set_axis_off()

    ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor=MODE_COLORS["通勤型"], markeredgecolor="#FFFFFF", markersize=8, label="通勤型"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor=MODE_COLORS["平衡型"], markeredgecolor="#FFFFFF", markersize=8, label="平衡型"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor=MODE_COLORS["省租型"], markeredgecolor="#FFFFFF", markersize=8, label="省租型"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor=MODE_COLORS["Pareto option"], markeredgecolor="#FFFFFF", markersize=7, label="其他 Pareto"),
            Line2D([0], [0], color="#7B8B74", lw=1.8, label="新北市外框"),
            Line2D([0], [0], color="#6B7F8A", lw=1.7, label="臺北市外框"),
        ],
        loc="upper right",
        frameon=True,
        facecolor="#FFFFFF",
        edgecolor="#D6DDE0",
        fontsize=8.1,
    )


def draw_summary(ax: plt.Axes) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    items = [
        ("通勤型", MODE_DESCRIPTIONS["通勤型"]),
        ("平衡型", MODE_DESCRIPTIONS["平衡型"]),
        ("省租型", MODE_DESCRIPTIONS["省租型"]),
    ]
    x_positions = [0.035, 0.36, 0.685]
    for (mode, desc), x in zip(items, x_positions):
        add_rounded_rect(ax, (x, 0.19), 0.285, 0.58, "#FFFFFF", "#DDE5E6", linewidth=0.8, radius=0.02)
        ax.scatter([x + 0.035], [0.50], s=120, color=MODE_COLORS[mode], edgecolor="#FFFFFF", linewidth=1.0, transform=ax.transAxes)
        ax.text(x + 0.065, 0.56, mode, transform=ax.transAxes, fontsize=10.5, color="#25333A", weight="bold", va="center")
        ax.text(x + 0.065, 0.39, desc, transform=ax.transAxes, fontsize=9.2, color="#5E6C72", va="center")

    ax.text(
        0.035,
        0.04,
        "通勤時間為平日 08:00、站到站公共運輸時間；租金為行政區獨立套房官方中位數 benchmark。OD 線僅表示相對位置，不代表實際路徑。",
        fontsize=8.2,
        color="#738086",
        va="bottom",
    )


def plot_view(points: pd.DataFrame, destination: dict[str, float | str], towns: gpd.GeoDataFrame, cities: gpd.GeoDataFrame) -> None:
    fig = plt.figure(figsize=(14, 8.6), facecolor="#F7F6F1")
    fig.text(0.055, 0.955, "青聚新北 MVP", fontsize=11, color="#6C7A7E", weight="bold", va="top")
    fig.text(0.055, 0.918, "找到適合你的新北生活圈", fontsize=25, color="#223139", weight="bold", va="top")
    fig.text(
        0.055,
        0.875,
        "以港墘站作為工作地錨點，呈現三種偏好模式的推薦生活圈與跨市位置關係。",
        fontsize=10.2,
        color="#65747A",
        va="top",
    )

    left_ax = fig.add_axes([0.055, 0.215, 0.29, 0.62])
    map_ax = fig.add_axes([0.375, 0.215, 0.57, 0.64])
    summary_ax = fig.add_axes([0.055, 0.055, 0.89, 0.13])

    add_rounded_rect(left_ax, (0.0, 0.0), 0.96, 1.0, "#FFFFFF", "#E0E5E6", linewidth=0.9, radius=0.03, zorder=0)
    draw_left_panel(left_ax, points)

    draw_map(map_ax, points, destination, towns, cities)
    draw_summary(summary_ax)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PNG, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(OUTPUT_SVG, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> int:
    configure_matplotlib()
    towns, cities = load_boundaries()
    points, destination = load_points()
    plot_view(points, destination, towns, cities)
    print(f"Wrote {OUTPUT_PNG.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {OUTPUT_SVG.relative_to(PROJECT_ROOT)}")
    print("Recommendation living areas: " + ", ".join(points["living_area"].tolist()))
    print("City boundaries plotted: 臺北市, 新北市")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
