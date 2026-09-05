from __future__ import annotations

import html
import os
import re
import tempfile
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from branca.colormap import LinearColormap
from branca.element import MacroElement, Template

PROJECT_CACHE_DIR = Path(tempfile.gettempdir()) / "qingju_ntpc_cache"
os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_CACHE_DIR / "xdg"))
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_CACHE_DIR / "matplotlib"))

import matplotlib.font_manager as fm
from matplotlib import pyplot as plt
from streamlit_folium import st_folium

from data_loader import (
    DISTRICT_ANALYSIS_LAYER_NONE,
    DISTRICT_ANALYSIS_LAYER_OPTIONS,
    DISTRICT_ANALYSIS_LAYER_RENT,
    DISTRICT_ANALYSIS_LAYER_YOUTH_COUNT,
    DISTRICT_ANALYSIS_LAYER_YOUTH_SHARE,
    load_district_analysis_table,
    money,
)


POLICY_BASEMAP_MINIMAL = "極簡底圖"
POLICY_BASEMAP_STREET = "街道地圖"
POLICY_BASEMAP_OPTIONS = [POLICY_BASEMAP_MINIMAL, POLICY_BASEMAP_STREET]
TRANSPARENT_TILE_DATA_URI = "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs="
POLICY_VIEWS = {
    "租金": {
        "field": "official_median_rent",
        "title": "租金",
        "unit": "NTD/month",
        "caption": "MOI 行政區獨立套房官方租金 benchmark；不是即時房源價格或站點周邊租金。",
        "low_color": "#F8EBDD",
        "high_color": "#D97950",
        "higher_label": "租金越高",
    },
    "公共運輸可達性": {
        "field": "commute_accessibility_minutes",
        "title": "公共運輸可達性",
        "unit": "min",
        "caption": "現有 9 個 workplace presets 的公共運輸通勤時間中位數。時間越長 = 可達性越弱。",
        "low_color": "#E9F1F4",
        "high_color": "#557F9A",
        "higher_label": "時間越長，可達性越弱",
    },
    "生活機能": {
        "field": "livability_index",
        "title": "生活機能",
        "unit": "index",
        "caption": "OSM 800m POI proxy，值越高代表周邊生活機能 proxy 越高；不代表完整生活品質。",
        "low_color": "#EEF2EA",
        "high_color": "#5D9C7A",
        "higher_label": "生活機能 proxy 越高",
    },
    "政策型租賃樣本": {
        "field": "policy_linked_record_share",
        "title": "政策型租賃相關登錄樣本占比",
        "unit": "share",
        "caption": "此比例僅反映目前清理後租賃登錄樣本結構，不是市場占比、供給率或青年租屋占比。",
        "low_color": "#EFEAF4",
        "high_color": "#8F78AD",
        "higher_label": "樣本占比越高",
    },
}
POLICY_DISTRICT_ANALYSIS_CONFIG = {
    DISTRICT_ANALYSIS_LAYER_RENT: {
        "field": "official_median_rent",
        "title": "行政區租金",
        "unit": "NTD/month",
        "low_color": "#F8EBDD",
        "high_color": "#D97950",
        "higher_label": "租金越高",
        "missing_label": "無租金資料",
    },
    DISTRICT_ANALYSIS_LAYER_YOUTH_COUNT: {
        "field": "youth_population_18_35",
        "title": "18–35 青年人口數",
        "unit": "people",
        "low_color": "#E8F1EF",
        "high_color": "#4F9E8D",
        "higher_label": "青年人口多只代表影響規模較大，不等於政策一定優先",
        "missing_label": "unresolved",
    },
    DISTRICT_ANALYSIS_LAYER_YOUTH_SHARE: {
        "field": "youth_population_18_35_share",
        "title": "18–35 青年人口占比",
        "unit": "share",
        "low_color": "#EEF0F7",
        "high_color": "#6F7FB7",
        "higher_label": "青年人口占比高只代表影響規模較大，不等於政策一定優先",
        "missing_label": "unresolved",
    },
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SMALL_SAMPLE_THRESHOLD = 50


def render_policy_lens(
    policy: pd.DataFrame,
    towns: gpd.GeoDataFrame,
    cities: gpd.GeoDataFrame,
    career_policy: pd.DataFrame | None = None,
    career_policy_md: str = "",
    career_ladder: pd.DataFrame | None = None,
) -> None:
    st.markdown(
        """
        <div class="qj-policy-header">
            <div class="qj-header-title">青聚新北｜青年局 Policy Lens</div>
            <div class="qj-subtitle">分開觀察青年職涯與安居資料訊號，作為政策端快速掃描工具</div>
            <div class="qj-policy-alert">Policy v0 為政策篩選與探索工具，不代表正式政策優先順序。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    career_tab, housing_tab = st.tabs(["職涯政策觀察", "安居政策觀察"])
    with career_tab:
        if career_policy is None:
            st.warning("尚未載入 Career Policy Lens Phase 7 輸出。")
        else:
            render_career_policy_observations(career_policy, career_policy_md, career_ladder)
    with housing_tab:
        render_housing_policy_lens(policy, towns, cities)


def render_housing_policy_lens(policy: pd.DataFrame, towns: gpd.GeoDataFrame, cities: gpd.GeoDataFrame) -> None:
    st.markdown(
        """
        <div class="qj-policy-section-head">
            <div class="qj-policy-section-title">安居政策觀察</div>
            <div class="qj-policy-section-copy">從租金、交通可達性、生活機能、租賃資料結構與行政區背景觀察新北青年居住環境。青年人口多只代表影響規模較大，不等於政策一定優先；本階段不提出社宅、公園、共居等政策處方。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, switch_col, _ = st.columns([0.55, 2.3, 0.55])
    with switch_col:
        selected_view = st.segmented_control(
            "Policy Lens 視角",
            options=list(POLICY_VIEWS.keys()),
            default=st.session_state.get("policy_view", "租金"),
            key="policy_view",
        )
        selected_district_layer = st.segmented_control(
            "行政區背景",
            options=DISTRICT_ANALYSIS_LAYER_OPTIONS,
            default=st.session_state.get("policy_district_analysis_layer", DISTRICT_ANALYSIS_LAYER_NONE),
            key="policy_district_analysis_layer",
        )
        selected_basemap = st.segmented_control(
            "底圖",
            options=POLICY_BASEMAP_OPTIONS,
            default=st.session_state.get("policy_basemap", POLICY_BASEMAP_MINIMAL),
            key="policy_basemap",
        )
    if selected_view is None:
        selected_view = "租金"
    if selected_district_layer is None:
        selected_district_layer = DISTRICT_ANALYSIS_LAYER_NONE
    if selected_basemap is None:
        selected_basemap = POLICY_BASEMAP_MINIMAL
    _render_policy_district_layer_note(str(selected_district_layer), towns)

    map_col, detail_col = st.columns([2.65, 1.0], gap="medium")
    with map_col:
        map_obj = build_policy_map(
            policy,
            towns,
            cities,
            selected_view,
            str(selected_district_layer),
            str(selected_basemap),
        )
        map_state = st_folium(
            map_obj,
            height=650,
            use_container_width=True,
            returned_objects=["last_object_clicked"],
            key=f"policy_map_{selected_view}_{selected_district_layer}_{selected_basemap}",
        )
    clicked_candidate = _candidate_from_click(policy, map_state)
    if clicked_candidate:
        st.session_state.policy_selected_candidate = clicked_candidate
    if "policy_selected_candidate" not in st.session_state:
        st.session_state.policy_selected_candidate = str(policy.sort_values(POLICY_VIEWS[selected_view]["field"], ascending=False).iloc[0]["candidate_name"])
    selected_candidate = st.session_state.policy_selected_candidate

    with detail_col:
        render_view_explainer(selected_view)
        selected_candidate = st.selectbox(
            "生活圈摘要",
            policy["candidate_name"].tolist(),
            index=policy["candidate_name"].tolist().index(selected_candidate)
            if selected_candidate in policy["candidate_name"].tolist()
            else 0,
            format_func=lambda value: str(policy.loc[policy["candidate_name"] == value, "living_area"].iloc[0]),
        )
        st.session_state.policy_selected_candidate = selected_candidate
        row = policy[policy["candidate_name"] == selected_candidate].iloc[0]
        render_candidate_detail(row)

    st.markdown("## 租金 × 公共運輸可達性壓力篩選")
    st.markdown(
        '<div class="qj-section-note">X = commute accessibility minutes，Y = official median rent，顏色 = livability_index。象限線使用目前 16 個候選點的 median 動態計算。</div>',
        unsafe_allow_html=True,
    )
    fig = build_policy_scatter(policy)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    with st.expander("資料、方法與限制", expanded=False):
        render_policy_method_notes()


def _render_policy_district_layer_note(analysis_layer: str, towns: gpd.GeoDataFrame) -> None:
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
        '<div class="qj-section-note">Phase 6 exact 18–35 青年人口目前只到新北市整體，沒有可 exact 對齊的行政區 18–35 資料；此行政區背景標示為 unresolved，不估算、不補值。</div>',
        unsafe_allow_html=True,
    )


def render_career_policy_observations(
    career_policy: pd.DataFrame,
    career_policy_md: str,
    career_ladder: pd.DataFrame | None = None,
) -> None:
    context = career_policy.iloc[0]
    ntpc_population = int(float(context["ntpc_population_18_35"]))
    transition_pct = float(context["mol_transition_intention_percent"])
    training_pct = float(context["mol_training_participation_percent"])
    no_course_pct = float(context["mol_no_course_info_percent"])
    fee_pct = float(context["mol_fee_barrier_percent"])

    st.markdown(
        """
        <div class="qj-policy-section-head">
            <div class="qj-policy-section-title">職涯政策觀察</div>
            <div class="qj-policy-section-copy">整合青年統計、轉職 feasibility、TaiwanJobs 市場訊號與職訓課程證據；不產生成功率、排名或補助金額。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 青年現況摘要")
    st.markdown(
        f"""
        <div class="qj-career-policy-grid">
            <div class="qj-career-policy-card">
                <span>新北青年母體</span>
                <b>{ntpc_population:,}</b>
                <small>18–35｜{html.escape(str(context['ntpc_population_age_harmonization']))}｜{html.escape(str(context['ntpc_population_period']))}</small>
            </div>
            <div class="qj-career-policy-card">
                <span>有轉換工作打算</span>
                <b>{transition_pct:.1f}%</b>
                <small>15–29 青年勞工｜{html.escape(str(context['mol_transition_age_harmonization']))}</small>
            </div>
            <div class="qj-career-policy-card">
                <span>近一年參加教育訓練</span>
                <b>{training_pct:.1f}%</b>
                <small>15–29 青年勞工｜{html.escape(str(context['mol_training_age_harmonization']))}</small>
            </div>
            <div class="qj-career-policy-card">
                <span>訓練資訊 / 費用障礙</span>
                <b>{no_course_pct:.1f}% / {fee_pct:.1f}%</b>
                <small>未參訓者｜單選主因｜Proxy</small>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "年齡標籤：新北人口 = Exact 18–35；MOL 轉職 / 培訓指標 = Proxy 15–29；"
        "教育與部分勞動資料的 Partial / unresolved 標籤保留在 Phase 6 QA，本頁不作強政策結論。"
    )

    st.markdown("### 有資料支持的政策觀察")
    observations = _extract_policy_observations(career_policy_md)
    for observation in observations[:5]:
        st.markdown(f"- {observation}")

    st.markdown("### 轉職與培訓訊號")
    signal_cols = st.columns(3)
    feasible_count = int(career_policy["career_opportunity_status"].eq("structurally feasible").sum())
    high_market_count = int(_num(career_policy["high_relevance_job_count"]).gt(0).sum())
    training_gap_count = int(career_policy["training_gap_status"].eq("Training gap").sum())
    with signal_cols[0]:
        st.metric("可進一步探索路徑", f"{feasible_count} / {len(career_policy)}")
        st.caption("不代表轉職成功率")
    with signal_cols[1]:
        st.metric("具高相關市場證據", f"{high_market_count} / {len(career_policy)}")
    with signal_cols[2]:
        st.metric("目前偵測到明顯 Training Gap", f"{training_gap_count}")
    st.caption(
        f"摘要：可進一步探索路徑 {feasible_count}/{len(career_policy)}，不代表轉職成功率；"
        f"具高相關市場證據 {high_market_count}/{len(career_policy)}；"
        f"目前偵測到明顯 Training Gap {training_gap_count}。"
    )

    render_career_learning_ladder(career_ladder)

    st.markdown("### 常見 Skill Gap")
    skill_gap = _common_skill_gaps(career_policy).head(8)
    if skill_gap.empty:
        st.info("目前 Phase 7 output 沒有可整理的 missing skill。")
    else:
        skill_gap_display = skill_gap.copy()
        skill_gap_display.insert(0, "skill_zh", skill_gap_display["skill"].map(_skill_zh))
        top_skill_text = "、".join(skill_gap_display["skill_zh"].head(5).tolist())
        st.caption(f"第一層中文摘要：{top_skill_text}")
        st.dataframe(
            skill_gap_display[["skill_zh", "path_count"]],
            hide_index=True,
            use_container_width=True,
            column_config={
                "skill_zh": st.column_config.TextColumn("缺口技能", width="large"),
                "path_count": st.column_config.NumberColumn("出現路徑數"),
            },
        )

    market_display = _market_summary(career_policy)
    with st.expander("查看 Market evidence 明細", expanded=False):
        st.dataframe(
            market_display,
            hide_index=True,
            use_container_width=True,
            column_config={
                "target_domain": st.column_config.TextColumn("探索領域", width="medium"),
                "target_occupation_name": st.column_config.TextColumn("職涯路徑", width="large"),
                "market_evidence_status": st.column_config.TextColumn("市場證據狀態", width="large"),
                "high_relevance_job_count": st.column_config.NumberColumn("高相關職缺"),
                "medium_relevance_job_count": st.column_config.NumberColumn("待確認職缺"),
                "high_relevance_demand_persons": st.column_config.NumberColumn("高相關需求人數"),
            },
        )

    training_display = career_policy[
        [
            "target_domain",
            "target_occupation_name",
            "number_of_missing_skills",
            "potential_training_coverage_ratio",
            "matched_course_count",
            "training_gap_status",
            "learning_burden",
        ]
    ].copy()
    training_display["potential_training_coverage_ratio"] = training_display[
        "potential_training_coverage_ratio"
    ].map(_format_ratio)
    with st.expander("查看潛在課程覆蓋 / Training Gap 明細", expanded=False):
        st.caption(
            "潛在課程覆蓋只表示缺口技能是否找到可能相關課程。此表不顯示候選課程集合的累計時數或累計費用。"
        )
        st.dataframe(
            training_display,
            hide_index=True,
            use_container_width=True,
            column_config={
                "target_domain": st.column_config.TextColumn("探索領域", width="medium"),
                "target_occupation_name": st.column_config.TextColumn("職涯路徑", width="large"),
                "number_of_missing_skills": st.column_config.NumberColumn("缺口技能數"),
                "potential_training_coverage_ratio": st.column_config.TextColumn("缺口技能找到可能相關課程比例"),
                "matched_course_count": st.column_config.NumberColumn("對應課程數"),
                "training_gap_status": st.column_config.TextColumn("Training Gap 狀態"),
                "learning_burden": st.column_config.TextColumn("學習負擔"),
            },
        )

    with st.expander("查看方法與資料限制", expanded=False):
        if not skill_gap.empty:
            st.markdown("**O*NET 原始 Skill Gap 名稱**")
            st.dataframe(
                skill_gap,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "skill": st.column_config.TextColumn("O*NET skill", width="large"),
                    "path_count": st.column_config.NumberColumn("path count"),
                },
            )
        st.markdown(
            """
            **讀取檔案**

            - `outputs/career/career_policy_lens_phase7.csv`
            - `outputs/career/career_policy_lens_phase7.md`

            **顯示規則**

            - Exact / Partial / Proxy 標籤保留在青年統計與市場證據解讀中。
            - unresolved NTPC employment / unemployment metadata 不作強政策結論。
            - High=0 顯示「公開市場證據不足」，不解讀為市場不存在。
            - potential training coverage 只表示缺口技能是否找到可能相關課程；不代表課程深度足夠、完整 curriculum 或技能已補足。
            - matched courses 是候選課程集合，不等於完整轉職 curriculum。
            - 只有能證明課程屬於 sequential learning pathway 時，才允許顯示累計時數 / 累計費用；目前 Phase 8 一律未建立 sequential pathway evidence。
            - 不產生轉職成功率、ranking、career score 或政策補助金額。
            """
        )


