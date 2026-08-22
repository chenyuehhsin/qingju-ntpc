#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_CACHE_DIR = Path(tempfile.gettempdir()) / "qingju_ntpc_cache"
os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_CACHE_DIR / "xdg"))
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_CACHE_DIR / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_LOCATIONS_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "candidate_locations_expanded.csv"
RENT_COMMUTE_CSV = PROJECT_ROOT / "data" / "processed" / "integration" / "rent_commute_candidates_expanded.csv"

RAW_CACHE_DIR = PROJECT_ROOT / "data" / "raw" / "livability" / "osm_overpass_800m_2026-08-22"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "livability"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "livability"
OUTPUT_CSV = PROCESSED_DIR / "livability_by_candidate.csv"
OUTPUT_FIG = OUTPUT_DIR / "01_livability_poi_comparison.png"
OUTPUT_MD = OUTPUT_DIR / "livability_exploration.md"
QUERY_DEFINITION_JSON = OUTPUT_DIR / "osm_overpass_query_definition.json"

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
OVERPASS_SOURCE_URL = "; ".join(OVERPASS_ENDPOINTS)
USER_AGENT = "qingju-ntpc-hackathon/0.1 (livability POI MVP)"
DOWNLOAD_DATE = "2026-08-22"
RADIUS_METERS = 800
EXPECTED_CANDIDATE_COUNT = 16

POI_CATEGORIES = {
    "food": {
        "label": "餐飲",
        "tags": {"amenity": {"restaurant", "cafe"}},
    },
    "shopping": {
        "label": "日常採買",
        "tags": {"shop": {"convenience", "supermarket"}},
    },
    "recreation": {
        "label": "休閒",
        "tags": {"leisure": {"park", "sports_centre", "pitch", "fitness_centre", "stadium"}},
    },
    "culture": {
        "label": "文娛",
        "tags": {
            "amenity": {"cinema", "library", "arts_centre", "theatre"},
            "tourism": {"museum", "gallery"},
        },
    },
    "medical": {
        "label": "基本醫療",
        "tags": {"amenity": {"clinic", "hospital", "pharmacy"}},
    },
}

CATEGORY_COUNT_COLUMNS = [
    "food_count",
    "shopping_count",
    "recreation_count",
    "culture_count",
    "medical_count",
]
CATEGORY_NORM_COLUMNS = [
    "food_norm",
    "shopping_norm",
    "recreation_norm",
    "culture_norm",
    "medical_norm",
]


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


def safe_slug(value: str) -> str:
    mapping = {
        "汐止車站": "xizhi_station",
        "頂溪站": "dingxi_station",
        "景安站": "jingan_station",
        "大坪林站": "dapinglin_station",
        "板橋站": "banqiao_station",
        "三重站": "sanchong_station",
        "新莊站": "xinzhuang_station",
        "蘆洲站": "luzhou_station",
        "土城站": "tucheng_station",
        "泰山站": "taishan_station",
        "林口站": "linkou_station",
        "淡水站": "tamsui_station",
        "三峽北大特區": "sanxia_ntpu_main_gate",
        "樹林車站": "shulin_station",
        "五股區公所": "wugu_district_office",
        "鶯歌車站": "yingge_station",
    }
    if value in mapping:
        return mapping[value]
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "candidate"


def category_filters() -> list[str]:
    filters: list[str] = []
    for category in POI_CATEGORIES.values():
        for key, values in category["tags"].items():
            value_pattern = "|".join(sorted(values))
            filters.append(f'["{key}"~"^({value_pattern})$"]')
    return filters


def build_overpass_query(lat: float, lon: float) -> str:
    filters = category_filters()
    query_lines = ["[out:json][timeout:90];", "("]
    for tag_filter in filters:
        query_lines.append(f"  nwr(around:{RADIUS_METERS},{lat:.6f},{lon:.6f}){tag_filter};")
    query_lines += [");", "out center tags;"]
    return "\n".join(query_lines)


