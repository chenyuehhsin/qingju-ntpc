from __future__ import annotations

import html
from typing import Any

import folium
import geopandas as gpd
import pandas as pd
from branca.colormap import LinearColormap
from branca.element import MacroElement, Template
from folium.plugins import HeatMap

from data_loader import (
    DISTRICT_ANALYSIS_LAYER_NONE,
    DISTRICT_ANALYSIS_LAYER_RENT,
    DISTRICT_ANALYSIS_LAYER_YOUTH_COUNT,
    DISTRICT_ANALYSIS_LAYER_YOUTH_SHARE,
    MODE_COLORS,
    MODE_ORDER,
    living_area,
    minutes,
    money,
)

CORE_LIVING_AREA_RADIUS_METERS = 1000
EXTENDED_LIVING_AREA_RADIUS_METERS = 2000
POI_STATISTICS_RADIUS_METERS = 800
DETAIL_POI_COLORS = {
    "center": "#243238",
    "transit": "#4F83A6",
    "youbike": "#2F9E73",
    "shopping": "#78B995",
    "medical": "#C45B65",
    "recreation": "#D39B43",
}
DETAIL_POI_SYMBOLS = {
    "center": "心",
    "transit": "站",
    "shopping": "採",
    "medical": "醫",
    "recreation": "園",
}
SHUANGBEI_BOUNDS = [[24.80, 121.22], [25.32, 121.75]]
TRANSPARENT_TILE_DATA_URI = "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs="
LIVING_AREA_PANE = "living_area_pane"
LIVABILITY_HEATMAP_RADIUS = 20
LIVABILITY_HEATMAP_BLUR = 18
LIVABILITY_HEATMAP_MIN_OPACITY = 0.12
LIVABILITY_HEATMAP_MAX_ZOOM = 16
LIVABILITY_HEATMAP_GRADIENT = {
    0.22: "#7CCDB7",
    0.48: "#F1D879",
    0.72: "#ECA15A",
    1.00: "#C45B65",
}
DISTRICT_ANALYSIS_CONFIG = {
    DISTRICT_ANALYSIS_LAYER_RENT: {
        "field": "official_median_rent",
        "title": "行政區租金",
        "unit": "NTD/month",
        "low_color": "#F8EBDD",
        "high_color": "#D97950",
        "higher_label": "租金越高",
        "missing_label": "無租金資料",
    },
    DISTRICT_ANALYSIS_LAYER_YOUTH_COUNT: {
        "field": "youth_population_18_35",
        "title": "18–35青年人口數",
        "unit": "people",
        "low_color": "#E8F1EF",
        "high_color": "#4F9E8D",
        "higher_label": "青年人口數越多，代表可能影響規模較大",
        "missing_label": "unresolved",
    },
    DISTRICT_ANALYSIS_LAYER_YOUTH_SHARE: {
        "field": "youth_population_18_35_share",
        "title": "18–35青年人口占比",
        "unit": "share",
        "low_color": "#EEF0F7",
        "high_color": "#6F7FB7",
        "higher_label": "青年人口占比越高，代表可能影響規模較大",
        "missing_label": "unresolved",
    },
}


def build_overview_map(
    candidates: pd.DataFrame,
    top3: pd.DataFrame,
    destination: dict[str, float | str],
    towns: gpd.GeoDataFrame,
    cities: gpd.GeoDataFrame,
    analysis_layer: str = DISTRICT_ANALYSIS_LAYER_NONE,
) -> folium.Map:
    center_lat = float(destination["destination_lat"])
    center_lon = float(destination["destination_lon"])
    map_obj = folium.Map(
        location=[center_lat, center_lon - 0.06],
        zoom_start=10,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )
    _fit_candidate_bounds(map_obj, candidates, center_lat, center_lon)
    _add_overview_base_context(map_obj, towns, cities)
    _add_district_analysis_layer(map_obj, towns, analysis_layer)
    _add_living_area_pane(map_obj)
    other_group = folium.FeatureGroup(name="其他候選", show=True).add_to(map_obj)
    commute_group = folium.FeatureGroup(name="通勤連結示意", show=True).add_to(map_obj)
    top3_group = folium.FeatureGroup(name="Top3", show=True).add_to(map_obj)
    workplace_group = folium.FeatureGroup(name="Workplace", show=True).add_to(map_obj)

    top1_names = set(top3[top3["rank"] == 1]["candidate_name"])
    top3_names = set(top3["candidate_name"])
    top3_only_names = top3_names - top1_names
    top3_candidates = candidates[candidates["candidate_name"].isin(top3_names)].copy()
    for _, row in top3_candidates.iterrows():
        candidate_rows = top3[top3["candidate_name"] == row["candidate_name"]].sort_values("rank")
        candidate_modes = _modes_for_candidate(top3, row["candidate_name"])
        rank = int(candidate_rows.iloc[0]["rank"])
        color = MODE_COLORS[candidate_modes[0]]
        _add_commute_link(commute_group, row, center_lat, center_lon, str(destination["destination"]), color, rank)

    for _, row in candidates.iterrows():
        if row["candidate_name"] in top3_names:
            continue
        _add_candidate_dot(other_group, row, radius=3.2, fill_opacity=0.32, opacity=0.44)

    for _, row in candidates[candidates["candidate_name"].isin(top3_only_names)].iterrows():
        candidate_modes = _modes_for_candidate(top3, row["candidate_name"])
        color = MODE_COLORS[candidate_modes[0]]
        rank = int(top3[top3["candidate_name"] == row["candidate_name"]].sort_values("rank").iloc[0]["rank"])
        _add_overview_living_area_circles(top3_group, row, color, rank)
        _add_ranked_recommendation_marker(
            top3_group,
            row,
            rank=rank,
            color=color,
            radius=8,
            fill_opacity=0.78,
            popup=_overview_popup(row, candidate_modes, f"Top {rank} option"),
        )
        _add_top3_label(top3_group, row, rank, color)

    for _, row in candidates[candidates["candidate_name"].isin(top1_names)].iterrows():
        all_candidate_modes = _modes_for_candidate(top3, row["candidate_name"])
        top1_modes = _modes_for_candidate(top3[top3["rank"] == 1], row["candidate_name"])
        primary_color = MODE_COLORS[top1_modes[0]]
        display_rank = int(top3[top3["candidate_name"] == row["candidate_name"]].sort_values("rank").iloc[0]["rank"])
        _add_overview_living_area_circles(top3_group, row, primary_color, display_rank)
        _add_ranked_recommendation_marker(
            top3_group,
            row,
            rank=display_rank,
            color=primary_color,
            radius=13,
            fill_opacity=0.96,
            popup=_overview_popup(row, all_candidate_modes, "Top 1 recommendation"),
        )
        if len(top1_modes) > 1:
            for index, mode in enumerate(top1_modes[1:], start=1):
                folium.CircleMarker(
                    location=[float(row["lat"]), float(row["lon"])],
                    radius=13 + index * 4,
                    color=MODE_COLORS[mode],
                    weight=3,
                    fill=False,
                    opacity=0.95,
                    tooltip=f"{living_area(row['candidate_name'])} also recommended by {mode}",
                ).add_to(top3_group)
        _add_top3_label(top3_group, row, display_rank, primary_color)

    _add_workplace_marker(workplace_group, center_lat, center_lon, str(destination["destination"]))
    _add_city_label(map_obj, 25.095, 121.405, "新北市")
    _add_city_label(map_obj, 25.045, 121.555, "臺北市")
    folium.LayerControl(collapsed=False).add_to(map_obj)
    _add_overview_legend(map_obj, str(destination["destination"]))
    _add_district_analysis_legend(map_obj, towns, analysis_layer, position="left")
    return map_obj


