from __future__ import annotations

import shutil
import urllib.request
import zipfile
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from mpl_toolkits.axes_grid1 import make_axes_locatable
import pandas as pd

from common import INTERIM_HOUSING, OUTPUT_HOUSING, PROCESSED_HOUSING, ensure_output_dirs


BENCHMARK_CSV = PROCESSED_HOUSING / "moi_independent_suite_rent_benchmark.csv"
OUTPUT_PNG = OUTPUT_HOUSING / "05_ntpc_rent_choropleth.png"
BOUNDARY_DIR = INTERIM_HOUSING / "boundaries"
BOUNDARY_ZIP = BOUNDARY_DIR / "nlsc_town_boundary_twd97.zip"
BOUNDARY_EXTRACT_DIR = BOUNDARY_DIR / "nlsc_town_boundary_twd97"
BOUNDARY_SOURCE_URL = "https://maps.nlsc.gov.tw/download/%E9%84%89%E9%8E%AE%E5%B8%82%E5%8D%80%E7%95%8C%E7%B7%9A(TWD97%E7%B6%93%E7%B7%AF%E5%BA%A6).zip"
BOUNDARY_SOURCE_LABEL = "內政部國土測繪中心 鄉鎮市區界線(TWD97經緯度), Government Open Data dataset 7441"

LABEL_DISTRICTS = ["汐止區", "新店區", "中和區", "永和區", "板橋區", "新莊區", "蘆洲區", "淡水區", "三峽區"]


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
    plt.rcParams["figure.dpi"] = 150


def ensure_boundary_zip() -> None:
    BOUNDARY_DIR.mkdir(parents=True, exist_ok=True)
    if BOUNDARY_ZIP.exists() and BOUNDARY_ZIP.stat().st_size > 0:
        return
    with urllib.request.urlopen(BOUNDARY_SOURCE_URL, timeout=60) as response:
        BOUNDARY_ZIP.write_bytes(response.read())


def extract_boundary_zip() -> Path:
    if BOUNDARY_EXTRACT_DIR.exists() and list(BOUNDARY_EXTRACT_DIR.rglob("*.shp")):
        return BOUNDARY_EXTRACT_DIR
    if BOUNDARY_EXTRACT_DIR.exists():
        shutil.rmtree(BOUNDARY_EXTRACT_DIR)
    BOUNDARY_EXTRACT_DIR.mkdir(parents=True)
    with zipfile.ZipFile(BOUNDARY_ZIP) as zf:
        zf.extractall(BOUNDARY_EXTRACT_DIR)
    return BOUNDARY_EXTRACT_DIR


def load_boundaries() -> gpd.GeoDataFrame:
    ensure_boundary_zip()
    extract_dir = extract_boundary_zip()
    shapefiles = list(extract_dir.rglob("*.shp"))
    if not shapefiles:
        raise FileNotFoundError(f"No .shp files found after extracting {BOUNDARY_ZIP}")

    shapefile = max(shapefiles, key=lambda path: path.stat().st_size)
    towns = gpd.read_file(shapefile, encoding="utf-8")
    if towns.crs is None:
        towns = towns.set_crs("EPSG:3824")
    towns = towns.to_crs("EPSG:4326")

    required = {"COUNTYNAME", "TOWNNAME"}
    missing = required - set(towns.columns)
    if missing:
        raise RuntimeError(f"Boundary file is missing expected columns: {sorted(missing)}")
    return towns


