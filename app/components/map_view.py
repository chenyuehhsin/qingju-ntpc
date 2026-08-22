from __future__ import annotations

import html

import folium
import geopandas as gpd
import pandas as pd
from branca.element import MacroElement, Template

from data_loader import MODE_COLORS, MODE_ORDER, living_area, minutes, money

LIVING_AREA_RADIUS_METERS = 3000


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
    _add_boundary_layers(map_obj, towns, cities)

    top1_names = set(top3[top3["rank"] == 1]["candidate_name"])
    top3_names = set(top3["candidate_name"])
    top3_only_names = top3_names - top1_names

    for _, row in candidates.iterrows():
        candidate_name = row["candidate_name"]
        if candidate_name in top1_names:
            candidate_modes = _modes_for_candidate(top3[top3["rank"] == 1], candidate_name)
            primary_color = MODE_COLORS[candidate_modes[0]]
            _add_living_area_circle(map_obj, row, primary_color, fill_opacity=0.24, weight=2.2, opacity=0.74)
            if len(candidate_modes) > 1:
                _add_living_area_circle(map_obj, row, MODE_COLORS[candidate_modes[1]], fill_opacity=0.06, weight=3.0, opacity=0.82)
        elif candidate_name in top3_only_names:
            candidate_modes = _modes_for_candidate(top3, candidate_name)
            _add_living_area_circle(map_obj, row, MODE_COLORS[candidate_modes[0]], fill_opacity=0.16, weight=1.7, opacity=0.58)
        else:
            _add_living_area_circle(map_obj, row, "#AEB8BA", fill_opacity=0.045, weight=0.9, opacity=0.28)

    for _, row in candidates.iterrows():
        if row["candidate_name"] in top3_names:
            continue
        folium.CircleMarker(
            location=[float(row["lat"]), float(row["lon"])],
            radius=4.2,
            color="#AEB8BA",
            weight=1,
            fill=True,
            fill_color="#AEB8BA",
            fill_opacity=0.56,
            opacity=0.72,
            tooltip=f"{living_area(row['candidate_name'])}｜已評估候選",
            popup=_candidate_popup(row, rank=None),
        ).add_to(map_obj)

    for _, row in candidates[candidates["candidate_name"].isin(top3_only_names)].iterrows():
        candidate_modes = _modes_for_candidate(top3, row["candidate_name"])
        color = MODE_COLORS[candidate_modes[0]]
        folium.CircleMarker(
            location=[float(row["lat"]), float(row["lon"])],
            radius=8,
            color="#FFFFFF",
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.58,
            opacity=0.92,
            tooltip=f"{living_area(row['candidate_name'])}｜Other Top-3 option",
            popup=_overview_popup(row, candidate_modes, "Other Top-3 option"),
        ).add_to(map_obj)

    for _, row in candidates[candidates["candidate_name"].isin(top1_names)].iterrows():
        candidate_modes = _modes_for_candidate(top3[top3["rank"] == 1], row["candidate_name"])
        primary_color = MODE_COLORS[candidate_modes[0]]
        folium.CircleMarker(
            location=[float(row["lat"]), float(row["lon"])],
            radius=13,
            color="#FFFFFF",
            weight=3,
            fill=True,
            fill_color=primary_color,
            fill_opacity=0.96,
            opacity=1,
            tooltip=f"{' / '.join(candidate_modes)}｜{living_area(row['candidate_name'])}",
            popup=_overview_popup(row, candidate_modes, "Recommended"),
        ).add_to(map_obj)
        if len(candidate_modes) > 1:
            for index, mode in enumerate(candidate_modes[1:], start=1):
                folium.CircleMarker(
                    location=[float(row["lat"]), float(row["lon"])],
                    radius=13 + index * 4,
                    color=MODE_COLORS[mode],
                    weight=3,
                    fill=False,
                    opacity=0.95,
                    tooltip=f"{living_area(row['candidate_name'])} also recommended by {mode}",
                ).add_to(map_obj)
        folium.Marker(
            location=[float(row["lat"]), float(row["lon"])],
            icon=folium.DivIcon(
                html=(
                    '<div style="font-weight:800;color:white;font-size:11px;'
                    'text-align:center;line-height:26px;width:26px;height:26px;">1</div>'
                ),
                icon_size=(26, 26),
                icon_anchor=(13, 13),
            ),
        ).add_to(map_obj)

    _add_workplace_marker(map_obj, center_lat, center_lon)
    _add_city_label(map_obj, 25.095, 121.405, "新北市")
    _add_city_label(map_obj, 25.045, 121.555, "臺北市")
    _add_overview_legend(map_obj)
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
    _fit_candidate_bounds(map_obj, candidates, center_lat, center_lon)
    _add_boundary_layers(map_obj, towns, cities)

    for _, row in candidates.iterrows():
        if row["candidate_name"] in top3_names:
            rank = int(mode_rows[mode_rows["candidate_name"] == row["candidate_name"]].iloc[0]["rank"])
            _add_living_area_circle(
                map_obj,
                row,
                color,
                fill_opacity=0.28 if rank == 1 else 0.18,
                weight=2.4 if rank == 1 else 1.7,
                opacity=0.78 if rank == 1 else 0.58,
            )
        else:
            _add_living_area_circle(map_obj, row, "#AEB8BA", fill_opacity=0.04, weight=0.9, opacity=0.24)

    for _, row in candidates.iterrows():
        if row["candidate_name"] in top3_names:
            continue
        folium.CircleMarker(
            location=[float(row["lat"]), float(row["lon"])],
            radius=4.6,
            color="#AEB8BA",
            weight=1,
            fill=True,
            fill_color="#AEB8BA",
            fill_opacity=0.62,
            opacity=0.78,
            tooltip=f"{living_area(row['candidate_name'])}｜已評估候選",
            popup=_candidate_popup(row, rank=None),
        ).add_to(map_obj)

    for _, row in mode_rows.iterrows():
        rank = int(row["rank"])
        radius = 12 if rank == 1 else 8
        fill_opacity = 0.95 if rank == 1 else 0.78
        folium.CircleMarker(
            location=[float(row["lat"]), float(row["lon"])],
            radius=radius,
            color="#FFFFFF",
            weight=3 if rank == 1 else 2,
            fill=True,
            fill_color=color,
            fill_opacity=fill_opacity,
            opacity=1,
            tooltip=f"#{rank} {row['living_area']}",
            popup=_candidate_popup(row, rank=rank),
        ).add_to(map_obj)
        folium.Marker(
            location=[float(row["lat"]), float(row["lon"])],
            icon=folium.DivIcon(
                html=(
                    f'<div style="font-weight:800;color:white;font-size:11px;'
                    f'text-align:center;line-height:24px;width:24px;height:24px;">{rank}</div>'
                ),
                icon_size=(24, 24),
                icon_anchor=(12, 12),
            ),
        ).add_to(map_obj)

    _add_workplace_marker(map_obj, center_lat, center_lon)

    _add_city_label(map_obj, 25.095, 121.405, "新北市")
    _add_city_label(map_obj, 25.045, 121.555, "臺北市")
    _add_legend(map_obj, color)
    return map_obj


