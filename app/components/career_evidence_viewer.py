from __future__ import annotations

import re
from html import escape
from textwrap import dedent

import pandas as pd
import streamlit as st


DEMO_SOURCE = "Registered Nurses"
DEMO_TARGET_DOMAIN = "Technology / AI"
DEMO_HORIZON = "6 months"
TARGET_DOMAIN_OPTIONS = ["科技 / AI", "美容 / 醫美 / 個人照護"]
DOMAIN_OUTPUT_LABELS = {
    "科技 / AI": "Technology / AI",
    "美容 / 醫美 / 個人照護": "Beauty / Aesthetic / Personal Care",
}
TECH_REPRESENTATIVE_PATHS = [
    "Clinical Research Coordinators",
    "Clinical Data Managers",
    "Health Informatics Specialists",
    "Data Scientists",
]
BEAUTY_REPRESENTATIVE_PATHS = [
    "First-Line Supervisors of Personal Service Workers",
    "Skincare Specialists",
    "Hairdressers, Hairstylists, and Cosmetologists",
    "Manicurists and Pedicurists",
]
BEAUTY_FULL_PATH_ORDER = [
    "First-Line Supervisors of Personal Service Workers",
    "Skincare Specialists",
    "Massage Therapists",
    "Hairdressers, Hairstylists, and Cosmetologists",
    "Barbers",
    "Shampooers",
    "Manicurists and Pedicurists",
    "Makeup Artists, Theatrical and Performance",
    "Retail Salespersons",
    "Door-to-Door Sales Workers, News and Street Vendors, and Related Workers",
    "Spa Managers",
    "Dermatologists",
]
PATH_NOTES = {
    "Data Scientists": "大幅重新學習對照組",
    "Health Informatics Specialists": "課程覆蓋缺口",
    "First-Line Supervisors of Personal Service Workers": "市場證據不足",
    "Manicurists and Pedicurists": "大幅重新學習路徑",
}
PATH_INTROS = {
    "Clinical Research Coordinators": "把護理現場經驗延伸到臨床研究流程、受試者溝通與資料紀錄協調。",
    "Clinical Data Managers": "把臨床理解轉成資料整理、品質控管與研究資料管理能力。",
    "Health Informatics Specialists": "結合護理知識與資訊系統，協助醫療流程數位化與系統導入。",
    "Data Scientists": "轉向以程式、數學與資料分析為核心的科技職涯，作為大幅重新學習對照組。",
    "First-Line Supervisors of Personal Service Workers": "把護理現場的照護、溝通與服務流程經驗，轉向美容或個人服務現場管理。",
    "Skincare Specialists": "把皮膚、照護與衛教溝通背景，延伸到護膚、醫美諮詢或美體服務。",
    "Massage Therapists": "把身體評估、照護溝通與服務經驗，轉向芳療、舒壓與身體照護服務。",
    "Hairdressers, Hairstylists, and Cosmetologists": "轉向美髮與美容服務技術，市場職缺較明確，但需要重新學習手作技術。",
    "Barbers": "轉向剪髮與造型服務，公開職缺較明確，但核心技術需要重新訓練。",
    "Shampooers": "從入門美髮助理或洗護服務切入，門檻較低但屬於重新學習。",
    "Manicurists and Pedicurists": "轉向美甲與手足保養，課程供給明確，但目前公開職缺證據不足。",
    "Makeup Artists, Theatrical and Performance": "轉向彩妝與整體造型，課程供給可見，但公開職缺證據不足。",
    "Retail Salespersons": "轉向美容、保養品或醫美服務銷售，可能沿用溝通與信任建立能力，但職稱 mapping 仍需確認。",
    "Door-to-Door Sales Workers, News and Street Vendors, and Related Workers": "對應 O*NET 的 beauty consultant alias，較像美容產品或服務顧問，需要台灣職稱人工確認。",
    "Spa Managers": "轉向 spa 或美容服務營運管理，管理技能缺口較明顯，台灣職缺 mapping 仍不足。",
    "Dermatologists": "與皮膚醫療高度相關，但屬醫師職涯，教育與證照門檻過高，主要作為高門檻對照。",
}
PATH_CONCLUSIONS = {
    "Clinical Research Coordinators": "你不需要完全從零開始，但需要先確認台灣臨床研究入口職缺與職稱。",
    "Clinical Data Managers": "需要補強資料管理與分析能力，目前公開職缺多屬待確認候選。",
    "Health Informatics Specialists": "能利用護理現場知識，但台灣醫療資訊職稱 mapping 仍不完整。",
    "Data Scientists": "屬於大幅重新學習的跨域路徑，需要補強資料與科技能力。",
    "First-Line Supervisors of Personal Service Workers": "可沿用服務與現場協調能力，但目前公開職缺不足以確認市場規模。",
    "Skincare Specialists": "能利用護理的皮膚照護與客戶信任基礎，但仍需補美容/護膚實作技能。",
    "Massage Therapists": "照護溝通與身體知識可部分沿用，但按摩/芳療技術仍需訓練。",
    "Hairdressers, Hairstylists, and Cosmetologists": "這不是從護理自然延伸的路徑，但市場職缺與課程都可追溯，適合作為 major-reskilling path。",
    "Barbers": "與護理技能相似度不應作為排除理由；若使用者明確想跨入美髮，可用課程與職缺再驗證。",
    "Shampooers": "可作為低門檻切入美容服務現場的重新學習路徑。",
    "Manicurists and Pedicurists": "課程供給明確，但目前公開職缺證據不足，不代表市場不存在。",
    "Makeup Artists, Theatrical and Performance": "屬於大幅重新學習，課程供給可見，但職缺證據仍弱。",
    "Retail Salespersons": "可能沿用諮詢與銷售溝通能力，但目前只有待確認職缺，不能納入主要市場統計。",
    "Door-to-Door Sales Workers, News and Street Vendors, and Related Workers": "O*NET 有 beauty consultant alias，但台灣職稱對應不穩，需要人工 review。",
    "Spa Managers": "管理與服務流程可部分沿用，但目前公開市場證據不足。",
    "Dermatologists": "雖然臨床知識重疊高，但短期轉換不合理，應因醫師教育/證照門檻排除。",
}
OCCUPATION_ZH = {
    "Registered Nurses": "護理師",
    "Clinical Research Coordinators": "臨床研究協調員",
    "Clinical Data Managers": "臨床資料管理",
    "Health Informatics Specialists": "醫療資訊相關職涯",
    "Data Scientists": "資料科學家",
    "First-Line Supervisors of Personal Service Workers": "美容／個人服務現場管理",
    "Skincare Specialists": "護膚／醫美諮詢相關職涯",
    "Massage Therapists": "芳療／按摩照護服務",
    "Hairdressers, Hairstylists, and Cosmetologists": "美髮與美容服務",
    "Barbers": "剪髮與造型服務",
    "Shampooers": "美髮助理／洗護服務",
    "Manicurists and Pedicurists": "美甲與手足保養",
    "Makeup Artists, Theatrical and Performance": "彩妝與整體造型",
    "Retail Salespersons": "美容產品／服務銷售",
    "Door-to-Door Sales Workers, News and Street Vendors, and Related Workers": "美容產品／服務顧問",
    "Spa Managers": "SPA／美容服務營運管理",
    "Dermatologists": "皮膚科醫師",
}
SKILL_ZH = {
    "Active Learning": "主動學習",
    "Active Listening": "主動聆聽",
    "Administration and Management": "行政與管理",
    "Administrative": "行政事務",
    "Complex Problem Solving": "複雜問題解決",
    "Computers and Electronics": "電腦與電子",
    "Coordination": "協調",
    "Critical Thinking": "批判性思考",
    "Customer and Personal Service": "客戶與個人服務",
    "Design": "設計",
    "Education and Training": "教育與訓練",
    "Engineering and Technology": "工程與科技",
    "English Language": "英語",
    "Judgment and Decision Making": "判斷與決策",
    "Learning Strategies": "學習策略",
    "Management of Personnel Resources": "人力資源管理",
    "Mathematics": "數學",
    "Medicine and Dentistry": "醫學與牙醫",
    "Monitoring": "監控",
    "Programming": "程式設計",
    "Reading Comprehension": "閱讀理解",
    "Speaking": "口語表達",
    "Systems Analysis": "系統分析",
    "Systems Evaluation": "系統評估",
    "Time Management": "時間管理",
    "Writing": "寫作",
}
VALUE_ZH = {
    "High skill reuse": "高度利用原有能力",
    "Partial skill reuse": "部分利用原有能力",
    "Major reskilling": "大幅重新學習",
    "Adjacent candidate": "鄰近候選路徑",
    "Bridge candidate": "橋接候選路徑",
    "Infeasible / high-barrier": "高門檻或暫不適合",
    "Major-reskilling path": "大幅重新學習路徑",
    "Insufficient public evidence": "公開資料不足",
    "Strong": "強",
    "Moderate": "中等",
    "Weak": "弱",
    "Unknown": "未知",
    "unknown": "未知",
    "High": "高",
    "Medium": "中",
    "Low": "低",
    "high": "高",
    "medium": "中",
    "low": "低",
    "yes": "是",
    "no": "否",
    "needed": "需要",
    "No": "否",
    "Needed": "需要",
    "candidate": "候選",
    "review": "需複核",
    "most missing skills have matched courses in window": "目前課程供給可覆蓋多數缺口技能",
    "limited missing-skill coverage in window": "目前課程供給只能覆蓋少部分缺口技能",
    "unknown: no matched course evidence": "未知：目前沒有對應課程證據",
}
JOB_RELEVANCE_RULES = {
    "Clinical Research Coordinators": {
        "title": ["臨床研究", "研究協調", "研究員", "試驗", "受試", "資料分析"],
        "category": ["研究", "醫療", "資料", "統計"],
        "detail": ["臨床", "研究", "試驗", "受試", "統計", "調查", "資料", "報告", "專案", "協調"],
    },
    "Clinical Data Managers": {
        "title": ["資料分析", "資料管理", "檔案管理", "市場研究分析", "研究員", "精算"],
        "category": ["資料", "統計", "資訊", "研究", "檔案"],
        "detail": ["資料", "數據", "統計", "分析", "資料庫", "報表", "視覺化", "PowerBI", "Tableau", "Python", "SPSS", "SAS"],
    },
    "Health Informatics Specialists": {
        "title": ["醫療資訊", "資訊系統", "AI系統", "資料分析", "病歷", "醫療"],
        "category": ["資訊", "醫療", "軟體", "系統"],
        "detail": ["醫療", "醫院", "診所", "病歷", "資訊", "系統", "資料", "數據", "AI", "RAG", "API", "軟體"],
    },
    "Data Scientists": {
        "title": ["資料分析", "資料科學", "數據", "AI", "系統設計", "市場研究分析", "研究員", "精算"],
        "category": ["資訊", "軟體", "統計", "研究", "行銷"],
        "detail": ["資料", "數據", "統計", "分析", "模型", "AI", "Python", "R", "機器學習", "視覺化", "GA4", "Looker"],
    },
}
JOB_RELEVANCE_EXCLUDE_TERMS = [
    "婚鞋",
    "門市",
    "餐飲",
    "傳送員",
    "傳送人員",
    "櫃台",
    "業務部助理",
    "行政助理",
    "銷售",
    "接待",
]
LOCALIZED_JOB_ALIASES = {
    "Clinical Research Coordinators": [
        "臨床研究協調",
        "臨床研究專員",
        "臨床試驗協調",
        "臨床試驗專員",
        "研究護理師",
        "臨床研究護理師",
        "受試者",
        "醫學研究助理",
    ],
    "Clinical Data Managers": [
        "臨床資料管理",
        "臨床數據管理",
        "醫療資料管理",
        "研究資料管理",
        "資料管理師",
        "資料分析專員",
        "數據分析專員",
        "統計分析",
        "資料庫管理",
    ],
    "Health Informatics Specialists": [
        "醫療資訊",
        "醫學資訊",
        "健康資訊",
        "醫療資訊系統",
        "醫院資訊系統",
        "病歷系統",
        "電子病歷",
        "醫療AI",
        "醫療 AI",
        "健康資料",
        "醫療數據",
        "HIS",
        "EMR",
    ],
    "Data Scientists": [
        "資料科學",
        "資料科學家",
        "數據科學",
        "資料分析師",
        "資料分析專員",
        "數據分析師",
        "AI系統設計",
        "AI 系統設計",
        "AI工程師",
        "AI 工程師",
        "機器學習",
        "資料工程",
        "統計分析",
        "Python",
        "PowerBI",
        "Tableau",
    ],
    "First-Line Supervisors of Personal Service Workers": ["美容主管", "美容店長", "SPA主管", "芳療主管", "美容服務管理"],
    "Skincare Specialists": ["護膚", "美容師", "美容諮詢師", "醫美諮詢", "美體", "芳療師"],
    "Massage Therapists": ["按摩", "芳療師", "經絡", "推拿", "舒壓", "SPA"],
    "Hairdressers, Hairstylists, and Cosmetologists": ["美髮", "髮型設計師", "美髮助理", "美髮培訓生", "剪髮", "燙染"],
    "Barbers": ["剪髮", "理髮", "美髮", "髮型設計師"],
    "Shampooers": ["美髮助理", "洗髮", "洗護", "美髮培訓生"],
    "Manicurists and Pedicurists": ["美甲", "指甲", "凝膠", "手部保養"],
    "Makeup Artists, Theatrical and Performance": ["彩妝", "化妝", "整體造型", "新秘"],
    "Retail Salespersons": ["美容諮詢師", "醫美", "保養品", "化妝品", "彩妝", "藥妝"],
    "Door-to-Door Sales Workers, News and Street Vendors, and Related Workers": ["美容顧問", "美容諮詢師", "保養品", "化妝品", "醫美"],
    "Spa Managers": ["SPA", "芳療", "美容主管", "美容店長", "水療中心"],
    "Dermatologists": ["皮膚科醫師", "皮膚科", "醫美醫師"],
}