def main() -> None:
    ensure_output_dirs()
    configure_matplotlib()

    benchmark = pd.read_csv(BENCHMARK_CSV)
    ntpc_rent = benchmark[benchmark["city"] == "新北市"][["district", "rent_median"]].rename(
        columns={"rent_median": "official_median_rent"}
    )
    neihu = benchmark[(benchmark["city"] == "臺北市") & (benchmark["district"] == "內湖區")].copy()
    if neihu.empty:
        raise RuntimeError("Neihu baseline is missing from MOI benchmark CSV.")
    neihu_rent = int(neihu.iloc[0]["rent_median"])

    towns = load_boundaries()
    ntpc = towns[towns["COUNTYNAME"] == "新北市"].copy()
    neihu_boundary = towns[(towns["COUNTYNAME"] == "臺北市") & (towns["TOWNNAME"] == "內湖區")].copy()
    if ntpc.empty:
        raise RuntimeError("No New Taipei district boundaries found.")
    if neihu_boundary.empty:
        raise RuntimeError("No Taipei Neihu boundary found.")

    mapped = ntpc.merge(ntpc_rent, left_on="TOWNNAME", right_on="district", how="left")
    no_data = sorted(mapped.loc[mapped["official_median_rent"].isna(), "TOWNNAME"].tolist())
    if len(mapped) != 29:
        raise RuntimeError(f"Expected 29 New Taipei districts from boundary, got {len(mapped)}")

    fig, ax = plt.subplots(figsize=(10, 9))
    mapped.plot(ax=ax, color="#D9D9D9", edgecolor="#FFFFFF", linewidth=0.7)
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.1)
    mapped.dropna(subset=["official_median_rent"]).plot(
        ax=ax,
        column="official_median_rent",
        cmap="YlOrRd",
        edgecolor="#FFFFFF",
        linewidth=0.7,
        legend=True,
        cax=cax,
        legend_kwds={"label": "Official median rent (NTD/month)"},
    )
    neihu_boundary.plot(ax=ax, color="none", edgecolor="#2F5597", linewidth=2.2, linestyle="--")

    label_geometries = mapped[mapped["TOWNNAME"].isin(LABEL_DISTRICTS)].copy()
    for _, row in label_geometries.iterrows():
        point = row.geometry.representative_point()
        ax.annotate(
            row["TOWNNAME"],
            xy=(point.x, point.y),
            ha="center",
            va="center",
            fontsize=8,
            color="#1F1F1F",
            bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.75},
        )

    neihu_point = neihu_boundary.iloc[0].geometry.representative_point()
    ax.annotate(
        f"內湖 baseline\n{neihu_rent:,} NTD",
        xy=(neihu_point.x, neihu_point.y),
        xytext=(16, -8),
        textcoords="offset points",
        ha="left",
        va="top",
        fontsize=8.5,
        color="#2F5597",
        bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "#2F5597", "alpha": 0.85},
        arrowprops={"arrowstyle": "-", "color": "#2F5597", "lw": 1.0},
    )

    minx, miny, maxx, maxy = pd.concat([mapped, neihu_boundary]).total_bounds
    ax.set_xlim(minx - 0.03, maxx + 0.03)
    ax.set_ylim(miny - 0.03, maxy + 0.03)
    ax.set_axis_off()
    ax.set_title("New Taipei Independent Suite Official Median Rent (MOI 2026-03)", fontsize=14, pad=12)
    ax.text(
        0.01,
        0.01,
        f"Boundary: {BOUNDARY_SOURCE_LABEL}\nNo Data districts shown in gray. Neihu is reference only, not ranked with New Taipei.",
        transform=ax.transAxes,
        fontsize=7.5,
        color="#555555",
        va="bottom",
    )
    ax.legend(
        handles=[
            Patch(facecolor="#D9D9D9", edgecolor="#FFFFFF", label="No Data"),
            Line2D([0], [0], color="#2F5597", lw=2.2, linestyle="--", label="Taipei Neihu baseline"),
        ],
        loc="upper left",
        frameon=True,
        fontsize=8,
    )

    plt.tight_layout()
    fig.savefig(OUTPUT_PNG, bbox_inches="tight")
    plt.close(fig)

    report = OUTPUT_HOUSING / "ntpc_rent_choropleth_metadata.md"
    report.write_text(
        "\n".join(
            [
                "# NTPC Rent Choropleth Metadata",
                "",
                f"Boundary source: {BOUNDARY_SOURCE_LABEL}",
                f"Boundary URL: {BOUNDARY_SOURCE_URL}",
                f"Cached boundary zip: `{BOUNDARY_ZIP.as_posix()}`",
                "",
                f"No Data districts: {', '.join(no_data) if no_data else 'None'}",
                "",
                "Map value: MOI official independent-suite median monthly rent (`rent_median`) from `data/processed/housing/moi_independent_suite_rent_benchmark.csv`.",
                "Taipei Neihu is displayed as a baseline reference and excluded from New Taipei ranking/color scale.",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Wrote {OUTPUT_PNG}")
    print(f"Wrote {report}")
    print("No Data districts:", ", ".join(no_data) if no_data else "None")


if __name__ == "__main__":
    main()
