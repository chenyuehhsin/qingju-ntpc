from __future__ import annotations

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

    st.markdown("## 四模式推薦總覽")
    st.markdown(
        '<div class="qj-section-note">先看每種偏好推薦住哪；切換單一模式後，可選 Top 1 / 2 / 3 查看約15分鐘核心生活圈與延伸生活圈。生活機能統計目前仍基於 800m 範圍。</div>',
        unsafe_allow_html=True,
    )
    _render_summary_cards(top1)

    st.markdown("### Overview map")
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
    st_folium(overview_map, height=560, use_container_width=True, returned_objects=[])

    _render_comparison_bar(top1)
    st.markdown("---")


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
                <div class="qj-overview-card" style="border-color: {color}; background: {_soft_background(mode)};">
                    <div class="qj-overview-mode" style="color: {color};">
                        <span class="qj-dot" style="background: {color};"></span>{mode}
                    </div>
                    <div class="qj-overview-title">{row['living_area']}</div>
                    <div class="qj-overview-grid">
                        <div><span>月租</span><b>{money(row['rent'])} NTD</b></div>
                        <div><span>通勤</span><b>{minutes(row['commute_minutes'])}</b></div>
                    </div>
                    <div class="qj-overview-copy">{MODE_COPY[mode]}</div>
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