def render_career_evidence_viewer(
    candidates_v35: pd.DataFrame,
    training_v4: pd.DataFrame,
    course_mapping: pd.DataFrame,
    taiwanjobs_raw: pd.DataFrame | None,
    beauty_phase5: pd.DataFrame,
) -> None:
    _html(
        f"""
        <div class="qj-career-header">
            <div class="qj-header-title">青年職涯探索</div>
            <div class="qj-subtitle">護理師 → {escape(_current_domain_label())} 的職涯可能性探索</div>
        </div>
        """
    )

    if "career_view_layer" not in st.session_state:
        st.session_state.career_view_layer = "discovery"
    if "career_target_domain" not in st.session_state:
        st.session_state.career_target_domain = TARGET_DOMAIN_OPTIONS[0]

    if st.session_state.career_view_layer == "evidence" and st.session_state.get("career_selected_path"):
        domain_label = _current_domain_label()
        evidence = _representative_paths(candidates_v35, training_v4, beauty_phase5, domain_label)
        _render_selected_evidence(evidence, course_mapping, taiwanjobs_raw, str(st.session_state.career_selected_path))
        return

    domain_label = _render_explore_section()
    evidence = _representative_paths(candidates_v35, training_v4, beauty_phase5, domain_label)
    _render_discovery_map(evidence, taiwanjobs_raw, domain_label)


def _render_selected_evidence(
    evidence: pd.DataFrame,
    course_mapping: pd.DataFrame,
    taiwanjobs_raw: pd.DataFrame | None,
    selected_name: str,
) -> None:
    if selected_name not in set(evidence["target_occupation_name"].astype(str)):
        selected_name = str(evidence.iloc[0]["target_occupation_name"])

    selected = evidence.loc[evidence["target_occupation_name"].eq(selected_name)].iloc[0]
    if _is_beauty_row(selected):
        selected_mapping = course_mapping.iloc[0:0].copy()
    else:
        selected_mapping = course_mapping.loc[
            course_mapping["target_occupation_code"].astype(str).eq(str(selected["target_occupation_code"]))
        ].copy()
    if st.button("← 回到職涯探索", key="career_back_to_discovery"):
        st.session_state.career_view_layer = "discovery"
        st.session_state.career_selected_path = None
        st.rerun()

    st.markdown("### 轉職路徑詳情")
    _html(
        f"""
        <div class="qj-section-note">
            目前查看：{escape(_occupation_zh(selected_name))} | {escape(selected_name)}
        </div>
        """
    )
    _render_detail(selected, selected_mapping, taiwanjobs_raw)


def _render_discovery_map(
    evidence: pd.DataFrame, taiwanjobs_raw: pd.DataFrame | None, domain_label: str
) -> None:
    if st.button("探索可能路徑", use_container_width=False, key="career_explore_button"):
        st.session_state.career_view_layer = "discovery"
        st.session_state.career_selected_path = None

    st.markdown("### 探索可能性")
    _html(
        '<div class="qj-section-note">代表性案例按產品需求固定展示，不是排序，也不是推薦分數。</div>'
    )
    _html(
        _transition_map_html(evidence)
    )
    _render_path_cards(evidence, taiwanjobs_raw)


