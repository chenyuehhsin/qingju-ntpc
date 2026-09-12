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
CANDIDATE_LOCATIONS_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "candidate_locations.csv"
COMMUTE_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "commute_to_gangqian.csv"
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
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "transport"
OUTPUT_PNG = OUTPUT_DIR / "01_candidate_commute_map.png"
OUTPUT_SVG = OUTPUT_DIR / "01_candidate_commute_map.svg"
BOUNDARY_SOURCE_LABEL = "NLSC/MOI township boundary (TWD97 lat/lon)"

LABEL_OFFSETS = {
    "汐止車站": (8, 6),
    "頂溪站": (8, -18),
    "景安站": (8, -18),
    "大坪林站": (8, -20),
    "板橋站": (-46, -18),
    "三重站": (-46, 10),
    "新莊站": (-48, -18),
    "蘆洲站": (-48, 8),
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


def load_points() -> tuple[pd.DataFrame, dict[str, float | str]]:
    candidates = pd.read_csv(CANDIDATE_LOCATIONS_CSV)
    commute = pd.read_csv(COMMUTE_CSV)
    merged = candidates.merge(
        commute[
            [
                "candidate_name",
                "destination",
                "destination_lat",
                "destination_lon",
                "departure_time",
                "commute_minutes",
                "transfer_count",
                "query_status",
            ]
        ],
        on="candidate_name",
        how="left",
        validate="one_to_one",
    )
    missing_commute = merged[merged["commute_minutes"].isna()]["candidate_name"].tolist()
    if missing_commute:
        raise RuntimeError(f"Missing commute_minutes for candidates: {missing_commute}")
    if len(merged) != 8:
        raise RuntimeError(f"Expected 8 candidate rows, got {len(merged)}.")

    destination_rows = commute[["destination", "destination_lat", "destination_lon"]].drop_duplicates()
    if len(destination_rows) != 1:
        raise RuntimeError(f"Expected one destination, found {len(destination_rows)}.")
    destination = destination_rows.iloc[0].to_dict()
    return merged, destination


def add_label(ax: plt.Axes, x: float, y: float, text: str, xytext: tuple[int, int]) -> None:
    annotation = ax.annotate(
        text,
        xy=(x, y),
        xytext=xytext,
        textcoords="offset points",
        ha="left" if xytext[0] >= 0 else "right",
        va="center",
        fontsize=8.5,
        color="#222222",
        arrowprops={"arrowstyle": "-", "color": "#777777", "lw": 0.7, "shrinkA": 0, "shrinkB": 4},
        bbox={"boxstyle": "round,pad=0.18", "fc": "white", "ec": "#D0D0D0", "alpha": 0.9},
        zorder=5,
    )
    annotation.set_path_effects([pe.withStroke(linewidth=2, foreground="white")])


def plot_map(candidates: pd.DataFrame, destination: dict[str, float | str], boundaries: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 8))

    boundaries.plot(ax=ax, color="#F1F1F1", edgecolor="#D2D2D2", linewidth=0.55, zorder=0)
    target_towns = boundaries[
        boundaries["TOWNNAME"].isin(set(candidates["district"].tolist()) | {"內湖區"})
    ]
    target_towns.plot(ax=ax, color="#E8EEF4", edgecolor="#AAB7C4", linewidth=0.8, zorder=1)

    dest_lon = float(destination["destination_lon"])
    dest_lat = float(destination["destination_lat"])
    for _, row in candidates.iterrows():
        ax.plot(
            [row["lon"], dest_lon],
            [row["lat"], dest_lat],
            color="#8A8A8A",
            linewidth=0.8,
            alpha=0.45,
            zorder=2,
        )

    ax.scatter(
        candidates["lon"],
        candidates["lat"],
        s=64,
        color="#2F6B9A",
        edgecolor="white",
        linewidth=0.8,
        zorder=4,
    )
    ax.scatter(
        [dest_lon],
        [dest_lat],
        s=150,
        marker="*",
        color="#C44E52",
        edgecolor="#7A1D22",
        linewidth=0.8,
        zorder=6,
    )

    for _, row in candidates.iterrows():
        label = f"{row['candidate_name']}\n{row['commute_minutes']:.1f} min"
        add_label(ax, float(row["lon"]), float(row["lat"]), label, LABEL_OFFSETS[row["candidate_name"]])

    ax.annotate(
        "Workplace anchor: Gangqian",
        xy=(dest_lon, dest_lat),
        xytext=(14, 16),
        textcoords="offset points",
        ha="left",
        va="bottom",
        fontsize=9.5,
        color="#7A1D22",
        arrowprops={"arrowstyle": "-", "color": "#7A1D22", "lw": 0.9, "shrinkA": 0, "shrinkB": 5},
        bbox={"boxstyle": "round,pad=0.22", "fc": "white", "ec": "#C44E52", "alpha": 0.92},
        zorder=7,
    )

    min_lon = min(candidates["lon"].min(), dest_lon)
    max_lon = max(candidates["lon"].max(), dest_lon)
    min_lat = min(candidates["lat"].min(), dest_lat)
    max_lat = max(candidates["lat"].max(), dest_lat)
    ax.set_xlim(min_lon - 0.035, max_lon + 0.045)
    ax.set_ylim(min_lat - 0.025, max_lat + 0.035)
    ax.set_axis_off()
    ax.set_title("Candidate Residence Nodes to Gangqian Station", fontsize=14, pad=12)
    ax.text(
        0.01,
        0.01,
        f"Inputs: candidate_locations.csv, commute_to_gangqian.csv\nBoundary: {BOUNDARY_SOURCE_LABEL}\nOD lines are schematic straight lines, not actual transit paths.",
        transform=ax.transAxes,
        fontsize=7.5,
        color="#555555",
        va="bottom",
    )
    ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor="#2F6B9A", markeredgecolor="white", markersize=8, label="candidate stations"),
            Line2D([0], [0], marker="*", color="none", markerfacecolor="#C44E52", markeredgecolor="#7A1D22", markersize=12, label="workplace anchor"),
            Line2D([0], [0], color="#8A8A8A", lw=0.9, alpha=0.6, label="OD line"),
        ],
        loc="upper left",
        frameon=True,
        fontsize=8.5,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    fig.savefig(OUTPUT_PNG, bbox_inches="tight")
    fig.savefig(OUTPUT_SVG, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    configure_matplotlib()
    boundaries = load_boundaries()
    candidates, destination = load_points()
    plot_map(candidates, destination, boundaries)
    print(f"Wrote {OUTPUT_PNG.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {OUTPUT_SVG.relative_to(PROJECT_ROOT)}")
    print(f"Candidate points plotted: {len(candidates)}")
    print(f"Destination plotted: {destination['destination']}")
    print("OD lines plotted: yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
