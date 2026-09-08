from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from custom_workplace import GEOCODING_SOURCE, build_custom_dashboard_data, geocode_address
from components.career_evidence_viewer import render_career_evidence_viewer
from components.overview import render_overview
from components.policy_lens import render_policy_lens
from data_loader import (
    MODE_COPY,
    MODE_ORDER,
    load_boundaries,
    load_career_evidence_data,
    load_career_learning_ladder_phase8,
    load_career_policy_lens_phase7,
    load_dashboard_data,
    load_policy_lens_data,
)
from recommendation_view import render_dashboard_view
from styles import apply_styles


NO_PRESET_LABEL = "無"
DEFAULT_PRESET_LABEL = "港墘站｜內湖"


def _apply_quick_preset(preset_addresses: dict[str, str]) -> None:
    preset_label = st.session_state.get("quick_preset", NO_PRESET_LABEL)
    if preset_label != NO_PRESET_LABEL:
        st.session_state.workplace_address = preset_addresses[preset_label]


def _mark_manual_address(preset_addresses: dict[str, str]) -> None:
    address = st.session_state.get("workplace_address", "").strip()
    if address and address not in preset_addresses.values():
        st.session_state.quick_preset = NO_PRESET_LABEL


def _load_custom_workplace(address: str) -> None:
    geocode = geocode_address(address)
    st.session_state.custom_workplace_data = build_custom_dashboard_data(address, geocode)
    st.session_state.custom_geocode = geocode
    st.session_state.active_workplace_address = address
    st.session_state.active_workplace_input_address = address
    st.session_state.active_workplace_source = GEOCODING_SOURCE


def _load_preset_workplace(preset_label: str, preset_workplaces: dict[str, dict[str, Any]]) -> None:
    preset = preset_workplaces[preset_label]
    workplace_id = preset.get("workplace_id")
    if not workplace_id:
        raise RuntimeError(f"{preset_label} is a custom quick example and has no precomputed workplace_id.")
    dashboard_data = load_dashboard_data(workplace_id)
    st.session_state.custom_workplace_data = dashboard_data
    _, _, _, destination = dashboard_data
    st.session_state.custom_geocode = {
        "lat": destination["destination_lat"],
        "lon": destination["destination_lon"],
        "source": "TDX station preset",
    }
    st.session_state.active_workplace_address = f"{preset_label}（快速範例）"
    st.session_state.active_workplace_input_address = preset["address"]
    st.session_state.active_workplace_source = "TDX station preset"


def _load_fixed_quick_example(preset_label: str, preset_workplaces: dict[str, dict[str, Any]]) -> None:
    preset = preset_workplaces[preset_label]
    geocode = {
        "lat": float(preset["lat"]),
        "lon": float(preset["lon"]),
        "source": str(preset["source"]),
        "display_name": str(preset["source_name"]),
    }
    address = str(preset["address"])
    st.session_state.custom_workplace_data = build_custom_dashboard_data(address, geocode)
    st.session_state.custom_geocode = geocode
    st.session_state.active_workplace_address = f"{preset_label}（快速範例 Beta）"
    st.session_state.active_workplace_input_address = address
    st.session_state.active_workplace_source = str(preset["source"])


def _load_quick_example(preset_label: str, preset_workplaces: dict[str, dict[str, Any]]) -> None:
    preset = preset_workplaces[preset_label]
    if preset.get("workplace_id"):
        _load_preset_workplace(preset_label, preset_workplaces)
        return
    if preset.get("lat") and preset.get("lon"):
        _load_fixed_quick_example(preset_label, preset_workplaces)
        return

    address = str(preset["address"])
    _load_custom_workplace(address)
    st.session_state.active_workplace_address = f"{preset_label}（快速範例 Beta）"
    st.session_state.active_workplace_input_address = address