def _transition_map_html(evidence: pd.DataFrame) -> str:
    lanes = "".join(
        _transition_lane_html(row)
        for _, row in evidence.iterrows()
    )
    return (
        '<div class="qj-transition-map">'
        '<div class="qj-transition-map-head">'
        '<div class="qj-transition-source">現在：護理師</div>'
        f'<div class="qj-transition-target">探索方向：{escape(_current_domain_label())}</div>'
        "</div>"
        '<div class="qj-transition-lanes">'
        f"{lanes}"
        "</div>"
        "</div>"
    )


def _representative_paths(
    candidates_v35: pd.DataFrame,
    training_v4: pd.DataFrame,
    beauty_phase5: pd.DataFrame,
    domain_label: str,
) -> pd.DataFrame:
    if domain_label == "美容 / 醫美 / 個人照護":
        return _beauty_representative_paths(beauty_phase5)
    return _technology_representative_paths(candidates_v35, training_v4)


def _technology_representative_paths(candidates_v35: pd.DataFrame, training_v4: pd.DataFrame) -> pd.DataFrame:
    merged = training_v4.merge(
        candidates_v35,
        on=["target_occupation_code", "target_occupation_name"],
        how="left",
        suffixes=("_v4", "_v35"),
        validate="one_to_one",
    )
    merged["_evidence_source"] = "technology_v35_v4"
    available = merged.loc[merged["target_occupation_name"].isin(TECH_REPRESENTATIVE_PATHS)].copy()
    missing = [name for name in TECH_REPRESENTATIVE_PATHS if name not in set(available["target_occupation_name"])]
    if missing:
        raise RuntimeError(f"Missing representative career paths in v3.5/v4 outputs: {missing}")
    available["_order"] = available["target_occupation_name"].map(
        {name: index for index, name in enumerate(TECH_REPRESENTATIVE_PATHS)}
    )
    return available.sort_values("_order").drop(columns=["_order"]).reset_index(drop=True)


def _beauty_representative_paths(beauty_phase5: pd.DataFrame) -> pd.DataFrame:
    available = beauty_phase5.loc[beauty_phase5["target_occupation_name"].isin(BEAUTY_REPRESENTATIVE_PATHS)].copy()
    missing = [name for name in BEAUTY_REPRESENTATIVE_PATHS if name not in set(available["target_occupation_name"])]
    if missing:
        raise RuntimeError(f"Missing representative beauty paths in Phase 5 output: {missing}")
    available["_order"] = available["target_occupation_name"].map(
        {name: index for index, name in enumerate(BEAUTY_REPRESENTATIVE_PATHS)}
    )
    available["_evidence_source"] = "beauty_phase5"
    available["transition_span_v4"] = available["transition_span"]
    available["learning_burden_level"] = available["learning_burden"]
    available["market_validation_v4"] = available["taiwan_market_evidence"]
    available["training_coverage_ratio"] = available["training_coverage_ratio_missing_skills"]
    available["gap_skill_training_coverage_ratio"] = available["training_coverage_ratio_missing_skills"]
    available["number_of_gap_skills"] = available["number_of_missing_skills"]
    available["number_of_trainable_skills_found"] = available["number_of_trainable_missing_skills_found"]
    available["matched_course_count"] = available["training_course_count"]
    available["missing_skills_v4"] = available["missing_skills"]
    available["shared_top_skills"] = available["already_covered_skills"]
    available["scenario_6m_feasibility_estimate"] = "Phase 5 未輸出 6 個月時間窗估計"
    available["possible_income_interruption"] = "unknown"
    available["mapping_method"] = available["job_mapping_method"]
    available["mapping_confidence"] = "Phase 5 job-level relevance"
    available["mapping_score"] = ""
    available["matched_titles"] = available["job_mapping_positive_aliases"]
    available["manual_review_needed"] = available["job_mapping_review_reason"].fillna("").ne("").map({True: "yes", False: "no"})
    return available.sort_values("_order").drop(columns=["_order"]).reset_index(drop=True)


def _render_explore_section() -> str:
    selected = st.selectbox(
        "目標領域",
        TARGET_DOMAIN_OPTIONS,
        index=TARGET_DOMAIN_OPTIONS.index(_current_domain_label()),
        key="career_target_domain_selector",
    )
    if selected != st.session_state.get("career_target_domain"):
        st.session_state.career_target_domain = selected
        st.session_state.career_view_layer = "discovery"
        st.session_state.career_selected_path = None
        st.rerun()

    cols = st.columns([1, 1, 1], gap="medium")
    values = [
        ("目前背景", _occupation_display_text(DEMO_SOURCE)),
        ("目標領域", selected),
        ("學習時間窗", "6 個月"),
    ]
    for col, (label, value) in zip(cols, values):
        with col:
            _html(
                f"""
                <div class="qj-career-preset">
                    <div class="qj-metric-label">{escape(label)}</div>
                    <div class="qj-career-preset-value">{escape(value)}</div>
                </div>
                """
            )
    _html(
        '<div class="qj-note">目前是固定展示情境，只支援護理師作為目前背景；目標領域可在科技 / AI 與美容 / 醫美 / 個人照護之間切換。</div>'
    )
    return selected


def _render_path_cards(evidence: pd.DataFrame, taiwanjobs_raw: pd.DataFrame | None) -> None:
    cols = st.columns(4, gap="medium")
    for col, (_, row) in zip(cols, evidence.iterrows()):
        occupation_name = str(row["target_occupation_name"])
        note = PATH_NOTES.get(str(row["target_occupation_name"]), "")
        if row["target_occupation_name"] == "Health Informatics Specialists" and float(row["training_coverage_ratio"]) >= 0.5:
            note = ""
        badge = _badge_html(note)
        with col:
            _html(
                f"""
                <div class="qj-career-card {_span_class(row)}">
                    {_occupation_title_html(occupation_name)}
                    {badge}
                    <div class="qj-career-intro">{escape(PATH_INTROS.get(occupation_name, ""))}</div>
                    <div class="qj-career-card-grid">
                        {_metric_html("原有能力沿用程度", _row_transition_span(row))}
                        {_metric_html("學習負擔", _row_learning_burden(row))}
                        {_metric_html("台灣市場訊號", _market_signal_label(row, taiwanjobs_raw), translate_value=False)}
                    </div>
                </div>
                """
            )
            if st.button("查看證據", key=f"career_evidence_button_{occupation_name}", use_container_width=True):
                st.session_state.career_selected_path = occupation_name
                st.session_state.career_view_layer = "evidence"
                st.rerun()