def build_recommendation_map(
    mode: str,
    candidates: pd.DataFrame,
    top3: pd.DataFrame,
    destination: dict[str, float | str],
    towns: gpd.GeoDataFrame,
    cities: gpd.GeoDataFrame,
) -> folium.Map:
    mode_rows = top3[top3["preference_mode"] == mode].sort_values("rank").copy()
    top3_names = set(mode_rows["candidate_name"])
    color = MODE_COLORS[mode]

    center_lat = float(destination["destination_lat"])
    center_lon = float(destination["destination_lon"])
    map_obj = folium.Map(
        location=[center_lat, center_lon - 0.06],
        zoom_start=10,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )
    _fit_candidate_bounds(map_obj, mode_rows, center_lat, center_lon)
    _add_overview_base_context(map_obj, towns, cities)
    _add_living_area_pane(map_obj)
    rent_group = folium.FeatureGroup(name="行政區租金背景", show=False).add_to(map_obj)
    other_group = folium.FeatureGroup(name="其他候選", show=True).add_to(map_obj)
    commute_group = folium.FeatureGroup(name="通勤連結示意", show=True).add_to(map_obj)
    top3_group = folium.FeatureGroup(name="Top3", show=True).add_to(map_obj)
    workplace_group = folium.FeatureGroup(name="Workplace", show=True).add_to(map_obj)
    _add_rent_context_layer(rent_group, towns)

    for _, row in mode_rows.iterrows():
        _add_commute_link(commute_group, row, center_lat, center_lon, str(destination["destination"]), color, int(row["rank"]))

    for _, row in candidates.iterrows():
        if row["candidate_name"] in top3_names:
            continue
        _add_candidate_dot(other_group, row, radius=3.5, fill_opacity=0.34, opacity=0.46)

    for _, row in mode_rows.iterrows():
        rank = int(row["rank"])
        radius = 12 if rank == 1 else 8
        fill_opacity = 0.95 if rank == 1 else 0.78
        _add_overview_living_area_circles(top3_group, row, color, rank)
        _add_ranked_recommendation_marker(
            top3_group,
            row,
            rank=rank,
            color=color,
            radius=radius,
            fill_opacity=fill_opacity,
            popup=_candidate_popup(row, rank=rank),
        )
        _add_top3_label(top3_group, row, rank, color)

    _add_workplace_marker(workplace_group, center_lat, center_lon, str(destination["destination"]))

    _add_city_label(map_obj, 25.095, 121.405, "新北市")
    _add_city_label(map_obj, 25.045, 121.555, "臺北市")
    folium.LayerControl(collapsed=False).add_to(map_obj)
    _add_legend(map_obj, color, str(destination["destination"]))
    return map_obj


