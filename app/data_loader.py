from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import streamlit as st
from shapely.geometry import Point


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREFERENCE_CSV = PROJECT_ROOT / "data" / "processed" / "integration" / "preference_recommendations_by_workplace.csv"
RENT_COMMUTE_CSV = PROJECT_ROOT / "data" / "processed" / "integration" / "rent_commute_candidates_by_workplace.csv"
LIVABILITY_CSV = PROJECT_ROOT / "data" / "processed" / "livability" / "livability_by_candidate.csv"
LIVABILITY_RAW_CACHE_DIR = PROJECT_ROOT / "data" / "raw" / "livability" / "osm_overpass_800m_2026-08-22"
TDX_STATION_DATA_DIR = PROJECT_ROOT / "data" / "interim" / "transport" / "tdx_station_data"
CANDIDATE_LOCATIONS_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "candidate_locations_expanded.csv"
COMMUTE_BY_WORKPLACE_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "commute_by_workplace.csv"
METRO_STATIONS_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "metro_stations.csv"
METRO_LINES_GEOJSON = PROJECT_ROOT / "data" / "processed" / "transport" / "metro_lines.geojson"
YOUBIKE_STATIONS_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "youbike_stations.csv"
HOUSING_BENCHMARK_CSV = PROJECT_ROOT / "data" / "processed" / "housing" / "moi_independent_suite_rent_benchmark.csv"
POLICY_LENS_CSV = PROJECT_ROOT / "data" / "processed" / "policy" / "policy_lens_v0.csv"
CAREER_POLICY_LENS_PHASE7_CSV = PROJECT_ROOT / "outputs" / "career" / "career_policy_lens_phase7.csv"
CAREER_POLICY_LENS_PHASE7_MD = PROJECT_ROOT / "outputs" / "career" / "career_policy_lens_phase7.md"
CAREER_LEARNING_LADDER_PHASE8_CSV = PROJECT_ROOT / "outputs" / "career" / "career_learning_ladder_phase8.csv"
CAREER_V35_CANDIDATES_CSV = PROJECT_ROOT / "outputs" / "career" / "nursing_to_technology_candidates_v35.csv"
CAREER_V4_TRAINING_CSV = PROJECT_ROOT / "outputs" / "career" / "nursing_to_technology_training_v4.csv"
CAREER_BEAUTY_PHASE5_CSV = PROJECT_ROOT / "outputs" / "career" / "nursing_to_beauty_candidates_phase5.csv"
CAREER_TRAINING_MAPPING_CSV = PROJECT_ROOT / "data" / "processed" / "career" / "career_training_skill_mapping.csv"
CAREER_TAIWANJOBS_RAW_CSV = PROJECT_ROOT / "data" / "raw" / "career" / "jobs" / "taiwanjobs_open_jobs_2026-09-01.csv"
BOUNDARY_SHP = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "housing"
    / "boundaries"
    / "nlsc_town_boundary_twd97"
    / "TOWN_MOI_1120317.shp"
)