def _render_detail(row: pd.Series, course_mapping: pd.DataFrame, taiwanjobs_raw: pd.DataFrame | None) -> None:
    left, right = st.columns([1.08, 0.92], gap="medium")
    with left:
        st.markdown("#### 為什麼值得探索？")
        _html(
            f"""
            <div class="qj-panel">
                <div class="qj-path-conclusion">{escape(_path_conclusion(row))}</div>
                {_detail_block("可利用的護理背景", _skill_chip_list(_row_shared_skills(row)))}
                {_detail_block("路徑定位", _path_reason(row))}
            </div>
            """
        )

        st.markdown("#### 原有能力可利用程度")
        _html(
            f"""
            <div class="qj-panel">
                <div class="qj-career-profile-grid">
                    {_metric_html("能力延續", _row_transition_span(row))}
                    {_metric_html("學習負擔", _row_learning_burden(row))}
                </div>
                {_detail_block("部分已具備技能", _skill_chip_list(row.get("partially_covered_skills", "")))}
            </div>
            """
        )

        st.markdown("#### 需要補強的技能")
        _html(
            f"""
            <div class="qj-panel">
                {_detail_block("缺口技能", _skill_chip_list(_row_missing_skills(row)))}
            </div>
            """
        )

        st.markdown("#### 學習負擔")
        _html(
            f"""
            <div class="qj-panel">
                <div class="qj-career-profile-grid">
                    {_metric_html("整體負擔", _row_learning_burden(row))}
                    {_metric_html("收入中斷估計", row.get("possible_income_interruption", "unknown"))}
                </div>
            </div>
            """
        )

    with right:
        st.markdown("#### 台灣市場證據")
        if taiwanjobs_raw is None and not _is_beauty_row(row):
            _render_aggregate_market_evidence(row)
        else:
            market_stats = _job_market_stats(row, taiwanjobs_raw)
            _html(
                f"""
                <div class="qj-panel">
                    <div class="qj-career-profile-grid">
                        {_metric_html("高相關職缺", _number(market_stats["verified_job_count"]), translate_value=False)}
                        {_metric_html("待確認候選", _number(market_stats["pending_job_count"]), translate_value=False)}
                        {_metric_html("需求人數", _number(market_stats["verified_demand_persons"]), translate_value=False)}
                        {_metric_html("月薪資料", market_stats["salary"], translate_value=False)}
                        {_metric_html("市場訊號", _market_signal_label(row, market_stats=market_stats), translate_value=False)}
                    </div>
                    <div class="qj-note">只把通過高相關性篩選的 TaiwanJobs 職缺納入主要統計；待確認候選不計入職缺數、需求人數或月薪。</div>
                </div>
                """
            )
        _render_market_job_preview(row, taiwanjobs_raw)

        st.markdown("#### 培訓資源")
        _html(
            f"""
            <div class="qj-panel">
                <div class="qj-career-profile-grid">
                    {_metric_html("潛在課程覆蓋", _coverage_label(row), translate_value=False)}
                    {_metric_html("對應課程數", _number(row.get("matched_course_count")), translate_value=False)}
                    {_metric_html("可見課程時數", _hours(row.get("total_training_hours")), translate_value=False)}
                    {_metric_html("可見直接費用", _money(row.get("estimated_direct_course_cost")), translate_value=False)}
                    {_metric_html("6 個月時間窗", row.get("scenario_6m_feasibility_estimate", "unknown"))}
                </div>
                <div class="qj-note">潛在課程覆蓋只代表目前公開課程供給可能對應到技能缺口，不代表技能已補足。</div>
            </div>
            """
        )
    _render_onet_evidence_expander(row, course_mapping)
    _render_market_evidence_expander(row)
    _render_course_table_expander(row, course_mapping)
    _render_method_limitations_expander()


def _render_course_table(course_mapping: pd.DataFrame) -> None:
    if course_mapping.empty:
        st.info("目前沒有對應課程證據。")
        return
    counted = course_mapping.loc[course_mapping["mapping_confidence"].isin(["High", "Medium"])].copy()
    display = counted.copy()
    if display.empty:
        st.warning("目前只有低可信度 course mapping；以下僅供人工確認，不計入潛在課程覆蓋。")
        display = course_mapping.copy()
    display = display.sort_values(["skill_gap_status", "mapping_score", "training_hours"], ascending=[True, False, True])
    display["counted_in_coverage"] = display["mapping_confidence"].isin(["High", "Medium"]).map({True: "yes", False: "no"})
    display["skill_name"] = display["skill_name"].map(_skill_zh)
    display["skill_gap_status"] = display["skill_gap_status"].map(_translate_status)
    display["mapping_confidence"] = display["mapping_confidence"].map(_translate_value)
    display["manual_review_needed"] = display["manual_review_needed"].map(_translate_value)
    display["counted_in_coverage"] = display["counted_in_coverage"].map(_translate_value)
    display = display[
        [
            "skill_name",
            "skill_gap_status",
            "course_name",
            "training_provider",
            "location",
            "training_hours",
            "fee_per_person",
            "mapping_score",
            "mapping_confidence",
            "manual_review_needed",
            "counted_in_coverage",
        ]
    ].head(12)
    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        height=320,
        column_config={
            "skill_name": st.column_config.TextColumn("對應技能", width="medium"),
            "skill_gap_status": st.column_config.TextColumn("缺口狀態", width="small"),
            "course_name": st.column_config.TextColumn("課程名稱", width="large"),
            "training_provider": st.column_config.TextColumn("開課單位", width="medium"),
            "location": st.column_config.TextColumn("地點", width="small"),
            "training_hours": st.column_config.NumberColumn("時數", format="%.0f"),
            "fee_per_person": st.column_config.NumberColumn("費用", format="NT$ %.0f"),
            "mapping_score": st.column_config.NumberColumn("映射分數", format="%.3f"),
            "mapping_confidence": st.column_config.TextColumn("映射可信度", width="small"),
            "manual_review_needed": st.column_config.TextColumn("人工確認", width="small"),
            "counted_in_coverage": st.column_config.TextColumn("計入覆蓋", width="small"),
        },
    )


def _render_course_table_expander(row: pd.Series, course_mapping: pd.DataFrame) -> None:
    with st.expander("查看資料依據：完整培訓課程表", expanded=False):
        if _is_beauty_row(row):
            courses = _parse_phase5_courses(row.get("matched_training_courses", ""))
            st.caption("Beauty Phase 5 output 只有 candidate-level course summary，沒有輸出完整 course→skill mapping table。")
            if courses:
                st.dataframe(
                    pd.DataFrame(courses),
                    hide_index=True,
                    use_container_width=True,
                    height=260,
                    column_config={
                        "course_name": st.column_config.TextColumn("課程名稱", width="large"),
                        "training_hours": st.column_config.TextColumn("時數", width="small"),
                        "fee": st.column_config.TextColumn("費用", width="medium"),
                        "mapping_confidence": st.column_config.TextColumn("映射可信度", width="small"),
                    },
                )
            else:
                st.info("Phase 5 output 沒有可顯示的課程 summary。")
            return
        _render_course_table(course_mapping)


def _render_method_limitations_expander() -> None:
    with st.expander("查看資料依據：方法與資料限制", expanded=False):
        _html(
            """
            <div class="qj-panel qj-note">
                O*NET 為美國職業資料，台灣職涯制度與證照要求可能不同。<br>
                TaiwanJobs 職稱 mapping 仍需要人工確認，尤其是醫療 × 科技職稱。<br>
                培訓資料目前只有課程名稱，沒有完整 syllabus 或細部課程內容。<br>
                本頁不代表轉職成功機率，也沒有合成單一職涯分數。<br>
                高相關職缺來自中文 alias + JOB_DETAIL relevance QA，只代表目前公開資料中可追溯的職缺證據。
            </div>
            """
        )


def _render_onet_evidence_expander(row: pd.Series, course_mapping: pd.DataFrame) -> None:
    with st.expander("查看資料依據：O*NET 技能與缺口", expanded=False):
        st.caption("原始英文名稱與 IM/gap 數值直接來自既有 v3.5 / v4 outputs；此處只做 UI 呈現。")
        raw_rows = (
            _raw_skill_rows(_row_shared_skills(row), "可轉移 / 共享技能")
            + _raw_skill_rows(row.get("partially_covered_skills", ""), "部分已具備技能")
            + _raw_skill_rows(_row_missing_skills(row), "仍需補強技能")
        )
        if raw_rows:
            raw_display = pd.DataFrame(raw_rows)
            st.dataframe(
                raw_display,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "status": st.column_config.TextColumn("狀態"),
                    "skill_zh": st.column_config.TextColumn("中文技能"),
                    "onet_skill_name": st.column_config.TextColumn("O*NET 原始技能"),
                    "skill_type": st.column_config.TextColumn("O*NET 類型"),
                    "target_im": st.column_config.TextColumn("Target IM / score"),
                    "source_im": st.column_config.TextColumn("RN IM"),
                    "gap": st.column_config.TextColumn("Gap"),
                    "raw_evidence": st.column_config.TextColumn("原始 evidence"),
                },
            )
        else:
            st.info("目前沒有可顯示的 O*NET skill evidence。")

        if not course_mapping.empty:
            im_display = (
                course_mapping[
                    [
                        "skill_name",
                        "skill_type",
                        "skill_gap_status",
                        "target_importance",
                        "source_importance",
                        "raw_gap",
                    ]
                ]
                .drop_duplicates()
                .copy()
            )
            im_display["skill_zh"] = im_display["skill_name"].map(_skill_zh)
            im_display["skill_gap_status"] = im_display["skill_gap_status"].map(_translate_status)
            im_display = im_display[
                [
                    "skill_zh",
                    "skill_name",
                    "skill_type",
                    "skill_gap_status",
                    "target_importance",
                    "source_importance",
                    "raw_gap",
                ]
            ].sort_values(["skill_gap_status", "raw_gap"], ascending=[True, False])
            st.caption("Course mapping 中可追溯到的 O*NET IM / gap")
            st.dataframe(
                im_display,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "skill_zh": st.column_config.TextColumn("中文技能"),
                    "skill_name": st.column_config.TextColumn("O*NET 原始技能"),
                    "skill_type": st.column_config.TextColumn("O*NET 類型"),
                    "skill_gap_status": st.column_config.TextColumn("缺口狀態"),
                    "target_importance": st.column_config.NumberColumn("Target IM", format="%.2f"),
                    "source_importance": st.column_config.NumberColumn("RN IM", format="%.2f"),
                    "raw_gap": st.column_config.NumberColumn("Gap", format="%.2f"),
                },
            )