def main() -> None:
    st.set_page_config(
        page_title="青聚新北",
        page_icon="Q",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    page_options = ["青年職涯探索", "青年安居推薦", "青年局 Policy Lens"]
    current_page = st.session_state.get("app_page", "青年職涯探索")
    if current_page == "Career Evidence Viewer":
        current_page = "青年職涯探索"
    if current_page == "青年生活圈推薦":
        current_page = "青年安居推薦"
    if current_page not in page_options:
        current_page = "青年職涯探索"
    apply_styles(current_page)

    page = st.segmented_control(
        "頁面",
        options=page_options,
        default=current_page,
        key="app_page",
        label_visibility="collapsed",
    )
    if page is None:
        page = "青年職涯探索"
    if page == "青年職涯探索":
        try:
            candidates_v35, training_v4, course_mapping, demo_job_evidence, beauty_phase5, crc_external_market = load_career_evidence_data()
        except Exception as exc:
            st.error(f"Career evidence data loading failed: {exc}")
            st.stop()
        render_career_evidence_viewer(candidates_v35, training_v4, course_mapping, demo_job_evidence, beauty_phase5, crc_external_market)
        return
    if page == "青年局 Policy Lens":
        try:
            policy = load_policy_lens_data()
            career_policy, career_policy_md = load_career_policy_lens_phase7()
            career_ladder = load_career_learning_ladder_phase8()
            towns, cities = load_boundaries()
        except Exception as exc:
            st.error(f"Policy Lens data loading failed: {exc}")
            st.stop()
        render_policy_lens(policy, towns, cities, career_policy, career_policy_md, career_ladder)
        return

    if page != "青年安居推薦":
        page = "青年安居推薦"

    nav_options = ["四模式總覽", *MODE_ORDER]
    current_view = st.session_state.get("main_view", "四模式總覽")

    preset_workplaces = {
        "港墘站｜內湖": {
            "address": "台北市內湖區瑞光路",
            "workplace_id": "gangqian_neihu",
        },
        "市政府站｜信義": {
            "address": "台北市信義區市府路",
            "workplace_id": "taipei_city_hall_xinyi",
        },
        "台北車站｜中正": {
            "address": "台北市中正區忠孝西路一段",
            "workplace_id": "taipei_main_zhongzheng",
        },
        "南港站｜南港": {
            "address": "台北市南港區忠孝東路七段",
            "workplace_id": "nangang_nangang",
        },
        "新板特區": {
            "address": "新北市板橋區新府路",
            "workplace_id": "xinban_special_district",
        },
        "新莊副都心": {
            "address": "新北市新莊區新北大道四段188號",
            "workplace_id": "xinzhuang_fuduxin",
        },
        "汐止科學園區": {
            "address": "新北市汐止區大同路二段182號",
            "workplace_id": "xizhi_science_park",
        },
        "中和科技園區": {
            "address": "新北市中和區橋和路282號",
            "workplace_id": "zhonghe_tech_park",
        },
        "土城產業園區": {
            "address": "新北市土城區中央路四段23號",
            "workplace_id": "tucheng_industrial_park",
        },
    }
    preset_addresses = {label: preset["address"] for label, preset in preset_workplaces.items()}
    preset_options = [NO_PRESET_LABEL, *preset_addresses.keys()]
    if "workplace_address" not in st.session_state:
        st.session_state.workplace_address = preset_addresses[DEFAULT_PRESET_LABEL]
    if "quick_preset" not in st.session_state:
        st.session_state.quick_preset = DEFAULT_PRESET_LABEL
    if "custom_workplace_data" not in st.session_state:
        st.session_state.custom_workplace_data = None
    if "custom_geocode" not in st.session_state:
        st.session_state.custom_geocode = None
    if "active_workplace_address" not in st.session_state:
        st.session_state.active_workplace_address = None
    if "active_workplace_input_address" not in st.session_state:
        st.session_state.active_workplace_input_address = None
    if "active_workplace_source" not in st.session_state:
        st.session_state.active_workplace_source = None
    if st.session_state.quick_preset not in preset_options:
        st.session_state.quick_preset = NO_PRESET_LABEL

    header_left, header_right = st.columns([1.65, 0.85], gap="large")
    with header_left:
        st.markdown(
            """
            <div class="qj-housing-page-intro">
                <div class="qj-housing-eyebrow">Youth housing explorer · New Taipei City</div>
                <div class="qj-header-title">青年安居推薦</div>
                <div class="qj-subtitle">設定工作地點，從租金、通勤與生活機能找到適合自己的新北生活圈。</div>
            </div>
            <div class="qj-housing-workflow-title">先設定工作地點</div>
            <div class="qj-housing-workflow-copy">可直接輸入地址，或從快速範例開始；送出後會更新地圖與四種偏好模式的排序。</div>
            """,
            unsafe_allow_html=True,
        )
        first_row = st.columns([1.42, 0.78, 0.44], gap="small")
        with first_row[0]:
            st.text_input(
                "工作地點",
                key="workplace_address",
                placeholder="例如：台北市內湖區瑞光路",
                on_change=_mark_manual_address,
                args=(preset_addresses,),
            )
        with first_row[1]:
            st.selectbox(
                "快速範例",
                preset_options,
                key="quick_preset",
                on_change=_apply_quick_preset,
                args=(preset_addresses,),
            )
        with first_row[2]:
            submitted = st.button("開始推薦", use_container_width=True)

        st.markdown(
            '<div class="qj-housing-setting-note">推薦設定：大眾運輸 · 獨立套房 <span>（目前為固定 MVP 條件）</span></div>',
            unsafe_allow_html=True,
        )
        note_slot = st.empty()

        if st.session_state.custom_workplace_data is None:
            try:
                with st.spinner("載入預設快速範例：港墘站｜內湖..."):
                    _load_preset_workplace(DEFAULT_PRESET_LABEL, preset_workplaces)
            except Exception as exc:
                st.session_state.custom_workplace_data = None
                st.session_state.custom_geocode = None
                st.session_state.active_workplace_address = None
                st.session_state.active_workplace_input_address = None
                st.session_state.active_workplace_source = None
                st.error(f"預設快速範例載入失敗：{exc}")

        if submitted:
            target_address = st.session_state.workplace_address.strip()
            if not target_address:
                st.error("請輸入工作地址，或先選擇一個快速範例。")
                st.stop()
            try:
                selected_preset = st.session_state.get("quick_preset", NO_PRESET_LABEL)
                if selected_preset != NO_PRESET_LABEL:
                    with st.spinner(f"載入快速範例：{selected_preset}..."):
                        _load_quick_example(selected_preset, preset_workplaces)
                else:
                    with st.spinner("定位工作地址並計算 16 個生活圈通勤時間..."):
                        _load_custom_workplace(target_address)
            except Exception as exc:
                st.session_state.custom_workplace_data = None
                st.session_state.custom_geocode = None
                st.session_state.active_workplace_address = None
                st.session_state.active_workplace_input_address = None
                st.session_state.active_workplace_source = None
                st.error(f"工作地址處理失敗：{exc}")

        if st.session_state.custom_geocode:
            geocode = st.session_state.custom_geocode
            active_address = st.session_state.active_workplace_address
            active_input_address = st.session_state.active_workplace_input_address
            current_address = st.session_state.workplace_address.strip()
            pending_note = ""
            if current_address and active_input_address and current_address != active_input_address:
                pending_note = "<br><b>輸入地址尚未套用：</b>請按「開始推薦」更新地圖與排名。"
            with note_slot:
                st.markdown(
                    f"""
                    <div class="qj-geocode-note">
                        <b>目前套用工作地：</b>{active_address}<span class="qj-geocode-detail">已定位：{float(geocode['lat']):.6f}, {float(geocode['lon']):.6f}｜來源：{st.session_state.active_workplace_source}</span>
                        {pending_note}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            with note_slot:
                st.markdown(
                    f'<div class="qj-geocode-note">請輸入工作地址後按「開始推薦」。快速範例可作為 fallback；geocoding 來源：{GEOCODING_SOURCE}。</div>',
                    unsafe_allow_html=True,
                )
    with header_right:
        hero_title = "推薦總覽"
        hero_copy = "比較四種偏好模式的 Top 1，快速掌握推薦生活圈差異。"
        if current_view in MODE_ORDER:
            hero_title = f"{current_view}推薦"
            hero_copy = MODE_COPY[current_view]
        st.markdown(
            f"""
            <div class="qj-housing-view-switch">
                <div class="qj-housing-view-eyebrow">接著選擇想看的推薦方式</div>
                <div class="qj-housing-view-title">{hero_title}</div>
                <div class="qj-housing-view-copy">{hero_copy}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        selected_view = st.segmented_control(
            "主畫面切換",
            nav_options,
            default=current_view,
            label_visibility="collapsed",
            key="main_view",
        )
        if selected_view is None:
            selected_view = "四模式總覽"

    if st.session_state.custom_workplace_data is None:
        st.info("請先輸入工作地址並按「開始推薦」，Dashboard 會在成功定位後更新推薦結果。")
        st.stop()

    try:
        candidates, recommendations, top3, destination = st.session_state.custom_workplace_data
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
            <b>主要資料來源與尺度</b><br>
            <b>租金｜MOI</b>：2026-03 行政區獨立套房租金 benchmark；行政區尺度，屬官方 benchmark，不是即時房源或車站周邊實際租金。<br>
            <b>通勤｜TDX MaaS</b>：2026-08-24 平日 08:00 情境；代表交通節點至工作地的公共運輸時間，屬 Derived scenario，不是 door-to-door 時間。<br>
            <b>生活機能｜OSM / Overpass</b>：2026-08-22 snapshot；候選站點周邊 800m POI 的 Derived proxy，不代表完整生活品質。<br>
            <b>青年人口｜RIS 戶政司</b>：2026-07；新北 29 行政區村里單一年齡彙整，Exact 18–35，不可解讀為 1km / 2km 生活圈人口。<br>
            <b>地址定位｜OpenStreetMap Nominatim</b>：使用者輸入地址的 External geocoding；結果僅 local cache，避免重複查詢。<br>
            <br><b>使用限制</b><br>
            任意工作地址使用 OpenStreetMap Nominatim geocoding；地址解析結果會 local cache，避免重複查詢。<br>
            目前不是 door-to-door 通勤。<br>
            目前不包含汽車 / 機車通勤模式。<br>
            推薦權重為 MVP preference settings，不代表客觀最佳居住選擇。<br>
            總覽地圖呈現工作地、Top 3 推薦的約15分鐘核心生活圈（1 km）與延伸生活圈（2 km），以及弱化候選點；行政區背景可切換為無、租金、18–35 青年人口數或 18–35 青年人口占比。<br>
            「15分鐘」為近似探索範圍，實際步行時間依道路與步行速度而異，不代表精準步行 isochrone；生活機能統計目前仍基於 800m 範圍。
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
