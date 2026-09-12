from __future__ import annotations

import html
from collections.abc import Callable

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from components.cards import render_recommendation_cards
from components.map_view import build_detail_map, build_recommendation_map
from data_loader import (
    MODE_COLORS,
    life_summary,
    load_detail_metro_lines,
    load_detail_metro_stations,
    load_detail_youbike_stations,
    load_district_analysis_table,
    load_livability_density_pois,
    load_representative_pois,
    minutes,
    money,
)

HOUSING_PAGE_OVERVIEW = "overview"
HOUSING_PAGE_DETAIL = "detail"

# TODO: move these editorial hints to data/config/housing/lifestyle_area_profiles.json.
LIFESTYLE_AREA_PROFILE_HINTS = {
    "三峽北大特區": "預算與較長通勤取捨的使用者",
    "三重站": "重視雙北通勤連結的使用者",
    "五股區公所": "優先考量租金節省的使用者",
    "土城站": "尋找租金與通勤平衡的使用者",
    "大坪林站": "重視通勤效率與生活機能的使用者",
    "新莊站": "重視大眾運輸與日常採買的使用者",
    "景安站": "重視跨區通勤選擇的使用者",
    "板橋站": "重視交通整合與生活機能的使用者",
    "林口站": "可接受較長通勤以換取不同租金取向的使用者",
    "樹林車站": "優先考量租金節省與在地生活機能的使用者",
    "汐止車站": "重視通勤路徑與租金取捨的使用者",
    "泰山站": "尋找租金與通勤折衷的使用者",
    "淡水站": "可接受較長通勤、優先考量租金的使用者",
    "蘆洲站": "重視生活機能與大眾運輸的使用者",
    "頂溪站": "重視跨區通勤與生活機能的使用者",
    "鶯歌車站": "優先考量租金節省的使用者",
}


def render_dashboard_view(
    mode: str,
    candidates: pd.DataFrame,
    recommendations: pd.DataFrame,
    top3: pd.DataFrame,
    destination: dict[str, float | str],
    towns,
    cities,
    render_controls: Callable[[], None],
) -> None:
    mode_rows = top3[top3["preference_mode"] == mode].sort_values("rank").copy()
    selected_candidate = _selected_top3_candidate(mode, mode_rows)
    selected_row = mode_rows[mode_rows["candidate_name"] == selected_candidate].iloc[0]
    page_key = _housing_page_key(mode)
    if st.session_state.get(page_key) not in {HOUSING_PAGE_OVERVIEW, HOUSING_PAGE_DETAIL}:
        st.session_state[page_key] = HOUSING_PAGE_OVERVIEW

    if st.session_state[page_key] == HOUSING_PAGE_DETAIL:
        _render_living_area_detail_page(mode, selected_row, destination, towns, cities)
        return

    _render_single_mode_overview_page(
        mode,
        candidates,
        top3,
        mode_rows,
        selected_row,
        destination,
        towns,
        cities,
        render_controls,
    )