def _render_market_evidence_expander(row: pd.Series) -> None:
    with st.expander("查看資料依據：TaiwanJobs 職稱映射", expanded=False):
        caption = (
            "Phase 5 job-level relevance、alias 與 examples 直接來自 nursing_to_beauty_candidates_phase5.csv。"
            if _is_beauty_row(row)
            else "v3.5 職稱映射可信度、mapping score 與 matched titles 直接來自既有 output；v3.6 中文 alias 只用於 TaiwanJobs job-level localization search。"
        )
        st.caption(caption)
        _html(
            f"""
            <div class="qj-panel">
                <div class="qj-career-profile-grid">
                    {_metric_html("職稱映射可信度", row.get("taiwanjobs_mapping_confidence", row.get("mapping_confidence", "")))}
                    {_metric_html("人工確認", _manual_review(row))}
                    {_metric_html("映射方法", row.get("mapping_method", ""), translate_value=False)}
                    {_metric_html("映射分數", _decimal(row.get("mapping_score")), translate_value=False)}
                </div>
                {_detail_block("TaiwanJobs matched titles", _plain_text_html(row.get("matched_titles", "")))}
                {_detail_block("v3.6 中文職稱 alias", _plain_text_html(_localized_alias_text(str(row.get("target_occupation_name", "")))))}
            </div>
            """
        )


def _render_aggregate_market_evidence(row: pd.Series) -> None:
    salary_lower = _clean(row.get("salary_lower_median", ""))
    salary_upper = _clean(row.get("salary_upper_median", ""))
    salary = "未知"
    if salary_lower and salary_upper:
        salary = f"NT$ {_salary_amount(salary_lower)} - {_salary_amount(salary_upper)}"
    elif salary_lower:
        salary = f"NT$ {_salary_amount(salary_lower)} 以上"
    _html(
        f"""
        <div class="qj-panel">
            <div class="qj-career-profile-grid">
                {_metric_html("彙整對應職缺", _number(row.get("matched_job_count")), translate_value=False)}
                {_metric_html("彙整需求人數", _number(row.get("total_demand_persons")), translate_value=False)}
                {_metric_html("月薪彙整", salary, translate_value=False)}
                {_metric_html("市場訊號", _row_market_validation(row), translate_value=False)}
            </div>
            <div class="qj-note">以上為既有 Career output 的彙整市場證據；未將其重新判定為逐筆職缺或高相關職缺統計。</div>
        </div>
        """
    )


def _render_market_job_preview(row: pd.Series, taiwanjobs_raw: pd.DataFrame | None) -> None:
    if _is_beauty_row(row):
        _render_phase5_beauty_job_preview(row)
        return

    if taiwanjobs_raw is None:
        st.info("原始 TaiwanJobs 資料未載入，此細節目前不可用。")
        return

    matched_jobs = _matched_taiwanjobs(row, taiwanjobs_raw)
    if matched_jobs.empty:
        st.info("目前公開資料尚不足以確認台灣市場規模，不代表此職涯不存在。")
        return

    verified_jobs = matched_jobs.loc[matched_jobs["relevance_confidence"].eq("High")].copy()
    pending_jobs = matched_jobs.loc[matched_jobs["relevance_confidence"].eq("Medium")].copy()
    if verified_jobs.empty:
        st.info("目前公開資料尚不足以確認台灣市場規模，不代表此職涯不存在。")
    else:
        st.markdown("##### 高相關職缺範例")
        preview = _prioritized_job_preview(verified_jobs)
        for _, job in preview.iterrows():
            _html(_job_card_html(str(row["target_occupation_name"]), job))

    if not pending_jobs.empty:
        with st.expander("查看待確認候選", expanded=False):
            for _, job in _prioritized_job_preview(pending_jobs).iterrows():
                _html(_job_card_html(str(row["target_occupation_name"]), job))

    with st.expander("查看全部對應職缺", expanded=False):
        display = matched_jobs.copy()
        display["salary_info"] = display.apply(_job_salary, axis=1)
        display["job_summary"] = display["JOB_DETAIL（工作內容）"].map(_job_summary)
        display["manual_review_needed"] = display["manual_review_needed"].map(_translate_value)
        display["relevance_confidence"] = display["relevance_confidence"].map(_translate_value)
        display = display[
            [
                "OCCU_DESC（職務名稱）",
                "COMPNAME（公司名稱）",
                "CITYNAME（工作地點）",
                "salary_info",
                "job_summary",
                "mapping_candidate_source",
                "localized_alias_hits",
                "relevance_score",
                "relevance_confidence",
                "manual_review_needed",
                "review_note",
                "URL_QUERY（職缺資料URL）",
            ]
        ]
        st.dataframe(
            display,
            hide_index=True,
            use_container_width=True,
            height=320,
            column_config={
                "OCCU_DESC（職務名稱）": st.column_config.TextColumn("職缺名稱", width="large"),
                "COMPNAME（公司名稱）": st.column_config.TextColumn("公司／機構", width="medium"),
                "CITYNAME（工作地點）": st.column_config.TextColumn("工作地點", width="small"),
                "salary_info": st.column_config.TextColumn("薪資資訊", width="medium"),
                "job_summary": st.column_config.TextColumn("工作內容摘要", width="large"),
                "mapping_candidate_source": st.column_config.TextColumn("候選來源", width="medium"),
                "localized_alias_hits": st.column_config.TextColumn("命中 alias", width="medium"),
                "relevance_score": st.column_config.NumberColumn("relevance score", format="%.2f"),
                "relevance_confidence": st.column_config.TextColumn("relevance confidence", width="small"),
                "manual_review_needed": st.column_config.TextColumn("人工確認", width="small"),
                "review_note": st.column_config.TextColumn("QA 註記", width="medium"),
                "URL_QUERY（職缺資料URL）": st.column_config.LinkColumn("原始職缺連結"),
            },
        )


def _render_phase5_beauty_job_preview(row: pd.Series) -> None:
    high_jobs = _parse_phase5_job_examples(row.get("high_relevance_job_examples", ""))
    medium_jobs = _parse_phase5_job_examples(row.get("medium_relevance_job_examples", ""))
    for job in high_jobs:
        job["relevance"] = "高相關"
    for job in medium_jobs:
        job["relevance"] = "待確認"
    if not high_jobs:
        st.info("目前公開資料尚不足以確認台灣市場規模，不代表此職涯不存在。")
    else:
        st.markdown("##### 高相關職缺範例")
        for job in high_jobs[:5]:
            _html(_phase5_job_card_html(job))

    if medium_jobs:
        with st.expander("查看待確認候選", expanded=False):
            for job in medium_jobs[:5]:
                _html(_phase5_job_card_html(job, pending=True))

    if high_jobs or medium_jobs:
        with st.expander("查看全部對應職缺", expanded=False):
            display = pd.DataFrame(high_jobs + medium_jobs)
            if not display.empty:
                st.dataframe(
                    display,
                    hide_index=True,
                    use_container_width=True,
                    height=260,
                    column_config={
                        "job_title": st.column_config.TextColumn("職缺名稱", width="large"),
                        "company": st.column_config.TextColumn("公司／機構", width="medium"),
                        "location": st.column_config.TextColumn("工作地點", width="small"),
                        "salary": st.column_config.TextColumn("薪資資訊", width="medium"),
                        "summary": st.column_config.TextColumn("工作內容摘要", width="large"),
                        "source_url": st.column_config.LinkColumn("原始職缺連結"),
                        "relevance": st.column_config.TextColumn("相關性", width="small"),
                    },
                )
    else:
        with st.expander("查看全部對應職缺", expanded=False):
            st.info("Phase 5 output 沒有可顯示的高相關或待確認職缺 examples。")


def _parse_phase5_job_examples(value: object) -> list[dict[str, str]]:
    text = _clean(value)
    if not text:
        return []
    jobs = []
    for item in [part.strip() for part in text.split(" || ") if part.strip()]:
        parts = item.split(" | ", 5)
        if len(parts) < 6:
            continue
        jobs.append(
            {
                "job_title": parts[0],
                "company": parts[1],
                "location": parts[2],
                "salary": parts[3],
                "summary": parts[4],
                "source_url": parts[5],
                "relevance": "高相關" if "high_relevance" not in text else "高相關",
            }
        )
    return jobs


