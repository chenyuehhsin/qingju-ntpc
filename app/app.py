from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from components.overview import render_overview
from data_loader import (
    MODE_COLORS,
    MODE_COPY,
    MODE_ORDER,
    MODE_SOFT_COLORS,
    load_boundaries,
    load_dashboard_data,
    load_workplaces,
)
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

    try:
        workplaces = load_workplaces()
    except Exception as exc:
        st.error(f"Workplace data loading failed: {exc}")
        st.stop()
    workplace_labels = {
        row["workplace_id"]: f"{row['workplace_name']}｜{row['workplace_district']}"
        for _, row in workplaces.iterrows()
    }

    header_left, header_right = st.columns([1.15, 0.85], gap="medium")
    with header_left:
        st.markdown(
            """
            <div class="qj-header-title">青聚新北｜青年生活圈推薦</div>
            <div class="qj-subtitle">選定工作地後，我住新北哪裡比較適合？</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="qj-control-row">', unsafe_allow_html=True)
        control_cols = st.columns([0.95, 0.68, 0.68, 1.45], gap="small")
        with control_cols[0]:
            selected_workplace_id = st.selectbox(
                "工作地",
                workplaces["workplace_id"].tolist(),
                format_func=lambda value: workplace_labels[value],
                label_visibility="visible",
            )
        with control_cols[1]:
            st.selectbox("交通方式", ["大眾運輸"], disabled=True, label_visibility="visible")
        with control_cols[2]:
            st.selectbox("租屋型態", ["獨立套房"], disabled=True, label_visibility="visible")
        st.markdown("</div>", unsafe_allow_html=True)
    with header_right:
        hero_title = "推薦總覽"
        hero_copy = "比較四種偏好模式的 Top 1，快速掌握推薦生活圈差異。"
        hero_color = "#52646B"
        if current_view in MODE_ORDER:
            hero_title = f"{current_view}推薦"
            hero_copy = MODE_COPY[current_view]
            hero_color = MODE_COLORS[current_view]
        st.markdown(
            f"""
            <div class="qj-mode-hero">
                <div class="qj-mode-heading" style="color: {hero_color};">{hero_title}</div>
                <div class="qj-mode-subtitle">{hero_copy}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
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

    try:
        candidates, recommendations, top3, destination = load_dashboard_data(selected_workplace_id)
        towns, cities = load_boundaries()
    except Exception as exc:
        st.error(f"Dashboard data loading failed: {exc}")
        st.stop()

    if selected_view == "四模式總覽":
        render_overview(candidates, top3, destination, towns, cities)
    else:
        mode = selected_view
        render_dashboard_view(mode, candidates, recommendations, top3, destination, towns, cities)

    st.markdown("---")
    with st.expander("資料與方法說明", expanded=False):
        st.markdown(
            """
            <div class="qj-note">
            <b>資料限制</b><br>
            租金為 MOI 行政區獨立套房官方 benchmark，不是即時房源價格。<br>
            租金目前是行政區尺度，不代表特定車站周邊實際租金。<br>
            通勤為 TDX MaaS 平日 08:00、代表交通節點到工作地的公共運輸時間。<br>
            目前不是 door-to-door 通勤。<br>
            目前不包含汽車 / 機車通勤模式。<br>
            生活品質型目前以站點周邊 800m OSM POI 作為生活機能 proxy。<br>
            推薦權重為 MVP preference settings，不代表客觀最佳居住選擇。<br>
            地圖上的生活圈圓圈為機車約 10 分鐘、約 3km 的產品視覺示意，不是推薦模型輸入。
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