def build_detail_map(
    row: pd.Series,
    pois: pd.DataFrame,
    livability_density_pois: pd.DataFrame,
    metro_lines: dict[str, Any],
    metro_stations: pd.DataFrame,
    youbike_stations: pd.DataFrame,
    destination: dict[str, float | str],
    towns: gpd.GeoDataFrame,
    cities: gpd.GeoDataFrame,
    mode: str,
) -> folium.Map:
    lat = float(row["lat"])
    lon = float(row["lon"])
    color = MODE_COLORS[mode]
    map_obj = folium.Map(
        location=[lat, lon],
        zoom_start=15,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )
    _add_detail_basemap(map_obj, towns, cities)
    _fit_detail_bounds(map_obj, lat, lon)
    _add_livability_density_heatmap(map_obj, livability_density_pois)
    has_livability_density = not livability_density_pois.empty
    extended_group = folium.FeatureGroup(name="延伸生活圈", show=True).add_to(map_obj)
    core_group = folium.FeatureGroup(name="約15分鐘核心生活圈", show=True).add_to(map_obj)
    rail_group = folium.FeatureGroup(name="軌道交通", show=True).add_to(map_obj)
    youbike_group = folium.FeatureGroup(name="YouBike", show=False).add_to(map_obj)
    shopping_group = folium.FeatureGroup(name="採買", show=True).add_to(map_obj)
    medical_group = folium.FeatureGroup(name="醫療", show=False).add_to(map_obj)
    recreation_group = folium.FeatureGroup(name="公園 / 運動", show=False).add_to(map_obj)
    poi_groups = {
        "shopping": shopping_group,
        "medical": medical_group,
        "recreation": recreation_group,
    }
    folium.Circle(
        location=[lat, lon],
        radius=EXTENDED_LIVING_AREA_RADIUS_METERS,
        color=color,
        weight=1.4,
        opacity=0.42,
        fill=True,
        fill_color=color,
        fill_opacity=0.045,
        tooltip=f"{row['living_area']}｜延伸生活圈（2 km）",
    ).add_to(extended_group)
    folium.Circle(
        location=[lat, lon],
        radius=CORE_LIVING_AREA_RADIUS_METERS,
        color=color,
        weight=2.4,
        opacity=0.88,
        fill=True,
        fill_color=color,
        fill_opacity=0.10,
        tooltip=f"{row['living_area']}｜約15分鐘核心生活圈（1 km）",
    ).add_to(core_group)
    _add_detail_poi_marker(
        core_group,
        lat,
        lon,
        "center",
        str(row["candidate_name"]),
        "生活圈中心",
        f"{row['living_area']}｜約15分鐘核心生活圈中心",
    )
    _add_detail_metro_lines(rail_group, metro_lines)
    for _, station in metro_stations.iterrows():
        _add_detail_metro_station_marker(
            rail_group,
            float(station["lat"]),
            float(station["lon"]),
            str(station["station_name_zh"]),
            str(station.get("line_ids", "")),
            str(station.get("line_names_zh", "")),
            float(station["distance_meters"]),
        )
    for _, station in youbike_stations.iterrows():
        _add_detail_youbike_marker(
            youbike_group,
            float(station["lat"]),
            float(station["lon"]),
            str(station["station_name_zh"]),
            float(station["distance_meters"]),
        )
    for _, poi in pois.iterrows():
        _add_detail_poi_marker(
            poi_groups.get(str(poi["category"]), recreation_group),
            float(poi["lat"]),
            float(poi["lon"]),
            str(poi["category"]),
            str(poi["name"]),
            str(poi["poi_type"]),
            f"{poi['category_label']}｜約 {float(poi['distance_meters']):.0f}m",
        )
    folium.LayerControl(collapsed=False).add_to(map_obj)
    _add_detail_legend(map_obj, str(row["living_area"]), has_livability_density)
    return map_obj


def _add_livability_density_heatmap(map_obj: folium.Map, pois: pd.DataFrame) -> None:
    if pois.empty:
        return
    heat_data = pois[["lat", "lon", "weight"]].dropna().astype(float).values.tolist()
    if not heat_data:
        return
    HeatMap(
        heat_data,
        name="生活機能密度",
        min_opacity=LIVABILITY_HEATMAP_MIN_OPACITY,
        max_zoom=LIVABILITY_HEATMAP_MAX_ZOOM,
        radius=LIVABILITY_HEATMAP_RADIUS,
        blur=LIVABILITY_HEATMAP_BLUR,
        gradient=LIVABILITY_HEATMAP_GRADIENT,
        overlay=True,
        control=True,
        show=True,
    ).add_to(map_obj)


def _add_top3_label(map_obj: folium.Map, row: pd.Series, rank: int, color: str) -> None:
    label = html.escape(f"#{rank} {row['living_area']}")
    font_size = 13 if rank == 1 else 12
    font_weight = 900 if rank == 1 else 820
    map_obj.add_child(
        folium.Marker(
            location=[float(row["lat"]), float(row["lon"])],
            icon=folium.DivIcon(
                html=(
                    f'<div style="transform:translate(16px,-38px);'
                    f'display:inline-flex;align-items:center;white-space:nowrap;'
                    f'background:rgba(255,255,255,0.92);border:1.6px solid {color};'
                    f'border-left:7px solid {color};border-radius:999px;'
                    f'padding:4px 9px;color:#243238;font-size:{font_size}px;'
                    f'font-weight:{font_weight};line-height:1.2;'
                    f'box-shadow:0 2px 7px rgba(36,50,56,0.16);">{label}</div>'
                ),
                icon_size=(180, 28),
                icon_anchor=(0, 0),
            ),
        )
    )


def _fit_candidate_bounds(map_obj: folium.Map, candidates: pd.DataFrame, center_lat: float, center_lon: float) -> None:
    candidate_bounds = [
        [min(candidates["lat"].min(), center_lat) - 0.032, min(candidates["lon"].min(), center_lon) - 0.038],
        [max(candidates["lat"].max(), center_lat) + 0.032, max(candidates["lon"].max(), center_lon) + 0.038],
    ]
    map_obj.fit_bounds(_clamp_bounds_to_shuangbei(candidate_bounds), padding=(6, 6))


def _fit_detail_bounds(map_obj: folium.Map, center_lat: float, center_lon: float) -> None:
    lat_delta = 0.022
    lon_delta = 0.024
    map_obj.fit_bounds(
        [[center_lat - lat_delta, center_lon - lon_delta], [center_lat + lat_delta, center_lon + lon_delta]],
        padding=(12, 12),
    )


def _add_overview_base_context(map_obj: folium.Map, towns: gpd.GeoDataFrame, cities: gpd.GeoDataFrame) -> None:
    def town_style(feature: dict) -> dict:
        city = feature["properties"].get("COUNTYNAME")
        return {
            "fillColor": "#F1F6F1" if city == "新北市" else "#F3F6F8",
            "color": "#D4DEDF",
            "weight": 0.55,
            "opacity": 0.46,
            "fillOpacity": 0.72,
        }

    folium.GeoJson(
        towns,
        name="雙北極簡背景",
        style_function=town_style,
        control=False,
        tooltip=None,
    ).add_to(map_obj)
    _add_city_boundary_context(map_obj, cities)


def _add_living_area_pane(map_obj: folium.Map) -> None:
    folium.map.CustomPane(LIVING_AREA_PANE, z_index=390).add_to(map_obj)