def _render_single_mode_overview_page(
    mode: str,
    candidates: pd.DataFrame,
    top3: pd.DataFrame,
    mode_rows: pd.DataFrame,
    selected_row: pd.Series,
    destination: dict[str, float | str],
    towns,
    cities,
    render_controls: Callable[[], None],
) -> None:
    left, middle, right = st.columns([24, 30, 46], gap="medium")
    with left:
        render_controls()
        _render_market_overview(candidates, destination)
    with middle:
        st.markdown('<div class="qj-column-heading"><h3>推薦生活圈 Top 3</h3></div>', unsafe_allow_html=True)
        render_recommendation_cards(
            mode,
            mode_rows,
            selected_candidate=str(selected_row["candidate_name"]),
            on_select=lambda candidate_name: _select_living_area(mode, candidate_name),
        )
    with right:
        map_title, map_cta = st.columns([0.57, 0.43], gap="small")
        with map_title:
            st.markdown('<div class="qj-column-heading"><h3>生活圈分布地圖</h3></div>', unsafe_allow_html=True)
        with map_cta:
            st.markdown(
                """
                <style>
                div[data-testid="stButton"] button[kind="primary"],
                div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
                    background: #FFE8A3 !important;
                    border-color: #F6C64A !important;
                    color: #17324D !important;
                }
                div[data-testid="stButton"] button[kind="primary"]:hover,
                div[data-testid="stButton"] button[data-testid="stBaseButton-primary"]:hover {
                    background: #FFD96B !important;
                    border-color: #F6C64A !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.button(
                "🌱 查看生活圈詳情",
                key=f"housing_open_detail_{mode}",
                use_container_width=True,
                type="primary",
                on_click=_open_living_area_detail,
                args=(mode,),
            )
        map_obj = build_recommendation_map(
            mode,
            candidates,
            top3,
            destination,
            towns,
            cities,
        )
        _enable_rent_context_layer(map_obj)
        _highlight_selected_candidate(map_obj, selected_row, mode)
        st_folium(
            map_obj,
            height=550,
            use_container_width=True,
            returned_objects=[],
            key="housing_recommendation_map",
        )
        _render_lifestyle_insight_card(selected_row)


def _render_living_area_detail_page(
    mode: str,
    selected_row: pd.Series,
    destination: dict[str, float | str],
    towns,
    cities,
) -> None:
    st.markdown(
        f"青年安居推薦 &gt; {html.escape(mode)} &gt; {html.escape(str(selected_row['living_area']))}"
    )

    candidate_name = str(selected_row["candidate_name"])
    pois = load_representative_pois(candidate_name)
    livability_density_pois = load_livability_density_pois(candidate_name)
    metro_lines = load_detail_metro_lines(candidate_name)
    metro_stations = load_detail_metro_stations(candidate_name)
    youbike_stations = load_detail_youbike_stations(candidate_name)

    left, middle, right = st.columns([22, 52, 26], gap="medium")
    with left:
        st.markdown("### 我的條件")
        st.markdown(f"**工作地點**：{html.escape(str(destination['destination']))}")
        st.markdown("**通勤方式**：大眾運輸")
        st.markdown("**房型**：獨立套房")
        st.markdown(f"**推薦偏好**：{html.escape(mode)}")
        _render_living_area_insights(selected_row, pois, destination)
    with middle:
        st.markdown("### 生活圈細節地圖")
        detail_map = build_detail_map(
            selected_row,
            pois,
            livability_density_pois,
            metro_lines,
            metro_stations,
            youbike_stations,
            destination,
            towns,
            cities,
            mode,
        )
        _prefer_street_basemap(detail_map)
        st_folium(
            detail_map,
            height=620,
            use_container_width=True,
            returned_objects=[],
            key="housing_detail_map",
        )
    with right:
        st.markdown("### 目前選擇的生活圈摘要")
        _render_life_summary_card(mode, selected_row, pois)
        st.button(
            "返回生活圈列表",
            key=f"housing_return_to_overview_{mode}",
            use_container_width=True,
            on_click=_return_to_living_area_list,
            args=(mode,),
        )


def _highlight_selected_candidate(map_obj, row: pd.Series, mode: str) -> None:
    color = MODE_COLORS[mode]
    folium.CircleMarker(
        location=[float(row["lat"]), float(row["lon"])],
        radius=20,
        color=color,
        weight=3.5,
        fill=False,
        opacity=0.98,
        tooltip=f"目前選擇｜{row['living_area']}",
    ).add_to(map_obj)
    folium.Marker(
        location=[float(row["lat"]), float(row["lon"])],
        icon=folium.DivIcon(
            html=(
                '<div style="background:#0F9F7A;color:#FFFFFF;border-radius:999px;padding:2px 6px;'
                'font-size:11px;font-weight:800;white-space:nowrap;box-shadow:0 1px 3px rgba(15,159,122,0.35);">'
                '目前選擇</div>'
            ),
            icon_size=(58, 20),
            icon_anchor=(29, 28),
        ),
    ).add_to(map_obj)


def _enable_rent_context_layer(map_obj) -> None:
    for layer in map_obj._children.values():
        if getattr(layer, "layer_name", None) == "行政區租金背景":
            layer.show = True


def _housing_page_key(mode: str) -> str:
    return f"housing_page_state_{mode}"


def _select_living_area(mode: str, candidate_name: str) -> None:
    st.session_state[f"housing_detail_candidate_{mode}"] = candidate_name


def _open_living_area_detail(mode: str) -> None:
    st.session_state[_housing_page_key(mode)] = HOUSING_PAGE_DETAIL


def _return_to_living_area_list(mode: str) -> None:
    st.session_state[_housing_page_key(mode)] = HOUSING_PAGE_OVERVIEW


def _render_market_overview(candidates: pd.DataFrame, destination: dict[str, float | str]) -> None:
    rents = pd.to_numeric(candidates["rent"], errors="coerce").dropna()
    st.markdown("### 新北租屋市場概況")
    if not rents.empty:
        st.markdown(f"**候選生活圈租金範圍**：{money(rents.min())}–{money(rents.max())} NTD/月")
    st.markdown(f"**目前工作地參考**：{html.escape(str(destination['destination']))}")
    st.caption("租金採 MOI 2026-03 行政區獨立套房 benchmark，非即時房源。通勤為 TDX MaaS 平日 08:00 情境。")


def _render_lifestyle_insight_card(row: pd.Series) -> None:
    youth_share = _district_youth_share(row)
    top_categories = _top_livability_categories(row)
    scenario = LIFESTYLE_AREA_PROFILE_HINTS.get(
        str(row["candidate_name"]),
        "重視租金、通勤與生活機能取捨的使用者",
    )
    with st.container(border=True):
        st.markdown("#### 生活圈特色")
        st.markdown(
            f"- **租金與通勤取向**：資料顯示，月租中位數約 {money(row['rent'])} NTD，通勤約 {minutes(row['commute_minutes'])}。"
        )
        st.markdown(
            f"- **周邊生活機能**：目前樣本中的生活機能指數為 {float(row['livability_index']):.3f}；"
            f"POI 類別以 {top_categories} 為主。"
        )
        st.markdown(f"- **適合情境**：適合偏好 {scenario}；行政區青年人口占比為 {youth_share}。")
        st.caption("租金：MOI 2026-03；生活機能：OSM 800m 範圍的 proxy。")


def _top_livability_categories(row: pd.Series) -> str:
    categories = [
        ("餐飲", _count(row, "food_count")),
        ("採買", _count(row, "shopping_count")),
        ("醫療", _count(row, "medical_count")),
        ("休閒", _count(row, "recreation_count")),
        ("文化", _count(row, "culture_count")),
    ]
    valid_categories = [(label, int(count)) for label, count in categories if isinstance(count, int)]
    if not valid_categories:
        return "可用 OSM 類別"
    return "、".join(label for label, _ in sorted(valid_categories, key=lambda item: item[1], reverse=True)[:2])


def _district_youth_share(row: pd.Series) -> str:
    district_analysis = load_district_analysis_table()
    matches = district_analysis[
        (district_analysis["city"] == "新北市") & (district_analysis["district"] == str(row["district"]))
    ]
    if matches.empty:
        return "unresolved"
    return str(matches.iloc[0].get("youth_population_share_display", "unresolved"))


def _render_living_area_insights(
    row: pd.Series,
    pois: pd.DataFrame,
    destination: dict[str, float | str],
) -> None:
    st.markdown("### 生活圈特色")
    st.write(life_summary(row))
    st.markdown("### 交通優勢")
    st.write(f"至 {destination['destination']} 約 {minutes(row['commute_minutes'])}；轉乘 {int(row['transfer_count'])} 次。")
    st.markdown("### 周邊機能")
    st.write(
        f"800m OSM 統計：餐飲 {_count(row, 'food_count')}、採買 {_count(row, 'shopping_count')}、"
        f"醫療 {_count(row, 'medical_count')}、休閒 {_count(row, 'recreation_count')}、文化 {_count(row, 'culture_count')}。"
    )
    st.caption(_representative_poi_note(pois))
    st.markdown("### 資料依據摘要")
    st.caption("租金：MOI 2026-03；通勤：TDX MaaS 平日 08:00 情境；生活機能：OSM 2026-08-22 snapshot；青年人口：RIS 2026-07。")


def render_all_candidates_table(mode: str, candidates: pd.DataFrame, recommendations: pd.DataFrame) -> None:
    st.markdown("### 全部候選生活圈比較")
    display = build_all_candidates_table(mode, candidates, recommendations)

    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        height=420,
        column_config={
            "candidate_name": st.column_config.TextColumn("candidate_name", width="medium"),
            "district": st.column_config.TextColumn("district", width="small"),
            "official_median_rent": st.column_config.TextColumn("official_median_rent", width="medium"),
            "commute_minutes": st.column_config.TextColumn("commute_minutes", width="small"),
            "transfer_count": st.column_config.NumberColumn("transfer_count", width="small"),
            "rent_saving_vs_neihu": st.column_config.TextColumn("rent_saving_vs_neihu", width="medium"),
            "livability_index": st.column_config.TextColumn("livability_index", width="small"),
            "mode_rank": st.column_config.TextColumn(f"{mode} rank", width="small"),
        },
    )


def build_all_candidates_table(mode: str, candidates: pd.DataFrame, recommendations: pd.DataFrame) -> pd.DataFrame:
    mode_preferences = recommendations[
        [
            "preference_mode",
            "candidate_name",
            "rank",
            "preference_score",
            "preference_cost",
        ]
    ][recommendations["preference_mode"] == mode].copy()

    table = candidates[
        [
            "candidate_name",
            "district",
            "official_median_rent",
            "commute_minutes",
            "transfer_count",
            "rent_saving_vs_neihu",
            "livability_index",
        ]
    ].merge(
        mode_preferences.drop(columns=["preference_mode"]),
        on="candidate_name",
        how="left",
        validate="one_to_one",
    )
    table = table.sort_values(
        by=["rank", "commute_minutes", "official_median_rent"],
        ascending=[True, True, True],
        na_position="last",
    ).copy()
    table["mode_rank"] = table["rank"].map(_rank_label)
    table["preference_score"] = table["preference_score"].map(lambda value: "" if pd.isna(value) else f"{float(value):.3f}")
    table["preference_cost"] = table["preference_cost"].map(lambda value: "" if pd.isna(value) else f"{float(value):.3f}")

    display = table[
        [
            "candidate_name",
            "district",
            "official_median_rent",
            "commute_minutes",
            "transfer_count",
            "rent_saving_vs_neihu",
            "livability_index",
            "mode_rank",
        ]
    ].copy()
    display["official_median_rent"] = display["official_median_rent"].map(lambda value: f"{money(value)} NTD")
    display["commute_minutes"] = display["commute_minutes"].map(minutes)
    display["rent_saving_vs_neihu"] = display["rent_saving_vs_neihu"].map(lambda value: f"{money(value)} NTD")
    display["livability_index"] = display["livability_index"].map(lambda value: f"{float(value):.3f}")
    return display


def _rank_label(value: float | int) -> str:
    if pd.isna(value):
        return ""
    rank = int(value)
    if rank <= 3:
        return f"Top {rank}"
    return f"#{rank}"


def _render_mode_summary(mode: str, mode_rows: pd.DataFrame, workplace_name: str) -> None:
    top1 = mode_rows.iloc[0]
    color = MODE_COLORS[mode]
    st.markdown(
        f"""
        <div class="qj-summary-strip" style="border-left-color: {color};">
            <b>{mode} Top 1：</b>{top1['living_area']}，月租約 {money(top1['rent'])} 元，
            到{workplace_name}約 {minutes(top1['commute_minutes'])}，
            相較內湖租金 benchmark 每月約省 {money(top1['rent_saving_vs_neihu'])} 元。
        </div>
        """,
        unsafe_allow_html=True,
    )


def _selected_top3_candidate(mode: str, mode_rows: pd.DataFrame) -> str:
    key = f"housing_detail_candidate_{mode}"
    candidate_names = mode_rows["candidate_name"].astype(str).tolist()
    if st.session_state.get(key) not in candidate_names:
        st.session_state[key] = candidate_names[0]
    return str(st.session_state[key])


def _top3_option_label(mode_rows: pd.DataFrame, candidate_name: str) -> str:
    row = mode_rows[mode_rows["candidate_name"] == candidate_name].iloc[0]
    return f"Top {int(row['rank'])} {row['living_area']}"


def _prefer_street_basemap(map_obj) -> None:
    for layer in map_obj._children.values():
        if getattr(layer, "layer_name", None) == "街道地圖":
            layer.show = True
        elif getattr(layer, "layer_name", None) == "極簡生活圈底圖":
            layer.show = False


def _render_life_summary_card(mode: str, row: pd.Series, pois: pd.DataFrame) -> None:
    color = MODE_COLORS[mode]
    food = _count(row, "food_count")
    shopping = _count(row, "shopping_count")
    medical = _count(row, "medical_count")
    recreation = _count(row, "recreation_count")
    culture = _count(row, "culture_count")
    poi_note = _representative_poi_note(pois)
    district_context = _district_context_summary(row)
    st.markdown(
        f"""
        <div class="qj-life-detail-card" style="border-left-color: {color};">
            <div class="qj-life-detail-eyebrow">Selected Top {int(row['rank'])}</div>
            <div class="qj-life-detail-title">{html.escape(str(row['living_area']))}</div>
            <div class="qj-station">{html.escape(str(row['candidate_name']))}｜{html.escape(str(row['district']))}</div>
            <div class="qj-life-poi-note">{html.escape(district_context)}</div>
            <div class="qj-life-metric-grid">
                <div><span>月租中位數</span><b>{money(row['rent'])}</b><small>MOI 2026-03</small></div>
                <div><span>通勤</span><b>{minutes(row['commute_minutes'])}</b><small>public transit</small></div>
                <div><span>food</span><b>{food}</b><small>OSM 800m 統計</small></div>
                <div><span>shopping</span><b>{shopping}</b><small>OSM 800m 統計</small></div>
                <div><span>medical</span><b>{medical}</b><small>OSM 800m 統計</small></div>
                <div><span>recreation</span><b>{recreation}</b><small>OSM 800m 統計</small></div>
                <div><span>culture</span><b>{culture}</b><small>OSM 800m 統計</small></div>
            </div>
            <div class="qj-life-summary">{html.escape(life_summary(row))}</div>
            <div class="qj-life-poi-note">{html.escape(poi_note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _count(row: pd.Series, column: str) -> int | str:
    if column not in row.index or pd.isna(row[column]):
        return "NA"
    return int(row[column])


def _district_context_summary(row: pd.Series) -> str:
    district = str(row["district"])
    district_analysis = load_district_analysis_table()
    matches = district_analysis[(district_analysis["city"] == "新北市") & (district_analysis["district"] == district)]
    if matches.empty:
        youth_population = "unresolved"
        youth_share = "unresolved"
        total_population = "unresolved"
        source_period = "unresolved"
        precision = "unresolved"
        rent = f"{money(row['rent'])} NTD/month"
    else:
        context = matches.iloc[0]
        youth_population = str(context.get("youth_population_18_35_display", "unresolved"))
        youth_share = str(context.get("youth_population_share_display", "unresolved"))
        total_population = str(context.get("district_total_population_display", "unresolved"))
        source_period = str(context.get("youth_population_source_period_display", "unresolved"))
        precision = str(context.get("youth_population_precision_display", "unresolved"))
        rent = str(context.get("official_median_rent_display", "unresolved"))
    return (
        f"所在行政區背景：{row['living_area']} → {district}｜"
        f"18–35 青年人口數 {youth_population}｜青年占比 {youth_share}｜行政區總人口 {total_population}｜"
        f"資料期別 {source_period}｜資料精度 {precision}｜行政區租金 {rent}。"
        "行政區人口不可解讀為 1km / 2km 生活圈人口。"
    )


def _representative_poi_note(pois: pd.DataFrame) -> str:
    if pois.empty:
        return "代表 POI：目前沒有可用的 raw OSM cache 點位，只顯示交通節點；生活機能統計仍基於 800m 範圍。"
    labels = pois["category_label"].dropna().astype(str).drop_duplicates().tolist()
    return f"代表 POI：每類最多顯示 2 個；目前顯示 {'、'.join(labels)}。生活機能統計仍基於 800m 範圍。"
