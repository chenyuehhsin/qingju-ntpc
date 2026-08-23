from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from components.cards import render_context_chips
from components.overview import render_overview
from data_loader import MODE_COLORS, MODE_COPY, MODE_ORDER, MODE_SOFT_COLORS, load_boundaries, load_dashboard_data
from recommendation_view import render_dashboard_view
from styles import apply_selected_radio_style, apply_styles


def main() -> None:
    st.set_page_config(
        page_title="青聚新北",
        page_icon="Q",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_styles()

    nav_options = ["四模式總覽", *MODE_ORDER]
    current_view = st.session_state.get("main_view", "四模式總覽")
    header_left, header_right = st.columns([0.92, 1.08], gap="medium")
    with header_left:
        st.markdown(
            """
            <div class="qj-header-title">青聚新北｜青年生活圈推薦</div>
            <div class="qj-subtitle">工作在內湖，我住新北哪裡比較適合？</div>
            """,
            unsafe_allow_html=True,
        )
        render_context_chips()
    with header_right:
        if current_view in MODE_ORDER:
            st.markdown(
                f"""
                <div class="qj-mode-hero">
                    <div class="qj-mode-heading" style="color: {MODE_COLORS[current_view]};">{current_view}推薦</div>
                    <div class="qj-mode-subtitle">{MODE_COPY[current_view]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    try:
        candidates, recommendations, top3, destination = load_dashboard_data()
        towns, cities = load_boundaries()
    except Exception as exc:
        st.error(f"Dashboard data loading failed: {exc}")
        st.stop()

    selected_view = st.radio(
        "主畫面切換",
        nav_options,
        horizontal=True,
        label_visibility="collapsed",
        key="main_view",
    )
    selected_color = MODE_COLORS.get(selected_view, "#78B995")
    selected_soft_color = MODE_SOFT_COLORS.get(selected_view, "#EAF6EF")
    apply_selected_radio_style(selected_color, selected_soft_color)

    if selected_view == "四模式總覽":
        render_overview(candidates, top3, destination, towns, cities)
    else:
        mode = selected_view
        render_dashboard_view(mode, candidates, recommendations, top3, destination, towns, cities)

    st.markdown("---")
    st.markdown(
        """
        <div class="qj-note">
        租金：MOI 行政區獨立套房官方租金 benchmark。<br>
        通勤：TDX MaaS，平日 08:00，交通節點到港墘站。<br>
        生活品質型：以站點周邊 800m OSM POI 作為生活機能 proxy；地圖生活圈為機車 10 分鐘、約 3km 的視覺示意。<br>
        目前為 MVP，不代表實際房源報價或 door-to-door 通勤時間。
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