def _add_district_analysis_layer(map_obj: folium.Map, towns: gpd.GeoDataFrame, analysis_layer: str) -> None:
    if analysis_layer == DISTRICT_ANALYSIS_LAYER_NONE or analysis_layer not in DISTRICT_ANALYSIS_CONFIG:
        return
    config = DISTRICT_ANALYSIS_CONFIG[analysis_layer]
    field = str(config["field"])
    values = pd.to_numeric(towns[field], errors="coerce") if field in towns.columns else pd.Series(dtype=float)
    valid_values = values.dropna()
    color_map = None
    if not valid_values.empty:
        color_map = LinearColormap(
            colors=[str(config["low_color"]), str(config["high_color"])],
            vmin=float(valid_values.min()),
            vmax=float(valid_values.max()),
        )

    def analysis_style(feature: dict[str, Any]) -> dict[str, Any]:
        properties = feature.get("properties", {})
        value = properties.get(field)
        has_value = value is not None and not pd.isna(value)
        fill_color = color_map(float(value)) if has_value and color_map is not None else "#EFF1F0"
        return {
            "fillColor": fill_color,
            "color": "#9EAAAD" if has_value else "#C7D0D2",
            "weight": 0.82 if has_value else 0.58,
            "opacity": 0.66 if has_value else 0.40,
            "fillOpacity": 0.34 if has_value else 0.13,
        }

    folium.GeoJson(
        towns,
        name=analysis_layer,
        style_function=analysis_style,
        control=False,
        tooltip=_district_analysis_tooltip(analysis_layer),
    ).add_to(map_obj)


def _district_analysis_tooltip(analysis_layer: str) -> folium.GeoJsonTooltip:
    display_fields = {
        DISTRICT_ANALYSIS_LAYER_RENT: ("official_median_rent_display", "行政區租金"),
        DISTRICT_ANALYSIS_LAYER_YOUTH_COUNT: ("youth_population_18_35_display", "18–35青年人口數"),
        DISTRICT_ANALYSIS_LAYER_YOUTH_SHARE: ("youth_population_share_display", "18–35青年人口占比"),
    }
    selected_field, selected_alias = display_fields[analysis_layer]
    remaining_fields = [
        (field, alias)
        for field, alias in display_fields.values()
        if field != selected_field
    ]
    return folium.GeoJsonTooltip(
        fields=["TOWNNAME", selected_field, *[field for field, _ in remaining_fields]],
        aliases=["行政區", f"★ {selected_alias}（目前圖層）", *[alias for _, alias in remaining_fields]],
        labels=True,
        sticky=False,
        localize=False,
    )


def _add_district_analysis_legend(
    map_obj: folium.Map,
    towns: gpd.GeoDataFrame,
    analysis_layer: str,
    position: str = "left",
) -> None:
    if analysis_layer == DISTRICT_ANALYSIS_LAYER_NONE or analysis_layer not in DISTRICT_ANALYSIS_CONFIG:
        return
    config = DISTRICT_ANALYSIS_CONFIG[analysis_layer]
    field = str(config["field"])
    values = pd.to_numeric(towns[field], errors="coerce") if field in towns.columns else pd.Series(dtype=float)
    valid_values = values.dropna()
    if valid_values.empty:
        min_label = "unresolved"
        max_label = "unresolved"
        bar_style = "background:#EFF1F0;border:1px solid #C7D0D2;"
        note = str(config["missing_label"])
    else:
        min_value = float(valid_values.min())
        max_value = float(valid_values.max())
        min_label = _analysis_value_label(min_value, str(config["unit"]))
        max_label = _analysis_value_label(max_value, str(config["unit"]))
        bar_style = f"background:linear-gradient(90deg,{config['low_color']},{config['high_color']});"
        note = str(config["higher_label"])
    side = "left" if position == "left" else "right"
    template = Template(
        f"""
        {{% macro html(this, kwargs) %}}
        <div style="
            position: fixed;
            {side}: 24px;
            bottom: 28px;
            z-index: 9998;
            background: rgba(255,255,255,0.94);
            border: 1px solid #D6DDE0;
            border-radius: 10px;
            padding: 10px 12px;
            color: #243238;
            font-size: 13px;
            box-shadow: 0 1px 4px rgba(36,50,56,0.10);
            min-width: 214px;
            max-width: 280px;
        ">
          <div style="font-weight:850;margin-bottom:7px;">{html.escape(str(config['title']))}</div>
          <div style="height:10px;border-radius:999px;{bar_style}margin-bottom:5px;"></div>
          <div style="display:flex;justify-content:space-between;color:#65747A;font-size:12px;"><span>{min_label}</span><span>{max_label}</span></div>
          <div style="margin-top:7px;color:#65747A;line-height:1.35;">{html.escape(note)}</div>
        </div>
        {{% endmacro %}}
        """
    )
    macro = MacroElement()
    macro._template = template
    map_obj.get_root().add_child(macro)


def _analysis_value_label(value: float, unit: str) -> str:
    if unit == "share":
        return f"{value * 100:.1f}%"
    if unit == "NTD/month":
        return f"{money(value)}"
    if unit == "people":
        return f"{value:,.0f}"
    return f"{value:.2f}"


def _add_detail_basemap(map_obj: folium.Map, towns: gpd.GeoDataFrame, cities: gpd.GeoDataFrame) -> None:
    _add_detail_background_style(map_obj)
    folium.TileLayer(
        tiles=TRANSPARENT_TILE_DATA_URI,
        name="極簡生活圈底圖",
        attr="Local transparent background",
        overlay=False,
        control=True,
        show=True,
    ).add_to(map_obj)
    boundary_group = folium.FeatureGroup(name="行政邊界", show=True, control=False).add_to(map_obj)

    def town_style(feature: dict) -> dict:
        city = feature["properties"].get("COUNTYNAME")
        return {
            "fillColor": "#F3F0E8" if city == "新北市" else "#F1F3F2",
            "color": "#C7CECC",
            "weight": 0.62,
            "opacity": 0.42,
            "fillOpacity": 0.42,
        }

    def city_style(feature: dict) -> dict:
        city = feature["properties"].get("COUNTYNAME")
        return {
            "fillColor": "transparent",
            "color": "#7A8A84" if city == "新北市" else "#71818A",
            "weight": 1.55,
            "opacity": 0.58,
            "fillOpacity": 0.0,
        }

    folium.GeoJson(
        towns,
        name="行政區邊界",
        style_function=town_style,
        control=False,
        tooltip=None,
    ).add_to(boundary_group)
    folium.GeoJson(
        cities,
        name="縣市邊界",
        style_function=city_style,
        control=False,
        tooltip=folium.GeoJsonTooltip(fields=["COUNTYNAME"], labels=False, sticky=False),
    ).add_to(boundary_group)
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="街道地圖",
        overlay=False,
        control=True,
        show=False,
    ).add_to(map_obj)