def _fit_candidate_bounds(map_obj: folium.Map, candidates: pd.DataFrame, center_lat: float, center_lon: float) -> None:
    bounds = [
        [min(candidates["lat"].min(), center_lat) - 0.055, min(candidates["lon"].min(), center_lon) - 0.065],
        [max(candidates["lat"].max(), center_lat) + 0.055, max(candidates["lon"].max(), center_lon) + 0.065],
    ]
    map_obj.fit_bounds(bounds)


def _add_boundary_layers(map_obj: folium.Map, towns: gpd.GeoDataFrame, cities: gpd.GeoDataFrame) -> None:
    folium.GeoJson(
        towns,
        name="district boundary",
        style_function=lambda _: {
            "fillColor": "#F4F6F5",
            "color": "#DDE3E5",
            "weight": 0.8,
            "fillOpacity": 0.42,
        },
        tooltip=None,
    ).add_to(map_obj)

    def city_style(feature: dict) -> dict:
        city = feature["properties"].get("COUNTYNAME")
        return {
            "fillColor": "#EDF3F2",
            "color": "#7B8B74" if city == "新北市" else "#6B7F8A",
            "weight": 3.0,
            "fillOpacity": 0.08,
        }

    folium.GeoJson(
        cities,
        name="city boundary",
        style_function=city_style,
        tooltip=folium.GeoJsonTooltip(fields=["COUNTYNAME"]),
    ).add_to(map_obj)


