#!/usr/bin/env python3
"""Build Career Learning Ladder Phase 8 from existing Phase 7 outputs.

This is an interpretation layer for policy analysis. It does not modify raw
data, v1-v4 career evidence, Career Discovery, or Phase 7 calculations.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE7_CSV = PROJECT_ROOT / "outputs" / "career" / "career_policy_lens_phase7.csv"

OUTPUT_CSV = PROJECT_ROOT / "outputs" / "career" / "career_learning_ladder_phase8.csv"
OUTPUT_MD = PROJECT_ROOT / "outputs" / "career" / "career_learning_ladder_phase8.md"
METHOD_MD = PROJECT_ROOT / "docs" / "career_learning_ladder_phase8_method.md"

OBSERVATION_DATE = "2026-09-03"

REPRESENTATIVE_PATHS = [
    "Clinical Research Coordinators",
    "Health Informatics Specialists",
    "Clinical Data Managers",
    "Data Scientists",
    "Hairdressers, Hairstylists, and Cosmetologists",
    "Skincare Specialists",
    "Spa Managers",
    "Makeup Artists, Theatrical and Performance",
]

SKILL_ZH = {
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
    "Communications and Media": "傳播與媒體",
    "Management of Financial Resources": "財務資源管理",
    "Economics and Accounting": "經濟與會計",
    "Management of Material Resources": "物料資源管理",
    "Administration and Management": "行政與管理",
    "Education and Training": "教育與訓練",
}

PUBLIC_LEARNING_SKILLS = {
    "Programming",
    "Computers and Electronics",
    "Mathematics",
    "Sales and Marketing",
    "Persuasion",
    "Design",
    "Communications and Media",
}


def read_phase7() -> pd.DataFrame:
    if not PHASE7_CSV.exists():
        raise FileNotFoundError(f"Missing Phase 7 CSV: {PHASE7_CSV}")
    df = pd.read_csv(PHASE7_CSV)
    missing = set(REPRESENTATIVE_PATHS) - set(df["target_occupation_name"])
    if missing:
        raise RuntimeError(f"Phase 7 CSV is missing representative paths: {sorted(missing)}")
    return df


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def num(value: object, default: float = 0.0) -> float:
    text = clean(value).replace(",", "")
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def split_list(value: object) -> list[str]:
    text = clean(value)
    if not text or text == "none":
        return []
    return [part.strip() for part in text.split(";") if part.strip() and not part.strip().startswith("...")]


def unique_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    unique = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def zh_skill_list(skills: list[str]) -> str:
    display_skills = unique_preserve_order(skills)
    if not display_skills:
        return "無明確 missing skill；仍需檢查 partially covered skills 與市場銜接"
    return "、".join(SKILL_ZH.get(skill, skill) for skill in display_skills)


def select_representative_paths(phase7: pd.DataFrame) -> pd.DataFrame:
    selected = phase7[phase7["target_occupation_name"].isin(REPRESENTATIVE_PATHS)].copy()
    selected["_order"] = selected["target_occupation_name"].map(
        {name: index for index, name in enumerate(REPRESENTATIVE_PATHS)}
    )
    return selected.sort_values("_order").drop(columns=["_order"]).reset_index(drop=True)


def build_exploration_direction(row: pd.Series) -> str:
    target = clean(row["target_occupation_name"])
    domain = clean(row["target_domain"])
    span = clean(row["transition_span"])
    if target == "Clinical Research Coordinators":
        return "從護理現場經驗切入臨床研究流程協調，先驗證研究行政、受試者溝通與資料紀錄工作的適配。"
    if target == "Health Informatics Specialists":
        return "從護理流程知識切入醫療資訊系統與流程數位化，先驗證醫療現場知識能否轉成系統需求理解。"
    if target == "Clinical Data Managers":
        return "從臨床資料理解切入資料管理、品質控管與研究資料流程。"
    if target == "Data Scientists":
        return "以資料科學作為科技跨域 major reskilling 對照路徑，重點是確認程式、數學與資料分析負擔。"
    if "Hairdressers" in target:
        return "從個人照護與服務溝通切入美容服務職涯，但主要技能需重新學習。"
    if target == "Skincare Specialists":
        return "從護理照護、皮膚與顧客信任感切入護膚服務，需驗證台灣美容職稱與課程銜接。"
    if target == "Spa Managers":
        return "從照護服務與現場管理切入美容服務管理，但市場職缺證據目前不足。"
    if "Makeup Artists" in target:
        return "以美妝創作作為低 skill reuse / high reskilling 對照，先檢查訓練負擔與市場證據。"
    return f"{domain} 中的 {target}；轉換跨度為 {span}。"


def build_foundation_step(row: pd.Series) -> str:
    missing = split_list(row.get("missing_skills_preview"))
    partial = split_list(row.get("partially_covered_skills_preview"))
    combined = missing + partial[:3]
    if not combined:
        return "先盤點護理既有能力與目標職務任務，確認可沿用能力如何轉譯成職缺語言。"
    return f"基礎能力補強：{zh_skill_list(combined[:6])}。優先處理 missing skills，再補 partially covered skills。"


def build_milestone(row: pd.Series) -> str:
    target = clean(row["target_occupation_name"])
    missing = split_list(row.get("missing_skills_preview"))
    if target in {"Clinical Data Managers", "Data Scientists", "Health Informatics Specialists"}:
        data_skills = [skill for skill in missing if skill in {"Programming", "Computers and Electronics", "Mathematics"}]
        if data_skills:
            return f"能力驗證：用小型資料清理 / 儀表板 / 分析作品驗證 {zh_skill_list(data_skills)}，並保留課程或作品證據。"
        return "能力驗證：以臨床流程文件、資料欄位整理或系統需求摘要證明可轉譯護理經驗。"
    if target == "Clinical Research Coordinators":
        return "能力驗證：整理臨床溝通、文件紀錄、時程協調案例，對應研究協調任務；目前沒有 missing-skill gap。"
    if "Hairdressers" in target or target == "Skincare Specialists":
        return "能力驗證：完成對應技術課程後，以實作紀錄、服務流程與顧客溝通案例驗證入門能力。"
    if target == "Spa Managers":
        return "能力驗證：以服務流程、排班 / 人員管理、銷售與財務基礎案例驗證管理能力。"
    if "Makeup Artists" in target:
        return "能力驗證：以妝容作品集與基礎設計 / 美感訓練紀錄驗證入門能力。"
    return "能力驗證：保留課程完成、作品或工作任務案例，作為下一步銜接依據。"


def build_advanced_training(row: pd.Series) -> str:
    courses = clean(row.get("matched_courses"))
    course_count = int(num(row.get("matched_course_count")))
    hours = num(row.get("total_training_hours"))
    cost = num(row.get("estimated_direct_course_cost"))
    if course_count == 0 or not courses or courses == "none":
        return "目前沒有明確 matched course；不應把 training coverage 解讀為技能已補足。"
    return (
        f"進階訓練：沿用既有 matched courses，現有證據顯示 {course_count} 門課、"
        f"{hours:.0f} 小時、直接課程費用約 NT$ {cost:,.0f}。這只是潛在課程覆蓋。"
    )


def build_market_linkage(row: pd.Series) -> str:
    high = num(row.get("high_relevance_job_count"), default=-1)
    medium = num(row.get("medium_relevance_job_count"), default=0)
    demand = num(row.get("high_relevance_demand_persons"), default=0)
    status = clean(row.get("market_evidence_status"))
    if high > 0:
        return f"市場職缺銜接：現有 output 有 {int(high)} 筆 High-relevance TaiwanJobs evidence，需求人數 {int(demand)}；Medium 待確認 {int(medium)}。"
    if high == 0:
        return "市場職缺銜接：High=0，公開市場證據不足；不代表職涯不存在，但不宜直接大量投入訓練資源。"
    return f"市場職缺銜接：{status}。既有 output 尚無 job-level High relevance count，需先做市場驗證。"


def intervention_flags(row: pd.Series) -> dict[str, str]:
    missing = split_list(row.get("missing_skills_preview"))
    public_hits = [skill for skill in missing if skill in PUBLIC_LEARNING_SKILLS]
    course_count = int(num(row.get("matched_course_count")))
    high = num(row.get("high_relevance_job_count"), default=-1)
    coverage = num(row.get("potential_training_coverage_ratio"), default=0)
    hours = num(row.get("total_training_hours"))
    cost = num(row.get("estimated_direct_course_cost"))
    learning_burden = clean(row.get("learning_burden")).lower()
    training_gap = clean(row.get("training_gap_status"))
    no_course_info = num(row.get("mol_no_course_info_percent"))
    fee_barrier = num(row.get("mol_fee_barrier_percent"))

    flags: list[str] = []
    reasons: list[str] = []

    if public_hits:
        flags.append("Public learning")
        reasons.append(f"Missing skills include standardizable foundations: {', '.join(unique_preserve_order(public_hits))}.")

    if course_count > 0:
        flags.append("Training guidance")
        reasons.append(
            f"Matched course evidence exists ({course_count} courses), while MOL proxy shows {no_course_info:.1f}% of non-participants did not know where training was available."
        )

    if course_count > 0 and (cost >= 50000 or hours >= 200):
        flags.append("Subsidy candidate")
        reasons.append(
            f"Existing training evidence implies substantial direct burden ({hours:.0f} hours, NT$ {cost:,.0f}); MOL proxy fee barrier is {fee_barrier:.1f}% among non-participants. No subsidy amount is proposed."
        )

    if high > 0 and missing and (coverage < 0.75 or training_gap == "Training gap"):
        flags.append("Cohort / partnership candidate")
        reasons.append(
            f"Market has High-relevance evidence ({int(high)} jobs) and skill gap is explicit, but potential training coverage is only {coverage:.3f}."
        )
    elif high <= 0 and training_gap == "Training gap":
        flags.append("Cohort / partnership candidate")
        reasons.append(
            "Skill gap and course-supply gap are visible, but market validation must come first because High-relevance job evidence is unavailable or zero."
        )

    if high <= 0 or high == -1:
        flags.append("Market validation needed")
        if high == 0:
            reasons.append("High=0 in existing TaiwanJobs evidence; treat as public market evidence insufficient, not market absence.")
        else:
            reasons.append("Existing output has aggregate market evidence only; job-level High-relevance evidence is unavailable.")

    if not flags:
        flags.append("Training guidance")
        reasons.append("Path has some evidence support but needs guided interpretation before scaling interventions.")

    # Deduplicate while preserving order.
    deduped_flags = list(dict.fromkeys(flags))
    deduped_reasons = list(dict.fromkeys(reasons))
    return {
        "policy_intervention_types": "; ".join(deduped_flags),
        "policy_intervention_evidence_reasons": " | ".join(deduped_reasons),
    }


def build_ladders(phase7: pd.DataFrame) -> pd.DataFrame:
    selected = select_representative_paths(phase7)
    rows = []
    for _, row in selected.iterrows():
        interventions = intervention_flags(row)
        missing = split_list(row.get("missing_skills_preview"))
        output = {
            "source_occupation": clean(row.get("source_occupation")),
            "target_domain": clean(row.get("target_domain")),
            "target_occupation_name": clean(row.get("target_occupation_name")),
            "transition_span": clean(row.get("transition_span")),
            "feasibility_level": clean(row.get("feasibility_level")),
            "market_evidence_status": clean(row.get("market_evidence_status")),
            "high_relevance_job_count": row.get("high_relevance_job_count"),
            "medium_relevance_job_count": row.get("medium_relevance_job_count"),
            "number_of_missing_skills": row.get("number_of_missing_skills"),
            "missing_skills": "; ".join(missing) if missing else "none",
            "missing_skills_zh": zh_skill_list(missing),
            "potential_training_coverage_ratio": row.get("potential_training_coverage_ratio"),
            "matched_course_count": row.get("matched_course_count"),
            "total_training_hours": row.get("total_training_hours"),
            "estimated_direct_course_cost": row.get("estimated_direct_course_cost"),
            "training_gap_status": clean(row.get("training_gap_status")),
            "learning_burden": clean(row.get("learning_burden")),
            "exploration_direction": build_exploration_direction(row),
            "foundation_skill_boost": build_foundation_step(row),
            "learning_milestone_or_validation": build_milestone(row),
            "advanced_training": build_advanced_training(row),
            "market_job_linkage": build_market_linkage(row),
            "policy_intervention_types": interventions["policy_intervention_types"],
            "policy_intervention_evidence_reasons": interventions["policy_intervention_evidence_reasons"],
            "conservative_note": "No success probability, no single career score, no subsidy amount; potential training coverage is not skill acquisition.",
            "phase7_data_limitations": clean(row.get("data_limitations")),
        }
        rows.append(output)
    return pd.DataFrame(rows)


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    frame = df.copy().fillna("")
    columns = [str(col) for col in frame.columns]

    def escape(value: object) -> str:
        return str(value).replace("\n", "<br>").replace("|", "\\|")

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(escape(row[col]) for col in frame.columns) + " |")
    return "\n".join(lines)


def write_method() -> None:
    lines = [
        "# Career Learning Ladder Phase 8 Method",
        "",
        f"Generated: {OBSERVATION_DATE}",
        "",
        "Phase 8 translates existing Phase 7 evidence into explainable learning-ladder and policy-intervention candidates. It does not modify raw data, v1-v4 analysis, Career Discovery, Phase 7 calculations, or UI.",
        "",
        "## Inputs",
        "",
        "- `outputs/career/career_policy_lens_phase7.csv` as the structured source for skill gap, market evidence, training evidence, MOL proxy signals, and Phase 7 data limitations.",
        "- `outputs/career/career_policy_lens_phase7.md` remains the human-readable upstream summary, but the Phase 8 script does not parse narrative text.",
        "",
        "## Representative Path Selection",
        "",
        "Phase 8 does not build full ladders for all 18 Phase 7 rows. It selects representative paths that cover different evidence situations:",
        "",
        "- high nursing skill reuse with low missing-skill gap",
        "- healthcare technology bridge path with training gap",
        "- clinical data bridge path with matched courses",
        "- major-reskilling technology comparator",
        "- beauty / personal-care paths with High-relevance market evidence",
        "- paths where public market evidence is insufficient",
        "",
        "Selected paths are not rankings.",
        "",
        "## Ladder Structure",
        "",
        "Each ladder has five stages:",
        "",
        "1. Exploration direction",
        "2. Foundation skill boost",
        "3. Learning milestone / capability validation",
        "4. Advanced training",
        "5. Market job linkage",
        "",
        "## Policy Intervention Type Rules",
        "",
        "| Type | Rule | Guardrail |",
        "|---|---|---|",
        "| Public learning | Missing skills include standardizable foundations such as Programming, Computers and Electronics, Mathematics, Sales and Marketing, Persuasion, Design, or Communications and Media. | Suitable for public digital materials, not proof of transition success. |",
        "| Training guidance | Existing matched course evidence is available. | Uses MOL 15-29 Proxy finding that some non-participants do not know where courses are available. |",
        "| Subsidy candidate | Existing course evidence implies substantial burden: at least 200 hours or NT$50,000 direct course cost. | This only flags cost-burden review; it does not set subsidy amount. |",
        "| Cohort / partnership candidate | High-relevance market evidence exists and skill gap is explicit while potential course coverage is weak; or a training gap is visible but market validation must precede scale-up. | Does not claim a cohort or partnership would be effective. |",
        "| Market validation needed | High-relevance job evidence is zero or unavailable. | High=0 means public market evidence is insufficient, not market absence. |",
        "",
        "## Interpretation Rules",
        "",
        "- Do not calculate success probability.",
        "- Do not calculate a single career score.",
        "- Do not infer policy effectiveness.",
        "- Do not propose subsidy amounts.",
        "- Do not treat potential training coverage as skill acquisition.",
        "- Be conservative when market evidence is insufficient.",
    ]
    METHOD_MD.write_text("\n".join(lines), encoding="utf-8")


def write_summary(ladders: pd.DataFrame) -> None:
    representative = ladders[
        ladders["target_occupation_name"].isin(
            [
                "Clinical Data Managers",
                "Health Informatics Specialists",
                "Data Scientists",
                "Hairdressers, Hairstylists, and Cosmetologists",
                "Skincare Specialists",
            ]
        )
    ].copy()
    public_learning_skills = sorted(
        {
            skill
            for value in ladders["missing_skills"]
            for skill in split_list(value)
            if skill in PUBLIC_LEARNING_SKILLS
        }
    )
    subsidy_or_partnership = ladders[
        ladders["policy_intervention_types"].str.contains("Subsidy candidate|Cohort / partnership candidate", na=False)
    ].copy()
    evidence_insufficient = ladders[
        ladders["policy_intervention_types"].str.contains("Market validation needed", na=False)
    ].copy()
    ui_ready = ladders[
        [
            "target_domain",
            "target_occupation_name",
            "transition_span",
            "policy_intervention_types",
            "market_evidence_status",
            "potential_training_coverage_ratio",
            "total_training_hours",
            "estimated_direct_course_cost",
            "learning_burden",
        ]
    ].copy()

    lines = [
        "# Career Learning Ladder Phase 8",
        "",
        f"Generated: {OBSERVATION_DATE}",
        "",
        "This output translates Phase 7 evidence into explainable learning ladders and policy-intervention candidates. It does not create success probability, ranking, subsidy amount, or policy effectiveness claims.",
        "",
        "## 1. Representative Learning Ladders",
        "",
        markdown_table(
            representative[
                [
                    "target_occupation_name",
                    "exploration_direction",
                    "foundation_skill_boost",
                    "learning_milestone_or_validation",
                    "advanced_training",
                    "market_job_linkage",
                    "policy_intervention_types",
                    "policy_intervention_evidence_reasons",
                ]
            ]
        ),
        "",
        "## 2. Skills Suitable For Public Digital Materials",
        "",
        "These are repeated or standardizable missing-skill signals from selected ladders. This is a content-planning cue, not a claim that self-learning is sufficient.",
        "",
        markdown_table(
            pd.DataFrame(
                [
                    {"skill": skill, "skill_zh": SKILL_ZH.get(skill, skill), "reason": "standardizable foundation skill in selected Phase 7 gaps"}
                    for skill in public_learning_skills
                ]
            )
        ),
        "",
        "## 3. Paths That May Need Subsidy / Cohort / Industry Partnership Review",
        "",
        "The following are candidates for further review because existing evidence shows substantial hours/cost, visible training gap, or possible need for structured support. No subsidy amount or intervention effectiveness is inferred.",
        "",
        markdown_table(
            subsidy_or_partnership[
                [
                    "target_occupation_name",
                    "policy_intervention_types",
                    "total_training_hours",
                    "estimated_direct_course_cost",
                    "training_gap_status",
                    "market_evidence_status",
                    "policy_intervention_evidence_reasons",
                ]
            ]
        ),
        "",
        "## 4. Evidence-Insufficient Paths",
        "",
        "These paths require market validation before large-scale training-resource investment. High=0 or unavailable High evidence means public market evidence is insufficient, not that the career does not exist.",
        "",
        markdown_table(
            evidence_insufficient[
                [
                    "target_occupation_name",
                    "market_evidence_status",
                    "high_relevance_job_count",
                    "policy_intervention_types",
                    "policy_intervention_evidence_reasons",
                ]
            ]
        ),
        "",
        "## 5. Policy Lens UI-Ready Fields",
        "",
        "These fields are suitable for a later Policy Lens UI layer because they are compact and preserve guardrails.",
        "",
        markdown_table(ui_ready),
        "",
        "## Limits",
        "",
        "- No raw data was modified.",
        "- No v1-v4 or Phase 7 calculation was changed.",
        "- No success probability, ranking, final score, subsidy amount, or policy prescription is produced.",
        "- Potential training coverage is not skill acquisition.",
        "- Market evidence insufficiency is not market absence.",
    ]
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    phase7 = read_phase7()
    ladders = build_ladders(phase7)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    METHOD_MD.parent.mkdir(parents=True, exist_ok=True)
    ladders.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    write_method()
    write_summary(ladders)
    print(f"Wrote {len(ladders)} ladders to {OUTPUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote method to {METHOD_MD.relative_to(PROJECT_ROOT)}")
    print(f"Wrote summary to {OUTPUT_MD.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
