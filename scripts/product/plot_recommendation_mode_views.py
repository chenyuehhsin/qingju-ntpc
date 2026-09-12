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
import matplotlib.font_manager as fm
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREFERENCE_CSV = PROJECT_ROOT / "data" / "processed" / "integration" / "preference_recommendations.csv"
LIVABILITY_CSV = PROJECT_ROOT / "data" / "processed" / "livability" / "livability_by_candidate.csv"
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
BOUNDARY_EXTRACT_DIR = PROJECT_ROOT / "data" / "interim" / "housing" / "boundaries" / "nlsc_town_boundary_twd97"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "product"

MODE_ORDER = ["省租型", "平衡型", "通勤型", "生活品質型"]
MODE_FILES = {
    "省租型": "01_saving_mode_view",
    "平衡型": "02_balanced_mode_view",
    "通勤型": "03_commute_mode_view",
    "生活品質型": "04_life_quality_mode_view",
}
MODE_COLORS = {
    "省租型": "#78B995",
    "平衡型": "#6EA7C7",
    "通勤型": "#E8A05A",
    "生活品質型": "#A98BC8",
}
MODE_SOFT_COLORS = {
    "省租型": "#EAF6EF",
    "平衡型": "#EAF4FA",
    "通勤型": "#FFF1E3",
    "生活品質型": "#F2ECF8",
}
MODE_COPY = {
    "省租型": "優先降低月租，接受較長通勤換取租金節省。",
    "平衡型": "在租金與通勤之間取得較佳折衷。",
    "通勤型": "優先縮短上班時間，降低每日移動壓力。",
    "生活品質型": "重視周邊生活機能，以 POI proxy 輔助判斷。",
}
MODE_WEIGHT_COPY = {
    "省租型": "rent 0.7 / commute 0.3",
    "平衡型": "rent 0.5 / commute 0.5",
    "通勤型": "rent 0.3 / commute 0.7",
    "生活品質型": "livability 0.6 / rent 0.2 / commute 0.2",
}
LIVING_AREA_NAMES = {
    "板橋站": "板橋生活圈",
    "汐止車站": "汐止生活圈",
    "淡水站": "淡水生活圈",
    "樹林車站": "樹林生活圈",
    "大坪林站": "大坪林生活圈",
    "三峽北大特區": "三峽北大生活圈",
    "景安站": "景安生活圈",
    "頂溪站": "頂溪生活圈",
    "三重站": "三重生活圈",
    "泰山站": "泰山生活圈",
    "新莊站": "新莊生活圈",
    "蘆洲站": "蘆洲生活圈",
    "土城站": "土城生活圈",
    "鶯歌車站": "鶯歌生活圈",
    "林口站": "林口生活圈",
    "五股區公所": "五股生活圈",
}
LABEL_OFFSETS = {
    "板橋站": (14, -18),
    "汐止車站": (-22, 8),
    "淡水站": (-8, 20),
    "樹林車站": (-18, -24),
    "大坪林站": (16, -8),
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
    raise FileNotFoundError(
        "Expected existing NLSC/MOI boundary data at "
        f"{BOUNDARY_SHP.relative_to(PROJECT_ROOT)}; this product view does not download new data."
    )


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


def living_area(candidate_name: str) -> str:
    return LIVING_AREA_NAMES.get(candidate_name, candidate_name.replace("車站", "").replace("站", "") + "生活圈")


def reason_for(mode: str, row: pd.Series) -> str:
    name = row["candidate_name"]
    if mode == "生活品質型":
        if name == "板橋站":
            return "生活機能 proxy 最高，且通勤最短。"
        if name == "大坪林站":
            return "餐飲與基本醫療機能密度高。"
        if name == "樹林車站":
            return "生活機能高，租金仍相對低。"
        return "POI 生活機能表現突出。"
    if mode == "通勤型":
        if int(row["rank"]) == 1:
            return "目前候選中通勤時間最短。"
        return "保留可接受租金下的通勤備選。"
    if mode == "平衡型":
        if int(row["rank"]) == 1:
            return "租金與通勤折衷最佳。"
        return "在租金或通勤上提供替代取捨。"
    if int(row["rank"]) == 1:
        return "租金最低，省租效果最明顯。"
    return "在省租優先下仍具備比較價值。"


def load_data() -> tuple[pd.DataFrame, dict[str, float | str]]:
    recommendations = pd.read_csv(PREFERENCE_CSV)
    livability = pd.read_csv(LIVABILITY_CSV)
    locations = pd.read_csv(CANDIDATE_LOCATIONS_CSV)
    commute = pd.read_csv(COMMUTE_EXPANDED_CSV)

    top3 = recommendations[recommendations["rank"] <= 3].copy()
    top3 = top3.merge(
        livability[["candidate_name", "equal_weight_livability_index"]],
        on="candidate_name",
        how="left",
        validate="many_to_one",
        suffixes=("", "_from_livability"),
    )
    top3["livability_index"] = top3["livability_index"].fillna(top3["equal_weight_livability_index"])
    top3 = top3.merge(
        locations[["candidate_name", "lat", "lon", "station_name", "station_operator"]],
        on="candidate_name",
        how="left",
        validate="many_to_one",
    )
    missing_locations = top3[top3["lat"].isna() | top3["lon"].isna()]["candidate_name"].tolist()
    if missing_locations:
        raise RuntimeError(f"Missing candidate coordinates: {missing_locations}")

    for mode in MODE_ORDER:
        rows = top3[top3["preference_mode"] == mode]
        if len(rows) != 3:
            raise RuntimeError(f"Expected 3 rows for {mode}, got {len(rows)}.")

    destination_rows = commute[["destination", "destination_lat", "destination_lon"]].drop_duplicates()
    if len(destination_rows) != 1:
        raise RuntimeError(f"Expected one destination coordinate row, found {len(destination_rows)}.")
    destination = destination_rows.iloc[0].to_dict()
    if destination["destination"] != "港墘站":
        raise RuntimeError(f"Expected destination 港墘站, found {destination['destination']}.")

    return top3, destination


def add_rounded_rect(
    ax: plt.Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    facecolor: str,
    edgecolor: str,
    linewidth: float = 1.0,
    radius: float = 0.02,
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


def draw_scenario_and_tabs(ax: plt.Axes, active_mode: str) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.02, 0.76, "青聚新北 MVP", fontsize=11, color="#6A787D", weight="bold", va="center")
    ax.text(0.02, 0.36, "推薦生活圈", fontsize=25, color="#223139", weight="bold", va="center")

    chips = [("工作地", "港墘站"), ("交通方式", "大眾運輸"), ("租屋型態", "獨立套房")]
    x = 0.30
    for label, value in chips:
        add_rounded_rect(ax, (x, 0.50), 0.13, 0.33, "#FFFFFF", "#D9E0E2", linewidth=0.8, radius=0.025)
        ax.text(x + 0.015, 0.70, label, fontsize=7.8, color="#7A878B", va="center")
        ax.text(x + 0.015, 0.58, value, fontsize=10.2, color="#25343A", weight="bold", va="center")
        x += 0.145

    tab_x = 0.30
    tab_width = 0.105
    for mode in MODE_ORDER:
        active = mode == active_mode
        color = MODE_COLORS[mode]
        add_rounded_rect(
            ax,
            (tab_x, 0.12),
            tab_width,
            0.27,
            color if active else "#FFFFFF",
            color if active else "#D9E0E2",
            linewidth=1.0,
            radius=0.025,
        )
        ax.text(
            tab_x + tab_width / 2,
            0.255,
            mode,
            fontsize=9.1,
            color="#FFFFFF" if active else "#4E5C61",
            weight="bold" if active else "normal",
            ha="center",
            va="center",
        )
        tab_x += tab_width + 0.012


def draw_cards(ax: plt.Axes, mode: str, rows: pd.DataFrame) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    color = MODE_COLORS[mode]
    soft = MODE_SOFT_COLORS[mode]
    ax.text(0.02, 0.975, mode, fontsize=18, color="#243238", weight="bold", va="top")
    ax.text(0.02, 0.925, MODE_COPY[mode], fontsize=8.7, color="#65747A", va="top")
    ax.text(0.02, 0.885, MODE_WEIGHT_COPY[mode], fontsize=8.0, color=color, va="top", weight="bold")

    y_positions = [0.635, 0.385, 0.135]
    for _, row in rows.sort_values("rank").iterrows():
        rank = int(row["rank"])
        y = y_positions[rank - 1]
        is_top = rank == 1
        add_rounded_rect(
            ax,
            (0.02, y),
            0.94,
            0.205,
            "#FFFFFF" if not is_top else soft,
            color if is_top else "#DDE5E7",
            linewidth=1.25 if is_top else 0.85,
            radius=0.026,
        )
        ax.scatter(
            [0.065],
            [y + 0.132],
            s=170 if is_top else 110,
            color=color,
            alpha=1.0 if is_top else 0.72,
            edgecolor="#FFFFFF",
            linewidth=1.2,
            transform=ax.transAxes,
            zorder=4,
        )
        ax.text(0.065, y + 0.132, str(rank), ha="center", va="center", fontsize=9.5, color="#FFFFFF", weight="bold")
        ax.text(0.105, y + 0.154, living_area(row["candidate_name"]), fontsize=13.2, color="#243238", weight="bold", va="center")
        ax.text(0.105, y + 0.116, row["candidate_name"], fontsize=8.5, color="#6C787D", va="center")
        ax.text(0.105, y + 0.074, reason_for(mode, row), fontsize=8.1, color="#58676D", va="center")

        ax.text(0.72, y + 0.158, f"{money(row['rent'])} NTD", fontsize=10.3, color="#243238", weight="bold", ha="right")
        ax.text(0.72, y + 0.117, minutes(row["commute_minutes"]), fontsize=10.3, color="#243238", weight="bold", ha="right")
        ax.text(0.72, y + 0.077, f"省 {money(row['rent_saving_vs_neihu'])}", fontsize=8.2, color="#6C787D", ha="right")
        livability_weight = "bold" if mode == "生活品質型" else "normal"
        livability_color = color if mode == "生活品質型" else "#6C787D"
        ax.text(
            0.93,
            y + 0.117,
            f"生活機能\n{float(row['livability_index']):.3f}",
            fontsize=8.1,
            color=livability_color,
            weight=livability_weight,
            ha="right",
            va="center",
        )


def add_map_label(ax: plt.Axes, row: pd.Series, mode: str) -> None:
    rank = int(row["rank"])
    color = MODE_COLORS[mode]
    label = f"#{rank} {living_area(row['candidate_name'])}"
    offset = LABEL_OFFSETS.get(row["candidate_name"], (14, 8))
    annotation = ax.annotate(
        label,
        xy=(float(row["lon"]), float(row["lat"])),
        xytext=offset,
        textcoords="offset points",
        ha="right" if offset[0] < 0 else "left",
        va="center",
        fontsize=9.0 if rank == 1 else 8.2,
        color="#243238",
        bbox={
            "boxstyle": "round,pad=0.22",
            "fc": "#FFFFFF",
            "ec": color if rank == 1 else "#CBD4D7",
            "alpha": 0.94,
            "lw": 1.0 if rank == 1 else 0.75,
        },
        arrowprops={"arrowstyle": "-", "color": color, "lw": 0.7, "alpha": 0.55, "shrinkA": 0, "shrinkB": 5},
        zorder=9,
    )
    annotation.set_path_effects([pe.withStroke(linewidth=2.3, foreground="#FFFFFF")])


def draw_map(
    ax: plt.Axes,
    mode: str,
    rows: pd.DataFrame,
    destination: dict[str, float | str],
    towns: gpd.GeoDataFrame,
    cities: gpd.GeoDataFrame,
) -> None:
    ax.set_facecolor("#F7F8F7")
    dest_lon = float(destination["destination_lon"])
    dest_lat = float(destination["destination_lat"])

    towns.plot(ax=ax, color="#F4F6F5", edgecolor="#DDE3E5", linewidth=0.34, zorder=0)
    target_towns = towns[towns["TOWNNAME"].isin(set(rows["district"].tolist()) | {"內湖區"})]
    target_towns.plot(ax=ax, color="#EDF3F2", edgecolor="#CDD7DA", linewidth=0.55, zorder=1)

    for city_name, edgecolor, linewidth in [("新北市", "#7B8B74", 1.8), ("臺北市", "#6B7F8A", 1.7)]:
        cities[cities["COUNTYNAME"] == city_name].boundary.plot(ax=ax, color=edgecolor, linewidth=linewidth, zorder=3)

    color = MODE_COLORS[mode]
    for _, row in rows.iterrows():
        ax.plot(
            [float(row["lon"]), dest_lon],
            [float(row["lat"]), dest_lat],
            color="#9EA7AA",
            linewidth=0.42,
            alpha=0.14,
            zorder=2,
        )

    for _, row in rows.iterrows():
        rank = int(row["rank"])
        ax.scatter(
            [float(row["lon"])],
            [float(row["lat"])],
            s=850 if rank == 1 else 520,
            color=color,
            alpha=0.20 if rank == 1 else 0.12,
            edgecolor="none",
            zorder=4,
        )
        ax.scatter(
            [float(row["lon"])],
            [float(row["lat"])],
            s=160 if rank == 1 else 96,
            color=color,
            alpha=1.0 if rank == 1 else 0.64,
            edgecolor="#FFFFFF",
            linewidth=1.4,
            zorder=6,
        )
        ax.text(
            float(row["lon"]),
            float(row["lat"]),
            str(rank),
            ha="center",
            va="center",
            fontsize=8.4,
            color="#FFFFFF",
            weight="bold",
            zorder=7,
        )

    ax.scatter(
        [dest_lon],
        [dest_lat],
        s=195,
        marker="*",
        color="#C45B65",
        edgecolor="#742C34",
        linewidth=0.9,
        zorder=7,
    )
    workplace = ax.annotate(
        "workplace anchor\n港墘站",
        xy=(dest_lon, dest_lat),
        xytext=(-18, 20),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=9.0,
        color="#742C34",
        bbox={"boxstyle": "round,pad=0.24", "fc": "#FFFFFF", "ec": "#C45B65", "alpha": 0.95, "lw": 0.9},
        arrowprops={"arrowstyle": "-", "color": "#C45B65", "lw": 0.78, "shrinkA": 0, "shrinkB": 5},
        zorder=9,
    )
    workplace.set_path_effects([pe.withStroke(linewidth=2.2, foreground="white")])

    for _, row in rows.iterrows():
        add_map_label(ax, row, mode)

    for city_name, x, y in [("新北市", 121.405, 25.095), ("臺北市", 121.555, 25.045)]:
        txt = ax.text(x, y, city_name, fontsize=10.5, color="#52646B", weight="bold", ha="center", va="center", zorder=8)
        txt.set_path_effects([pe.withStroke(linewidth=3.0, foreground="#FFFFFF")])

    min_lon = min(rows["lon"].min(), dest_lon)
    max_lon = max(rows["lon"].max(), dest_lon)
    min_lat = min(rows["lat"].min(), dest_lat)
    max_lat = max(rows["lat"].max(), dest_lat)
    ax.set_xlim(min_lon - 0.085, max_lon + 0.085)
    ax.set_ylim(min_lat - 0.055, max_lat + 0.040)
    ax.set_axis_off()
    ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markeredgecolor="#FFFFFF", markersize=8, label=f"{mode} Top 3"),
            Line2D([0], [0], marker="*", color="none", markerfacecolor="#C45B65", markeredgecolor="#742C34", markersize=11, label="港墘站"),
            Line2D([0], [0], color="#7B8B74", lw=1.8, label="新北市外框"),
            Line2D([0], [0], color="#6B7F8A", lw=1.7, label="臺北市外框"),
        ],
        loc="upper right",
        frameon=True,
        facecolor="#FFFFFF",
        edgecolor="#D6DDE0",
        fontsize=8.1,
    )