def _add_living_area_circle(
    map_obj: folium.Map,
    row: pd.Series,
    color: str,
    fill_opacity: float,
    weight: float,
    opacity: float,
) -> None:
    folium.Circle(
        location=[float(row["lat"]), float(row["lon"])],
        radius=LIVING_AREA_RADIUS_METERS,
        color=color,
        weight=weight,
        opacity=opacity,
        fill=True,
        fill_color=color,
        fill_opacity=fill_opacity,
        tooltip=f"{living_area(row['candidate_name'])}｜機車10分鐘生活圈（約3km）",
    ).add_to(map_obj)


def _add_workplace_marker(map_obj: folium.Map, center_lat: float, center_lon: float) -> None:
    folium.Marker(
        location=[center_lat, center_lon],
        tooltip="Workplace anchor: 港墘站",
        popup="<b>Workplace anchor</b><br>港墘站",
        icon=folium.DivIcon(
            html=(
                '<div style="font-size:27px;color:#C45B65;text-shadow:0 0 2px #742C34,0 0 5px white;">'
                '★</div>'
                '<div style="margin-left:18px;margin-top:-28px;background:white;border:1px solid #C45B65;'
                'border-radius:8px;padding:3px 7px;color:#742C34;font-weight:700;white-space:nowrap;">'
                'Workplace anchor<br>港墘站</div>'
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
      <div>livability_index：<b>{float(row['livability_index']):.3f}</b></div>
      <div style="color:#65747A;margin-top:6px;">生活圈範圍：機車10分鐘內可達，約 3km 視覺半徑</div>
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
      <div>livability_index：<b>{float(row['livability_index']):.3f}</b></div>
      <div style="color:#65747A;margin-top:6px;">生活圈範圍：機車10分鐘內可達，約 3km 視覺半徑</div>
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


def _add_legend(map_obj: folium.Map, mode_color: str) -> None:
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
          <div><span style="display:inline-block;width:18px;height:10px;border-radius:50%;background:{mode_color};opacity:0.34;margin-right:6px;"></span>機車10分鐘生活圈</div>
          <div><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#AEB8BA;margin-right:7px;"></span>其他已評估候選</div>
          <div><span style="color:#C45B65;font-size:16px;margin-right:4px;">★</span>工作地：港墘站</div>
          <div><span style="display:inline-block;width:18px;border-top:3px solid #7B8B74;margin-right:6px;"></span>新北市 / 臺北市外框</div>
        </div>
        {{% endmacro %}}
        """
    )
    macro = MacroElement()
    macro._template = template
    map_obj.get_root().add_child(macro)


def _add_overview_legend(map_obj: folium.Map) -> None:
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
          <div><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#AEB8BA;margin-right:7px;"></span>Other evaluated candidates</div>
          <div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#A98BC8;border:2px solid #fff;margin-right:6px;"></span>Other Top-3 options</div>
          <div><span style="display:inline-block;width:18px;height:10px;border-radius:50%;background:#78B995;opacity:0.34;margin-right:6px;"></span>10-min scooter living area</div>
          <div><span style="color:#C45B65;font-size:16px;margin-right:4px;">★</span>Workplace anchor</div>
        </div>
        {{% endmacro %}}
        """
    )
    macro = MacroElement()
    macro._template = template
    map_obj.get_root().add_child(macro)