def _add_detail_background_style(map_obj: folium.Map) -> None:
    template = Template(
        """
        {% macro html(this, kwargs) %}
        <style>
          .leaflet-container {
            background: #F6F3EC;
          }
        </style>
        {% endmacro %}
        """
    )
    macro = MacroElement()
    macro._template = template
    map_obj.get_root().add_child(macro)


def _clamp_bounds_to_shuangbei(bounds: list[list[float]]) -> list[list[float]]:
    return [
        [
            max(bounds[0][0], SHUANGBEI_BOUNDS[0][0]),
            max(bounds[0][1], SHUANGBEI_BOUNDS[0][1]),
        ],
        [
            min(bounds[1][0], SHUANGBEI_BOUNDS[1][0]),
            min(bounds[1][1], SHUANGBEI_BOUNDS[1][1]),
        ],
    ]


def _add_rent_context_layer(layer: folium.FeatureGroup, towns: gpd.GeoDataFrame) -> None:
    folium.GeoJson(
        towns,
        name="district rent context",
        style_function=_district_context_style,
        control=False,
        tooltip=folium.GeoJsonTooltip(
            fields=["TOWNNAME", "official_median_rent"],
            aliases=["行政區", "月租中位數"],
            localize=True,
            sticky=False,
        ),
    ).add_to(layer)


def _add_city_boundary_context(map_obj: folium.Map, cities: gpd.GeoDataFrame) -> None:
    def city_style(feature: dict) -> dict:
        city = feature["properties"].get("COUNTYNAME")
        return {
            "fillColor": "transparent",
            "color": "#7B8B74" if city == "新北市" else "#6B7F8A",
            "weight": 1.25,
            "opacity": 0.42,
            "fillOpacity": 0.0,
        }

    folium.GeoJson(
        cities,
        name="city boundary",
        style_function=city_style,
        control=False,
        tooltip=folium.GeoJsonTooltip(fields=["COUNTYNAME"]),
    ).add_to(map_obj)


def _add_overview_living_area_circles(layer: folium.FeatureGroup, row: pd.Series, color: str, rank: int) -> None:
    lat = float(row["lat"])
    lon = float(row["lon"])
    area_name = living_area(row["candidate_name"])
    folium.Circle(
        location=[lat, lon],
        radius=EXTENDED_LIVING_AREA_RADIUS_METERS,
        color=color,
        weight=1.2 if rank == 1 else 0.9,
        opacity=0.26 if rank == 1 else 0.19,
        fill=True,
        fill_color=color,
        fill_opacity=0.2 if rank == 1 else 0.1,
        pane=LIVING_AREA_PANE,
        tooltip=f"Top {rank}｜{area_name}｜延伸生活圈（2 km）",
    ).add_to(layer)
    folium.Circle(
        location=[lat, lon],
        radius=CORE_LIVING_AREA_RADIUS_METERS,
        color=color,
        weight=2.0 if rank == 1 else 1.45,
        opacity=0.46 if rank == 1 else 0.32,
        fill=True,
        fill_color=color,
        fill_opacity=0.075 if rank == 1 else 0.046,
        pane=LIVING_AREA_PANE,
        tooltip=f"Top {rank}｜{area_name}｜約15分鐘核心生活圈（1 km）",
    ).add_to(layer)


def _add_commute_link(
    layer: folium.FeatureGroup,
    row: pd.Series,
    workplace_lat: float,
    workplace_lon: float,
    workplace_name: str,
    color: str,
    rank: int,
) -> None:
    commute_text = _commute_link_text(row, workplace_name)
    folium.PolyLine(
        locations=[
            [float(row["lat"]), float(row["lon"])],
            [workplace_lat, workplace_lon],
        ],
        color=color,
        weight=2.2 if rank == 1 else 1.6,
        opacity=0.38 if rank == 1 else 0.28,
        dash_array=None if rank == 1 else "6, 8",
        tooltip=f"通勤連結示意｜Top {rank}｜{commute_text}",
    ).add_to(layer)
    _add_commute_time_label(layer, row, workplace_lat, workplace_lon, workplace_name, color, rank)


def _add_commute_time_label(
    layer: folium.FeatureGroup,
    row: pd.Series,
    workplace_lat: float,
    workplace_lon: float,
    workplace_name: str,
    color: str,
    rank: int,
) -> None:
    label_lat = (float(row["lat"]) * 0.58) + (workplace_lat * 0.42) + ((rank - 2) * 0.006)
    label_lon = (float(row["lon"]) * 0.58) + (workplace_lon * 0.42) + ((2 - rank) * 0.004)
    label = html.escape(f"約 {_rounded_commute_minutes(row)} 分鐘")
    tooltip = html.escape(f"通勤連結示意｜{_commute_link_text(row, workplace_name)}")
    folium.Marker(
        location=[label_lat, label_lon],
        tooltip=tooltip,
        icon=folium.DivIcon(
            html=(
                '<div style="'
                'display:inline-flex;align-items:center;justify-content:center;'
                'min-width:56px;height:24px;padding:0 7px;'
                'background:rgba(255,255,255,0.88);'
                f'border:1.4px solid {color};'
                'border-radius:999px;'
                'box-shadow:0 1px 4px rgba(36,50,56,0.14);'
                'color:#243238;font-size:12px;font-weight:850;'
                'line-height:1;white-space:nowrap;'
                f'opacity:{0.92 if rank == 1 else 0.82};'
                f'">{label}</div>'
            ),
            icon_size=(70, 24),
            icon_anchor=(35, 12),
        ),
    ).add_to(layer)


def _commute_link_text(row: pd.Series, workplace_name: str) -> str:
    origin = _short_place_name(str(row["candidate_name"]))
    destination = _short_place_name(workplace_name)
    return f"{origin} → {destination}｜約 {_rounded_commute_minutes(row)} 分鐘"