def draw_footer(ax: plt.Axes, mode: str) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    color = MODE_COLORS[mode]
    add_rounded_rect(ax, (0.02, 0.18), 0.30, 0.60, "#FFFFFF", "#DDE5E6", linewidth=0.8, radius=0.02)
    add_rounded_rect(ax, (0.35, 0.18), 0.30, 0.60, "#FFFFFF", "#DDE5E6", linewidth=0.8, radius=0.02)
    add_rounded_rect(ax, (0.68, 0.18), 0.30, 0.60, "#FFFFFF", "#DDE5E6", linewidth=0.8, radius=0.02)
    footer_items = [
        ("目前模式", MODE_COPY[mode]),
        ("排序方式", "使用既有 preference_recommendations.csv，不重新計算。"),
        ("資料提醒", "生活機能為 POI proxy；OD 線僅表示相對位置。"),
    ]
    for i, (title, body) in enumerate(footer_items):
        x = [0.02, 0.35, 0.68][i]
        ax.scatter([x + 0.035], [0.50], s=105, color=color, edgecolor="#FFFFFF", linewidth=1.0, transform=ax.transAxes)
        ax.text(x + 0.065, 0.58, title, fontsize=10.2, color="#25333A", weight="bold", va="center", transform=ax.transAxes)
        ax.text(x + 0.065, 0.40, body, fontsize=8.5, color="#5E6C72", va="center", transform=ax.transAxes)