MODE_ORDER = ["省租型", "平衡型", "通勤型", "生活品質型"]
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
    "省租型": "適合願意增加通勤時間，以換取較低租金的使用者。",
    "平衡型": "在租金與通勤時間之間取得較佳折衷。",
    "通勤型": "適合最重視每日上下班時間的使用者。",
    "生活品質型": "優先考慮站點周邊餐飲、採買、休閒、文娛與醫療機能。",
}
POI_COUNT_COLUMNS = ["food_count", "shopping_count", "medical_count", "recreation_count", "culture_count"]
REPRESENTATIVE_POI_LIMIT_PER_CATEGORY = 2
REPRESENTATIVE_TRANSPORT_STATION_LIMIT = 5
DETAIL_TRANSPORT_RADIUS_METERS = 800
DETAIL_EXTENDED_LIVING_AREA_RADIUS_METERS = 2000
TAIWAN_PROJECTED_CRS = "EPSG:3826"
REPRESENTATIVE_POI_CATEGORIES = {
    "shopping": {
        "label": "採買",
        "tags": {"shop": {"supermarket"}, "amenity": {"marketplace"}},
    },
    "medical": {
        "label": "醫療",
        "tags": {"amenity": {"clinic", "hospital", "pharmacy"}},
    },
    "recreation": {
        "label": "公園/運動",
        "tags": {"leisure": {"park", "sports_centre", "pitch", "fitness_centre", "stadium"}},
    },
}
OSM_TYPE_LABELS = {
    "convenience": "便利商店",
    "supermarket": "超市",
    "marketplace": "市場",
    "clinic": "診所",
    "hospital": "醫院",
    "pharmacy": "藥局",
    "park": "公園",
    "sports_centre": "運動中心",
    "pitch": "球場",
    "fitness_centre": "健身",
    "stadium": "場館",
}
TDX_RAIL_STATION_FILES = {
    "trtc_stations.json": {"operator": "TRTC", "label": "捷運"},
    "tymc_stations.json": {"operator": "TYMC", "label": "機場捷運"},
    "tra_stations.json": {"operator": "TRA", "label": "台鐵"},
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


def living_area(candidate_name: str) -> str:
    return LIVING_AREA_NAMES.get(candidate_name, candidate_name.replace("車站", "").replace("站", "") + "生活圈")


def money(value: float | int) -> str:
    return f"{float(value):,.0f}"


def minutes(value: float | int) -> str:
    return f"{float(value):.1f} min"


def reason_for(mode: str, row: pd.Series) -> str:
    if mode == "生活品質型":
        return "周邊生活機能 proxy 較突出，適合重視日常便利的使用者。"
    if mode == "通勤型":
        return "以縮短每日上下班時間為主要排序方向。"
    if mode == "平衡型":
        return "在租金與通勤時間之間取得較佳折衷。"
    return "以降低月租為主要排序方向，接受較長通勤換取省租。"


def life_summary(row: pd.Series) -> str:
    labels = {
        "food_count": "餐飲",
        "shopping_count": "採買",
        "medical_count": "醫療",
        "recreation_count": "休閒運動",
        "culture_count": "文娛",
    }
    counts = {
        column: int(row[column])
        for column in POI_COUNT_COLUMNS
        if column in row.index and not pd.isna(row[column])
    }
    if not counts:
        return "目前只有租金與通勤資訊，生活機能細項不足以描述。"
    strongest = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:2]
    weakest = [labels[column] for column, count in counts.items() if count == 0]
    if weakest:
        return f"{labels[strongest[0][0]]}機能相對明顯，但{weakest[0]}資料在 OSM 樣本中偏少。"
    if strongest[0][1] >= 100:
        return f"{labels[strongest[0][0]]}密度高，{labels[strongest[1][0]]}也有支撐，適合重視日常便利的人。"
    return f"{labels[strongest[0][0]]}與{labels[strongest[1][0]]}是此生活圈較突出的日常機能。"


