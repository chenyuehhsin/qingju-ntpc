from __future__ import annotations

import html
from collections.abc import Callable

import pandas as pd
import streamlit as st

from data_loader import MODE_COLORS, MODE_COPY, MODE_SOFT_COLORS, minutes, money, reason_for


MODE_ICONS = {
    "省租型": '<path d="M4 7.5h12v8H4z"/><path d="M6 7.5V5h8v2.5M7 11h6M10 9v4"/>',
    "平衡型": '<path d="M10 3v14M5 6h10M5 6l-3 5h6L5 6Zm10 0-3 5h6l-3-5Z"/>',
    "通勤型": '<circle cx="10" cy="10" r="7"/><path d="M10 6v4l3 2"/>',
    "生活品質型": '<path d="M10 17S3.5 13.2 3.5 8.2A3.7 3.7 0 0 1 10 5.8a3.7 3.7 0 0 1 6.5 2.4C16.5 13.2 10 17 10 17Z"/>',
}

MODE_CARD_CLASSES = {
    "省租型": "saving",
    "平衡型": "balanced",
    "通勤型": "commute",
    "生活品質型": "lifestyle",
}

MODE_TEXT_COLORS = {
    "省租型": "#4D936C",
    "平衡型": "#397FA8",
    "通勤型": "#B66D15",
    "生活品質型": "#C2534D",
}


def render_housing_mode_grid(
    rows_by_mode: dict[str, pd.Series | None],
    selected_mode: str,
    on_select: Callable[[str], None],
) -> None:
    """Render four preference results as an equal 2x2 grid."""
    modes = list(rows_by_mode)
    for row_start in range(0, len(modes), 2):
        columns = st.columns(2, gap="medium", vertical_alignment="top")
        for column, mode in zip(columns, modes[row_start : row_start + 2]):
            with column:
                _render_housing_mode_card(
                    mode,
                    rows_by_mode[mode],
                    is_selected=mode == selected_mode,
                    on_select=on_select,
                )


def _render_housing_mode_card(
    mode: str,
    row: pd.Series | None,
    *,
    is_selected: bool,
    on_select: Callable[[str], None],
) -> None:
    color = MODE_COLORS[mode]
    soft_color = MODE_SOFT_COLORS[mode]
    text_color = MODE_TEXT_COLORS[mode]
    mode_class = MODE_CARD_CLASSES[mode]
    selection_class = " is-selected" if is_selected else ""
    # Use stable ASCII keys so Streamlit's generated CSS classes can be targeted reliably.
    with st.container(border=True, key=f"housing_result_card_{mode_class}"):
        if row is None:
            content = (
                '<div class="qj-housing-card-empty">目前預算內沒有符合條件的生活圈，請提高預算後重新分析。</div>'
            )
            living_area = "暫無符合結果"
            rent = commute = livability = "資料不足"
        else:
            content = f'<p>{html.escape(MODE_COPY[mode])}</p>'
            living_area = _display_text(row.get("living_area"))
            rent = _money_or_missing(row.get("rent"))
            commute = _minutes_or_missing(row.get("commute_minutes"))
            livability = _display_text(row.get("livability_level"))
        selected_badge = (
            f'<span class="qj-housing-selected-badge" style="background:{soft_color};'
            f'border-color:{color};color:{text_color};">✓ 目前選取</span>'
            if is_selected
            else ""
        )
        icon = MODE_ICONS.get(mode, '<circle cx="10" cy="10" r="6"/>')
        card_markup = (
            f'<article class="qj-housing-mode-card qj-housing-mode-card--{mode_class}{selection_class}" '
            f'style="--qj-mode-color:{color};border-top:2px solid {color};padding-top:0.5rem;">'
            '<div class="qj-housing-card-head">'
            f'<div class="qj-housing-mode-label" style="color:{text_color};">'
            f'<svg viewBox="0 0 20 20" aria-hidden="true" style="background:{soft_color};">{icon}</svg>'
            f'<span>{html.escape(mode)}</span>'
            "</div>"
            f"{selected_badge}"
            "</div>"
            f"<h3>{html.escape(living_area)}</h3>"
            f"{content}"
            '<div class="qj-housing-card-metrics">'
            f'<div><span>租金中位數</span><b style="color:{text_color};">{html.escape(rent)}</b></div>'
            f'<div><span>通勤時間</span><b style="color:{text_color};">{html.escape(commute)}</b></div>'
            f'<div><span>生活機能</span><b style="color:{text_color};">{html.escape(livability)}</b></div>'
            "</div>"
            "</article>"
        )
        st.markdown(card_markup, unsafe_allow_html=True)
        st.button(
            "目前選取" if is_selected else "查看方案",
            key=f"housing_select_mode_{mode}",
            type="primary" if is_selected else "secondary",
            use_container_width=True,
            disabled=is_selected or row is None,
            on_click=on_select,
            args=(mode,),
            help=f"切換到{mode}推薦生活圈" if row is not None else "目前預算內沒有符合結果",
        )


def _display_text(value: object) -> str:
    if value is None or pd.isna(value) or not str(value).strip():
        return "資料不足"
    return str(value)


def _money_or_missing(value: object) -> str:
    if value is None or pd.isna(value):
        return "資料不足"
    return f"NT$ {money(value)}／月"


def _minutes_or_missing(value: object) -> str:
    if value is None or pd.isna(value):
        return "暫無資料"
    return f"{float(value):.0f} 分鐘"


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
        st.markdown(
            f'<div style="background:#ECFBF3;border-left:4px solid {color};border-radius:6px;padding:0.28rem 0.5rem;font-size:0.78rem;font-weight:800;color:#187A59;">目前查看</div>',
            unsafe_allow_html=True,
        )
        title_col, action_col = st.columns([0.72, 0.28], gap="small")
        with title_col:
            st.markdown(f"**Top {rank}｜{row['living_area']}**")
            st.caption(f"{row['candidate_name']}｜{row['district']}")
        with action_col:
            _render_card_select_button(mode, row, True, on_select)
        first_metric_row = st.columns(2, gap="small")
        first_metric_row[0].metric("月租中位數", f"{money(row['rent'])} NTD")
        first_metric_row[1].metric("通勤時間", minutes(row["commute_minutes"]))
        second_metric_row = st.columns(2, gap="small")
        second_metric_row[0].metric("相較內湖租金", f"省 {money(row['rent_saving_vs_neihu'])}")
        second_metric_row[1].metric("生活機能", livability)
        st.caption("租金：MOI 2026-03 行政區獨立套房 benchmark")
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
            f"月租中位數 {money(row['rent'])} NTD｜{minutes(row['commute_minutes'])}｜"
            f"省 {money(row['rent_saving_vs_neihu'])}｜{reason_for(mode, row)}"
        )


def _render_card_select_button(
    mode: str,
    row: pd.Series,
    is_selected: bool,
    on_select: Callable[[str], None],
) -> None:
    label = "目前查看" if is_selected else "查看"
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
