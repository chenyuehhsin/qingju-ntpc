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
BOUNDARY_SOURCE_LABEL = "NLSC/MOI township boundary (TWD97 lat/lon)"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "integration"
OUTPUT_PNG = OUTPUT_DIR / "03_recommendation_map.png"
OUTPUT_SVG = OUTPUT_DIR / "03_recommendation_map.svg"

MODE_COLORS = {
    "省租型": "#2A9D8F",
    "平衡型": "#E76F51",
    "通勤型": "#3A6EA5",
}
PARETO_OPTION_COLOR = "#9AA3A8"

MODE_LABELS = {
    "省租型": "省租型",
    "平衡型": "平衡型",
    "通勤型": "通勤型",
}

LABEL_OFFSETS = {
    "淡水站": (-18, 18),
    "汐止車站": (14, 10),
    "板橋站": (-28, -20),
    "樹林車站": (-18, -26),
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


def load_boundaries() -> gpd.GeoDataFrame:
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
    return towns[towns["COUNTYNAME"].isin(["新北市", "臺北市"])].copy()


def money(value: float | int) -> str:
    return f"{float(value):,.0f} NTD"


def minutes(value: float) -> str:
    return f"{float(value):.1f} min"


def load_recommendation_points() -> tuple[pd.DataFrame, dict[str, float | str]]:
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
        raise RuntimeError(f"Preference Top 1 mismatch; refusing to plot stale assumptions: {mismatches}")

    display = top_1[
        [
            "preference_mode",
            "candidate_name",
            "district",
            "official_median_rent",
            "commute_minutes",
            "transfer_count",
            "rent_saving_vs_neihu",
        ]
    ].copy()
    display["display_role"] = display["preference_mode"]

    shulin = rent_commute[
        (rent_commute["candidate_name"] == "樹林車站")
        & (rent_commute["is_pareto_efficient"] == True)  # noqa: E712
    ].copy()
    if len(shulin) != 1:
        raise RuntimeError(f"Expected one Pareto-efficient Shulin row, found {len(shulin)}.")
    shulin = shulin[
        [
            "candidate_name",
            "district",
            "official_median_rent",
            "commute_minutes",
            "transfer_count",
            "rent_saving_vs_neihu",
        ]
    ].copy()
    shulin["preference_mode"] = ""
    shulin["display_role"] = "Pareto option"
    display = pd.concat([display, shulin], ignore_index=True)

    display = display.merge(
        locations[["candidate_name", "lat", "lon", "station_name", "station_operator"]],
        on="candidate_name",
        how="left",
        validate="one_to_one",
    )
    missing_locations = display[display["lat"].isna() | display["lon"].isna()]["candidate_name"].tolist()
    if missing_locations:
        raise RuntimeError(f"Missing candidate coordinates: {missing_locations}")

    destination_rows = commute[["destination", "destination_lat", "destination_lon"]].drop_duplicates()
    if len(destination_rows) != 1:
        raise RuntimeError(f"Expected one destination coordinate row, found {len(destination_rows)}.")
    destination = destination_rows.iloc[0].to_dict()
    if destination["destination"] != "港墘站":
        raise RuntimeError(f"Expected destination 港墘站, found {destination['destination']}.")

    return display, destination


def add_candidate_label(ax: plt.Axes, row: pd.Series) -> None:
    mode_label = row["display_role"]
    label = (
        f"{row['candidate_name']}\n"
        f"{mode_label}\n"
        f"Rent {money(row['official_median_rent'])}\n"
        f"Commute {minutes(row['commute_minutes'])}"
    )
    offset = LABEL_OFFSETS.get(row["candidate_name"], (10, 10))
    annotation = ax.annotate(
        label,
        xy=(float(row["lon"]), float(row["lat"])),
        xytext=offset,
        textcoords="offset points",
        ha="right" if offset[0] < 0 else "left",
        va="center",
        fontsize=8.2,
        color="#222222",
        arrowprops={"arrowstyle": "-", "color": "#6E6E6E", "lw": 0.75, "shrinkA": 0, "shrinkB": 4},
        bbox={"boxstyle": "round,pad=0.24", "fc": "white", "ec": "#C9CED3", "alpha": 0.94},
        zorder=8,
    )
    annotation.set_path_effects([pe.withStroke(linewidth=2.2, foreground="white")])


def plot_map(points: pd.DataFrame, destination: dict[str, float | str], boundaries: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10.8, 8.2))

    boundaries.plot(ax=ax, color="#F4F5F5", edgecolor="#D6DADD", linewidth=0.5, zorder=0)
    target_towns = boundaries[
        boundaries["TOWNNAME"].isin(set(points["district"].tolist()) | {"內湖區"})
    ]
    target_towns.plot(ax=ax, color="#E7EDF1", edgecolor="#AEB9C2", linewidth=0.85, zorder=1)

    dest_lon = float(destination["destination_lon"])
    dest_lat = float(destination["destination_lat"])

    for _, row in points.iterrows():
        ax.plot(
            [float(row["lon"]), dest_lon],
            [float(row["lat"]), dest_lat],
            color="#8C8C8C",
            linewidth=0.85,
            alpha=0.42,
            zorder=2,
        )

    for _, row in points.iterrows():
        role = row["display_role"]
        is_pareto_option = role == "Pareto option"
        color = PARETO_OPTION_COLOR if is_pareto_option else MODE_COLORS[str(role)]
        ax.scatter(
            [float(row["lon"])],
            [float(row["lat"])],
            s=82 if is_pareto_option else 118,
            marker="o",
            color=color,
            edgecolor="white" if is_pareto_option else "#202020",
            linewidth=1.0,
            alpha=0.72 if is_pareto_option else 1.0,
            zorder=5 if is_pareto_option else 6,
        )

    ax.scatter(
        [dest_lon],
        [dest_lat],
        s=185,
        marker="*",
        color="#C43B4B",
        edgecolor="#771D28",
        linewidth=0.9,
        zorder=7,
    )

    for _, row in points.iterrows():
        add_candidate_label(ax, row)

    workplace = ax.annotate(
        "Workplace anchor: Gangqian",
        xy=(dest_lon, dest_lat),
        xytext=(16, 18),
        textcoords="offset points",
        ha="left",
        va="bottom",
        fontsize=9.5,
        color="#771D28",
        arrowprops={"arrowstyle": "-", "color": "#771D28", "lw": 0.9, "shrinkA": 0, "shrinkB": 5},
        bbox={"boxstyle": "round,pad=0.24", "fc": "white", "ec": "#C43B4B", "alpha": 0.95},
        zorder=9,
    )
    workplace.set_path_effects([pe.withStroke(linewidth=2.2, foreground="white")])

    min_lon = min(points["lon"].min(), dest_lon)
    max_lon = max(points["lon"].max(), dest_lon)
    min_lat = min(points["lat"].min(), dest_lat)
    max_lat = max(points["lat"].max(), dest_lat)
    ax.set_xlim(min_lon - 0.085, max_lon + 0.055)
    ax.set_ylim(min_lat - 0.055, max_lat + 0.035)
    ax.set_axis_off()
    ax.set_title("MVP Recommendation Map: Living Areas to Gangqian", fontsize=14, pad=12)

    ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor=MODE_COLORS["省租型"], markeredgecolor="#202020", markersize=8.5, label="省租型"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor=MODE_COLORS["平衡型"], markeredgecolor="#202020", markersize=8.5, label="平衡型"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor=MODE_COLORS["通勤型"], markeredgecolor="#202020", markersize=8.5, label="通勤型"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor=PARETO_OPTION_COLOR, markeredgecolor="white", alpha=0.72, markersize=8, label="Pareto option"),
            Line2D([0], [0], marker="*", color="none", markerfacecolor="#C43B4B", markeredgecolor="#771D28", markersize=12, label="港墘站"),
            Line2D([0], [0], color="#8C8C8C", lw=0.9, alpha=0.55, label="OD line (schematic)"),
        ],
        loc="upper right",
        frameon=True,
        fontsize=8.5,
    )

    ax.text(
        0.01,
        0.015,
        "Commute: weekday 08:00 station-to-station public-transit time.\n"
        "Rent: district-level official independent-suite median benchmark.\n"
        f"Boundary: {BOUNDARY_SOURCE_LABEL}. OD lines are schematic straight lines.",
        transform=ax.transAxes,
        fontsize=7.6,
        color="#555555",
        va="bottom",
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUTPUT_PNG, bbox_inches="tight")
    fig.savefig(OUTPUT_SVG, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    configure_matplotlib()
    boundaries = load_boundaries()
    points, destination = load_recommendation_points()
    plot_map(points, destination, boundaries)

    print(f"Wrote {OUTPUT_PNG.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {OUTPUT_SVG.relative_to(PROJECT_ROOT)}")
    print("Recommendation points plotted: " + ", ".join(points["candidate_name"].tolist()))
    print(f"Destination plotted: {destination['destination']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