def _rounded_commute_minutes(row: pd.Series) -> int:
    return int(round(float(row["commute_minutes"])))


def _short_place_name(value: str) -> str:
    name = value.replace("生活圈", "").replace("車站", "").replace("站", "")
    if name == "三峽北大特區":
        return "三峽北大"
    if name == "五股區公所":
        return "五股"
    if name == "我的工作地":
        return name
    return name


def _district_context_style(feature: dict) -> dict:
    rent = feature["properties"].get("official_median_rent")
    has_rent = rent is not None and not pd.isna(rent)
    return {
        "fillColor": _rent_context_color(rent),
        "color": "#AEB8BA",
        "weight": 0.45,
        "opacity": 0.24,
        "fillOpacity": 0.11 if has_rent else 0.04,
    }


def _rent_context_color(value: object) -> str:
    try:
        rent = float(value)
    except (TypeError, ValueError):
        return "#F8FAF9"
    if pd.isna(rent):
        return "#F8FAF9"
    if rent >= 18000:
        return "#D8A4A8"
    if rent >= 15000:
        return "#EBC7AF"
    if rent >= 12000:
        return "#EADCA9"
    return "#CFE4D5"


def _add_candidate_dot(
    map_obj: folium.Map,
    row: pd.Series,
    radius: float,
    fill_opacity: float,
    opacity: float,
) -> None:
    folium.CircleMarker(
        location=[float(row["lat"]), float(row["lon"])],
        radius=radius,
        color="#9EA9AC",
        weight=0.8,
        fill=True,
        fill_color="#AEB8BA",
        fill_opacity=fill_opacity,
        opacity=opacity,
        tooltip=f"{living_area(row['candidate_name'])}｜已評估候選",
        popup=_candidate_popup(row, rank=None),
    ).add_to(map_obj)


