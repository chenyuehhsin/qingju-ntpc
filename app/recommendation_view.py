from __future__ import annotations

import html

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from components.cards import render_recommendation_cards
from components.map_view import build_detail_map, build_recommendation_map
from data_loader import (
    MODE_COLORS,
    life_summary,
    load_representative_pois,
    load_representative_transport_stations,
    minutes,
    money,
)


def render_dashboard_view(
    mode: str,
    candidates: pd.DataFrame,
    recommendations: pd.DataFrame,
    top3: pd.DataFrame,
    destination: dict[str, float | str],
    towns,
    cities,
) -> None:
    mode_rows = top3[top3["preference_mode"] == mode].sort_values("rank").copy()
    selected_candidate = _selected_top3_candidate(mode, mode_rows)
    selected_row = mode_rows[mode_rows["candidate_name"] == selected_candidate].iloc[0]

    left, right = st.columns([0.92, 2.78], gap="medium")
    with left:
        st.markdown("### Top 3 推薦")
        render_recommendation_cards(mode, mode_rows)
        st.markdown("### 查看生活圈")
        selected_candidate = st.segmented_control(
            "選擇 Top 3 生活圈",
            options=mode_rows["candidate_name"].tolist(),
            format_func=lambda candidate_name: _top3_option_label(mode_rows, str(candidate_name)),
            key=f"housing_detail_candidate_{mode}",
            label_visibility="collapsed",
        )
        if selected_candidate is None:
            selected_candidate = str(mode_rows.iloc[0]["candidate_name"])
        selected_row = mode_rows[mode_rows["candidate_name"] == selected_candidate].iloc[0]
    with right:
        st.markdown("### 推薦總覽地圖")
        map_obj = build_recommendation_map(mode, candidates, top3, destination, towns, cities)
        st_folium(map_obj, height=470, use_container_width=True, returned_objects=[])

    _render_detail_section(mode, selected_row, destination, towns, cities)

    _render_mode_summary(mode, mode_rows, str(destination["destination"]))
    with st.expander("查看全部 16 個候選生活圈", expanded=False):
        render_all_candidates_table(mode, candidates, recommendations)


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


def _render_detail_section(
    mode: str,
    selected_row: pd.Series,
    destination: dict[str, float | str],
    towns,
    cities,
) -> None:
    st.markdown("### Detail map｜約15分鐘核心生活圈 + 延伸生活圈")
    st.markdown(
        '<div class="qj-section-note">「15分鐘」為近似探索範圍，實際步行時間依道路與步行速度而異，不代表精準步行 isochrone。生活機能統計目前仍基於 800m 範圍。</div>',
        unsafe_allow_html=True,
    )
    pois = load_representative_pois(str(selected_row["candidate_name"]))
    transport_stations = load_representative_transport_stations(
        str(selected_row["candidate_name"])
    )
    detail_left, detail_right = st.columns([0.96, 2.74], gap="medium")
    with detail_left:
        _render_life_summary_card(mode, selected_row, pois)
    with detail_right:
        detail_map = build_detail_map(
            selected_row,
            pois,
            transport_stations,
            destination,
            towns,
            cities,
            mode,
        )
        st_folium(detail_map, height=520, use_container_width=True, returned_objects=[])


def _render_life_summary_card(mode: str, row: pd.Series, pois: pd.DataFrame) -> None:
    color = MODE_COLORS[mode]
    food = _count(row, "food_count")
    shopping = _count(row, "shopping_count")
    medical = _count(row, "medical_count")
    recreation = _count(row, "recreation_count")
    culture = _count(row, "culture_count")
    poi_note = _representative_poi_note(pois)
    st.markdown(
        f"""
        <div class="qj-life-detail-card" style="border-left-color: {color};">
            <div class="qj-life-detail-eyebrow">Selected Top {int(row['rank'])}</div>
            <div class="qj-life-detail-title">{html.escape(str(row['living_area']))}</div>
            <div class="qj-station">{html.escape(str(row['candidate_name']))}｜{html.escape(str(row['district']))}</div>
            <div class="qj-life-metric-grid">
                <div><span>月租</span><b>{money(row['rent'])}</b><small>NTD/month</small></div>
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


def _representative_poi_note(pois: pd.DataFrame) -> str:
    if pois.empty:
        return "代表 POI：目前沒有可用的 raw OSM cache 點位，只顯示交通節點；生活機能統計仍基於 800m 範圍。"
    labels = pois["category_label"].dropna().astype(str).drop_duplicates().tolist()
    return f"代表 POI：每類最多顯示 2 個；目前顯示 {'、'.join(labels)}。生活機能統計仍基於 800m 範圍。"