def render_career_learning_ladder(career_ladder: pd.DataFrame | None) -> None:
    st.markdown("### 青年轉職學習階梯")
    st.caption(
        "把 Skill Gap、Market evidence 與 Training evidence 轉成可檢視的政策介入路徑；"
        "matched courses 是候選課程集合，不是完整轉職 curriculum；本頁顯示單門課程 median/range，不顯示累計轉職成本。"
    )
    if career_ladder is None or career_ladder.empty:
        st.info("尚未載入 Career Learning Ladder Phase 8 輸出。")
        return

    representative_names = [
        "Health Informatics Specialists",
        "Clinical Data Managers",
        "Data Scientists",
        "Hairdressers, Hairstylists, and Cosmetologists",
        "Skincare Specialists",
    ]
    representative = career_ladder[career_ladder["target_occupation_name"].isin(representative_names)].copy()
    if representative.empty:
        representative = career_ladder.head(5).copy()
    representative["_order"] = representative["target_occupation_name"].map(
        {name: index for index, name in enumerate(representative_names)}
    )
    representative = representative.sort_values("_order", na_position="last").drop(columns=["_order"]).head(5)

    for _, row in representative.iterrows():
        _render_learning_ladder_card(row)

    with st.expander("查看完整 8 條 path 與 technical fields", expanded=False):
        technical = career_ladder[
            [
                "target_domain",
                "target_occupation_name",
                "transition_span",
                "policy_intervention_types",
                "market_evidence_status",
                "high_relevance_job_count",
                "medium_relevance_job_count",
                "potential_training_coverage_ratio",
                "matched_course_candidate_count",
                "single_course_hours_median",
                "single_course_hours_min",
                "single_course_hours_max",
                "single_course_fee_median",
                "single_course_fee_min",
                "single_course_fee_max",
                "sequential_learning_pathway_evidence",
                "cumulative_hours_cost_display_allowed",
                "training_evidence_potential_course_found",
                "training_evidence_course_depth",
                "training_evidence_complete_pathway",
                "learning_burden",
                "training_gap_status",
                "phase7_data_limitations",
                "conservative_note",
            ]
        ].copy()
        technical["target_occupation_name"] = technical["target_occupation_name"].map(
            lambda value: f"{_occupation_zh(value)}｜{value}"
        )
        technical["potential_training_coverage_ratio"] = technical["potential_training_coverage_ratio"].map(_format_ratio)
        for column in ["single_course_fee_median", "single_course_fee_min", "single_course_fee_max"]:
            technical[column] = technical[column].map(_format_money)
        st.dataframe(
            technical,
            hide_index=True,
            use_container_width=True,
            column_config={
                "target_domain": st.column_config.TextColumn("探索領域", width="medium"),
                "target_occupation_name": st.column_config.TextColumn("職涯路徑", width="large"),
                "transition_span": st.column_config.TextColumn("轉換跨度"),
                "policy_intervention_types": st.column_config.TextColumn("政策介入類型", width="large"),
                "market_evidence_status": st.column_config.TextColumn("市場證據狀態", width="large"),
                "high_relevance_job_count": st.column_config.NumberColumn("高相關職缺"),
                "medium_relevance_job_count": st.column_config.NumberColumn("待確認職缺"),
                "potential_training_coverage_ratio": st.column_config.TextColumn("缺口技能找到可能相關課程比例"),
                "matched_course_candidate_count": st.column_config.NumberColumn("候選課程數"),
                "single_course_hours_median": st.column_config.NumberColumn("單門課時數 median"),
                "single_course_hours_min": st.column_config.NumberColumn("單門課時數 min"),
                "single_course_hours_max": st.column_config.NumberColumn("單門課時數 max"),
                "single_course_fee_median": st.column_config.TextColumn("單門課費用 median"),
                "single_course_fee_min": st.column_config.TextColumn("單門課費用 min"),
                "single_course_fee_max": st.column_config.TextColumn("單門課費用 max"),
                "sequential_learning_pathway_evidence": st.column_config.TextColumn("sequential pathway evidence"),
                "cumulative_hours_cost_display_allowed": st.column_config.TextColumn("允許顯示累計"),
                "training_evidence_potential_course_found": st.column_config.TextColumn("potential course found"),
                "training_evidence_course_depth": st.column_config.TextColumn("course depth"),
                "training_evidence_complete_pathway": st.column_config.TextColumn("complete pathway"),
                "learning_burden": st.column_config.TextColumn("學習負擔"),
                "training_gap_status": st.column_config.TextColumn("Training Gap 狀態"),
                "phase7_data_limitations": st.column_config.TextColumn("資料限制", width="large"),
                "conservative_note": st.column_config.TextColumn("保守解讀", width="large"),
            },
        )