def plot_mode_view(
    mode: str,
    recommendations: pd.DataFrame,
    destination: dict[str, float | str],
    towns: gpd.GeoDataFrame,
    cities: gpd.GeoDataFrame,
) -> tuple[Path, Path]:
    rows = recommendations[recommendations["preference_mode"] == mode].sort_values("rank").head(3).copy()
    fig = plt.figure(figsize=(14.5, 8.8), facecolor="#F7F6F1")
    header_ax = fig.add_axes([0.045, 0.865, 0.91, 0.105])
    cards_ax = fig.add_axes([0.055, 0.215, 0.30, 0.615])
    map_ax = fig.add_axes([0.385, 0.215, 0.57, 0.62])
    footer_ax = fig.add_axes([0.055, 0.055, 0.90, 0.12])

    draw_scenario_and_tabs(header_ax, mode)
    add_rounded_rect(cards_ax, (0, 0), 0.98, 1.0, "#FFFFFF", "#E0E5E6", linewidth=0.9, radius=0.03, zorder=0)
    draw_cards(cards_ax, mode, rows)
    draw_map(map_ax, mode, rows, destination, towns, cities)
    draw_footer(footer_ax, mode)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    png = OUTPUT_DIR / f"{MODE_FILES[mode]}.png"
    svg = OUTPUT_DIR / f"{MODE_FILES[mode]}.svg"
    fig.savefig(png, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(svg, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return png, svg


def main() -> int:
    configure_matplotlib()
    towns, cities = load_boundaries()
    recommendations, destination = load_data()

    outputs: list[Path] = []
    for mode in MODE_ORDER:
        png, svg = plot_mode_view(mode, recommendations, destination, towns, cities)
        outputs.extend([png, svg])
        top_names = recommendations[recommendations["preference_mode"] == mode].sort_values("rank").head(3)["candidate_name"].tolist()
        print(f"{mode}: " + ", ".join(top_names))

    for path in outputs:
        print(f"Wrote {path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
