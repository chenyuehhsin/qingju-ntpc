"""Offline, evidence-grounded answers for the AI policy dashboard.

This deliberately has no network or model dependency.  It turns only the
official dashboard snapshot already shipped with the site into a readable
answer, so the local demo remains useful even when AWS is unavailable.
"""

from __future__ import annotations

from typing import Any


TOPIC_KEYWORDS = {
    "employment_service_awareness": ("就業通", "台灣就業通", "臺灣就業通", "公立就業服務", "就業博覽會", "認知"),
    "government_service_expectations": ("政府", "期望", "希望", "職涯諮詢"),
    "employment_information_access": ("就業資訊", "求職管道", "資訊"),
    "job_search_barriers": ("尋職", "找工作", "求職", "困難"),
    "job_choice_preferences": ("選擇工作", "考量", "偏好"),
    "career_mobility": ("轉職", "換工作", "離職"),
    "career_stability": ("留任", "穩定", "轉換工作"),
    "education_job_match": ("學用", "所學", "相關程度", "實習", "科系"),
    "training_and_skills": ("訓練", "進修", "證照", "技能"),
    "employment_quality": ("薪資", "工時", "加班", "計薪", "待遇", "工作條件"),
}


def answer_policy_question(question: str, selected_topic: str, payloads: dict[str, Any]) -> str:
    """Return a deterministic Traditional-Chinese answer from the snapshot."""
    attention = sorted(
        payloads["policy_attention"].get("topics", []),
        key=lambda row: row.get("rank_baseline", 999),
    )
    topics = {row.get("topic_id"): row for row in attention}
    requested = _find_topic(question, selected_topic, attention)

    if _is_out_of_scope(question):
        return _scope_answer(payloads)
    if _asks_about_score(question):
        return _score_answer(requested or attention[0], payloads)
    if requested:
        return _topic_answer(requested, payloads)
    return _ranking_answer(attention, payloads)


def _find_topic(question: str, selected_topic: str, attention: list[dict[str, Any]]) -> dict[str, Any] | None:
    if selected_topic != "不限主題，由系統依問題判斷":
        return next((row for row in attention if row.get("topic_name_zh") == selected_topic), None)
    text = question.lower()
    for topic_id, keywords in TOPIC_KEYWORDS.items():
        if any(keyword.lower() in text for keyword in keywords):
            return next((row for row in attention if row.get("topic_id") == topic_id), None)
    return None


def _is_out_of_scope(question: str) -> bool:
    text = question.lower()
    return any(token in text for token in ("新北", "台北", "臺北", "18-35", "18–35", "失業", "neet"))


def _asks_about_score(question: str) -> bool:
    return any(token in question.lower() for token in ("怎麼算", "如何計算", "為什麼", "權重", "排名"))


def _ranking_answer(attention: list[dict[str, Any]], payloads: dict[str, Any]) -> str:
    top = attention[:3]
    names = "、".join(f"{row['topic_name_zh']}（關注度 {int(row['score_display'])}）" for row in top)
    lines = [
        "### 【結論】",
        f"依目前已收集並驗證的證據，最值得優先檢視的青年就業議題為：{names}。",
        "「關注度」表示目前證據指向該議題的程度，不是政策成效或政府績效評分。",
        "",
        "### 【可查閱的證據】",
    ]
    for row in attention[:5]:
        lines.append(
            f"- {row['topic_name_zh']}：關注度 {int(row['score_display'])}，"
            f"基準權重下第 {int(row['rank_baseline'])} 名，信心{_confidence(row.get('score_confidence'))}。"
        )
    return "\n".join(lines + _common_sections(payloads))


def _topic_answer(topic: dict[str, Any], payloads: dict[str, Any]) -> str:
    lines = [
        "### 【結論】",
        f"{topic['topic_name_zh']}目前的政策關注度為 {int(topic['score_display'])}"
        f"（基準權重下第 {int(topic['rank_baseline'])} 名，信心{_confidence(topic.get('score_confidence'))}）。",
        "這個分數可作為閱讀官方證據的順序，不代表政策成效、政府績效或預算優先順序。",
        "",
        "### 【資料證據】",
    ]
    for component in topic.get("components", []):
        if component.get("available"):
            lines.append(
                f"- {component['label_zh']}：分數 {float(component['score']):.1f}、"
                f"權重 {float(component['weight']):.2f}、貢獻 {float(component['contribution']):.1f}。"
            )
    lines.append("- 可切換上方「青年就業數據」、「歷年趨勢與服務」及「政策關注度」查看對應圖表與原始定義。")
    return "\n".join(lines + _common_sections(payloads))


def _score_answer(topic: dict[str, Any], payloads: dict[str, Any]) -> str:
    lines = [
        "### 【結論】",
        f"{topic['topic_name_zh']}的政策關注度為 {int(topic['score_display'])}，"
        f"在基準權重下排名第 {int(topic['rank_baseline'])}。",
        "分數以各項可用元件乘上權重後，除以實際可用元件的權重總和，再換算為 0–100；缺少資料不會以 0 分計算。",
        "",
        "### 【分數組成】",
    ]
    for component in topic.get("components", []):
        if component.get("available"):
            lines.append(
                f"- {component['label_zh']}：分數 {float(component['score']):.1f}，"
                f"權重 {float(component['weight']):.2f}，貢獻 {float(component['contribution']):.1f}。"
            )
    return "\n".join(lines + _common_sections(payloads))


def _scope_answer(payloads: dict[str, Any]) -> str:
    scope = payloads["data_scope"]
    return "\n".join([
        "### 【範圍說明】",
        "本頁資料是全臺 15–29 歲受僱青年勞工的調查結果，不能代表個別縣市、18–35 歲青年或失業／未就業青年。",
        "因此目前資料不足以直接回答這個範圍的問題。",
        *_common_sections(payloads),
    ])


def _common_sections(payloads: dict[str, Any]) -> list[str]:
    scope = payloads["data_scope"]
    years = " / ".join(str(year) for year in scope.get("survey_years", []))
    return [
        "",
        "### 【資料限制】",
        "- 這是全臺 15–29 歲受僱青年勞工的抽樣調查；數值不能延伸為失業青年、特定縣市或其他年齡層。",
        "- 所有比較都是描述性證據，不表示因果關係或政策成效。",
        "",
        "### 【資料來源】",
        f"- {scope.get('source_agency', '勞動部')}「{scope.get('survey_name', '15–29 歲青年勞工就業狀況調查')}」{years} 年，全臺範圍。",
        "- 每項數值均可回查官方統計表與本頁資料來源。",
    ]


def _confidence(value: object) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(str(value), "未標示")