def _render_learning_ladder_card(row: pd.Series) -> None:
    title = str(row["target_occupation_name"])
    market_status = str(row.get("market_evidence_status", "Unknown"))
    market_needs_validation = _needs_market_validation(row)
    with st.container(border=True):
        heading_cols = st.columns([1.5, 1.0, 1.0], gap="medium")
        with heading_cols[0]:
            st.markdown(f"**{_occupation_zh(title)}**")
            st.caption(title)
        with heading_cols[1]:
            st.markdown("**可考慮的政策介入類型**")
            st.caption(_intervention_zh(str(row.get("policy_intervention_types", ""))))
        with heading_cols[2]:
            st.markdown("**市場證據狀態**")
            if market_needs_validation:
                st.warning("先補市場驗證")
            else:
                st.success("已有高相關市場證據")
            st.caption(_market_status_zh(market_status))

        step_cols = st.columns(5, gap="small")
        steps = [
            ("探索方向", row.get("exploration_direction")),
            ("基礎能力補強", row.get("foundation_skill_boost")),
            ("學習里程碑", row.get("learning_milestone_or_validation")),
            ("進階訓練", row.get("advanced_training")),
            ("市場職缺銜接", row.get("market_job_linkage")),
        ]
        for index, (label, value) in enumerate(steps):
            with step_cols[index]:
                st.markdown(f"**{label}**")
                st.caption(_compact_ladder_text(value))

        metric_cols = st.columns(4, gap="medium")
        with metric_cols[0]:
            st.metric("候選課程數", _format_count(row.get("matched_course_candidate_count")))
        with metric_cols[1]:
            st.metric("單門課程時數", _format_single_course_hours(row))
        with metric_cols[2]:
            st.metric("單門課程費用", _format_single_course_fee(row))
        with metric_cols[3]:
            st.metric("學習負擔", _learning_burden_zh(row.get("learning_burden")))

        st.caption("候選課程未證明為 sequential learning pathway；因此不顯示累計時數 / 累計費用，也不把它解讀為轉職所需總成本。")

        evidence_cols = st.columns(3, gap="medium")
        with evidence_cols[0]:
            st.caption(f"Training evidence：{_training_evidence_zh(row.get('training_evidence_potential_course_found'))}")
        with evidence_cols[1]:
            st.caption(f"課程深度：{_training_evidence_zh(row.get('training_evidence_course_depth'))}")
        with evidence_cols[2]:
            st.caption(f"完整路徑：{_training_evidence_zh(row.get('training_evidence_complete_pathway'))}")

        st.markdown("**證據理由（Evidence reason）**")
        for reason in _reason_lines(row.get("policy_intervention_evidence_reasons")):
            st.caption(f"- {_reason_zh(reason)}")