@st.cache_data(show_spinner=False)
def load_workplaces() -> pd.DataFrame:
    commute = pd.read_csv(COMMUTE_BY_WORKPLACE_CSV)
    workplaces = (
        commute[
            [
                "workplace_id",
                "workplace_name",
                "workplace_district",
                "workplace_lat",
                "workplace_lon",
                "workplace_station_operator",
                "workplace_station_uid",
            ]
        ]
        .drop_duplicates()
        .copy()
    )
    if len(workplaces) != len(WORKPLACE_ORDER):
        raise RuntimeError(f"Expected {len(WORKPLACE_ORDER)} workplaces, found {len(workplaces)}.")
    workplaces["_order"] = workplaces["workplace_id"].map({value: index for index, value in enumerate(WORKPLACE_ORDER)})
    if workplaces["_order"].isna().any():
        missing = workplaces[workplaces["_order"].isna()]["workplace_id"].tolist()
        raise RuntimeError(f"Unexpected workplace ids: {missing}")
    return workplaces.sort_values("_order").drop(columns=["_order"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_dashboard_data(workplace_id: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, float | str]]:
    preferences = pd.read_csv(PREFERENCE_CSV)
    rent_commute = pd.read_csv(RENT_COMMUTE_CSV)
    livability = pd.read_csv(LIVABILITY_CSV)
    locations = pd.read_csv(CANDIDATE_LOCATIONS_CSV)

    if workplace_id not in set(rent_commute["workplace_id"]):
        raise RuntimeError(f"Unknown workplace_id: {workplace_id}")
    rent_commute = rent_commute[rent_commute["workplace_id"] == workplace_id].copy()
    preferences = preferences[preferences["workplace_id"] == workplace_id].copy()
    if len(rent_commute) != 16:
        raise RuntimeError(f"Expected 16 evaluated candidates for {workplace_id}, found {len(rent_commute)}.")

    candidates = rent_commute.merge(
        locations[["candidate_name", "lat", "lon"]],
        on="candidate_name",
        how="left",
        suffixes=("", "_location"),
        validate="one_to_one",
    )
    candidates["lat"] = candidates["lat"].fillna(candidates["lat_location"])
    candidates["lon"] = candidates["lon"].fillna(candidates["lon_location"])
    candidates = candidates.drop(columns=[column for column in ["lat_location", "lon_location"] if column in candidates])
    livability_columns = ["candidate_name", "equal_weight_livability_index", "total_poi_count", *POI_COUNT_COLUMNS]
    candidates = candidates.merge(
        livability[[column for column in livability_columns if column in livability.columns]],
        on="candidate_name",
        how="left",
        validate="one_to_one",
    )
    candidates["rent"] = candidates["official_median_rent"]
    candidates["livability_index"] = candidates["equal_weight_livability_index"]
    candidates["living_area"] = candidates["candidate_name"].map(living_area)

    recommendations = preferences.copy()
    recommendations = recommendations.merge(
        candidates[
            [
                "candidate_name",
                "lat",
                "lon",
                "living_area",
                "livability_index",
                "total_poi_count",
                *[column for column in POI_COUNT_COLUMNS if column in candidates.columns],
                "route_summary",
            ]
        ],
        on="candidate_name",
        how="left",
        validate="many_to_one",
        suffixes=("", "_from_candidates"),
    )
    recommendations["livability_index"] = recommendations["livability_index"].fillna(
        recommendations["livability_index_from_candidates"]
    )
    for column in ["total_poi_count", *POI_COUNT_COLUMNS]:
        from_candidates = f"{column}_from_candidates"
        if from_candidates not in recommendations.columns:
            continue
        if column in recommendations.columns:
            recommendations[column] = recommendations[column].fillna(recommendations[from_candidates])
        else:
            recommendations[column] = recommendations[from_candidates]
    recommendations = recommendations.drop(
        columns=[column for column in recommendations.columns if column.endswith("_from_candidates")]
    )

    top3 = recommendations[recommendations["rank"] <= 3].copy()

    _validate_dashboard_data(candidates, recommendations, top3)

    destination_rows = rent_commute[
        [
            "workplace_id",
            "workplace_name",
            "workplace_district",
            "workplace_lat",
            "workplace_lon",
        ]
    ].drop_duplicates()
    if len(destination_rows) != 1:
        raise RuntimeError(f"Expected one workplace row, found {len(destination_rows)}.")
    destination_row = destination_rows.iloc[0].to_dict()
    destination = {
        "workplace_id": destination_row["workplace_id"],
        "workplace_name": destination_row["workplace_name"],
        "workplace_district": destination_row["workplace_district"],
        "destination": destination_row["workplace_name"],
        "destination_lat": destination_row["workplace_lat"],
        "destination_lon": destination_row["workplace_lon"],
    }

    return candidates, recommendations, top3, destination


def _validate_dashboard_data(candidates: pd.DataFrame, recommendations: pd.DataFrame, top3: pd.DataFrame) -> None:
    if len(candidates) != 16:
        raise RuntimeError(f"Expected 16 evaluated candidates, found {len(candidates)}.")
    required_candidate_columns = [
        "candidate_name",
        "district",
        "rent",
        "commute_minutes",
        "transfer_count",
        "rent_saving_vs_neihu",
        "lat",
        "lon",
        "livability_index",
    ]
    missing_values = candidates[candidates[required_candidate_columns].isna().any(axis=1)]["candidate_name"].tolist()
    if missing_values:
        raise RuntimeError(f"Candidates have missing dashboard fields: {missing_values}.")

    for mode in MODE_ORDER:
        rows = top3[top3["preference_mode"] == mode]
        if len(rows) != 3:
            raise RuntimeError(f"Expected three Top 3 recommendations for {mode}, found {len(rows)}.")
        if sorted(rows["rank"].tolist()) != [1, 2, 3]:
            raise RuntimeError(f"{mode} ranks are not exactly 1, 2, 3.")

    life_quality_rows = recommendations[recommendations["preference_mode"] == "生活品質型"]
    if len(life_quality_rows) != 16:
        raise RuntimeError(f"Expected 16 生活品質型 rows for the full candidate table, found {len(life_quality_rows)}.")


@st.cache_data(show_spinner=False)
def load_boundaries() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    if not BOUNDARY_SHP.exists():
        raise FileNotFoundError(
            "Expected existing NLSC/MOI boundary data at "
            f"{BOUNDARY_SHP.relative_to(PROJECT_ROOT)}; the dashboard does not download new data."
        )
    towns = gpd.read_file(BOUNDARY_SHP, encoding="utf-8")
    if towns.crs is None:
        towns = towns.set_crs("EPSG:3824")
    towns = towns.to_crs("EPSG:4326")
    required = {"COUNTYNAME", "TOWNNAME", "geometry"}
    missing = required - set(towns.columns)
    if missing:
        raise RuntimeError(f"Boundary file is missing expected columns: {sorted(missing)}")
    towns = towns[towns["COUNTYNAME"].isin(["新北市", "臺北市"])].copy()
    if HOUSING_BENCHMARK_CSV.exists():
        rent = pd.read_csv(HOUSING_BENCHMARK_CSV)
        rent = rent[rent["city"].isin(["新北市", "臺北市"])][["city", "district", "rent_median"]].rename(
            columns={"rent_median": "official_median_rent"}
        )
        towns = towns.merge(
            rent,
            left_on=["COUNTYNAME", "TOWNNAME"],
            right_on=["city", "district"],
            how="left",
        )
        towns = towns.drop(columns=[column for column in ["city", "district"] if column in towns.columns])
    cities = towns.dissolve(by="COUNTYNAME", as_index=False)
    return towns, cities


@st.cache_data(show_spinner=False)
def load_representative_pois(candidate_name: str) -> pd.DataFrame:
    cache_path = LIVABILITY_RAW_CACHE_DIR / f"{_safe_poi_slug(candidate_name)}.json"
    columns = ["category", "category_label", "name", "lat", "lon", "osm_type", "osm_id", "poi_type", "distance_meters"]
    if not cache_path.exists():
        return pd.DataFrame(columns=columns)

    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    metadata = payload.get("metadata", {})
    center_lat = float(metadata.get("lat", 0.0))
    center_lon = float(metadata.get("lon", 0.0))
    elements = payload.get("overpass_response", payload).get("elements", [])
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_named_categories: set[tuple[str, str]] = set()

    for element in elements:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags", {})
        if not isinstance(tags, dict):
            continue
        category = _representative_poi_category(tags)
        if category is None:
            continue
        lat, lon = _element_lat_lon(element)
        if lat is None or lon is None:
            continue
        osm_key = f"{element.get('type')}:{element.get('id')}"
        if osm_key in seen_ids:
            continue
        seen_ids.add(osm_key)
        name = _poi_name(tags)
        named_category_key = (category, name)
        if named_category_key in seen_named_categories:
            continue
        seen_named_categories.add(named_category_key)
        poi_type = _poi_type(tags)
        rows.append(
            {
                "category": category,
                "category_label": REPRESENTATIVE_POI_CATEGORIES[category]["label"],
                "name": name,
                "lat": lat,
                "lon": lon,
                "osm_type": str(element.get("type", "")),
                "osm_id": str(element.get("id", "")),
                "poi_type": OSM_TYPE_LABELS.get(poi_type, poi_type),
                "distance_meters": _haversine_meters(center_lat, center_lon, lat, lon),
            }
        )

    poi = pd.DataFrame(rows, columns=columns)
    if poi.empty:
        return poi
    return (
        poi.sort_values(["category", "distance_meters", "name"])
        .groupby("category", as_index=False, sort=False)
        .head(REPRESENTATIVE_POI_LIMIT_PER_CATEGORY)
        .sort_values(["category", "distance_meters"])
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner=False)
def load_representative_transport_stations(candidate_name: str) -> pd.DataFrame:
    columns = [
        "name",
        "lat",
        "lon",
        "operator",
        "poi_type",
        "station_uid",
        "station_id",
        "distance_meters",
        "source",
    ]
    candidates = pd.read_csv(CANDIDATE_LOCATIONS_CSV)
    candidate_rows = candidates[candidates["candidate_name"] == candidate_name]
    if candidate_rows.empty:
        return pd.DataFrame(columns=columns)

    center = candidate_rows.iloc[0]
    center_lat = float(center["lat"])
    center_lon = float(center["lon"])
    rows: list[dict[str, Any]] = []
    seen_uids: set[str] = set()

    for filename, metadata in TDX_RAIL_STATION_FILES.items():
        station_path = TDX_STATION_DATA_DIR / filename
        if not station_path.exists():
            continue
        stations = json.loads(station_path.read_text(encoding="utf-8"))
        if not isinstance(stations, list):
            continue
        for station in stations:
            if not isinstance(station, dict):
                continue
            lat, lon = _station_lat_lon(station)
            if lat is None or lon is None:
                continue
            distance = _haversine_meters(center_lat, center_lon, lat, lon)
            if distance > DETAIL_TRANSPORT_RADIUS_METERS:
                continue
            station_uid = str(station.get("StationUID", ""))
            if station_uid in seen_uids:
                continue
            seen_uids.add(station_uid)
            rows.append(
                {
                    "name": _station_name(station),
                    "lat": lat,
                    "lon": lon,
                    "operator": metadata["operator"],
                    "poi_type": metadata["label"],
                    "station_uid": station_uid,
                    "station_id": str(station.get("StationID", "")),
                    "distance_meters": distance,
                    "source": f"TDX station cache: {filename}",
                }
            )

    stations = pd.DataFrame(rows, columns=columns)
    if stations.empty:
        return stations
    return (
        stations.sort_values(["distance_meters", "operator", "name"])
        .head(REPRESENTATIVE_TRANSPORT_STATION_LIMIT)
        .reset_index(drop=True)
    )


def _candidate_center(candidate_name: str) -> tuple[float, float]:
    candidates = pd.read_csv(CANDIDATE_LOCATIONS_CSV)
    candidate_rows = candidates[candidates["candidate_name"] == candidate_name]
    if candidate_rows.empty:
        raise RuntimeError(f"Unknown candidate_name: {candidate_name}")
    center = candidate_rows.iloc[0]
    return float(center["lat"]), float(center["lon"])


@st.cache_data(show_spinner=False)
def load_detail_metro_stations(candidate_name: str) -> pd.DataFrame:
    columns = [
        "station_uid",
        "station_id",
        "station_name_zh",
        "station_name_en",
        "line_ids",
        "line_names_zh",
        "lat",
        "lon",
        "distance_meters",
    ]
    if not METRO_STATIONS_CSV.exists():
        return pd.DataFrame(columns=columns)

    center_lat, center_lon = _candidate_center(candidate_name)
    stations = pd.read_csv(METRO_STATIONS_CSV)
    stations["lat"] = pd.to_numeric(stations["lat"], errors="coerce")
    stations["lon"] = pd.to_numeric(stations["lon"], errors="coerce")
    stations = stations.dropna(subset=["lat", "lon"]).copy()
    stations["distance_meters"] = stations.apply(
        lambda row: _haversine_meters(center_lat, center_lon, float(row["lat"]), float(row["lon"])),
        axis=1,
    )
    stations = stations[stations["distance_meters"] <= DETAIL_EXTENDED_LIVING_AREA_RADIUS_METERS].copy()
    if stations.empty:
        return pd.DataFrame(columns=columns)
    return stations.sort_values(["distance_meters", "line_ids", "station_name_zh"])[columns].reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_detail_youbike_stations(candidate_name: str) -> pd.DataFrame:
    columns = [
        "city",
        "station_uid",
        "station_id",
        "station_name_zh",
        "station_name_en",
        "lat",
        "lon",
        "station_address_zh",
        "distance_meters",
    ]
    if not YOUBIKE_STATIONS_CSV.exists():
        return pd.DataFrame(columns=columns)

    center_lat, center_lon = _candidate_center(candidate_name)
    stations = pd.read_csv(YOUBIKE_STATIONS_CSV)
    stations["lat"] = pd.to_numeric(stations["lat"], errors="coerce")
    stations["lon"] = pd.to_numeric(stations["lon"], errors="coerce")
    stations = stations.dropna(subset=["lat", "lon"]).copy()
    stations["distance_meters"] = stations.apply(
        lambda row: _haversine_meters(center_lat, center_lon, float(row["lat"]), float(row["lon"])),
        axis=1,
    )
    stations = stations[stations["distance_meters"] <= DETAIL_EXTENDED_LIVING_AREA_RADIUS_METERS].copy()
    if stations.empty:
        return pd.DataFrame(columns=columns)
    return stations.sort_values(["distance_meters", "station_name_zh"])[columns].reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_detail_metro_lines(candidate_name: str) -> dict[str, Any]:
    empty = {
        "type": "FeatureCollection",
        "features": [],
        "metadata": {
            "source": str(METRO_LINES_GEOJSON.relative_to(PROJECT_ROOT)),
            "filter_radius_meters": DETAIL_EXTENDED_LIVING_AREA_RADIUS_METERS,
        },
    }
    if not METRO_LINES_GEOJSON.exists():
        return empty

    center_lat, center_lon = _candidate_center(candidate_name)
    lines = gpd.read_file(METRO_LINES_GEOJSON)
    if lines.empty or "geometry" not in lines:
        return empty
    if lines.crs is None:
        lines = lines.set_crs("EPSG:4326")

    center = gpd.GeoSeries([Point(center_lon, center_lat)], crs="EPSG:4326").to_crs(TAIWAN_PROJECTED_CRS).iloc[0]
    buffer = center.buffer(DETAIL_EXTENDED_LIVING_AREA_RADIUS_METERS)
    projected = lines.to_crs(TAIWAN_PROJECTED_CRS)
    filtered = lines[projected.geometry.notna() & projected.geometry.intersects(buffer)].copy()
    if filtered.empty:
        return empty
    for column in filtered.columns:
        if column == filtered.geometry.name:
            continue
        filtered[column] = filtered[column].map(lambda value: "" if pd.isna(value) else str(value))
    return json.loads(filtered.to_crs("EPSG:4326").to_json())


def _safe_poi_slug(value: str) -> str:
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
    return mapping[value]


def _station_lat_lon(station: dict[str, Any]) -> tuple[float | None, float | None]:
    position = station.get("StationPosition")
    if not isinstance(position, dict):
        return None, None
    lat = position.get("PositionLat")
    lon = position.get("PositionLon")
    if lat is None or lon is None:
        return None, None
    return float(lat), float(lon)


def _station_name(station: dict[str, Any]) -> str:
    name = station.get("StationName", {})
    if isinstance(name, dict):
        value = str(name.get("Zh_tw", "")).strip()
        if value:
            return value
    return str(station.get("StationID", "未命名站點")).strip()


def _representative_poi_category(tags: dict[str, Any]) -> str | None:
    for category, definition in REPRESENTATIVE_POI_CATEGORIES.items():
        for key, values in definition["tags"].items():
            if str(tags.get(key, "")) in values:
                return category
    return None


def _element_lat_lon(element: dict[str, Any]) -> tuple[float | None, float | None]:
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    center = element.get("center")
    if isinstance(center, dict) and "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])
    return None, None


def _poi_name(tags: dict[str, Any]) -> str:
    for key in ["name:zh", "name", "brand:zh", "brand"]:
        value = str(tags.get(key, "")).strip()
        if value:
            return value
    poi_type = _poi_type(tags)
    return OSM_TYPE_LABELS.get(poi_type, "未命名 POI")


def _poi_type(tags: dict[str, Any]) -> str:
    for key in ["shop", "amenity", "leisure"]:
        value = str(tags.get(key, "")).strip()
        if value:
            return value
    return "poi"


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@st.cache_data(show_spinner=False)
def load_policy_lens_data() -> pd.DataFrame:
    policy = pd.read_csv(POLICY_LENS_CSV)
    livability = pd.read_csv(LIVABILITY_CSV)

    required_columns = {
        "candidate_name",
        "district",
        "official_median_rent",
        "official_contract_count",
        "commute_accessibility_minutes",
        "commute_accessibility_workplace_count",
        "livability_index",
        "policy_linked_record_count",
        "total_rental_record_count",
        "policy_linked_record_share",
        "lat",
        "lon",
        "policy_quadrant",
    }
    missing = required_columns - set(policy.columns)
    if missing:
        raise RuntimeError(f"Policy Lens v0 data is missing columns: {sorted(missing)}")
    if len(policy) != 16:
        raise RuntimeError(f"Expected 16 policy candidates, found {len(policy)}.")
    if policy["candidate_name"].nunique() != 16:
        raise RuntimeError("Policy Lens v0 data includes duplicated candidate_name values.")

    poi_columns = [
        "candidate_name",
        "food_count",
        "shopping_count",
        "recreation_count",
        "culture_count",
        "medical_count",
        "total_poi_count",
    ]
    available_poi_columns = [column for column in poi_columns if column in livability.columns]
    policy = policy.merge(
        livability[available_poi_columns],
        on="candidate_name",
        how="left",
        validate="one_to_one",
    )
    policy["living_area"] = policy["candidate_name"].map(living_area)

    required_no_missing = [
        "official_median_rent",
        "official_contract_count",
        "commute_accessibility_minutes",
        "commute_accessibility_workplace_count",
        "livability_index",
        "policy_linked_record_count",
        "total_rental_record_count",
        "policy_linked_record_share",
        "lat",
        "lon",
    ]
    missing_values = policy[policy[required_no_missing].isna().any(axis=1)]["candidate_name"].tolist()
    if missing_values:
        raise RuntimeError(f"Policy Lens v0 rows have missing required values: {missing_values}")
    return policy.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_career_policy_lens_phase7() -> tuple[pd.DataFrame, str]:
    missing_files = [
        path.relative_to(PROJECT_ROOT)
        for path in [CAREER_POLICY_LENS_PHASE7_CSV, CAREER_POLICY_LENS_PHASE7_MD]
        if not path.exists()
    ]
    if missing_files:
        raise FileNotFoundError(f"Missing Career Policy Lens Phase 7 files: {missing_files}")

    career_policy = pd.read_csv(CAREER_POLICY_LENS_PHASE7_CSV)
    career_policy_md = CAREER_POLICY_LENS_PHASE7_MD.read_text(encoding="utf-8")
    required_columns = {
        "target_domain",
        "target_occupation_name",
        "transition_span",
        "feasibility_level",
        "market_evidence_status",
        "high_relevance_job_count",
        "medium_relevance_job_count",
        "number_of_missing_skills",
        "missing_skills_preview",
        "potential_training_coverage_ratio",
        "matched_course_count",
        "total_training_hours",
        "estimated_direct_course_cost",
        "training_gap_status",
        "learning_burden",
        "ntpc_population_18_35",
        "ntpc_population_period",
        "ntpc_population_age_scope",
        "ntpc_population_age_harmonization",
        "mol_transition_intention_percent",
        "mol_transition_age_harmonization",
        "mol_training_participation_percent",
        "mol_training_age_harmonization",
        "mol_no_course_info_percent",
        "mol_no_course_info_denominator",
        "mol_fee_barrier_percent",
        "mol_fee_barrier_denominator",
    }
    missing = sorted(required_columns - set(career_policy.columns))
    if missing:
        raise RuntimeError(f"Career Policy Lens Phase 7 data is missing columns: {missing}")
    return career_policy.reset_index(drop=True), career_policy_md


@st.cache_data(show_spinner=False)
def load_career_learning_ladder_phase8() -> pd.DataFrame:
    if not CAREER_LEARNING_LADDER_PHASE8_CSV.exists():
        raise FileNotFoundError(
            f"Missing Career Learning Ladder Phase 8 file: {CAREER_LEARNING_LADDER_PHASE8_CSV.relative_to(PROJECT_ROOT)}"
        )

    ladder = pd.read_csv(CAREER_LEARNING_LADDER_PHASE8_CSV)
    required_columns = {
        "target_domain",
        "target_occupation_name",
        "transition_span",
        "market_evidence_status",
        "high_relevance_job_count",
        "medium_relevance_job_count",
        "potential_training_coverage_ratio",
        "total_training_hours",
        "estimated_direct_course_cost",
        "currently_found_related_course_hours",
        "currently_found_related_course_cost_ntd",
        "matched_course_candidate_count",
        "single_course_hours_median",
        "single_course_hours_min",
        "single_course_hours_max",
        "single_course_fee_median",
        "single_course_fee_min",
        "single_course_fee_max",
        "sequential_learning_pathway_evidence",
        "cumulative_hours_cost_display_allowed",
        "cumulative_hours_cost_display_note",
        "training_evidence_potential_course_found",
        "training_evidence_course_depth",
        "training_evidence_complete_pathway",
        "learning_burden",
        "exploration_direction",
        "foundation_skill_boost",
        "learning_milestone_or_validation",
        "advanced_training",
        "market_job_linkage",
        "policy_intervention_types",
        "policy_intervention_evidence_reasons",
        "conservative_note",
        "phase7_data_limitations",
    }
    missing = sorted(required_columns - set(ladder.columns))
    if missing:
        raise RuntimeError(f"Career Learning Ladder Phase 8 data is missing columns: {missing}")
    return ladder.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_career_evidence_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    missing_files = [
        path.relative_to(PROJECT_ROOT)
        for path in [
            CAREER_V35_CANDIDATES_CSV,
            CAREER_V4_TRAINING_CSV,
            CAREER_BEAUTY_PHASE5_CSV,
            CAREER_TRAINING_MAPPING_CSV,
            CAREER_TAIWANJOBS_RAW_CSV,
        ]
        if not path.exists()
    ]
    if missing_files:
        raise FileNotFoundError(f"Missing career evidence output files: {missing_files}")

    candidates_v35 = pd.read_csv(CAREER_V35_CANDIDATES_CSV)
    training_v4 = pd.read_csv(CAREER_V4_TRAINING_CSV)
    beauty_phase5 = pd.read_csv(CAREER_BEAUTY_PHASE5_CSV)
    course_mapping = pd.read_csv(CAREER_TRAINING_MAPPING_CSV)
    taiwanjobs_raw = pd.read_csv(CAREER_TAIWANJOBS_RAW_CSV, encoding="utf-8-sig")

    required_v35 = {
        "target_occupation_code",
        "target_occupation_name",
        "transition_span",
        "feasibility_level",
        "market_validation",
        "mapping_confidence",
        "manual_review_needed",
        "matched_job_count",
        "total_demand_persons",
        "salary_lower_median",
        "salary_upper_median",
        "salary_basis",
        "shared_top_skills",
        "missing_skills",
        "target_skill_gap",
        "transferable_skill_coverage",
    }
    required_v4 = {
        "target_occupation_code",
        "target_occupation_name",
        "training_coverage_ratio",
        "gap_skill_training_coverage_ratio",
        "number_of_missing_skills",
        "number_of_gap_skills",
        "number_of_trainable_skills_found",
        "total_training_hours",
        "estimated_direct_course_cost",
        "learning_burden_level",
        "partially_covered_skills",
        "missing_skills",
        "learning_plan_phase_1_foundational_skills",
        "learning_plan_phase_2_domain_technical_skills",
        "learning_plan_phase_3_portfolio_job_preparation",
        "scenario_6m_training_coverage_ratio",
        "scenario_6m_feasibility_estimate",
    }
    required_mapping = {
        "target_occupation_code",
        "skill_name",
        "skill_gap_status",
        "course_code",
        "course_name",
        "training_provider",
        "location",
        "training_hours",
        "fee_per_person",
        "mapping_score",
        "mapping_confidence",
        "manual_review_needed",
    }
    required_taiwanjobs = {
        "OCCU_DESC（職務名稱）",
        "CJOB_NAME1（職務大類別名稱）",
        "CJOB_NAME2（職務小類別名稱）",
        "JOB_PERSON（雇用人數）",
        "JOB_DETAIL（工作內容）",
        "CITYNAME（工作地點）",
        "SALARYCD（核薪方式）",
        "NT_L（薪資範圍下限）",
        "NT_U（薪資範圍上限）",
        "URL_QUERY（職缺資料URL）",
        "COMPNAME（公司名稱）",
    }
    required_beauty = {
        "target_occupation_code",
        "target_occupation_name",
        "target_domain_primary_signal",
        "transition_span",
        "feasibility_level",
        "skill_similarity",
        "transferable_skill_coverage",
        "target_skill_gap",
        "education_barrier",
        "credential_barrier",
        "taiwan_market_evidence",
        "taiwanjobs_high_relevance_job_count",
        "taiwanjobs_medium_relevance_job_count",
        "total_demand_persons_high",
        "salary_lower_median_high",
        "salary_upper_median_high",
        "training_availability",
        "training_course_count",
        "total_training_hours",
        "estimated_direct_course_cost",
        "learning_burden",
        "already_covered_skills",
        "partially_covered_skills",
        "missing_skills",
        "matched_training_courses",
        "high_relevance_job_examples",
        "medium_relevance_job_examples",
    }
    for label, frame, required in [
        ("v3.5 candidates", candidates_v35, required_v35),
        ("v4 training", training_v4, required_v4),
        ("Phase 5 beauty candidates", beauty_phase5, required_beauty),
        ("v4 course mapping", course_mapping, required_mapping),
        ("TaiwanJobs raw jobs", taiwanjobs_raw, required_taiwanjobs),
    ]:
        missing = sorted(required - set(frame.columns))
        if missing:
            raise RuntimeError(f"Career {label} is missing required columns: {missing}")

    return candidates_v35, training_v4, course_mapping, taiwanjobs_raw, beauty_phase5
