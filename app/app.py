from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from components.cards import render_context_chips
from components.overview import render_overview
from data_loader import MODE_ORDER, load_boundaries, load_dashboard_data
from recommendation_view import render_dashboard_view
from styles import apply_styles


def main() -> None:
    st.set_page_config(
        page_title="青聚新北",
        page_icon="Q",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_styles()

    st.title("青聚新北｜青年生活圈推薦")
    st.markdown('<div class="qj-subtitle">工作在內湖，我住新北哪裡比較適合？</div>', unsafe_allow_html=True)
    render_context_chips()

    try:
        candidates, recommendations, top3, destination = load_dashboard_data()
        towns, cities = load_boundaries()
    except Exception as exc:
        st.error(f"Dashboard data loading failed: {exc}")
        st.stop()

    page_mode = st.radio(
        "選擇瀏覽模式",
        ["四模式推薦總覽", "該模式詳細推薦"],
        horizontal=True,
        label_visibility="visible",
    )

    if page_mode == "四模式推薦總覽":
        render_overview(candidates, top3, destination, towns, cities)
    else:
        st.markdown("## 該模式詳細推薦")
        mode = st.radio(
            "選擇推薦模式",
            MODE_ORDER,
            horizontal=True,
            label_visibility="visible",
        )
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