def _occupation_zh(title: object) -> str:
    translations = {
        "Clinical Research Coordinators": "臨床研究協調員",
        "Health Informatics Specialists": "醫療資訊相關職涯",
        "Clinical Data Managers": "臨床資料管理",
        "Data Scientists": "資料科學家",
        "Hairdressers, Hairstylists, and Cosmetologists": "美容美髮與美容服務",
        "Skincare Specialists": "護膚美容服務",
        "Spa Managers": "美容服務管理",
        "Makeup Artists, Theatrical and Performance": "彩妝造型",
    }
    return translations.get(str(title), str(title))


def _intervention_zh(value: str) -> str:
    translations = {
        "Public learning": "公共學習資源",
        "Training guidance": "訓練導引",
        "Subsidy candidate": "費用負擔檢視",
        "Cohort / partnership candidate": "專班 / 產業合作候選",
        "Market validation needed": "需先補市場驗證",
    }
    parts = [part.strip() for part in str(value).split(";") if part.strip()]
    return "、".join(translations.get(part, part) for part in parts) if parts else "未標示"


def _market_status_zh(value: str) -> str:
    if "High-relevance TaiwanJobs evidence" in value:
        return "既有輸出包含高相關 TaiwanJobs 職缺證據"
    if "Aggregate market evidence only" in value:
        return "目前只有 aggregate market evidence，缺 job-level 高相關驗證"
    if "公開市場證據不足" in value:
        return "公開市場證據不足，不代表職涯不存在"
    return value or "Unknown"


def _needs_market_validation(row: pd.Series) -> bool:
    high = pd.to_numeric(pd.Series([row.get("high_relevance_job_count")]), errors="coerce").iloc[0]
    if pd.isna(high):
        return True
    return float(high) <= 0


def _compact_ladder_text(value: object) -> str:
    text = str(value).strip() if not pd.isna(value) else ""
    if text.lower() == "nan":
        return "目前資料不足"
    return text if text else "目前資料不足"