def request_overpass(query: str) -> tuple[dict[str, Any], str]:
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    last_error: Exception | None = None
    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(3):
            request = urllib.request.Request(
                endpoint,
                data=data,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": USER_AGENT,
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    content_type = response.headers.get("Content-Type", "")
                    body = response.read().decode("utf-8")
                if "json" not in content_type:
                    raise RuntimeError(f"Overpass returned non-JSON content type: {content_type}")
                return json.loads(body), endpoint
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {429, 502, 503, 504}:
                    raise
                exc.read()
                time.sleep(20 * (attempt + 1))
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"All Overpass endpoints failed. Last error: {last_error}")


def load_or_fetch_candidate_response(row: pd.Series) -> dict[str, Any]:
    RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = RAW_CACHE_DIR / f"{safe_slug(str(row['candidate_name']))}.json"
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    query = build_overpass_query(float(row["lat"]), float(row["lon"]))
    response, endpoint = request_overpass(query)
    cache_payload = {
        "metadata": {
            "candidate_name": row["candidate_name"],
            "district": row["district"],
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "radius_meters": RADIUS_METERS,
            "source": "OpenStreetMap via Overpass API",
            "source_url": endpoint,
            "download_date": DOWNLOAD_DATE,
            "retrieved_at": datetime.now().isoformat(timespec="seconds"),
            "query": query,
        },
        "overpass_response": response,
    }
    cache_path.write_text(json.dumps(cache_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    time.sleep(2.0)
    return cache_payload


def element_matches_category(tags: dict[str, Any], category_name: str) -> bool:
    definition = POI_CATEGORIES[category_name]
    for key, values in definition["tags"].items():
        if str(tags.get(key, "")) in values:
            return True
    return False


def classify_response(cache_payload: dict[str, Any]) -> dict[str, int]:
    response = cache_payload.get("overpass_response", cache_payload)
    elements = response.get("elements", [])
    category_ids = {category_name: set() for category_name in POI_CATEGORIES}
    all_ids: set[str] = set()

    for element in elements:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags", {})
        if not isinstance(tags, dict):
            continue
        element_id = f"{element.get('type')}:{element.get('id')}"
        matched_any = False
        for category_name in POI_CATEGORIES:
            if element_matches_category(tags, category_name):
                category_ids[category_name].add(element_id)
                matched_any = True
        if matched_any:
            all_ids.add(element_id)

    counts = {f"{category_name}_count": len(ids) for category_name, ids in category_ids.items()}
    counts["total_poi_count"] = len(all_ids)
    return counts


def normalize_min_max(series: pd.Series) -> pd.Series:
    min_value = series.min()
    max_value = series.max()
    if max_value == min_value:
        return pd.Series(0.0, index=series.index)
    return (series - min_value) / (max_value - min_value)


def load_candidates() -> pd.DataFrame:
    locations = pd.read_csv(CANDIDATE_LOCATIONS_CSV)
    rent_commute = pd.read_csv(RENT_COMMUTE_CSV)
    if len(locations) != EXPECTED_CANDIDATE_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_CANDIDATE_COUNT} candidate locations, got {len(locations)}.")
    candidates = locations.merge(
        rent_commute[["candidate_name", "district", "official_median_rent", "commute_minutes"]],
        on=["candidate_name", "district"],
        how="left",
        validate="one_to_one",
    )
    missing = candidates[candidates["official_median_rent"].isna()]["candidate_name"].tolist()
    if missing:
        raise RuntimeError(f"Missing rent/commute rows for candidates: {missing}")
    return candidates.sort_values("candidate_name").reset_index(drop=True)


def build_livability_table(candidates: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, candidate in candidates.iterrows():
        cache_payload = load_or_fetch_candidate_response(candidate)
        counts = classify_response(cache_payload)
        rows.append(
            {
                "candidate_name": candidate["candidate_name"],
                "district": candidate["district"],
                "lat": candidate["lat"],
                "lon": candidate["lon"],
                "radius_meters": RADIUS_METERS,
                **counts,
            }
        )

    result = pd.DataFrame(rows)
    for count_col, norm_col in zip(CATEGORY_COUNT_COLUMNS, CATEGORY_NORM_COLUMNS):
        result[norm_col] = normalize_min_max(result[count_col])
    result["equal_weight_livability_index"] = result[CATEGORY_NORM_COLUMNS].mean(axis=1)
    result = result.sort_values(["equal_weight_livability_index", "total_poi_count"], ascending=False)
    return result[
        [
            "candidate_name",
            "district",
            "lat",
            "lon",
            "radius_meters",
            "food_count",
            "shopping_count",
            "recreation_count",
            "culture_count",
            "medical_count",
            "total_poi_count",
            "food_norm",
            "shopping_norm",
            "recreation_norm",
            "culture_norm",
            "medical_norm",
            "equal_weight_livability_index",
        ]
    ].copy()


def plot_comparison(df: pd.DataFrame) -> None:
    configure_matplotlib()
    plot_df = df.sort_values("equal_weight_livability_index", ascending=True).copy()
    colors = {
        "food_count": "#7FBF9A",
        "shopping_count": "#E9A15B",
        "recreation_count": "#6FA8C9",
        "culture_count": "#B9AED2",
        "medical_count": "#D8898A",
    }
    labels = {
        "food_count": "餐飲",
        "shopping_count": "日常採買",
        "recreation_count": "休閒",
        "culture_count": "文娛",
        "medical_count": "基本醫療",
    }

    fig, ax = plt.subplots(figsize=(11, 8.2))
    left = pd.Series(0, index=plot_df.index)
    y_positions = range(len(plot_df))
    for col in CATEGORY_COUNT_COLUMNS:
        ax.barh(
            y_positions,
            plot_df[col],
            left=left,
            color=colors[col],
            label=labels[col],
            height=0.68,
        )
        left += plot_df[col]

    ax.set_yticks(list(y_positions), plot_df["candidate_name"])
    ax.set_xlabel("800m 生活圈內 POI 數量")
    ax.set_title("候選生活圈 800m POI 機能比較", fontsize=14, pad=12)
    ax.grid(axis="x", alpha=0.22)
    ax.legend(ncol=5, loc="lower right", frameon=False, fontsize=9)
    for y, total, index_value in zip(y_positions, plot_df["total_poi_count"], plot_df["equal_weight_livability_index"]):
        ax.text(total + 1.4, y, f"{int(total)} | idx {index_value:.2f}", va="center", fontsize=8.2, color="#4B5558")
    ax.text(
        0.0,
        -0.095,
        "Source: OpenStreetMap via Overpass API. POI 數量是 MVP 生活機能 proxy，不代表完整生活品質。",
        transform=ax.transAxes,
        fontsize=8.4,
        color="#5D686D",
        va="top",
    )
    fig.tight_layout()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_FIG, bbox_inches="tight")
    plt.close(fig)


def build_markdown(df: pd.DataFrame) -> str:
    top_index = df.sort_values("equal_weight_livability_index", ascending=False).head(5)
    top_total = df.sort_values("total_poi_count", ascending=False).head(5)

    lines = [
        "# Livability POI Exploration",
        "",
        "範圍：16 個候選生活圈，每個生活圈以代表交通節點周邊 800m 半徑計算。",
        "",
        "這是 MVP 階段的生活機能 proxy，用來觀察青年租屋時可能感受到的便利與休閒機能。它不應被解讀為完整或客觀的生活品質分數。",
        "",
        "## 資料來源與 Query Definition",
        "",
        "- Source: OpenStreetMap via Overpass API.",
        f"- Endpoint(s): `{OVERPASS_SOURCE_URL}`",
        f"- Download date: {DOWNLOAD_DATE}.",
        f"- Cache directory: `{RAW_CACHE_DIR.relative_to(PROJECT_ROOT)}`",
        f"- Radius: {RADIUS_METERS}m around each candidate node.",
        "",
        "POI 類別定義：",
        "",
        "- 餐飲: `amenity=restaurant|cafe`",
        "- 日常採買: `shop=convenience|supermarket`",
        "- 休閒: `leisure=park|sports_centre|pitch|fitness_centre|stadium`",
        "- 文娛: `amenity=cinema|library|arts_centre|theatre`, `tourism=museum|gallery`",
        "- 基本醫療: `amenity=clinic|hospital|pharmacy`",
        "",
        "## 主要數量",
        "",
        "| candidate | food | shopping | recreation | culture | medical | total | equal_weight_index |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in df.sort_values("equal_weight_livability_index", ascending=False).iterrows():
        lines.append(
            f"| {row['candidate_name']} | {int(row['food_count'])} | {int(row['shopping_count'])} | "
            f"{int(row['recreation_count'])} | {int(row['culture_count'])} | {int(row['medical_count'])} | "
            f"{int(row['total_poi_count'])} | {row['equal_weight_livability_index']:.3f} |"
        )

    lines += [
        "",
        "## 初步觀察",
        "",
        "equal-weight livability proxy 最高的生活圈：",
        "",
    ]
    for _, row in top_index.iterrows():
        lines.append(
            f"- {row['candidate_name']}: index {row['equal_weight_livability_index']:.3f}, "
            f"total POI {int(row['total_poi_count'])}."
        )

    lines += [
        "",
        "raw total POI count 最高的生活圈：",
        "",
    ]
    for _, row in top_total.iterrows():
        lines.append(f"- {row['candidate_name']}: {int(row['total_poi_count'])} POIs.")

    category_leaders = []
    for col in CATEGORY_COUNT_COLUMNS:
        label = POI_CATEGORIES[col.replace("_count", "")]["label"]
        leader = df.sort_values(col, ascending=False).iloc[0]
        category_leaders.append(f"{label}: {leader['candidate_name']} ({int(leader[col])})")
    lines += [
        "",
        "各類別最高：",
        "",
    ]
    for item in category_leaders:
        lines.append(f"- {item}")

    lines += [
        "",
        "## 資料限制",
        "",
        "- OSM 完整度會受地區與 mapper 活躍度影響；較低數量可能反映未完整標圖，不一定代表實際機能不足。",
        "- POI count 將所有點等權計算，未衡量品質、容量、營業時間、價格、步行安全、擁擠程度。",
        "- 800m 是以代表節點為中心的簡單圓形範圍，不是實際步行路網可達範圍。",
        "- 部分設施可能使用本 MVP query 未涵蓋的 OSM tag，因此會漏算。",
        "- equal-weight index 只作探索用途，不應呈現為客觀生活品質分數。",
        "",
        "## Outputs",
        "",
        f"- Processed table: `{OUTPUT_CSV.relative_to(PROJECT_ROOT)}`",
        f"- Comparison chart: `{OUTPUT_FIG.relative_to(PROJECT_ROOT)}`",
        f"- Query definition: `{QUERY_DEFINITION_JSON.relative_to(PROJECT_ROOT)}`",
    ]
    return "\n".join(lines) + "\n"


def write_query_definition() -> None:
    sample_query = build_overpass_query(25.0679, 121.66113)
    serializable_categories = {
        category_name: {
            "label": definition["label"],
            "tags": {key: sorted(values) for key, values in definition["tags"].items()},
        }
        for category_name, definition in POI_CATEGORIES.items()
    }
    payload = {
        "source": "OpenStreetMap via Overpass API",
        "source_url": OVERPASS_SOURCE_URL,
        "download_date": DOWNLOAD_DATE,
        "radius_meters": RADIUS_METERS,
        "categories": serializable_categories,
        "sample_query": sample_query,
        "cache_dir": str(RAW_CACHE_DIR.relative_to(PROJECT_ROOT)),
        "notes": "One Overpass query is executed per candidate node and cached as immutable raw JSON if not already present.",
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    QUERY_DEFINITION_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    candidates = load_candidates()
    df = build_livability_table(candidates)
    if len(df) != EXPECTED_CANDIDATE_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_CANDIDATE_COUNT} livability rows, got {len(df)}.")

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    plot_comparison(df)
    OUTPUT_MD.write_text(build_markdown(df), encoding="utf-8")
    write_query_definition()

    print(f"Wrote {OUTPUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {OUTPUT_FIG.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {OUTPUT_MD.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {QUERY_DEFINITION_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Candidates processed: {len(df)} / {EXPECTED_CANDIDATE_COUNT}")
    print("Top equal-weight livability proxy: " + df.iloc[0]["candidate_name"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
