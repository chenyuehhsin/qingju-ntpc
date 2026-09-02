from __future__ import annotations

import re
from html import escape
from textwrap import dedent

import pandas as pd
import streamlit as st


DEMO_SOURCE = "Registered Nurses"
DEMO_TARGET_DOMAIN = "Technology / AI"
DEMO_HORIZON = "6 months"
REPRESENTATIVE_PATHS = [
    "Clinical Research Coordinators",
    "Clinical Data Managers",
    "Health Informatics Specialists",
    "Data Scientists",
]
PATH_NOTES = {
    "Data Scientists": "大幅重新學習對照組",
    "Health Informatics Specialists": "課程覆蓋缺口",
}
OCCUPATION_ZH = {
    "Registered Nurses": "護理師",
    "Clinical Research Coordinators": "臨床研究協調員",
    "Clinical Data Managers": "臨床資料管理師",
    "Health Informatics Specialists": "醫療資訊專員",
    "Data Scientists": "資料科學家",
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


def render_career_evidence_viewer(
    candidates_v35: pd.DataFrame,
    training_v4: pd.DataFrame,
    course_mapping: pd.DataFrame,
) -> None:
    evidence = _representative_paths(candidates_v35, training_v4)

    _html(
        """
        <div class="qj-career-header">
            <div class="qj-header-title">職涯轉換證據檢視器</div>
            <div class="qj-subtitle">護理師 → 科技 / AI 領域的可追溯證據檢視</div>
        </div>
        """
    )

    _render_explore_section()
    if st.button("探索可能路徑", use_container_width=False, key="career_explore_button"):
        st.session_state.career_evidence_explored = True

    if not st.session_state.get("career_evidence_explored", False):
        _html(
            """
            <div class="qj-career-empty">
                這是固定展示情境。按下「探索可能路徑」後，會顯示 v3.5 / v4 輸出中的代表性職涯路徑。
            </div>
            """
        )
        return

    st.markdown("### 值得探索的職涯路徑")
    _html(
        '<div class="qj-section-note">代表性案例按產品需求固定展示，不是排序，也不是推薦分數。</div>'
    )
    _render_path_cards(evidence)

    st.markdown("### 證據細節")
    option_labels = [_occupation_option_label(name) for name in REPRESENTATIVE_PATHS]
    selected_label = st.selectbox(
        "選擇職涯路徑",
        option_labels,
        index=0,
        key="career_path_select",
    )
    selected_name = REPRESENTATIVE_PATHS[option_labels.index(selected_label)]
    selected = evidence.loc[evidence["target_occupation_name"].eq(selected_name)].iloc[0]
    selected_mapping = course_mapping.loc[
        course_mapping["target_occupation_code"].astype(str).eq(str(selected["target_occupation_code"]))
    ].copy()
    _render_detail(selected, selected_mapping)


def _representative_paths(candidates_v35: pd.DataFrame, training_v4: pd.DataFrame) -> pd.DataFrame:
    merged = training_v4.merge(
        candidates_v35,
        on=["target_occupation_code", "target_occupation_name"],
        how="left",
        suffixes=("_v4", "_v35"),
        validate="one_to_one",
    )
    available = merged.loc[merged["target_occupation_name"].isin(REPRESENTATIVE_PATHS)].copy()
    missing = [name for name in REPRESENTATIVE_PATHS if name not in set(available["target_occupation_name"])]
    if missing:
        raise RuntimeError(f"Missing representative career paths in v3.5/v4 outputs: {missing}")
    available["_order"] = available["target_occupation_name"].map(
        {name: index for index, name in enumerate(REPRESENTATIVE_PATHS)}
    )
    return available.sort_values("_order").drop(columns=["_order"]).reset_index(drop=True)


def _render_explore_section() -> None:
    cols = st.columns([1, 1, 1], gap="medium")
    values = [
        ("目前背景", _occupation_display_text(DEMO_SOURCE)),
        ("目標領域", "科技 / AI"),
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
        '<div class="qj-note">目前是固定展示情境，只支援護理師 → 科技 / AI 的證據檢視。</div>'
    )


def _render_path_cards(evidence: pd.DataFrame) -> None:
    cols = st.columns(4, gap="medium")
    for col, (_, row) in zip(cols, evidence.iterrows()):
        note = PATH_NOTES.get(str(row["target_occupation_name"]), "")
        if row["target_occupation_name"] == "Health Informatics Specialists" and float(row["training_coverage_ratio"]) >= 0.5:
            note = ""
        badge = _badge_html(note)
        with col:
            _html(
                f"""
                <div class="qj-career-card">
                    {_occupation_title_html(str(row["target_occupation_name"]))}
                    {badge}
                    <div class="qj-career-card-grid">
                        {_metric_html("原有能力可利用程度", row["transition_span_v4"])}
                        {_metric_html("需要補強的技能", _gap_summary(row), translate_value=False)}
                        {_metric_html("台灣市場訊號", row["market_validation_v4"])}
                        {_metric_html("潛在課程覆蓋", _coverage_label(row), translate_value=False)}
                        {_metric_html("學習負擔", row["learning_burden_level"])}
                    </div>
                </div>
                """
            )


def _render_detail(row: pd.Series, course_mapping: pd.DataFrame) -> None:
    left, right = st.columns([1.08, 0.92], gap="medium")
    with left:
        st.markdown("#### 為什麼值得探索？")
        _html(
            f"""
            <div class="qj-panel">
                {_detail_block("可利用的護理背景", _skill_chip_list(row.get("shared_top_skills", "")))}
                {_detail_block("路徑定位", _path_reason(row))}
            </div>
            """
        )

        st.markdown("#### 原有能力可利用程度")
        _html(
            f"""
            <div class="qj-panel">
                <div class="qj-career-profile-grid">
                    {_metric_html("能力延續", row.get("transition_span_v4", ""))}
                    {_metric_html("學習負擔", row.get("learning_burden_level", ""))}
                </div>
                {_detail_block("部分已具備技能", _skill_chip_list(row.get("partially_covered_skills", "")))}
            </div>
            """
        )

        st.markdown("#### 需要補強的技能")
        _html(
            f"""
            <div class="qj-panel">
                {_detail_block("缺口技能", _skill_chip_list(row.get("missing_skills_v4", "")))}
            </div>
            """
        )

    with right:
        st.markdown("#### 台灣市場訊號")
        _html(
            f"""
            <div class="qj-panel">
                <div class="qj-career-profile-grid">
                    {_metric_html("對應職缺數", _number(row.get("matched_job_count")), translate_value=False)}
                    {_metric_html("需求人數", _number(row.get("total_demand_persons")), translate_value=False)}
                    {_metric_html("月薪資料", _salary(row), translate_value=False)}
                    {_metric_html("市場訊號", row.get("market_validation_v4", ""))}
                    {_metric_html("人工確認", _manual_review(row))}
                </div>
            </div>
            """
        )

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

        st.markdown("#### 學習負擔")
        _html(
            f"""
            <div class="qj-panel">
                <div class="qj-career-profile-grid">
                    {_metric_html("整體負擔", row.get("learning_burden_level", ""))}
                    {_metric_html("收入中斷估計", row.get("possible_income_interruption", "unknown"))}
                </div>
            </div>
            """
        )

        st.markdown("#### 資料限制")
        _html(
            """
            <div class="qj-panel qj-note">
                O*NET 為美國職業資料，台灣職涯制度與證照要求可能不同。<br>
                TaiwanJobs 職稱映射仍需要人工確認，尤其是醫療 × 科技職稱。<br>
                培訓資料目前只有課程名稱，沒有完整 syllabus 或細部課程內容。<br>
                本頁不代表轉職成功機率，也沒有合成單一職涯分數。
            </div>
            """
        )
    _render_onet_evidence_expander(row, course_mapping)
    _render_market_evidence_expander(row)
    _render_course_table_expander(course_mapping)


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


def _render_course_table_expander(course_mapping: pd.DataFrame) -> None:
    with st.expander("查看完整培訓課程表", expanded=False):
        _render_course_table(course_mapping)


def _render_onet_evidence_expander(row: pd.Series, course_mapping: pd.DataFrame) -> None:
    with st.expander("查看 O*NET 原始證據", expanded=False):
        st.caption("原始英文名稱與 IM/gap 數值直接來自既有 v3.5 / v4 outputs；此處只做 UI 呈現。")
        raw_rows = (
            _raw_skill_rows(row.get("shared_top_skills", ""), "可轉移 / 共享技能")
            + _raw_skill_rows(row.get("partially_covered_skills", ""), "部分已具備技能")
            + _raw_skill_rows(row.get("missing_skills_v4", ""), "仍需補強技能")
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
    with st.expander("查看 TaiwanJobs 映射技術證據", expanded=False):
        st.caption("職稱映射可信度、mapping score 與 matched titles 直接來自既有 v3.5 output。")
        _html(
            f"""
            <div class="qj-panel">
                <div class="qj-career-profile-grid">
                    {_metric_html("職稱映射可信度", row.get("taiwanjobs_mapping_confidence", ""))}
                    {_metric_html("人工確認", _manual_review(row))}
                    {_metric_html("映射方法", row.get("mapping_method", ""), translate_value=False)}
                    {_metric_html("映射分數", _decimal(row.get("mapping_score")), translate_value=False)}
                </div>
                {_detail_block("TaiwanJobs matched titles", _plain_text_html(row.get("matched_titles", "")))}
            </div>
            """
        )


def _html(markup: str) -> None:
    st.markdown(dedent(markup).strip(), unsafe_allow_html=True)


def _badge_html(note: str) -> str:
    if note:
        return f'<div class="qj-career-badge">{escape(note)}</div>'
    return '<div aria-hidden="true" style="min-height: 1.9rem; margin: 0.45rem 0 0.2rem 0;"></div>'


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
        f"此路徑目前被標示為「{_translate_value(row.get('transition_span_v4'))}」，"
        f"台灣市場訊號為「{_translate_value(row.get('market_validation_v4'))}」。"
    ]
    if _clean(row.get("target_occupation_name")) == "Data Scientists":
        parts.append("這張卡主要作為大幅重新學習的對照組。")
    if _clean(row.get("target_occupation_name")) == "Health Informatics Specialists":
        parts.append("此路徑與護理領域知識關聯較高，但目前培訓資料顯示仍有課程覆蓋缺口。")
    return escape("".join(parts))


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
    if pd.isna(value):
        return "未知"
    return f"{float(value) * 100:.0f}%"


def _money(value: object) -> str:
    if pd.isna(value):
        return "未知"
    return f"NT$ {float(value):,.0f}"


def _hours(value: object) -> str:
    if pd.isna(value):
        return "未知"
    return f"{float(value):.0f} h"


def _number(value: object) -> str:
    if pd.isna(value):
        return "未知"
    return f"{float(value):,.0f}"


def _decimal(value: object) -> str:
    if pd.isna(value):
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
