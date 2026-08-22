from __future__ import annotations

import pandas as pd
import streamlit as st

from data_loader import MODE_COLORS, MODE_COPY, minutes, money, reason_for


def render_context_chips() -> None:
    st.markdown(
        """
        <div class="qj-chip-row">
            <div class="qj-chip"><div class="qj-chip-label">工作地</div><div class="qj-chip-value">港墘站</div></div>
            <div class="qj-chip"><div class="qj-chip-label">交通方式</div><div class="qj-chip-value">大眾運輸</div></div>
            <div class="qj-chip"><div class="qj-chip-label">租屋型態</div><div class="qj-chip-value">獨立套房</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def render_recommendation_cards(mode: str, rows: pd.DataFrame) -> None:
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