def _phase5_job_card_html(job: dict[str, str], pending: bool = False) -> str:
    review_badge = '<div class="qj-job-review">待人工確認</div>' if pending else ""
    source_url = _clean(job.get("source_url", ""))
    link = f'<a href="{escape(source_url)}" target="_blank" rel="noopener noreferrer">原始職缺來源</a>' if source_url else "原始職缺來源：未提供"
    return (
        '<div class="qj-job-card">'
        f'<div class="qj-job-title">{escape(_clean(job.get("job_title", "")))}</div>'
        f"{review_badge}"
        '<div class="qj-job-meta">'
        f'<span>{escape(_clean(job.get("company", "")))}</span>'
        f'<span>{escape(_clean(job.get("location", "")))}</span>'
        f'<span>{escape(_clean(job.get("salary", "")))}</span>'
        "</div>"
        f'<div class="qj-job-summary">{escape(_clean(job.get("summary", "")))}</div>'
        f'<div class="qj-job-source">{link}</div>'
        "</div>"
    )


def _parse_phase5_courses(value: object) -> list[dict[str, str]]:
    text = _clean(value)
    if not text:
        return []
    courses = []
    pattern = re.compile(r"^(?P<name>.+?) \((?P<hours>[^,]+), (?P<fee>[^,]+), (?P<confidence>[^)]+)\)$")
    for item in [part.strip() for part in text.split(";") if part.strip()]:
        match = pattern.match(item)
        if match:
            courses.append(
                {
                    "course_name": match.group("name"),
                    "training_hours": match.group("hours"),
                    "fee": match.group("fee"),
                    "mapping_confidence": _translate_value(match.group("confidence")),
                }
            )
        else:
            courses.append(
                {
                    "course_name": item,
                    "training_hours": "未知",
                    "fee": "未知",
                    "mapping_confidence": "未知",
                }
            )
    return courses


def _html(markup: str) -> None:
    st.markdown(dedent(markup).strip(), unsafe_allow_html=True)


def _badge_html(note: str) -> str:
    if note:
        return f'<div class="qj-career-badge">{escape(note)}</div>'
    return '<div aria-hidden="true" style="min-height: 1.9rem; margin: 0.45rem 0 0.2rem 0;"></div>'


def _transition_lane_html(row: pd.Series) -> str:
    return (
        '<div class="qj-transition-lane">'
        '<div class="qj-transition-origin">護理師</div>'
        f'<div class="qj-transition-arrow {_arrow_class(row)}"></div>'
        f"{_map_node_html(row)}"
        "</div>"
    )


def _map_node_html(row: pd.Series) -> str:
    occupation_name = str(row["target_occupation_name"])
    return (
        f'<div class="qj-transition-node {_span_class(row)}">'
        f'<div class="qj-transition-node-title">{escape(_occupation_zh(occupation_name))}</div>'
        f'<div class="qj-transition-node-intro">{escape(PATH_INTROS.get(occupation_name, ""))}</div>'
        '<div class="qj-transition-node-meta">'
        f'<span>跨度：{escape(_span_level(row))}</span>'
        f'<span>沿用：{escape(_translate_value(_row_transition_span(row)))}</span>'
        f'<span>負擔：{escape(_translate_value(_row_learning_burden(row)))}</span>'
        "</div>"
        "</div>"
    )


def _arrow_class(row: pd.Series) -> str:
    span = _row_transition_span(row)
    if span == "Major reskilling":
        return "qj-transition-arrow-long"
    return ""


def _span_level(row: pd.Series) -> str:
    span = _row_transition_span(row)
    if span == "High skill reuse":
        return "低"
    if span == "Major reskilling":
        return "高"
    return "中"


def _span_class(row: pd.Series) -> str:
    span = _row_transition_span(row)
    if span == "High skill reuse":
        return "qj-career-card-high-reuse"
    if span == "Major reskilling":
        return "qj-career-card-major-reskilling"
    return "qj-career-card-partial-reuse"


def _occupation_title_html(occupation_name: str) -> str:
    return (
        f'<div class="qj-card-title">{escape(_occupation_zh(occupation_name))}</div>'
        f'<div class="qj-card-title-sub">{escape(occupation_name)}</div>'
    )


def _occupation_option_label(occupation_name: str) -> str:
    return f"{_occupation_zh(occupation_name)} | {occupation_name}"


def _occupation_display_text(occupation_name: str) -> str:
    return f"{_occupation_zh(occupation_name)} ({occupation_name})"


def _occupation_zh(occupation_name: str) -> str:
    return OCCUPATION_ZH.get(occupation_name, occupation_name)


def _current_domain_label() -> str:
    value = st.session_state.get("career_target_domain", TARGET_DOMAIN_OPTIONS[0])
    return value if value in TARGET_DOMAIN_OPTIONS else TARGET_DOMAIN_OPTIONS[0]


def _is_beauty_row(row: pd.Series) -> bool:
    return _clean(row.get("_evidence_source", "")) == "beauty_phase5"


def _row_transition_span(row: pd.Series) -> str:
    return _clean(row.get("transition_span_v4", row.get("transition_span", "")))


def _row_learning_burden(row: pd.Series) -> str:
    return _clean(row.get("learning_burden_level", row.get("learning_burden", "")))


def _row_market_validation(row: pd.Series) -> str:
    return _clean(row.get("market_validation_v4", row.get("taiwan_market_evidence", row.get("market_validation", ""))))


def _row_missing_skills(row: pd.Series) -> object:
    return row.get("missing_skills_v4", row.get("missing_skills", ""))


def _row_shared_skills(row: pd.Series) -> object:
    return row.get("shared_top_skills", row.get("already_covered_skills", ""))


def _metric_html(label: str, value: object, translate_value: bool = True) -> str:
    display_value = _translate_value(value) if translate_value else _clean(value)
    return (
        '<div class="qj-metric">'
        f'<div class="qj-metric-label">{escape(str(label))}</div>'
        f'<div class="qj-metric-value">{escape(display_value)}</div>'
        "</div>"
    )


def _plain_text_html(value: object) -> str:
    text = _clean(value)
    if not text:
        return ""
    return escape(text)


def _path_reason(row: pd.Series) -> str:
    parts = [
        f"此路徑目前被標示為「{_translate_value(_row_transition_span(row))}」。"
    ]
    if _clean(row.get("target_occupation_name")) == "Data Scientists":
        parts.append("這張卡主要作為大幅重新學習的對照組。")
    if _clean(row.get("target_occupation_name")) == "Health Informatics Specialists":
        parts.append("此路徑與護理領域知識關聯較高，但目前培訓資料顯示仍有課程覆蓋缺口。")
    return escape("".join(parts))


def _path_conclusion(row: pd.Series) -> str:
    return PATH_CONCLUSIONS.get(_clean(row.get("target_occupation_name")), "需要先檢查可沿用能力、技能缺口與市場證據。")


def _market_signal_label(
    row: pd.Series,
    taiwanjobs_raw: pd.DataFrame | None = None,
    market_stats: dict[str, object] | None = None,
) -> str:
    if taiwanjobs_raw is None and market_stats is None:
        return _translate_value(_row_market_validation(row))
    stats = market_stats if market_stats is not None else _job_market_stats(row, taiwanjobs_raw)
    verified_count = int(float(stats.get("verified_job_count", 0) or 0))
    pending_count = int(float(stats.get("pending_job_count", 0) or 0))
    if verified_count == 0 and pending_count > 0:
        return "可能有市場，待確認"
    if verified_count == 0:
        return "市場證據不足"
    return _translate_value(_row_market_validation(row))


def _localized_alias_text(target_occupation: str) -> str:
    return "；".join(LOCALIZED_JOB_ALIASES.get(target_occupation, []))


