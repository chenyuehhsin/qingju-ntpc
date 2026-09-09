from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from components.map_view import build_overview_map
from data_loader import (
    DISTRICT_ANALYSIS_LAYER_OPTIONS,
    DISTRICT_ANALYSIS_LAYER_RENT,
    DISTRICT_ANALYSIS_LAYER_YOUTH_COUNT,
    DISTRICT_ANALYSIS_LAYER_YOUTH_SHARE,
    MODE_COLORS,
    MODE_COPY,
    MODE_ORDER,
    minutes,
    money,
)


def render_overview(
    candidates: pd.DataFrame,
    top3: pd.DataFrame,
    destination: dict[str, float | str],
    towns,
    cities,
) -> None:
    top1 = _top1_by_mode(top3)

    st.markdown(
        """
        <div class="qj-overview-section-head">
            <div class="qj-section-eyebrow">Recommendation snapshot</div>
            <div class="qj-section-title">比較四種模式</div>
            <div class="qj-section-copy">比較不同偏好下，各自推薦的 Top 1 生活圈。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_summary_cards(top1)

    with st.container(border=True):
        map_head, map_selector = st.columns([1.08, 1.32], gap="medium")
        with map_head:
            st.markdown(
                """
                <div class="qj-overview-map-head">
                    <div class="qj-section-eyebrow">Explore the context</div>
                    <div class="qj-section-title">推薦總覽地圖</div>
                    <div class="qj-section-copy">查看工作地、推薦生活圈與行政區背景資料的相對位置。</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with map_selector:
            analysis_layer = st.segmented_control(
                "行政區背景",
                options=DISTRICT_ANALYSIS_LAYER_OPTIONS,
                default=DISTRICT_ANALYSIS_LAYER_RENT,
                key="overview_district_analysis_layer",
            )
        if analysis_layer is None:
            analysis_layer = DISTRICT_ANALYSIS_LAYER_RENT
        _render_analysis_layer_note(str(analysis_layer), towns)
        st.markdown(
            """
            <div class="qj-map-provenance">
                <b>行政區背景資料來源與期別</b>
                <span>租金：MOI 2026-03</span>
                <span>青年人口：RIS 2026-07・Exact 18–35</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        overview_map = build_overview_map(candidates, top3, destination, towns, cities, str(analysis_layer))
        st_folium(
            overview_map,
            height=560,
            use_container_width=True,
            returned_objects=[],
            key="housing_overview_map",
        )

    _render_comparison_bar(top1)
    st.markdown("---")


def render_comparison_dashboard(
    candidates: pd.DataFrame,
    top3: pd.DataFrame,
    destination: dict[str, float | str],
    towns,
    cities,
    render_controls: Callable[[], None],
) -> None:
    top1 = _top1_by_mode(top3)
    left_col, middle_col, right_col = st.columns([0.23, 0.28, 0.49], gap="large", vertical_alignment="top")
    with left_col:
        _render_column_heading("設定我的條件")
        render_controls()
        _render_comparison_market_overview(candidates, destination)
    with middle_col:
        _render_column_heading("四種偏好下的 Top 1")
        _render_comparison_mode_cards(top1)
    with right_col:
        _render_column_heading("推薦總覽地圖")
        analysis_layer = st.segmented_control(
            "行政區背景",
            options=DISTRICT_ANALYSIS_LAYER_OPTIONS,
            default=DISTRICT_ANALYSIS_LAYER_RENT,
            key="comparison_district_analysis_layer",
        )
        if analysis_layer is None:
            analysis_layer = DISTRICT_ANALYSIS_LAYER_RENT
        _render_analysis_layer_note(str(analysis_layer), towns)
        overview_map = build_overview_map(candidates, top3, destination, towns, cities, str(analysis_layer))
        st_folium(
            overview_map,
            height=590,
            use_container_width=True,
            returned_objects=[],
            key="housing_overview_map",
        )
        st.caption("比較不同偏好下的 Top 1 生活圈，協助理解租金、通勤與生活機能之間的取捨。")


def _render_column_heading(title: str) -> None:
    st.markdown(f'<div class="qj-column-heading"><h3>{title}</h3></div>', unsafe_allow_html=True)


def _render_comparison_market_overview(candidates: pd.DataFrame, destination: dict[str, float | str]) -> None:
    rents = pd.to_numeric(candidates["rent"], errors="coerce").dropna()
    st.markdown("### 新北租屋市場概況")
    if not rents.empty:
        st.markdown(f"**候選生活圈租金範圍**：{money(rents.min())}–{money(rents.max())} NTD/月")
    st.markdown(f"**目前工作地參考**：{destination['destination']}")
    st.caption("租金採 MOI 2026-03 行政區獨立套房 benchmark，非即時房源。")


def _render_comparison_mode_cards(top1: pd.DataFrame) -> None:
    rows_by_mode = {row["preference_mode"]: row for _, row in top1.iterrows()}
    for index, mode in enumerate(MODE_ORDER):
        row = rows_by_mode[mode]
        with st.container(border=True, key=f"housing_mode_card_{index}"):
            title_col, action_col = st.columns([0.68, 0.32], gap="small")
            with title_col:
                st.markdown(f"### {mode}")
            with action_col:
                st.button(
                    f"查看{mode}",
                    key=f"housing_open_mode_{mode}",
                    use_container_width=False,
                    on_click=_open_single_mode,
                    args=(mode,),
                )
            st.markdown(f"**{row['living_area']}**")
            st.caption(
                f"月租中位數 {money(row['rent'])} NTD｜通勤 {minutes(row['commute_minutes'])}｜"
                f"生活機能 {float(row['livability_index']):.3f}"
            )
            st.caption(MODE_COPY[mode])


def _open_single_mode(mode: str) -> None:
    st.session_state.housing_view_mode = "查看單一模式"
    st.session_state.housing_recommendation_mode = mode


def _top1_by_mode(top3: pd.DataFrame) -> pd.DataFrame:
    rows = top3[top3["rank"] == 1].copy()
    if len(rows) != len(MODE_ORDER):
        raise RuntimeError(f"Expected {len(MODE_ORDER)} mode Top 1 rows, found {len(rows)}.")
    mode_order = {mode: index for index, mode in enumerate(MODE_ORDER)}
    rows["_mode_order"] = rows["preference_mode"].map(mode_order)
    return rows.sort_values("_mode_order").drop(columns=["_mode_order"])


def _render_summary_cards(top1: pd.DataFrame) -> None:
    columns = st.columns(4, gap="medium")
    rows_by_mode = {row["preference_mode"]: row for _, row in top1.iterrows()}
    for column, mode in zip(columns, MODE_ORDER):
        row = rows_by_mode[mode]
        color = MODE_COLORS[mode]
        with column:
            st.markdown(
                f"""
                <div class="qj-overview-card" style="--qj-mode-color: {color}; --qj-mode-soft: {_soft_background(mode)};">
                    <div class="qj-overview-card-top">
                        <div class="qj-overview-mode">
                            <span class="qj-dot"></span>{mode}
                        </div>
                        <span class="qj-overview-rank">Top 1</span>
                    </div>
                    <div class="qj-overview-title">{row['living_area']}</div>
                    <div class="qj-overview-location">{row['candidate_name']} · {row['district']}</div>
                    <div class="qj-overview-grid">
                        <div class="qj-overview-primary-metric"><span>月租中位數</span><b>{money(row['rent'])}<small>NTD</small></b></div>
                        <div><span>通勤時間</span><b>{minutes(row['commute_minutes'])}</b></div>
                    </div>
                    <div class="qj-overview-copy"><span>推薦重點</span>{MODE_COPY[mode]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_comparison_bar(top1: pd.DataFrame) -> None:
    rows_by_mode = {row["preference_mode"]: row for _, row in top1.iterrows()}
    st.markdown(
        '<div class="qj-comparison-title">四模式 Top 1 橫向比較</div>',
        unsafe_allow_html=True,
    )
    columns = st.columns(4, gap="medium")
    for column, mode in zip(columns, MODE_ORDER):
        row = rows_by_mode[mode]
        short_name = row["living_area"].replace("生活圈", "")
        with column:
            st.markdown(
                f"""
                <div class="qj-comparison-card">
                    <div class="qj-comparison-mode">
                        <span class="qj-dot" style="background: {MODE_COLORS[mode]};"></span>
                        <b>{mode}</b>
                    </div>
                    <div class="qj-comparison-main">{short_name}</div>
                    <div class="qj-comparison-meta">{money(row['rent'])} NTD｜{minutes(row['commute_minutes'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_analysis_layer_note(analysis_layer: str, towns) -> None:
    if analysis_layer not in {DISTRICT_ANALYSIS_LAYER_YOUTH_COUNT, DISTRICT_ANALYSIS_LAYER_YOUTH_SHARE}:
        return
    field = (
        "youth_population_18_35"
        if analysis_layer == DISTRICT_ANALYSIS_LAYER_YOUTH_COUNT
        else "youth_population_18_35_share"
    )
    valid_count = int(pd.to_numeric(towns.get(field, pd.Series(dtype=float)), errors="coerce").notna().sum())
    if valid_count > 0:
        return
    st.markdown(
        '<div class="qj-section-note">目前沒有可用的行政區 Exact 18–35 青年人口資料；不估算、不補值。</div>',
        unsafe_allow_html=True,
    )


def _soft_background(mode: str) -> str:
    return {
        "省租型": "#EAF6EF",
        "平衡型": "#EAF4FA",
        "通勤型": "#FFF1E3",
        "生活品質型": "#F2ECF8",
    }[mode]