def _add_ranked_recommendation_marker(
    map_obj: folium.Map,
    row: pd.Series,
    rank: int,
    color: str,
    radius: float,
    fill_opacity: float,
    popup: folium.Popup,
) -> None:
    folium.CircleMarker(
        location=[float(row["lat"]), float(row["lon"])],
        radius=radius,
        color="#FFFFFF",
        weight=3 if rank == 1 else 2,
        fill=True,
        fill_color=color,
        fill_opacity=fill_opacity,
        opacity=1,
        tooltip=f"Top {rank}｜{row['living_area']}",
        popup=popup,
    ).add_to(map_obj)
    icon_size = 26 if rank == 1 else 22
    folium.Marker(
        location=[float(row["lat"]), float(row["lon"])],
        icon=folium.DivIcon(
            html=(
                f'<div style="font-weight:900;color:white;font-size:11px;'
                f'text-align:center;line-height:{icon_size}px;width:{icon_size}px;height:{icon_size}px;">{rank}</div>'
            ),
            icon_size=(icon_size, icon_size),
            icon_anchor=(icon_size // 2, icon_size // 2),
        ),
    ).add_to(map_obj)


def _add_detail_metro_lines(layer: folium.FeatureGroup, metro_lines: dict[str, Any]) -> None:
    features = metro_lines.get("features", []) if isinstance(metro_lines, dict) else []
    if not features:
        return

    def line_style(feature: dict[str, Any]) -> dict[str, Any]:
        properties = feature.get("properties", {})
        color = str(properties.get("line_color") or "#4F83A6")
        return {
            "color": color,
            "weight": 3.0,
            "opacity": 0.72,
        }

    folium.GeoJson(
        metro_lines,
        name="TDX TRTC Shape",
        style_function=line_style,
        control=False,
        tooltip=folium.GeoJsonTooltip(
            fields=["line_name_zh", "line_id"],
            aliases=["路線", "Line"],
            labels=True,
            sticky=False,
        ),
    ).add_to(layer)


def _clean_map_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _add_detail_metro_station_marker(
    layer: folium.FeatureGroup,
    lat: float,
    lon: float,
    station_name: str,
    line_ids: str,
    line_names: str,
    distance_meters: float,
) -> None:
    name = _clean_map_text(station_name) or "未命名捷運站"
    line_text = _clean_map_text(line_names) or _clean_map_text(line_ids) or "TRTC"
    safe_name = html.escape(name)
    safe_line = html.escape(line_text)
    folium.CircleMarker(
        location=[lat, lon],
        radius=5.2,
        color="#FFFFFF",
        weight=1.8,
        fill=True,
        fill_color="#4F83A6",
        fill_opacity=0.96,
        opacity=0.98,
        tooltip=f"{safe_name}｜{safe_line}",
        popup=folium.Popup(
            f"""
            <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-width:170px;">
              <div style="font-weight:850;font-size:14px;">{safe_name}</div>
              <div style="color:#65747A;margin-top:3px;">{safe_line}</div>
              <div style="color:#65747A;margin-top:5px;">TDX TRTC 站點｜約 {distance_meters:.0f}m</div>
            </div>
            """,
            max_width=240,
        ),
    ).add_to(layer)


def _add_detail_youbike_marker(
    layer: folium.FeatureGroup,
    lat: float,
    lon: float,
    station_name: str,
    distance_meters: float,
) -> None:
    name = _clean_map_text(station_name) or "未命名 YouBike 站"
    safe_name = html.escape(name)
    folium.CircleMarker(
        location=[lat, lon],
        radius=3.8,
        color="#FFFFFF",
        weight=1.0,
        fill=True,
        fill_color=DETAIL_POI_COLORS["youbike"],
        fill_opacity=0.74,
        opacity=0.86,
        tooltip=safe_name,
        popup=folium.Popup(
            f"""
            <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-width:170px;">
              <div style="font-weight:850;font-size:14px;">{safe_name}</div>
              <div style="color:#65747A;margin-top:5px;">YouBike 靜態站點｜約 {distance_meters:.0f}m</div>
              <div style="color:#65747A;margin-top:5px;">僅靜態站點資料</div>
            </div>
            """,
            max_width=240,
        ),
    ).add_to(layer)


def _add_detail_poi_marker(
    map_obj: folium.Map,
    lat: float,
    lon: float,
    category: str,
    name: str,
    poi_type: str,
    subtitle: str,
) -> None:
    color = DETAIL_POI_COLORS.get(category, "#52646B")
    symbol = DETAIL_POI_SYMBOLS.get(category, "•")
    safe_name = html.escape(name)
    safe_type = html.escape(poi_type)
    safe_subtitle = html.escape(subtitle)
    folium.Marker(
        location=[lat, lon],
        tooltip=f"{safe_name}｜{safe_type}",
        popup=folium.Popup(
            f"""
            <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-width:170px;">
              <div style="font-weight:850;font-size:14px;">{safe_name}</div>
              <div style="color:#65747A;margin-top:3px;">{safe_type}</div>
              <div style="color:#65747A;margin-top:5px;">{safe_subtitle}</div>
            </div>
            """,
            max_width=240,
        ),
        icon=folium.DivIcon(
            html=(
                '<div style="display:flex;align-items:center;gap:5px;white-space:nowrap;">'
                f'<div style="width:24px;height:24px;border-radius:999px;background:{color};'
                'border:2px solid white;box-shadow:0 2px 7px rgba(36,50,56,0.24);'
                'display:flex;align-items:center;justify-content:center;flex:0 0 auto;'
                'color:white;font-size:11px;font-weight:900;line-height:1;">'
                f'{html.escape(symbol)}</div>'
                '<div style="max-width:136px;overflow:hidden;text-overflow:ellipsis;'
                'background:rgba(255,255,255,0.94);border:1px solid #D6DDE0;'
                'border-left-width:4px;border-radius:8px;padding:3px 7px;'
                f'border-left-color:{color};color:#243238;'
                'font-size:12px;font-weight:760;line-height:1.2;'
                'box-shadow:0 2px 8px rgba(36,50,56,0.13);">'
                f'{safe_type}｜{safe_name}</div></div>'
            ),
            icon_size=(178, 32),
            icon_anchor=(12, 16),
        ),
    ).add_to(map_obj)


def _add_workplace_marker(map_obj: folium.Map, center_lat: float, center_lon: float, workplace_name: str) -> None:
    safe_name = html.escape(workplace_name)
    folium.Marker(
        location=[center_lat, center_lon],
        tooltip=f"Workplace anchor: {safe_name}",
        popup=f"<b>Workplace anchor</b><br>{safe_name}",
        icon=folium.DivIcon(
            html=(
                '<div style="font-size:27px;color:#C45B65;text-shadow:0 0 2px #742C34,0 0 5px white;">'
                '★</div>'
                '<div style="margin-left:18px;margin-top:-28px;background:white;border:1px solid #C45B65;'
                'border-radius:8px;padding:3px 7px;color:#742C34;font-weight:700;white-space:nowrap;">'
                f'Workplace anchor<br>{safe_name}</div>'
            ),
            icon_size=(150, 48),
            icon_anchor=(12, 24),
        ),
    ).add_to(map_obj)


def _candidate_popup(row: pd.Series, rank: int | None) -> folium.Popup:
    rank_label = f"#{rank}" if rank is not None else "已評估候選"
    html_body = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-width:210px;">
      <div style="font-weight:800;font-size:15px;margin-bottom:2px;">{html.escape(living_area(row['candidate_name']))}</div>
      <div style="color:#65747A;margin-bottom:8px;">{html.escape(str(row['candidate_name']))}｜{rank_label}</div>
      <div>月租中位數：<b>{money(row['rent'])} NTD</b></div>
      <div>通勤時間：<b>{minutes(row['commute_minutes'])}</b></div>
      <div>轉乘次數：<b>{int(row['transfer_count'])}</b></div>
      <div>相較內湖省租：<b>{money(row['rent_saving_vs_neihu'])} NTD/月</b></div>
    </div>
    """
    return folium.Popup(html_body, max_width=280)


def _overview_popup(row: pd.Series, modes: list[str], role: str) -> folium.Popup:
    mode_text = " / ".join(modes)
    html_body = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-width:220px;">
      <div style="font-weight:800;font-size:15px;margin-bottom:2px;">{html.escape(living_area(row['candidate_name']))}</div>
      <div style="color:#65747A;margin-bottom:8px;">{html.escape(str(row['candidate_name']))}｜{html.escape(role)}</div>
      <div>模式：<b>{html.escape(mode_text)}</b></div>
      <div>月租中位數：<b>{money(row['rent'])} NTD</b></div>
      <div>通勤時間：<b>{minutes(row['commute_minutes'])}</b></div>
    </div>
    """
    return folium.Popup(html_body, max_width=300)


def _modes_for_candidate(rows: pd.DataFrame, candidate_name: str) -> list[str]:
    found = rows[rows["candidate_name"] == candidate_name]["preference_mode"].tolist()
    mode_order = {mode: index for index, mode in enumerate(MODE_ORDER)}
    return sorted(found, key=lambda mode: mode_order[mode])


def _add_city_label(map_obj: folium.Map, lat: float, lon: float, label: str) -> None:
    folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(
            html=(
                '<div style="font-size:16px;font-weight:800;color:#52646B;'
                'text-shadow:0 0 5px white,0 0 7px white;white-space:nowrap;">'
                f"{label}</div>"
            ),
            icon_size=(64, 24),
            icon_anchor=(32, 12),
        ),
    ).add_to(map_obj)