def _matched_taiwanjobs(row: pd.Series, taiwanjobs_raw: pd.DataFrame | None) -> pd.DataFrame:
    if taiwanjobs_raw is None:
        return pd.DataFrame()
    matched_title_list = [title.strip() for title in _clean(row.get("matched_titles", "")).split(";") if title.strip()]
    matched_titles = set(matched_title_list)
    if not matched_titles and str(row.get("target_occupation_name", "")) not in LOCALIZED_JOB_ALIASES:
        return taiwanjobs_raw.iloc[0:0].copy()

    target_occupation = str(row["target_occupation_name"])
    working = taiwanjobs_raw.copy()
    working["_raw_job_index"] = working.index
    working["localized_alias_hits"] = working.apply(
        lambda job: "；".join(_localized_alias_hits(target_occupation, job)),
        axis=1,
    )
    exact_mask = working["OCCU_DESC（職務名稱）"].astype(str).isin(matched_titles)
    alias_mask = working["localized_alias_hits"].astype(str).ne("")
    matched = working.loc[exact_mask | alias_mask].copy()
    if matched.empty:
        return taiwanjobs_raw.iloc[0:0].copy()

    matched["mapping_candidate_source"] = matched.apply(
        lambda job: _mapping_candidate_source(job, matched_titles),
        axis=1,
    )
    title_order = {title: index for index, title in enumerate(matched_title_list)}
    matched["_matched_order"] = matched["OCCU_DESC（職務名稱）"].map(title_order).fillna(
        len(title_order) + matched["_raw_job_index"]
    )
    relevance = matched.apply(lambda job: _job_relevance(target_occupation, job), axis=1)
    matched["relevance_score"] = [item["score"] for item in relevance]
    matched["relevance_confidence"] = [item["confidence"] for item in relevance]
    matched["manual_review_needed"] = [item["manual_review_needed"] for item in relevance]
    matched["review_note"] = [item["review_note"] for item in relevance]
    return matched.sort_values(
        ["relevance_score", "_matched_order", "_raw_job_index"],
        ascending=[False, True, True],
    ).drop(
        columns=["_matched_order", "_raw_job_index"]
    ).reset_index(drop=True)


def _prioritized_job_preview(matched_jobs: pd.DataFrame) -> pd.DataFrame:
    display = matched_jobs.copy()
    display["_confidence_order"] = display["relevance_confidence"].map({"High": 0, "Medium": 1}).fillna(2)
    display["_monthly"] = display["SALARYCD（核薪方式）"].astype(str).eq("月薪")
    display = display.sort_values(["_confidence_order", "relevance_score", "_monthly"], ascending=[True, False, False])
    return display.head(5).drop(columns=["_confidence_order", "_monthly"])


def _job_market_stats(row: pd.Series, taiwanjobs_raw: pd.DataFrame | None) -> dict[str, object]:
    if _is_beauty_row(row):
        lower = _clean(row.get("salary_lower_median_high", ""))
        upper = _clean(row.get("salary_upper_median_high", ""))
        salary = "未知"
        if lower and upper:
            salary = f"NT$ {_salary_amount(lower)} - {_salary_amount(upper)}"
        elif lower:
            salary = f"NT$ {_salary_amount(lower)} 以上"
        return {
            "verified_job_count": int(float(row.get("taiwanjobs_high_relevance_job_count", 0) or 0)),
            "pending_job_count": int(float(row.get("taiwanjobs_medium_relevance_job_count", 0) or 0)),
            "verified_demand_persons": int(float(row.get("total_demand_persons_high", 0) or 0)),
            "salary": salary,
        }
    matched_jobs = _matched_taiwanjobs(row, taiwanjobs_raw)
    if matched_jobs.empty:
        return {
            "verified_job_count": 0,
            "pending_job_count": 0,
            "verified_demand_persons": 0,
            "salary": "未知",
        }
    verified = matched_jobs.loc[matched_jobs["relevance_confidence"].eq("High")].copy()
    pending = matched_jobs.loc[matched_jobs["relevance_confidence"].eq("Medium")].copy()
    demand = pd.to_numeric(verified.get("JOB_PERSON（雇用人數）"), errors="coerce").fillna(0).sum()
    monthly = verified.loc[verified["SALARYCD（核薪方式）"].astype(str).eq("月薪")].copy()
    monthly["salary_lower"] = pd.to_numeric(monthly["NT_L（薪資範圍下限）"], errors="coerce")
    monthly["salary_upper"] = pd.to_numeric(monthly["NT_U（薪資範圍上限）"], errors="coerce")
    monthly = monthly.dropna(subset=["salary_lower", "salary_upper"])
    if monthly.empty:
        salary = "未知"
    else:
        salary = f"NT$ {monthly['salary_lower'].median():,.0f} - {monthly['salary_upper'].median():,.0f}"
    return {
        "verified_job_count": len(verified),
        "pending_job_count": len(pending),
        "verified_demand_persons": demand,
        "salary": salary,
    }


def _job_card_html(target_occupation: str, job: pd.Series) -> str:
    review_note = _clean(job.get("review_note", ""))
    review_badge = f'<div class="qj-job-review">{escape(review_note)}</div>' if review_note else ""
    url = _clean(job.get("URL_QUERY（職缺資料URL）", ""))
    link = f'<a href="{escape(url)}" target="_blank" rel="noopener noreferrer">原始職缺來源</a>' if url else "原始職缺來源：未提供"
    return (
        '<div class="qj-job-card">'
        f'<div class="qj-job-title">{escape(_clean(job.get("OCCU_DESC（職務名稱）", "")))}</div>'
        f"{review_badge}"
        '<div class="qj-job-meta">'
        f'<span>{escape(_clean(job.get("COMPNAME（公司名稱）", "")))}</span>'
        f'<span>{escape(_clean(job.get("CITYNAME（工作地點）", "")))}</span>'
        f'<span>{escape(_job_salary(job))}</span>'
        "</div>"
        f'<div class="qj-job-summary">{escape(_job_summary(job.get("JOB_DETAIL（工作內容）", "")))}</div>'
        f'<div class="qj-job-source">{link}</div>'
        "</div>"
    )


def _job_salary(job: pd.Series) -> str:
    salary_type = _clean(job.get("SALARYCD（核薪方式）", ""))
    lower = _clean(job.get("NT_L（薪資範圍下限）", ""))
    upper = _clean(job.get("NT_U（薪資範圍上限）", ""))
    if salary_type == "月薪":
        lower_text = _salary_amount(lower)
        upper_text = _salary_amount(upper)
        if lower_text and upper_text:
            return f"月薪 NT$ {lower_text} - {upper_text}"
        if lower_text:
            return f"月薪 NT$ {lower_text} 以上"
        return "月薪：未提供範圍"
    if "每月經常性薪資" in salary_type:
        return f"薪資資訊：{salary_type}（未列入月薪中位數比較）"
    if salary_type:
        return f"薪資資訊：{salary_type}（未列入月薪比較）"
    return "薪資資訊：未知"


def _salary_amount(value: str) -> str:
    if not value or value == "-":
        return ""
    try:
        return f"{float(value):,.0f}"
    except ValueError:
        return value


def _job_summary(value: object) -> str:
    text = re.sub(r"\s+", " ", _clean(value)).strip()
    if not text:
        return "目前職缺未提供工作內容摘要。"
    if len(text) <= 150:
        return text
    return text[:150].rstrip("，,。 ") + "..."


def _mapping_candidate_source(job: pd.Series, matched_titles: set[str]) -> str:
    sources = []
    if _clean(job.get("OCCU_DESC（職務名稱）", "")) in matched_titles:
        sources.append("v3.5 matched title")
    if _clean(job.get("localized_alias_hits", "")):
        sources.append("v3.6 localized alias")
    return " + ".join(sources)


def _localized_alias_hits(target_occupation: str, job: pd.Series) -> list[str]:
    text = _job_search_text(job)
    return [alias for alias in LOCALIZED_JOB_ALIASES.get(target_occupation, []) if _contains_keyword(text, alias)]


def _job_search_text(job: pd.Series) -> str:
    fields = [
        "OCCU_DESC（職務名稱）",
        "CJOB_NAME1（職務大類別名稱）",
        "CJOB_NAME2（職務小類別名稱）",
        "JOB_DETAIL（工作內容）",
    ]
    return " ".join(_clean(job.get(field, "")) for field in fields)


