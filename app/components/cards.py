from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import streamlit as st

from data_loader import MODE_COLORS, MODE_COPY, minutes, money, reason_for


def render_mode_intro(mode: str) -> None:
    color = MODE_COLORS[mode]
    st.markdown(
        f"""
        <div class="qj-panel" style="border-left: 5px solid {color};">
            <div style="font-weight: 800; font-size: 1.08rem; color: {color};">{mode}</div>
            <div class="qj-reason">{MODE_COPY[mode]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_recommendation_cards(
    mode: str,
    rows: pd.DataFrame,
    selected_candidate: str,
    on_select: Callable[[str], None],
) -> None:
    color = MODE_COLORS[mode]
    sorted_rows = rows.sort_values("rank")
    for _, row in sorted_rows.iterrows():
        is_selected = str(row["candidate_name"]) == selected_candidate
        if is_selected:
            _render_selected_card(mode, row, color, on_select)
        else:
            _render_compact_card(mode, row, color, on_select)


def _render_selected_card(
    mode: str,
    row: pd.Series,
    color: str,
    on_select: Callable[[str], None],
) -> None:
    rank = int(row["rank"])
    livability = f"{float(row['livability_index']):.3f}"
    with st.container(border=True):
        title_col, action_col = st.columns([0.72, 0.28], gap="small")
        with title_col:
            st.markdown(f"**Top {rank}｜{row['living_area']} · 目前查看**")
            st.caption(f"{row['candidate_name']}｜{row['district']}")
        with action_col:
            _render_card_select_button(mode, row, True, on_select)
        metrics = st.columns(4, gap="small")
        metrics[0].caption(f"月租\n\n{money(row['rent'])} NTD")
        metrics[1].caption(f"通勤\n\n{minutes(row['commute_minutes'])}")
        metrics[2].caption(f"較內湖\n\n省 {money(row['rent_saving_vs_neihu'])}")
        metrics[3].caption(f"生活機能\n\n{livability}")
        st.caption(reason_for(mode, row))


def _render_compact_card(
    mode: str,
    row: pd.Series,
    color: str,
    on_select: Callable[[str], None],
) -> None:
    rank = int(row["rank"])
    with st.container(border=True):
        title_col, action_col = st.columns([0.72, 0.28], gap="small")
        with title_col:
            st.markdown(f"**Top {rank}｜{row['living_area']}**")
        with action_col:
            _render_card_select_button(mode, row, False, on_select)
        st.caption(
            f"{money(row['rent'])} NTD｜{minutes(row['commute_minutes'])}｜"
            f"省 {money(row['rent_saving_vs_neihu'])}｜{reason_for(mode, row)}"
        )


def _render_card_select_button(
    mode: str,
    row: pd.Series,
    is_selected: bool,
    on_select: Callable[[str], None],
) -> None:
    label = "已選取" if is_selected else "查看"
    if st.button(
        label,
        key=f"housing_select_candidate_{mode}_{int(row['rank'])}",
        use_container_width=False,
        disabled=is_selected,
    ):
        on_select(str(row["candidate_name"]))
        st.rerun()


def render_recommendation_cards_legacy(mode: str, rows: pd.DataFrame) -> None:
    color = MODE_COLORS[mode]
    for _, row in rows.sort_values("rank").iterrows():
        rank = int(row["rank"])
        border = color if rank == 1 else "#DDE5E6"
        background = "#FFFFFF" if rank != 1 else "#FBFCFB"
        livability = f"{float(row['livability_index']):.3f}"
        livability_style = f"color: {color}; font-weight: 900;" if mode == "生活品質型" else ""
        st.markdown(
            f"""
            <div class="qj-card" style="border-color: {border}; background: {background};">
                <div class="qj-card-top">
                    <div class="qj-rank" style="color: {color};">#{rank}</div>
                    <div style="color: #6c787d; font-size: 0.82rem;">{row['district']}</div>
                </div>
                <div class="qj-card-title">{row['living_area']}</div>
                <div class="qj-station">{row['candidate_name']}</div>
                <div class="qj-metrics">
                    <div class="qj-metric"><div class="qj-metric-label">月租中位數</div><div class="qj-metric-value">{money(row['rent'])} NTD</div></div>
                    <div class="qj-metric"><div class="qj-metric-label">通勤時間</div><div class="qj-metric-value">{minutes(row['commute_minutes'])}</div></div>
                    <div class="qj-metric"><div class="qj-metric-label">相較內湖省租</div><div class="qj-metric-value">省 {money(row['rent_saving_vs_neihu'])}</div></div>
                    <div class="qj-metric"><div class="qj-metric-label">生活機能 proxy</div><div class="qj-metric-value" style="{livability_style}">{livability}</div></div>
                </div>
                <div class="qj-reason">{reason_for(mode, row)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