def _add_legend(map_obj: folium.Map, mode_color: str, workplace_name: str) -> None:
    safe_name = html.escape(workplace_name)
    template = Template(
        f"""
        {{% macro html(this, kwargs) %}}
        <div style="
            position: fixed;
            right: 24px;
            bottom: 28px;
            z-index: 9999;
            background: rgba(255,255,255,0.94);
            border: 1px solid #D6DDE0;
            border-radius: 10px;
            padding: 10px 12px;
            color: #243238;
            font-size: 13px;
            box-shadow: 0 1px 4px rgba(36,50,56,0.10);
        ">
          <div style="font-weight:800;margin-bottom:6px;">圖例</div>
          <div><span style="display:inline-block;width:11px;height:11px;border-radius:50%;background:{mode_color};margin-right:6px;"></span>目前模式 Top 3</div>
          <div><span style="display:inline-block;width:18px;height:10px;border-radius:50%;background:{mode_color};opacity:0.30;margin-right:6px;"></span>Top3 約15分鐘核心生活圈（1 km）</div>
          <div><span style="display:inline-block;width:22px;height:12px;border-radius:50%;background:{mode_color};opacity:0.18;margin-right:6px;"></span>Top3 延伸生活圈（2 km）</div>
          <div><span style="display:inline-block;width:20px;border-top:3px solid {mode_color};opacity:0.38;margin-right:6px;"></span>通勤連結示意</div>
          <div><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#AEB8BA;margin-right:7px;"></span>其他已評估候選</div>
          <div><span style="color:#C45B65;font-size:16px;margin-right:4px;">★</span>工作地：{safe_name}</div>
          <div><span style="display:inline-block;width:18px;height:10px;background:#EADCA9;opacity:0.35;margin-right:6px;"></span>行政區租金背景（預設關閉）</div>
        </div>
        {{% endmacro %}}
        """
    )
    macro = MacroElement()
    macro._template = template
    map_obj.get_root().add_child(macro)


def _add_overview_legend(map_obj: folium.Map, workplace_name: str) -> None:
    safe_name = html.escape(workplace_name)
    mode_items = "".join(
        f'<div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{MODE_COLORS[mode]};margin-right:6px;"></span>{mode} Top 1</div>'
        for mode in MODE_ORDER
    )
    template = Template(
        f"""
        {{% macro html(this, kwargs) %}}
        <div style="
            position: fixed;
            right: 24px;
            bottom: 28px;
            z-index: 9999;
            background: rgba(255,255,255,0.94);
            border: 1px solid #D6DDE0;
            border-radius: 10px;
            padding: 10px 12px;
            color: #243238;
            font-size: 13px;
            box-shadow: 0 1px 4px rgba(36,50,56,0.10);
        ">
          <div style="font-weight:800;margin-bottom:6px;">Overview</div>
          {mode_items}
          <div><span style="display:inline-block;width:18px;height:10px;border-radius:50%;background:#78B995;opacity:0.30;margin-right:6px;"></span>Top3 約15分鐘核心生活圈（1 km）</div>
          <div><span style="display:inline-block;width:22px;height:12px;border-radius:50%;background:#78B995;opacity:0.18;margin-right:6px;"></span>Top3 延伸生活圈（2 km）</div>
          <div><span style="display:inline-block;width:20px;border-top:3px solid #78B995;opacity:0.38;margin-right:6px;"></span>通勤連結示意</div>
          <div><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#AEB8BA;margin-right:7px;"></span>Other evaluated candidates</div>
          <div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#A98BC8;border:2px solid #fff;margin-right:6px;"></span>Other Top-3 options</div>
          <div><span style="color:#C45B65;font-size:16px;margin-right:4px;">★</span>工作地：{safe_name}</div>
          <div><span style="display:inline-block;width:18px;height:10px;background:#EADCA9;opacity:0.35;margin-right:6px;"></span>行政區背景由 selector 單選切換</div>
        </div>
        {{% endmacro %}}
        """
    )
    macro = MacroElement()
    macro._template = template
    map_obj.get_root().add_child(macro)


def _add_detail_legend(map_obj: folium.Map, living_area_name: str, has_livability_density: bool) -> None:
    safe_name = html.escape(living_area_name)
    heatmap_legend = (
        '<div><span style="display:inline-block;width:22px;height:11px;border-radius:999px;'
        'background:linear-gradient(90deg,#7CCDB7,#F1D879,#ECA15A,#C45B65);opacity:0.52;'
        'margin-right:6px;"></span>生活機能密度（預設開啟）</div>'
        if has_livability_density
        else '<div style="color:#8A5B34;">生活機能密度：未載入 POI 點位資料</div>'
    )
    template = Template(
        f"""
        {{% macro html(this, kwargs) %}}
        <div style="
            position: fixed;
            right: 24px;
            bottom: 28px;
            z-index: 9999;
            background: rgba(255,255,255,0.94);
            border: 1px solid #D6DDE0;
            border-radius: 10px;
            padding: 10px 12px;
            color: #243238;
            font-size: 13px;
            box-shadow: 0 1px 4px rgba(36,50,56,0.10);
        ">
          <div style="font-weight:800;margin-bottom:6px;">{safe_name}</div>
          {heatmap_legend}
          <div><span style="display:inline-block;width:18px;height:10px;border-radius:50%;background:#78B995;opacity:0.30;margin-right:6px;"></span>約15分鐘核心生活圈（1 km）</div>
          <div><span style="display:inline-block;width:22px;height:12px;border-radius:50%;background:#78B995;opacity:0.18;margin-right:6px;"></span>延伸生活圈（2 km）</div>
          <div><span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:#243238;color:white;font-size:9px;font-weight:900;margin-right:6px;">心</span>生活圈中心</div>
          <div><span style="display:inline-block;width:20px;border-top:3px solid #4F83A6;opacity:0.72;margin-right:6px;"></span>軌道交通（TDX TRTC Shape / 站點）</div>
          <div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#2F9E73;border:1px solid #fff;margin-right:6px;"></span>YouBike 靜態站點（預設關閉）</div>
          <div><span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:#78B995;color:white;font-size:9px;font-weight:900;margin-right:6px;">採</span>超市 / 市場</div>
          <div><span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:#C45B65;color:white;font-size:9px;font-weight:900;margin-right:6px;">醫</span>醫療</div>
          <div><span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:#D39B43;color:white;font-size:9px;font-weight:900;margin-right:6px;">園</span>公園/運動</div>
          <div style="margin-top:6px;color:#65747A;font-size:12px;line-height:1.35;">生活機能密度使用餐飲、採買、休閒與文化 POI；醫療維持獨立圖層。生活機能統計目前仍基於 OSM {POI_STATISTICS_RADIUS_METERS}m 範圍。</div>
        </div>
        {{% endmacro %}}
        """
    )
    macro = MacroElement()
    macro._template = template
    map_obj.get_root().add_child(macro)