def _job_relevance(target_occupation: str, job: pd.Series) -> dict[str, object]:
    rules = JOB_RELEVANCE_RULES[target_occupation]
    title = _clean(job.get("OCCU_DESC（職務名稱）", ""))
    category = " ".join(
        [
            _clean(job.get("CJOB_NAME1（職務大類別名稱）", "")),
            _clean(job.get("CJOB_NAME2（職務小類別名稱）", "")),
        ]
    )
    detail = _clean(job.get("JOB_DETAIL（工作內容）", ""))
    combined = f"{title} {category} {detail}"

    title_hits = _keyword_hits(title, rules["title"])
    category_hits = _keyword_hits(category, rules["category"])
    detail_hits = _keyword_hits(detail, rules["detail"])
    exclude_hits = _keyword_hits(combined, JOB_RELEVANCE_EXCLUDE_TERMS)

    score = min(0.45, 0.18 * len(title_hits))
    score += min(0.20, 0.08 * len(category_hits))
    score += min(0.45, 0.07 * len(detail_hits))
    if exclude_hits:
        score -= 0.45
    score = max(0.0, min(1.0, score))

    if _needs_domain_anchor(target_occupation, combined):
        score = min(score, 0.44)

    if score >= 0.72:
        confidence = "High"
    elif score >= 0.48:
        confidence = "Medium"
    else:
        confidence = "Low"

    notes = []
    if exclude_hits:
        notes.append("含行政、銷售、櫃台、傳送或門市等排除訊號")
    if confidence == "Medium":
        notes.append("相關但仍需人工確認")
    if confidence == "Low":
        notes.append("relevance 不足，暫不納入市場統計")
    if _needs_domain_anchor(target_occupation, combined):
        notes.append("缺少此路徑必要的臨床／資料／資訊錨點")

    return {
        "score": round(score, 2),
        "confidence": confidence,
        "manual_review_needed": "yes" if confidence != "High" else "no",
        "review_note": "；".join(notes),
    }


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if _contains_keyword(text, keyword)]


def _contains_keyword(text: str, keyword: str) -> bool:
    if not keyword:
        return False
    if re.fullmatch(r"[A-Za-z0-9+#.]+", keyword):
        return re.search(rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])", text, flags=re.IGNORECASE) is not None
    return keyword.lower() in text.lower()


def _needs_domain_anchor(target_occupation: str, text: str) -> bool:
    if target_occupation == "Clinical Research Coordinators":
        clinical_terms = ["臨床", "醫療", "醫院", "診所", "病人", "患者", "受試", "試驗", "醫學"]
        research_terms = ["研究", "試驗", "受試", "調查"]
        return not (any(term in text for term in clinical_terms) and any(term in text for term in research_terms))
    if target_occupation == "Clinical Data Managers":
        return not any(term in text for term in ["資料", "數據", "資料庫", "統計", "分析", "精算"])
    if target_occupation == "Health Informatics Specialists":
        health_terms = ["醫療", "醫院", "診所", "健康", "病歷", "病房", "衛材", "臨床"]
        informatics_terms = ["資訊", "系統", "AI", "軟體", "資料", "數據", "資料庫", "RAG", "API"]
        return not (any(term in text for term in health_terms) and any(term in text for term in informatics_terms))
    if target_occupation == "Data Scientists":
        return not any(term in text for term in ["資料", "數據", "統計", "分析", "AI", "Python", "R", "模型", "機器學習"])
    return False


def _detail_block(label: str, value_html: str) -> str:
    if not value_html:
        value_html = '<span class="qj-note">目前證據輸出沒有列出此類技能缺口。</span>'
    return (
        '<div class="qj-career-detail-block">'
        f'<div class="qj-metric-label">{escape(label)}</div>'
        f'<div class="qj-career-detail-text">{value_html}</div>'
        "</div>"
    )


def _coverage_label(row: pd.Series) -> str:
    missing_count = int(float(row.get("number_of_missing_skills", 0) or 0))
    trainable_missing = int(float(row.get("number_of_trainable_missing_skills_found", 0) or 0))
    if _is_beauty_row(row):
        course_count = int(float(row.get("training_course_count", 0) or 0))
        if missing_count == 0:
            return f"Phase 5 找到 {course_count} 門對應課程；O*NET 未列主要缺口"
        return f"Phase 5 找到 {course_count} 門對應課程；{trainable_missing}/{missing_count} 個缺口有課程"
    if missing_count == 0:
        gap_count = int(float(row.get("number_of_gap_skills", 0) or 0))
        trainable_gap = int(float(row.get("number_of_trainable_skills_found", 0) or 0))
        if gap_count > 0:
            return f"無缺口；{trainable_gap}/{gap_count} 個部分缺口有課程"
        return "無缺口技能"
    return f"{trainable_missing}/{missing_count} 個缺口（{_percent(row.get('training_coverage_ratio'))}）"


def _gap_coverage_label(row: pd.Series) -> str:
    gap_count = int(float(row.get("number_of_gap_skills", 0) or 0))
    trainable_gap = int(float(row.get("number_of_trainable_skills_found", 0) or 0))
    if gap_count == 0:
        return "沒有缺口技能"
    return f"{trainable_gap}/{gap_count} 個缺口（{_percent(row.get('gap_skill_training_coverage_ratio'))}）"


def _gap_summary(row: pd.Series) -> str:
    missing_count = int(float(row.get("number_of_missing_skills", 0) or 0))
    partial_count = int(float(row.get("number_of_partially_covered_skills", 0) or 0))
    if missing_count and partial_count:
        return f"{missing_count} 個缺口，{partial_count} 個部分具備"
    if missing_count:
        return f"{missing_count} 個缺口"
    if partial_count:
        return f"{partial_count} 個部分具備"
    return "目前未列出主要缺口"


def _skill_chip_list(value: object) -> str:
    chips = []
    for item in _split_skill_items(value):
        if item.startswith("..."):
            chips.append(f'<span class="qj-skill-more">{escape(_translate_more_item(item))}</span>')
            continue
        skill_name = _skill_name_from_item(item)
        chips.append(f'<span class="qj-skill-chip">{escape(_skill_zh(skill_name))}</span>')
    if not chips:
        return ""
    return '<div class="qj-skill-list">' + "".join(chips) + "</div>"


def _raw_skill_rows(value: object, status: str) -> list[dict[str, str]]:
    rows = []
    for item in _split_skill_items(value):
        if item.startswith("..."):
            continue
        skill_name = _skill_name_from_item(item)
        rows.append(
            {
                "status": status,
                "skill_zh": _skill_zh(skill_name),
                "onet_skill_name": skill_name,
                "skill_type": _skill_type_from_item(item),
                "target_im": _match_value(item, r"target ([0-9.]+)") or _score_from_item(item),
                "source_im": _match_value(item, r"RN ([0-9.]+)"),
                "gap": _match_value(item, r"gap ([0-9.]+)"),
                "raw_evidence": item,
            }
        )
    return rows


def _split_skill_items(value: object) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    return [item.strip() for item in text.split(";") if item.strip()]


def _skill_name_from_item(item: str) -> str:
    return item.split(" (", 1)[0].strip()


def _skill_type_from_item(item: str) -> str:
    if "(" not in item or ")" not in item:
        return ""
    body = item.split("(", 1)[1].rsplit(")", 1)[0]
    return re.split(r"[:,]", body, maxsplit=1)[0].strip()


def _score_from_item(item: str) -> str:
    if "target " in item:
        return ""
    return _match_value(item, r": ([0-9.]+)")


def _match_value(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1) if match else ""


def _skill_zh(skill_name: object) -> str:
    return SKILL_ZH.get(_clean(skill_name), _clean(skill_name))


def _translate_value(value: object) -> str:
    text = _clean(value)
    return VALUE_ZH.get(text, text)


def _translate_status(value: object) -> str:
    status = _clean(value)
    return {
        "already_covered": "已具備",
        "partially_covered": "部分具備",
        "missing": "缺口",
    }.get(status, _translate_value(status))


def _translate_more_item(item: str) -> str:
    match = re.search(r"\+(\d+)", item)
    if match:
        return f"另有 {match.group(1)} 項原始技能"
    return item


def _percent(value: object) -> str:
    if pd.isna(value) or _clean(value) == "":
        return "未知"
    return f"{float(value) * 100:.0f}%"


def _money(value: object) -> str:
    if pd.isna(value) or _clean(value) == "":
        return "未知"
    return f"NT$ {float(value):,.0f}"


def _hours(value: object) -> str:
    if pd.isna(value) or _clean(value) == "":
        return "未知"
    return f"{float(value):.0f} h"


def _number(value: object) -> str:
    if pd.isna(value) or _clean(value) == "":
        return "未知"
    return f"{float(value):,.0f}"


def _decimal(value: object) -> str:
    if pd.isna(value) or _clean(value) == "":
        return "未知"
    return f"{float(value):.3f}"


def _salary(row: pd.Series) -> str:
    basis = _clean(row.get("salary_basis", ""))
    lower = row.get("salary_lower_median")
    upper = row.get("salary_upper_median")
    if "monthly" not in basis or pd.isna(lower) or pd.isna(upper):
        return "未知"
    return f"NT$ {float(lower):,.0f} - {float(upper):,.0f}"


def _manual_review(row: pd.Series) -> str:
    value = _clean(row.get("taiwanjobs_manual_review_needed", row.get("manual_review_needed", "")))
    return "Needed" if value == "yes" else "No"


def _clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text
