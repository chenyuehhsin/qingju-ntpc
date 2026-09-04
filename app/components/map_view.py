from __future__ import annotations

import html

import folium
import geopandas as gpd
import pandas as pd
from branca.element import MacroElement, Template

from data_loader import MODE_COLORS, MODE_ORDER, living_area, minutes, money

WALKING_LIVING_AREA_RADIUS_METERS = 800
DETAIL_POI_COLORS = {
    "transit": "#4F83A6",
    "shopping": "#78B995",
    "medical": "#C45B65",
    "recreation": "#D39B43",
}
DETAIL_POI_SYMBOLS = {
    "transit": "T",
    "shopping": "S",
    "medical": "M",
    "recreation": "P",
}
SHUANGBEI_BOUNDS = [[24.80, 121.22], [25.32, 121.75]]


def build_overview_map(
    candidates: pd.DataFrame,
    top3: pd.DataFrame,
    destination: dict[str, float | str],
    towns: gpd.GeoDataFrame,
    cities: gpd.GeoDataFrame,
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
    rent_group = folium.FeatureGroup(name="行政區租金背景", show=False).add_to(map_obj)
    other_group = folium.FeatureGroup(name="其他候選", show=True).add_to(map_obj)
    commute_group = folium.FeatureGroup(name="通勤連結", show=True).add_to(map_obj)
    top3_group = folium.FeatureGroup(name="Top3", show=True).add_to(map_obj)
    workplace_group = folium.FeatureGroup(name="Workplace", show=True).add_to(map_obj)
    _add_rent_context_layer(rent_group, towns)

    top1_names = set(top3[top3["rank"] == 1]["candidate_name"])
    top3_names = set(top3["candidate_name"])
    top3_only_names = top3_names - top1_names
    top3_candidates = candidates[candidates["candidate_name"].isin(top3_names)].copy()
    for _, row in top3_candidates.iterrows():
        candidate_rows = top3[top3["candidate_name"] == row["candidate_name"]].sort_values("rank")
        candidate_modes = _modes_for_candidate(top3, row["candidate_name"])
        rank = int(candidate_rows.iloc[0]["rank"])
        color = MODE_COLORS[candidate_modes[0]]
        _add_commute_link(commute_group, row, center_lat, center_lon, color, rank)

    for _, row in candidates.iterrows():
        if row["candidate_name"] in top3_names:
            continue
        _add_candidate_dot(other_group, row, radius=3.2, fill_opacity=0.32, opacity=0.44)

    for _, row in candidates[candidates["candidate_name"].isin(top3_only_names)].iterrows():
        candidate_modes = _modes_for_candidate(top3, row["candidate_name"])
        color = MODE_COLORS[candidate_modes[0]]
        rank = int(top3[top3["candidate_name"] == row["candidate_name"]].sort_values("rank").iloc[0]["rank"])
        _add_overview_top3_halo(top3_group, row, color, rank)
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
        _add_overview_top3_halo(top3_group, row, primary_color, display_rank)
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
    rent_group = folium.FeatureGroup(name="行政區租金背景", show=False).add_to(map_obj)
    other_group = folium.FeatureGroup(name="其他候選", show=True).add_to(map_obj)
    commute_group = folium.FeatureGroup(name="通勤連結", show=True).add_to(map_obj)
    top3_group = folium.FeatureGroup(name="Top3", show=True).add_to(map_obj)
    workplace_group = folium.FeatureGroup(name="Workplace", show=True).add_to(map_obj)
    _add_rent_context_layer(rent_group, towns)

    for _, row in mode_rows.iterrows():
        _add_commute_link(commute_group, row, center_lat, center_lon, color, int(row["rank"]))

    for _, row in candidates.iterrows():
        if row["candidate_name"] in top3_names:
            continue
        _add_candidate_dot(other_group, row, radius=3.5, fill_opacity=0.34, opacity=0.46)

    for _, row in mode_rows.iterrows():
        rank = int(row["rank"])
        radius = 12 if rank == 1 else 8
        fill_opacity = 0.95 if rank == 1 else 0.78
        _add_overview_top3_halo(top3_group, row, color, rank)
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
    _add_detail_basemap(map_obj)
    _fit_detail_bounds(map_obj, lat, lon)
    walking_group = folium.FeatureGroup(name="800m 生活圈", show=True).add_to(map_obj)
    transit_group = folium.FeatureGroup(name="交通", show=True).add_to(map_obj)
    shopping_group = folium.FeatureGroup(name="採買", show=True).add_to(map_obj)
    medical_group = folium.FeatureGroup(name="醫療", show=True).add_to(map_obj)
    recreation_group = folium.FeatureGroup(name="公園/運動", show=True).add_to(map_obj)
    poi_groups = {
        "shopping": shopping_group,
        "medical": medical_group,
        "recreation": recreation_group,
    }
    folium.Circle(
        location=[lat, lon],
        radius=WALKING_LIVING_AREA_RADIUS_METERS,
        color=color,
        weight=2.4,
        opacity=0.88,
        fill=True,
        fill_color=color,
        fill_opacity=0.10,
        tooltip=f"{row['living_area']}｜800m 步行生活圈",
    ).add_to(walking_group)
    _add_detail_poi_marker(
        transit_group,
        lat,
        lon,
        "transit",
        str(row["candidate_name"]),
        "代表交通節點",
        f"{row['living_area']} 的交通錨點",
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
    _add_detail_legend(map_obj, str(row["living_area"]))
    return map_obj


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
    lat_delta = 0.011
    lon_delta = 0.012
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


def _add_detail_basemap(map_obj: folium.Map) -> None:
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="OSM Standard",
        overlay=False,
        control=True,
    ).add_to(map_obj)


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


def _add_overview_top3_halo(layer: folium.FeatureGroup, row: pd.Series, color: str, rank: int) -> None:
    folium.Circle(
        location=[float(row["lat"]), float(row["lon"])],
        radius=WALKING_LIVING_AREA_RADIUS_METERS,
        color=color,
        weight=2.0 if rank == 1 else 1.5,
        opacity=0.46 if rank == 1 else 0.34,
        fill=True,
        fill_color=color,
        fill_opacity=0.13 if rank == 1 else 0.08,
        tooltip=f"Top {rank}｜{living_area(row['candidate_name'])}｜800m",
    ).add_to(layer)


def _add_commute_link(
    layer: folium.FeatureGroup,
    row: pd.Series,
    workplace_lat: float,
    workplace_lon: float,
    color: str,
    rank: int,
) -> None:
    folium.PolyLine(
        locations=[
            [float(row["lat"]), float(row["lon"])],
            [workplace_lat, workplace_lon],
        ],
        color=color,
        weight=3.2 if rank == 1 else 2.2,
        opacity=0.58 if rank == 1 else 0.42,
        dash_array=None if rank == 1 else "6, 8",
        tooltip=f"Top {rank}｜{living_area(row['candidate_name'])} → Workplace｜{minutes(row['commute_minutes'])}",
    ).add_to(layer)


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
                f'<div style="width:24px;height:24px;border-radius:999px;background:{color};'
                'border:2px solid white;box-shadow:0 2px 7px rgba(36,50,56,0.24);'
                'display:flex;align-items:center;justify-content:center;'
                'color:white;font-size:11px;font-weight:900;">'
                f'{symbol}</div>'
            ),
            icon_size=(24, 24),
            icon_anchor=(12, 12),
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
          <div><span style="display:inline-block;width:18px;height:10px;border-radius:50%;background:{mode_color};opacity:0.22;margin-right:6px;"></span>Top3 800m halo</div>
          <div><span style="display:inline-block;width:20px;border-top:3px solid {mode_color};opacity:0.58;margin-right:6px;"></span>通勤連結</div>
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
          <div><span style="display:inline-block;width:18px;height:10px;border-radius:50%;background:#78B995;opacity:0.22;margin-right:6px;"></span>Top3 800m halo</div>
          <div><span style="display:inline-block;width:20px;border-top:3px solid #78B995;opacity:0.58;margin-right:6px;"></span>Commute links</div>
          <div><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#AEB8BA;margin-right:7px;"></span>Other evaluated candidates</div>
          <div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#A98BC8;border:2px solid #fff;margin-right:6px;"></span>Other Top-3 options</div>
          <div><span style="color:#C45B65;font-size:16px;margin-right:4px;">★</span>工作地：{safe_name}</div>
          <div><span style="display:inline-block;width:18px;height:10px;background:#EADCA9;opacity:0.35;margin-right:6px;"></span>District rent context off by default</div>
        </div>
        {{% endmacro %}}
        """
    )
    macro = MacroElement()
    macro._template = template
    map_obj.get_root().add_child(macro)


def _add_detail_legend(map_obj: folium.Map, living_area_name: str) -> None:
    safe_name = html.escape(living_area_name)
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
          <div><span style="display:inline-block;width:18px;height:10px;border-radius:50%;background:#78B995;opacity:0.30;margin-right:6px;"></span>800m 步行生活圈</div>
          <div><span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:#4F83A6;color:white;font-size:9px;font-weight:900;margin-right:6px;">T</span>交通節點</div>
          <div><span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:#78B995;color:white;font-size:9px;font-weight:900;margin-right:6px;">S</span>採買</div>
          <div><span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:#C45B65;color:white;font-size:9px;font-weight:900;margin-right:6px;">M</span>醫療</div>
          <div><span style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;border-radius:50%;background:#D39B43;color:white;font-size:9px;font-weight:900;margin-right:6px;">P</span>公園/運動</div>
        </div>
        {{% endmacro %}}
        """
    )
    macro = MacroElement()
    macro._template = template
    map_obj.get_root().add_child(macro)