def _format_hours(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "未提供"
    return f"{numeric:.0f} 小時"


def _format_count(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "未提供"
    return f"{numeric:.0f}"


def _format_single_course_hours(row: pd.Series) -> str:
    return _format_median_range(
        row.get("single_course_hours_median"),
        row.get("single_course_hours_min"),
        row.get("single_course_hours_max"),
        "小時",
    )


def _format_single_course_fee(row: pd.Series) -> str:
    return _format_median_range(
        row.get("single_course_fee_median"),
        row.get("single_course_fee_min"),
        row.get("single_course_fee_max"),
        "NT$",
    )


def _format_median_range(median: object, low: object, high: object, unit: str) -> str:
    median_num = pd.to_numeric(pd.Series([median]), errors="coerce").iloc[0]
    low_num = pd.to_numeric(pd.Series([low]), errors="coerce").iloc[0]
    high_num = pd.to_numeric(pd.Series([high]), errors="coerce").iloc[0]
    if pd.isna(median_num) or pd.isna(low_num) or pd.isna(high_num):
        return "未知"
    if unit == "NT$":
        return f"NT$ {median_num:,.0f}（{low_num:,.0f}-{high_num:,.0f}）"
    return f"{median_num:,.0f} {unit}（{low_num:,.0f}-{high_num:,.0f}）"


def _format_cost_metric(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "未提供"
    return f"NT$ {numeric:,.0f}"


def _training_evidence_zh(value: object) -> str:
    translations = {
        "potential course found": "找到可能相關課程",
        "no matched course found": "目前未找到明確對應課程",
        "course depth unknown": "課程深度未知",
        "complete pathway unknown": "完整轉職課程路徑未知",
    }
    return translations.get(str(value).strip(), str(value))


def _learning_burden_zh(value: object) -> str:
    translations = {"low": "低", "medium": "中", "high": "高"}
    return translations.get(str(value).strip().lower(), str(value))


def _reason_lines(value: object) -> list[str]:
    text = str(value).strip() if not pd.isna(value) else ""
    if not text:
        return ["目前沒有可顯示的 evidence reason。"]
    return [part.strip() for part in text.split(" | ") if part.strip()]


def _reason_zh(reason: str) -> str:
    text = reason
    text = text.replace("Missing skills include standardizable foundations:", "缺口技能包含適合標準化教材的基礎能力：")
    text = text.replace("Matched course evidence exists", "已有對應課程證據")
    text = re.sub(
        r"\((\d+) courses\), while MOL proxy shows ([\d.]+)% of non-participants did not know where training was available\.",
        r"（\1 門課）；MOL 代理指標顯示未參訓者中有 \2% 不知道去哪裡找訓練課程。",
        text,
    )
    text = re.sub(
        r"Matched course candidate set includes at least one higher-burden single course \(single-course hours (.+?); single-course fee (.+?)\); MOL proxy fee barrier is ([\d.]+)% among non-participants\.",
        r"候選課程集合中至少有一門課呈現較高時數或費用負擔（單門課時數 \1；單門課費用 \2）；MOL 代理指標顯示未參訓者中有 \3% 主因為費用太高。",
        text,
    )
    text = text.replace("Candidate courses are not summed because no sequential learning pathway is established.", "因目前未建立 sequential learning pathway evidence，不加總候選課程時數或費用。")
    text = re.sub(
        r"Market has High-relevance evidence \((\d+) jobs\) and skill gap is explicit, but potential training coverage is only ([\d.]+)\.",
        r"市場已有高相關職缺證據（\1 筆），且 skill gap 明確，但潛在課程覆蓋只有 \2。",
        text,
    )
    text = text.replace("Existing output has aggregate market evidence only; job-level High-relevance evidence is unavailable.", "既有輸出目前只有 aggregate market evidence，尚無 job-level 高相關職缺證據。")
    text = text.replace("High=0 in existing TaiwanJobs evidence; treat as public market evidence insufficient, not market absence.", "既有 TaiwanJobs evidence 的 High=0，應解讀為公開市場證據不足，不是市場不存在。")
    text = text.replace("No subsidy amount is proposed.", "不設定補助金額。")
    text = text.replace("Skill gap and course-supply gap are visible, but market validation must come first because High-relevance job evidence is unavailable or zero.", "已有 skill gap 與課程供給缺口訊號，但高相關職缺證據不足時，應先補市場驗證。")
    return text


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _format_ratio(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "未提供"
    return f"{numeric * 100:.1f}%"


def _format_money(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "未提供"
    return f"{numeric:,.0f}"


def _common_skill_gaps(career_policy: pd.DataFrame) -> pd.DataFrame:
    counts: dict[str, int] = {}
    for value in career_policy["missing_skills_preview"].fillna(""):
        for skill in [part.strip() for part in str(value).split(";") if part.strip()]:
            if skill == "none" or skill.startswith("..."):
                continue
            counts[skill] = counts.get(skill, 0) + 1
    rows = [{"skill": skill, "path_count": count} for skill, count in counts.items()]
    if not rows:
        return pd.DataFrame(columns=["skill", "path_count"])
    return pd.DataFrame(rows).sort_values(["path_count", "skill"], ascending=[False, True]).reset_index(drop=True)


def _skill_zh(skill: str) -> str:
    translations = {
        "Programming": "程式設計",
        "Computers and Electronics": "電腦與電子",
        "Mathematics": "數學",
        "Sales and Marketing": "銷售與行銷",
        "Personnel and Human Resources": "人事與人力資源",
        "Design": "設計",
        "Management of Personnel Resources": "人力資源管理",
        "Persuasion": "說服溝通",
        "Engineering and Technology": "工程與科技",
        "Fine Arts": "美術與藝術",
        "Management of Financial Resources": "財務資源管理",
        "Economics and Accounting": "經濟與會計",
    }
    return translations.get(str(skill), str(skill))


def _market_summary(career_policy: pd.DataFrame) -> pd.DataFrame:
    display = career_policy[
        [
            "target_domain",
            "target_occupation_name",
            "market_evidence_status",
            "high_relevance_job_count",
            "medium_relevance_job_count",
            "high_relevance_demand_persons",
        ]
    ].copy()
    for column in ["high_relevance_job_count", "medium_relevance_job_count", "high_relevance_demand_persons"]:
        display[column] = pd.to_numeric(display[column], errors="coerce")
    display["market_evidence_status"] = display["market_evidence_status"].fillna("Unknown")
    display.loc[display["high_relevance_job_count"].fillna(-1).eq(0), "market_evidence_status"] = "公開市場證據不足"
    return display


def _extract_policy_observations(markdown_text: str) -> list[str]:
    if not markdown_text:
        return [
            "新北 18–35 人口可 Exact 對齊；MOL 轉職與培訓訊號為全台 15–29 Proxy。",
            "結構可行、台灣市場證據與訓練負擔必須分開看，不能合成成功率。",
            "High=0 應解讀為公開市場證據不足，不代表職涯不存在。",
        ]
    marker = "## Data-Supported Policy Observations"
    next_marker = "\n## "
    if marker not in markdown_text:
        return []
    section = markdown_text.split(marker, 1)[1]
    if next_marker in section:
        section = section.split(next_marker, 1)[0]
    observations = []
    for line in section.splitlines():
        line = line.strip()
        match = re.match(r"^\d+\.\s+(.+)$", line)
        if match:
            observations.append(_translate_policy_observation(match.group(1)))
    return observations


def _translate_policy_observation(text: str) -> str:
    translations = {
        "The youth denominator is solid for population but mixed for labor evidence: New Taipei 18-35 population is Exact, while MOL transition/training indicators are national 15-29 Proxy evidence.": "青年人口母體可精準掌握，但勞動與培訓訊號仍是混合證據：新北 18–35 人口為 Exact，MOL 轉職 / 培訓指標是全台 15–29 Proxy。",
        "Several explored paths are structurally feasible from nursing, but market validation strength differs by output: beauty service roles have job-level High relevance evidence; technology paths currently have aggregate market evidence only in the existing v4 output.": "多條護理出發的轉職路徑在結構上可行，但市場證據強度不同：美容服務類已有 job-level 高相關職缺證據，科技路徑在既有 v4 output 仍只有 aggregate market evidence。",
        "Common cross-domain skill gaps cluster around technology/data skills and business-facing skills, especially Programming, Computers and Electronics, Mathematics, and Sales and Marketing.": "跨域常見缺口集中在科技 / 資料能力與商業面能力，尤其是 Programming、Computers and Electronics、Mathematics、Sales and Marketing。",
        "Potential course coverage exists for many missing skills, but it varies by path and should be read with hours/cost. It is not proof that skills are fully acquired.": "多數缺口技能可以找到潛在課程覆蓋，但各路徑的時數與費用差異很大；這不代表技能已被補足。",
        "Paths with High=0 should be treated as public market evidence gaps, not evidence that the career does not exist.": "High=0 的路徑應解讀為公開市場證據不足，不代表該職涯不存在。",
    }
    return translations.get(text, text)


def build_policy_map(
    policy: pd.DataFrame,
    towns: gpd.GeoDataFrame,
    cities: gpd.GeoDataFrame,
    view: str,
    district_analysis_layer: str = DISTRICT_ANALYSIS_LAYER_NONE,
    basemap: str = POLICY_BASEMAP_MINIMAL,
) -> folium.Map:
    view_config = POLICY_VIEWS[view]
    values = policy[view_config["field"]]
    min_value = float(values.min())
    max_value = float(values.max())
    color_map = LinearColormap(
        colors=[view_config["low_color"], view_config["high_color"]],
        vmin=min_value,
        vmax=max_value,
    )

    map_obj = folium.Map(
        location=[25.04, 121.50],
        zoom_start=10,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )
    _add_policy_basemap(map_obj, basemap)
    _fit_policy_bounds(map_obj, policy)
    _add_policy_boundaries(map_obj, towns, cities)
    _add_policy_district_analysis_layer(map_obj, towns, district_analysis_layer)

    for _, row in policy.iterrows():
        value = float(row[view_config["field"]])
        radius = _scaled_radius(value, min_value, max_value)
        color = color_map(value)
        if view == "生活機能":
            tooltip = _livability_tooltip(row)
        elif view == "政策型租賃樣本":
            tooltip = _policy_sample_tooltip(row)
        elif view == "公共運輸可達性":
            tooltip = (
                f"{row['living_area']}｜median {row['commute_accessibility_minutes']:.1f} min｜"
                f"{int(row['commute_accessibility_workplace_count'])} workplaces"
            )
        else:
            tooltip = (
                f"{row['living_area']}｜{money(row['official_median_rent'])} NTD/month｜"
                f"{int(row['official_contract_count'])} official contracts"
            )

        folium.CircleMarker(
            location=[float(row["lat"]), float(row["lon"])],
            radius=radius,
            color="#FFFFFF",
            weight=2.0,
            fill=True,
            fill_color=color,
            fill_opacity=0.90,
            opacity=0.95,
            tooltip=tooltip,
            popup=_policy_popup(row),
        ).add_to(map_obj)

    _add_city_label(map_obj, 25.095, 121.405, "新北市")
    _add_city_label(map_obj, 25.045, 121.555, "臺北市")
    _add_policy_legend(map_obj, view_config, min_value, max_value)
    _add_policy_district_analysis_legend(map_obj, towns, district_analysis_layer)
    return map_obj


def render_view_explainer(view: str) -> None:
    view_config = POLICY_VIEWS[view]
    st.html(
        f"""
        <div class="qj-policy-panel">
            <div class="qj-policy-eyebrow">目前視角</div>
            <div class="qj-policy-panel-title">{html.escape(view_config['title'])}</div>
            <div class="qj-policy-panel-copy">{html.escape(view_config['caption'])}</div>
            <div class="qj-policy-mini-note">{html.escape(view_config['higher_label'])}</div>
        </div>
        """
    )


def render_candidate_detail(row: pd.Series) -> None:
    share = float(row["policy_linked_record_share"])
    sample_warning = ""
    if int(row["total_rental_record_count"]) < SMALL_SAMPLE_THRESHOLD:
        sample_warning = '<div class="qj-policy-warning">小樣本，請謹慎解讀</div>'
    district_context = _district_context_for_candidate(row)
    st.html(
        f"""
        <div class="qj-policy-detail">
            <div class="qj-policy-detail-title">{html.escape(str(row['living_area']))}</div>
            <div class="qj-policy-detail-subtitle">{html.escape(str(row['candidate_name']))}｜{html.escape(str(row['district']))}｜{html.escape(str(row['policy_quadrant']))}</div>
            <div class="qj-policy-metric-grid">
                <div><span>租金</span><b>{money(row['official_median_rent'])}</b><small>NTD/month</small></div>
                <div><span>公共運輸可達性</span><b>{float(row['commute_accessibility_minutes']):.1f}</b><small>min</small></div>
                <div><span>生活機能 proxy</span><b>{float(row['livability_index']):.3f}</b><small>OSM 800m</small></div>
                <div><span>政策型租賃相關登錄樣本</span><b>{share * 100:.1f}%</b><small>{int(row['policy_linked_record_count'])} / {int(row['total_rental_record_count'])}</small></div>
            </div>
            <div class="qj-policy-mini-note">{html.escape(district_context)}</div>
            {sample_warning}
            <div class="qj-policy-description">{html.escape(_describe_candidate(row))}</div>
        </div>
        """
    )


def build_policy_scatter(policy: pd.DataFrame):
    _configure_matplotlib()
    rent_threshold = float(policy["official_median_rent"].median())
    commute_threshold = float(policy["commute_accessibility_minutes"].median())

    fig, ax = plt.subplots(figsize=(12.2, 6.6))
    scatter = ax.scatter(
        policy["commute_accessibility_minutes"],
        policy["official_median_rent"],
        c=policy["livability_index"],
        cmap="YlGnBu",
        s=120,
        edgecolor="white",
        linewidth=1.2,
        alpha=0.92,
    )
    ax.axhline(rent_threshold, color="#9AA7AA", linewidth=1.2, linestyle=(0, (5, 5)))
    ax.axvline(commute_threshold, color="#9AA7AA", linewidth=1.2, linestyle=(0, (5, 5)))

    label_candidates = set(
        policy.sort_values("official_median_rent", ascending=False).head(3)["candidate_name"].tolist()
        + policy.sort_values("commute_accessibility_minutes", ascending=False).head(3)["candidate_name"].tolist()
        + policy.sort_values("livability_index", ascending=False).head(2)["candidate_name"].tolist()
    )
    for _, row in policy[policy["candidate_name"].isin(label_candidates)].iterrows():
        ax.annotate(
            row["candidate_name"],
            (row["commute_accessibility_minutes"], row["official_median_rent"]),
            xytext=(7, 5),
            textcoords="offset points",
            fontsize=9,
            color="#243238",
        )

    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    ax.text(x_min + 1, y_max - 700, "較高租金 × 較短通勤", color="#58676D", fontsize=10, weight="bold")
    ax.text(commute_threshold + 1, y_max - 700, "較高租金 × 較長通勤", color="#58676D", fontsize=10, weight="bold")
    ax.text(x_min + 1, y_min + 700, "較低租金 × 較短通勤", color="#58676D", fontsize=10, weight="bold")
    ax.text(commute_threshold + 1, y_min + 700, "較低租金 × 較長通勤", color="#58676D", fontsize=10, weight="bold")

    ax.set_xlabel("公共運輸可達性（分鐘；越右 = 可達性越弱）")
    ax.set_ylabel("行政區租金中位數（NTD／月）")
    ax.set_title("租金 × 公共運輸可達性壓力篩選", loc="left", fontsize=15, weight="bold")
    ax.grid(True, color="#E5EBEC", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#B8C2C5")
    colorbar = fig.colorbar(scatter, ax=ax, shrink=0.86, pad=0.02)
    colorbar.set_label("生活機能 proxy（OSM 800m）")
    fig.tight_layout()
    return fig


def render_policy_method_notes() -> None:
    st.markdown(
        """
        <div class="qj-note">
        <b>資料與方法限制</b><br>
        租金是行政區尺度 MOI 獨立套房官方 benchmark，不是站點周邊即時房租。<br>
        commute 是候選生活圈代表節點到現有 workplace anchors 的公共運輸 proxy。<br>
        livability 是 OSM 800m POI proxy，不代表完整生活品質。<br>
        policy-linked share 是租賃登錄樣本結構，不是市場占比、政策住宅供給率或青年租屋占比。<br>
        租賃資料沒有承租人年齡，因此不可稱為青年租賃案件。<br>
        青年人口多只代表可能影響規模較大，不等於政策一定優先；本階段不直接提出社宅、公園、共居等政策處方。<br>
        Policy Lens 是 screening tool，不是因果分析或正式政策排序。
        </div>
        """,
        unsafe_allow_html=True,
    )


def _add_policy_basemap(map_obj: folium.Map, basemap: str) -> None:
    if basemap == POLICY_BASEMAP_STREET:
        folium.TileLayer(
            tiles="OpenStreetMap",
            name=POLICY_BASEMAP_STREET,
            overlay=False,
            control=False,
            show=True,
        ).add_to(map_obj)
        return

    _add_policy_minimal_background_style(map_obj)
    folium.TileLayer(
        tiles=TRANSPARENT_TILE_DATA_URI,
        name=POLICY_BASEMAP_MINIMAL,
        attr="Local transparent background",
        overlay=False,
        control=False,
        show=True,
    ).add_to(map_obj)


def _add_policy_minimal_background_style(map_obj: folium.Map) -> None:
    template = Template(
        """
        {% macro html(this, kwargs) %}
        <style>
          .leaflet-container {
            background: #F6F3EC;
          }
        </style>
        {% endmacro %}
        """
    )
    macro = MacroElement()
    macro._template = template
    map_obj.get_root().add_child(macro)


def _fit_policy_bounds(map_obj: folium.Map, policy: pd.DataFrame) -> None:
    bounds = [
        [max(24.91, float(policy["lat"].min()) - 0.04), max(121.30, float(policy["lon"].min()) - 0.05)],
        [min(25.24, float(policy["lat"].max()) + 0.04), min(121.72, float(policy["lon"].max()) + 0.05)],
    ]
    map_obj.fit_bounds(bounds, padding=(12, 12))


def _add_policy_boundaries(map_obj: folium.Map, towns: gpd.GeoDataFrame, cities: gpd.GeoDataFrame) -> None:
    taipei_towns = towns[towns["COUNTYNAME"] == "臺北市"]
    ntpc_towns = towns[towns["COUNTYNAME"] == "新北市"]
    folium.GeoJson(
        taipei_towns,
        name="taipei context",
        style_function=lambda _: {
            "fillColor": "#F3F5F4",
            "color": "#D4DCDE",
            "weight": 0.7,
            "opacity": 0.55,
            "fillOpacity": 0.12,
        },
    ).add_to(map_obj)
    folium.GeoJson(
        ntpc_towns,
        name="ntpc district boundary",
        style_function=lambda _: {
            "fillColor": "#FFFFFF",
            "color": "#C8D2D4",
            "weight": 0.95,
            "opacity": 0.75,
            "fillOpacity": 0.07,
        },
        tooltip=folium.GeoJsonTooltip(fields=["TOWNNAME"], labels=False),
    ).add_to(map_obj)

    def city_style(feature: dict) -> dict:
        city = feature["properties"].get("COUNTYNAME")
        return {
            "fillColor": "#FFFFFF",
            "color": "#728D79" if city == "新北市" else "#7890A0",
            "weight": 3.0 if city == "新北市" else 2.0,
            "opacity": 0.92 if city == "新北市" else 0.58,
            "fillOpacity": 0.0,
        }

    folium.GeoJson(
        cities,
        name="city boundary",
        style_function=city_style,
        tooltip=folium.GeoJsonTooltip(fields=["COUNTYNAME"], labels=False),
    ).add_to(map_obj)


def _add_policy_district_analysis_layer(
    map_obj: folium.Map,
    towns: gpd.GeoDataFrame,
    analysis_layer: str,
) -> None:
    if analysis_layer == DISTRICT_ANALYSIS_LAYER_NONE or analysis_layer not in POLICY_DISTRICT_ANALYSIS_CONFIG:
        return
    config = POLICY_DISTRICT_ANALYSIS_CONFIG[analysis_layer]
    field = str(config["field"])
    values = pd.to_numeric(towns[field], errors="coerce") if field in towns.columns else pd.Series(dtype=float)
    valid_values = values.dropna()
    color_map = None
    if not valid_values.empty:
        color_map = LinearColormap(
            colors=[str(config["low_color"]), str(config["high_color"])],
            vmin=float(valid_values.min()),
            vmax=float(valid_values.max()),
        )

    def analysis_style(feature: dict[str, object]) -> dict[str, object]:
        properties = feature.get("properties", {})
        value = properties.get(field) if isinstance(properties, dict) else None
        has_value = value is not None and not pd.isna(value)
        fill_color = color_map(float(value)) if has_value and color_map is not None else "#EFF1F0"
        return {
            "fillColor": fill_color,
            "color": "#8FA0A4" if has_value else "#C7D0D2",
            "weight": 0.80 if has_value else 0.56,
            "opacity": 0.64 if has_value else 0.38,
            "fillOpacity": 0.32 if has_value else 0.12,
        }

    folium.GeoJson(
        towns,
        name=analysis_layer,
        style_function=analysis_style,
        control=False,
        tooltip=_policy_district_analysis_tooltip(),
    ).add_to(map_obj)


def _policy_district_analysis_tooltip() -> folium.GeoJsonTooltip:
    return folium.GeoJsonTooltip(
        fields=[
            "TOWNNAME",
            "youth_population_18_35_display",
            "youth_population_share_display",
            "district_total_population_display",
            "youth_population_source_period_display",
            "youth_population_precision_display",
        ],
        aliases=[
            "行政區",
            "18–35 青年人口數",
            "18–35 青年人口占比",
            "行政區總人口",
            "資料期別",
            "資料精度",
        ],
        labels=True,
        sticky=False,
        localize=False,
    )


def _scaled_radius(value: float, min_value: float, max_value: float) -> float:
    if max_value == min_value:
        return 10.0
    return 6.0 + ((value - min_value) / (max_value - min_value)) * 11.0


def _policy_popup(row: pd.Series) -> folium.Popup:
    warning = ""
    if int(row["total_rental_record_count"]) < SMALL_SAMPLE_THRESHOLD:
        warning = '<div style="color:#A15C2F;font-weight:700;margin-top:5px;">小樣本，請謹慎解讀</div>'
    html_body = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-width:235px;">
      <div style="font-weight:850;font-size:16px;margin-bottom:2px;">{html.escape(str(row['living_area']))}</div>
      <div style="color:#65747A;margin-bottom:8px;">{html.escape(str(row['candidate_name']))}｜{html.escape(str(row['district']))}</div>
      <div>租金：<b>{money(row['official_median_rent'])} NTD/month</b></div>
      <div>公共運輸可達性：<b>{float(row['commute_accessibility_minutes']):.1f} min</b></div>
      <div>生活機能 proxy：<b>{float(row['livability_index']):.3f}</b></div>
      <div>政策型租賃相關登錄樣本：<b>{float(row['policy_linked_record_share']) * 100:.1f}%</b> ({int(row['policy_linked_record_count'])} / {int(row['total_rental_record_count'])})</div>
      <div style="color:#65747A;margin-top:6px;">{html.escape(str(row['policy_quadrant']))}</div>
      {warning}
    </div>
    """
    return folium.Popup(html_body, max_width=320)


def _livability_tooltip(row: pd.Series) -> str:
    pieces = [
        f"{row['living_area']}｜livability {float(row['livability_index']):.3f}",
    ]
    if "food_count" in row and not pd.isna(row["food_count"]):
        pieces.append(
            "餐飲 {food}｜採買 {shopping}｜休閒 {recreation}｜文娛 {culture}｜醫療 {medical}".format(
                food=int(row["food_count"]),
                shopping=int(row["shopping_count"]),
                recreation=int(row["recreation_count"]),
                culture=int(row["culture_count"]),
                medical=int(row["medical_count"]),
            )
        )
    return "｜".join(pieces)


def _policy_sample_tooltip(row: pd.Series) -> str:
    warning = "｜小樣本，請謹慎解讀" if int(row["total_rental_record_count"]) < SMALL_SAMPLE_THRESHOLD else ""
    return (
        f"{row['living_area']}｜{float(row['policy_linked_record_share']) * 100:.1f}%"
        f"（{int(row['policy_linked_record_count'])} / {int(row['total_rental_record_count'])}）{warning}"
    )


def _district_context_for_candidate(row: pd.Series) -> str:
    district = str(row["district"])
    district_analysis = load_district_analysis_table()
    matches = district_analysis[(district_analysis["city"] == "新北市") & (district_analysis["district"] == district)]
    if matches.empty:
        youth_population = "unresolved"
        youth_share = "unresolved"
        total_population = "unresolved"
        source_period = "unresolved"
        precision = "unresolved"
        rent = f"{money(row['official_median_rent'])} NTD/month"
    else:
        context = matches.iloc[0]
        youth_population = str(context.get("youth_population_18_35_display", "unresolved"))
        youth_share = str(context.get("youth_population_share_display", "unresolved"))
        total_population = str(context.get("district_total_population_display", "unresolved"))
        source_period = str(context.get("youth_population_source_period_display", "unresolved"))
        precision = str(context.get("youth_population_precision_display", "unresolved"))
        rent = str(context.get("official_median_rent_display", "unresolved"))
    return (
        f"所在行政區背景：{row['living_area']} → {district}｜"
        f"18–35 青年人口數 {youth_population}｜青年占比 {youth_share}｜行政區總人口 {total_population}｜"
        f"資料期別 {source_period}｜資料精度 {precision}｜行政區租金 {rent}。"
        "行政區人口不可解讀為 1km / 2km 生活圈人口。"
    )


def _candidate_from_click(policy: pd.DataFrame, map_state: dict | None) -> str | None:
    if not map_state or not map_state.get("last_object_clicked"):
        return None
    clicked = map_state["last_object_clicked"]
    if clicked.get("lat") is None or clicked.get("lng") is None:
        return None
    lat = float(clicked["lat"])
    lon = float(clicked["lng"])
    distances = (policy["lat"] - lat).abs() + (policy["lon"] - lon).abs()
    closest_index = distances.idxmin()
    if float(distances.loc[closest_index]) > 0.01:
        return None
    return str(policy.loc[closest_index, "candidate_name"])


def _describe_candidate(row: pd.Series) -> str:
    rent = "較高租金" if "高租金" in row["policy_quadrant"] else "較低租金"
    commute = "較長通勤" if "長通勤" in row["policy_quadrant"] else "較短通勤"
    livability = float(row["livability_index"])
    if livability >= 0.6:
        livability_text = "生活機能 proxy 在候選中相對較高"
    elif livability >= 0.3:
        livability_text = "生活機能 proxy 屬中間程度"
    else:
        livability_text = "生活機能 proxy 相對較弱"
    return f"目前資料顯示此生活圈位於「{rent} × {commute}」象限；{livability_text}。此描述僅供政策篩選，不代表政策優先順序。"


def _add_city_label(map_obj: folium.Map, lat: float, lon: float, label: str) -> None:
    folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(
            html=(
                '<div style="font-size:16px;font-weight:850;color:#52646B;'
                'text-shadow:0 0 5px white,0 0 7px white;white-space:nowrap;">'
                f"{html.escape(label)}</div>"
            ),
            icon_size=(70, 24),
            icon_anchor=(35, 12),
        ),
    ).add_to(map_obj)


def _add_policy_legend(map_obj: folium.Map, view_config: dict[str, str], min_value: float, max_value: float) -> None:
    if view_config["unit"] == "share":
        min_label = f"{min_value * 100:.1f}%"
        max_label = f"{max_value * 100:.1f}%"
    elif view_config["unit"] == "NTD/month":
        min_label = f"{money(min_value)}"
        max_label = f"{money(max_value)}"
    elif view_config["unit"] == "min":
        min_label = f"{min_value:.1f}"
        max_label = f"{max_value:.1f}"
    else:
        min_label = f"{min_value:.3f}"
        max_label = f"{max_value:.3f}"
    template = Template(
        f"""
        {{% macro html(this, kwargs) %}}
        <div style="
            position: fixed;
            right: 24px;
            bottom: 28px;
            z-index: 9999;
            background: rgba(255,255,255,0.94);
            border: 1px solid #D6DDE0;
            border-radius: 10px;
            padding: 10px 12px;
            color: #243238;
            font-size: 13px;
            box-shadow: 0 1px 4px rgba(36,50,56,0.10);
            min-width: 190px;
        ">
          <div style="font-weight:850;margin-bottom:7px;">{html.escape(view_config['title'])}</div>
          <div style="height:10px;border-radius:999px;background:linear-gradient(90deg,{view_config['low_color']},{view_config['high_color']});margin-bottom:5px;"></div>
          <div style="display:flex;justify-content:space-between;color:#65747A;font-size:12px;"><span>{min_label}</span><span>{max_label}</span></div>
          <div style="margin-top:7px;color:#65747A;">{html.escape(view_config['higher_label'])}</div>
          <div style="margin-top:6px;"><span style="display:inline-block;width:18px;border-top:3px solid #728D79;margin-right:6px;"></span>新北市外框</div>
        </div>
        {{% endmacro %}}
        """
    )
    macro = MacroElement()
    macro._template = template
    map_obj.get_root().add_child(macro)


def _add_policy_district_analysis_legend(
    map_obj: folium.Map,
    towns: gpd.GeoDataFrame,
    analysis_layer: str,
) -> None:
    if analysis_layer == DISTRICT_ANALYSIS_LAYER_NONE or analysis_layer not in POLICY_DISTRICT_ANALYSIS_CONFIG:
        return
    config = POLICY_DISTRICT_ANALYSIS_CONFIG[analysis_layer]
    field = str(config["field"])
    values = pd.to_numeric(towns[field], errors="coerce") if field in towns.columns else pd.Series(dtype=float)
    valid_values = values.dropna()
    if valid_values.empty:
        min_label = "unresolved"
        max_label = "unresolved"
        bar_style = "background:#EFF1F0;border:1px solid #C7D0D2;"
        note = str(config["missing_label"])
    else:
        min_value = float(valid_values.min())
        max_value = float(valid_values.max())
        min_label = _policy_analysis_value_label(min_value, str(config["unit"]))
        max_label = _policy_analysis_value_label(max_value, str(config["unit"]))
        bar_style = f"background:linear-gradient(90deg,{config['low_color']},{config['high_color']});"
        note = str(config["higher_label"])
    template = Template(
        f"""
        {{% macro html(this, kwargs) %}}
        <div style="
            position: fixed;
            left: 24px;
            bottom: 28px;
            z-index: 9998;
            background: rgba(255,255,255,0.94);
            border: 1px solid #D6DDE0;
            border-radius: 10px;
            padding: 10px 12px;
            color: #243238;
            font-size: 13px;
            box-shadow: 0 1px 4px rgba(36,50,56,0.10);
            min-width: 214px;
            max-width: 290px;
        ">
          <div style="font-weight:850;margin-bottom:7px;">行政區背景：{html.escape(str(config['title']))}</div>
          <div style="height:10px;border-radius:999px;{bar_style}margin-bottom:5px;"></div>
          <div style="display:flex;justify-content:space-between;color:#65747A;font-size:12px;"><span>{min_label}</span><span>{max_label}</span></div>
          <div style="margin-top:7px;color:#65747A;line-height:1.35;">{html.escape(note)}</div>
        </div>
        {{% endmacro %}}
        """
    )
    macro = MacroElement()
    macro._template = template
    map_obj.get_root().add_child(macro)


def _policy_analysis_value_label(value: float, unit: str) -> str:
    if unit == "share":
        return f"{value * 100:.1f}%"
    if unit == "NTD/month":
        return f"{money(value)}"
    if unit == "people":
        return f"{value:,.0f}"
    return f"{value:.2f}"


def _configure_matplotlib() -> None:
    candidates = [
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            fm.fontManager.addfont(candidate)
            prop = fm.FontProperties(fname=candidate)
            plt.rcParams["font.family"] = prop.get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 150
