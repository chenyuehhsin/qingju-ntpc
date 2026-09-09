#!/usr/bin/env python3
"""Build Career Policy Lens Phase 7 from existing career and youth outputs.

This script does not modify raw data or the v1-v4 career evidence pipeline. It
only reads existing Phase 6, transition, market, and training outputs and writes
Phase 7 policy-lens artifacts.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

TECH_TRAINING_CSV = PROJECT_ROOT / "outputs" / "career" / "nursing_to_technology_training_v4.csv"
TECH_CANDIDATES_CSV = PROJECT_ROOT / "outputs" / "career" / "nursing_to_technology_candidates_v35.csv"
BEAUTY_CSV = PROJECT_ROOT / "outputs" / "career" / "nursing_to_beauty_candidates_phase5.csv"
YOUTH_POP_CSV = PROJECT_ROOT / "data" / "processed" / "career" / "youth" / "ntpc_population_18_35_summary_phase6.csv"
YOUTH_SCOPE_CSV = (
    PROJECT_ROOT / "data" / "processed" / "career" / "youth" / "ntpc_population_age_scope_comparison_phase6.csv"
)
YOUTH_MOL_STATS_CSV = (
    PROJECT_ROOT / "data" / "processed" / "career" / "youth" / "mol_youth_employment_survey_stats_phase6.csv"
)
YOUTH_INVENTORY_CSV = PROJECT_ROOT / "data" / "processed" / "career" / "youth" / "youth_data_inventory_phase6.csv"
YOUTH_QA_MD = PROJECT_ROOT / "docs" / "youth_statistics_phase6_qa.md"

OUTPUT_CSV = PROJECT_ROOT / "outputs" / "career" / "career_policy_lens_phase7.csv"
OUTPUT_MD = PROJECT_ROOT / "outputs" / "career" / "career_policy_lens_phase7.md"
METHOD_MD = PROJECT_ROOT / "docs" / "career_policy_lens_phase7_method.md"

OBSERVATION_DATE = "2026-09-03"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    return pd.read_csv(path)


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def to_float(value: object) -> float | None:
    text = clean(value).replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def to_int(value: object) -> int | None:
    number = to_float(value)
    if number is None:
        return None
    return int(round(number))


def split_skill_names(value: object) -> list[str]:
    text = clean(value)
    if not text:
        return []
    names = []
    for item in [part.strip() for part in text.split(";") if part.strip()]:
        match = re.match(r"(.+?)\s+\(", item)
        names.append(match.group(1).strip() if match else item)
    return names


def list_preview(value: object, limit: int = 8) -> str:
    names = split_skill_names(value)
    if not names:
        return "none"
    if len(names) <= limit:
        return "; ".join(names)
    return "; ".join(names[:limit]) + f"; ... +{len(names) - limit} more"


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


def get_mol_indicator(stats: pd.DataFrame, indicator: str) -> tuple[float | None, str, str]:
    row = stats.loc[stats["indicator"].eq(indicator)].head(1)
    if row.empty:
        return None, "", ""
    record = row.iloc[0]
    return (
        to_float(record.get("percent")),
        clean(record.get("denominator_note")),
        clean(record.get("age_harmonization_status")),
    )


def training_gap_status(
    missing_skills: int | None,
    trainable_missing: int | None,
    potential_ratio: float | None,
    course_count: int | None,
) -> str:
    if missing_skills is None:
        return "Unknown"
    if missing_skills == 0:
        return "No missing-skill gap identified"
    if trainable_missing is None or potential_ratio is None:
        return "Unknown"
    if trainable_missing == 0 or potential_ratio == 0:
        return "No matched course evidence"
    if potential_ratio < 0.5:
        return "Training gap"
    if course_count is not None and course_count > 0:
        return "Potential course coverage found"
    return "Partial potential course coverage"


def market_evidence_status(row: dict[str, object]) -> str:
    high_count = row.get("high_relevance_job_count")
    if high_count is None:
        aggregate = clean(row.get("aggregate_market_validation"))
        confidence = clean(row.get("taiwanjobs_mapping_confidence"))
        if aggregate:
            return f"Aggregate market evidence only ({aggregate}, mapping {confidence or 'unknown'}); job-level High evidence unavailable in existing output"
        return "Unknown"
    if high_count > 0:
        return "High-relevance TaiwanJobs evidence"
    return "公開市場證據不足"


def build_tech_rows(tech: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    for _, src in tech.iterrows():
        missing = to_int(src.get("number_of_missing_skills"))
        trainable = to_int(src.get("number_of_trainable_missing_skills_found"))
        potential_ratio = to_float(src.get("training_coverage_ratio"))
        record = {
            "source_occupation": clean(src.get("source_occupation_name")),
            "target_domain": "Technology / AI",
            "target_occupation_code": clean(src.get("target_occupation_code")),
            "target_occupation_name": clean(src.get("target_occupation_name")),
            "evidence_source": "nursing_to_technology_training_v4.csv",
            "skill_similarity": to_float(src.get("skill_similarity")),
            "transferable_skill_coverage": to_float(src.get("transferable_skill_coverage")),
            "target_skill_gap": to_float(src.get("target_skill_gap")),
            "transition_span": clean(src.get("transition_span")),
            "feasibility_level": clean(src.get("feasibility_level")),
            "education_barrier": clean(src.get("education_barrier")),
            "credential_barrier": clean(src.get("credential_barrier")),
            "training_experience_barrier": clean(src.get("training_experience_barrier")),
            "taxonomy_distance_level": clean(src.get("taxonomy_distance_level")),
            "aggregate_market_validation": clean(src.get("market_validation")),
            "taiwanjobs_mapping_confidence": clean(src.get("taiwanjobs_mapping_confidence")),
            "taiwanjobs_manual_review_needed": clean(src.get("taiwanjobs_manual_review_needed")),
            "high_relevance_job_count": None,
            "medium_relevance_job_count": None,
            "high_relevance_demand_persons": None,
            "salary_lower_median_monthly_high": None,
            "salary_upper_median_monthly_high": None,
            "salary_basis": "not_available_for_high_relevance_in_existing_output",
            "number_of_missing_skills": missing,
            "number_of_gap_skills": to_int(src.get("number_of_gap_skills")),
            "missing_skills_preview": list_preview(src.get("missing_skills")),
            "partially_covered_skills_preview": list_preview(src.get("partially_covered_skills")),
            "trainable_missing_skills_found": clean(src.get("trainable_missing_skills_found")) or "none",
            "number_of_trainable_missing_skills_found": trainable,
            "potential_training_coverage_ratio": potential_ratio,
            "gap_skill_potential_training_coverage_ratio": to_float(src.get("gap_skill_training_coverage_ratio")),
            "matched_course_count": to_int(src.get("matched_course_count")),
            "matched_courses": clean(src.get("matched_courses")) or "none",
            "total_training_hours": to_float(src.get("total_training_hours")),
            "estimated_direct_course_cost": to_float(src.get("estimated_direct_course_cost")),
            "learning_burden": clean(src.get("learning_burden_level")),
            "scenario_6m_potential_training_coverage_ratio": to_float(src.get("scenario_6m_training_coverage_ratio")),
            "scenario_6m_training_hours": to_float(src.get("scenario_6m_training_hours")),
            "scenario_6m_direct_course_cost": to_float(src.get("scenario_6m_direct_course_cost")),
            "scenario_6m_feasibility_estimate": clean(src.get("scenario_6m_feasibility_estimate")),
            "data_limitations": clean(src.get("limitation")),
        }
        record["market_evidence_status"] = market_evidence_status(record)
        record["training_gap_status"] = training_gap_status(
            missing,
            trainable,
            potential_ratio,
            record["matched_course_count"],
        )
        record["career_opportunity_status"] = (
            "structurally feasible"
            if clean(src.get("feasibility_level")) != "Infeasible / high-barrier"
            else "high barrier"
        )
        rows.append(record)
    return rows


def build_beauty_rows(beauty: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    for _, src in beauty.iterrows():
        missing = to_int(src.get("number_of_missing_skills"))
        trainable = to_int(src.get("number_of_trainable_missing_skills_found"))
        potential_ratio = to_float(src.get("training_coverage_ratio_missing_skills"))
        record = {
            "source_occupation": clean(src.get("source_occupation_name")),
            "target_domain": clean(src.get("target_domain")) or "Beauty / Aesthetic / Personal Care",
            "target_occupation_code": clean(src.get("target_occupation_code")),
            "target_occupation_name": clean(src.get("target_occupation_name")),
            "evidence_source": "nursing_to_beauty_candidates_phase5.csv",
            "skill_similarity": to_float(src.get("skill_similarity")),
            "transferable_skill_coverage": to_float(src.get("transferable_skill_coverage")),
            "target_skill_gap": to_float(src.get("target_skill_gap")),
            "transition_span": clean(src.get("transition_span")),
            "feasibility_level": clean(src.get("feasibility_level")),
            "education_barrier": clean(src.get("education_barrier")),
            "credential_barrier": clean(src.get("credential_barrier")),
            "training_experience_barrier": clean(src.get("training_experience_barrier")),
            "taxonomy_distance_level": clean(src.get("taxonomy_distance_level")),
            "aggregate_market_validation": clean(src.get("taiwan_market_evidence")),
            "taiwanjobs_mapping_confidence": "job-level phase5 relevance output",
            "taiwanjobs_manual_review_needed": clean(src.get("job_mapping_review_reason")),
            "high_relevance_job_count": to_int(src.get("taiwanjobs_high_relevance_job_count")),
            "medium_relevance_job_count": to_int(src.get("taiwanjobs_medium_relevance_job_count")),
            "high_relevance_demand_persons": to_int(src.get("total_demand_persons_high")),
            "salary_lower_median_monthly_high": to_float(src.get("salary_lower_median_high")),
            "salary_upper_median_monthly_high": to_float(src.get("salary_upper_median_high")),
            "salary_basis": clean(src.get("salary_basis")),
            "number_of_missing_skills": missing,
            "number_of_gap_skills": missing,
            "missing_skills_preview": list_preview(src.get("missing_skills")),
            "partially_covered_skills_preview": list_preview(src.get("partially_covered_skills")),
            "trainable_missing_skills_found": "see matched_training_courses" if trainable else "none",
            "number_of_trainable_missing_skills_found": trainable,
            "potential_training_coverage_ratio": potential_ratio,
            "gap_skill_potential_training_coverage_ratio": potential_ratio,
            "matched_course_count": to_int(src.get("training_course_count")),
            "matched_courses": clean(src.get("matched_training_courses")) or "none",
            "total_training_hours": to_float(src.get("total_training_hours")),
            "estimated_direct_course_cost": to_float(src.get("estimated_direct_course_cost")),
            "learning_burden": clean(src.get("learning_burden")),
            "scenario_6m_potential_training_coverage_ratio": None,
            "scenario_6m_training_hours": None,
            "scenario_6m_direct_course_cost": None,
            "scenario_6m_feasibility_estimate": "not_available_in_phase5_output",
            "data_limitations": clean(src.get("interpretation_note")),
        }
        record["market_evidence_status"] = market_evidence_status(record)
        record["training_gap_status"] = training_gap_status(
            missing,
            trainable,
            potential_ratio,
            record["matched_course_count"],
        )
        record["career_opportunity_status"] = (
            "structurally feasible"
            if clean(src.get("feasibility_level")) != "Infeasible / high-barrier"
            else "high barrier"
        )
        rows.append(record)
    return rows


def build_policy_lens() -> tuple[pd.DataFrame, dict[str, object], pd.DataFrame]:
    tech = read_csv(TECH_TRAINING_CSV)
    beauty = read_csv(BEAUTY_CSV)
    youth_pop = read_csv(YOUTH_POP_CSV)
    youth_scope = read_csv(YOUTH_SCOPE_CSV)
    mol_stats = read_csv(YOUTH_MOL_STATS_CSV)

    rows = build_tech_rows(tech) + build_beauty_rows(beauty)
    lens = pd.DataFrame(rows)

    total_row = youth_pop.loc[youth_pop["sex"].eq("性別總計")].iloc[0]
    male_row = youth_pop.loc[youth_pop["sex"].eq("男")].iloc[0]
    female_row = youth_pop.loc[youth_pop["sex"].eq("女")].iloc[0]

    transition_pct, transition_denominator, transition_scope = get_mol_indicator(mol_stats, "有打算轉換工作")
    training_pct, training_denominator, training_scope = get_mol_indicator(mol_stats, "近一年有參加教育訓練")
    no_course_pct, no_course_denominator, no_course_scope = get_mol_indicator(
        mol_stats, "不知道哪裡有提供訓練課程的機構"
    )
    fee_pct, fee_denominator, fee_scope = get_mol_indicator(mol_stats, "參加訓練的費用太高，負擔不起")

    youth_context = {
        "ntpc_population_18_35": int(total_row["population_18_35"]),
        "ntpc_population_period": clean(total_row["period"]),
        "ntpc_population_age_scope": clean(total_row["age_scope"]),
        "ntpc_population_age_harmonization": "Exact",
        "ntpc_population_male": int(male_row["population_18_35"]),
        "ntpc_population_female": int(female_row["population_18_35"]),
        "mol_transition_intention_percent": transition_pct,
        "mol_transition_denominator": transition_denominator,
        "mol_transition_age_harmonization": transition_scope,
        "mol_training_participation_percent": training_pct,
        "mol_training_denominator": training_denominator,
        "mol_training_age_harmonization": training_scope,
        "mol_no_course_info_percent": no_course_pct,
        "mol_no_course_info_denominator": no_course_denominator,
        "mol_no_course_info_age_harmonization": no_course_scope,
        "mol_fee_barrier_percent": fee_pct,
        "mol_fee_barrier_denominator": fee_denominator,
        "mol_fee_barrier_age_harmonization": fee_scope,
    }
    for key, value in youth_context.items():
        lens[key] = value

    return lens, youth_context, youth_scope


def skill_gap_counts(lens: pd.DataFrame) -> pd.DataFrame:
    counter: Counter[str] = Counter()
    for value in lens["missing_skills_preview"]:
        if clean(value) == "none":
            continue
        for name in [part.strip() for part in clean(value).split(";") if part.strip()]:
            if name.startswith("..."):
                continue
            counter[name] += 1
    rows = [{"skill": skill, "path_count": count} for skill, count in counter.most_common()]
    return pd.DataFrame(rows)


def write_method() -> None:
    lines = [
        "# Career Policy Lens Phase 7 Method",
        "",
        f"Generated: {OBSERVATION_DATE}",
        "",
        "Phase 7 creates a first policy-analysis lens by integrating existing outputs only. It does not modify raw data, v1-v4 methodology, Career Discovery UI, or recommendation results.",
        "",
        "## Inputs",
        "",
        "| Evidence area | Files | Use |",
        "|---|---|---|",
        "| Youth status | `data/processed/career/youth/*phase6*.csv`, `docs/youth_statistics_phase6_qa.md` | 18-35 exact population and proxy youth labor/training signals. |",
        "| Career opportunity | `outputs/career/nursing_to_technology_training_v4.csv`, `outputs/career/nursing_to_beauty_candidates_phase5.csv` | Feasibility, transition span, skill reuse, education/credential/training barriers. |",
        "| Market demand | Existing TaiwanJobs fields in career outputs | High-relevance job evidence where available; aggregate market validation otherwise stays labeled aggregate-only. |",
        "| Skill gap | Existing missing/partial skill columns | Common missing skills and repeated capability gaps. |",
        "| Training gap | Existing course mapping and training coverage fields | Potential course coverage, hours, direct course cost, and uncovered missing skills. |",
        "",
        "## Evidence Guardrails",
        "",
        "- Exact / Partial / Proxy labels are preserved.",
        "- Unresolved New Taipei employment/unemployment metadata is not used for strong policy claims.",
        "- High-relevance TaiwanJobs evidence is counted only when an existing output provides job-level High relevance counts.",
        "- High=0 is interpreted as `公開市場證據不足`, not market absence.",
        "- Training coverage is named `potential_training_coverage_ratio`; it does not mean a skill has been fully acquired.",
        "- No youth transition success probability, final recommendation score, or subsidy amount is calculated.",
        "- No concrete policy prescription is produced in Phase 7.",
        "",
        "## Output Unit",
        "",
        "One row represents one source-target career path from Registered Nurses to an explored target occupation. The table keeps independent dimensions instead of collapsing them into a single score:",
        "",
        "- Youth context",
        "- Career opportunity / feasibility",
        "- Market demand evidence",
        "- Skill gap",
        "- Training gap",
        "- Data limitations",
    ]
    METHOD_MD.write_text("\n".join(lines), encoding="utf-8")


def write_summary(lens: pd.DataFrame, youth_context: dict[str, object], youth_scope: pd.DataFrame) -> None:
    feasible = lens[lens["career_opportunity_status"].eq("structurally feasible")].copy()
    high_market = lens[pd.to_numeric(lens["high_relevance_job_count"], errors="coerce").fillna(0).gt(0)].copy()
    insufficient_market = lens[lens["market_evidence_status"].eq("公開市場證據不足")].copy()
    aggregate_only = lens[lens["market_evidence_status"].str.contains("Aggregate market evidence only", na=False)].copy()
    training_gap = lens[lens["training_gap_status"].eq("Training gap")].copy()
    high_burden = lens[lens["learning_burden"].astype(str).str.lower().eq("high")].copy()
    common_skills = skill_gap_counts(lens).head(8)

    display_cols = [
        "target_domain",
        "target_occupation_name",
        "transition_span",
        "feasibility_level",
        "market_evidence_status",
        "high_relevance_job_count",
        "potential_training_coverage_ratio",
        "matched_course_count",
        "total_training_hours",
        "estimated_direct_course_cost",
        "training_gap_status",
        "learning_burden",
    ]

    observations = [
        "1. The youth denominator is solid for population but mixed for labor evidence: New Taipei 18-35 population is Exact, while MOL transition/training indicators are national 15-29 Proxy evidence.",
        "2. Several explored paths are structurally feasible from nursing, but market validation strength differs by output: beauty service roles have job-level High relevance evidence; technology paths currently have aggregate market evidence only in the existing v4 output.",
        "3. Common cross-domain skill gaps cluster around technology/data skills and business-facing skills, especially Programming, Computers and Electronics, Mathematics, and Sales and Marketing.",
        "4. Potential course coverage exists for many missing skills, but it varies by path and should be read with hours/cost. It is not proof that skills are fully acquired.",
        "5. Paths with High=0 should be treated as public market evidence gaps, not evidence that the career does not exist.",
    ]

    phase8_candidates = lens[
        lens["career_opportunity_status"].eq("structurally feasible")
        & (
            pd.to_numeric(lens["number_of_missing_skills"], errors="coerce").fillna(0).gt(0)
            | pd.to_numeric(lens["matched_course_count"], errors="coerce").fillna(0).gt(0)
        )
    ].copy()
    phase8_candidates = phase8_candidates[
        [
            "target_domain",
            "target_occupation_name",
            "transition_span",
            "number_of_missing_skills",
            "number_of_trainable_missing_skills_found",
            "potential_training_coverage_ratio",
            "total_training_hours",
            "estimated_direct_course_cost",
            "learning_burden",
        ]
    ]

    lines = [
        "# Career Policy Lens Phase 7",
        "",
        f"Generated: {OBSERVATION_DATE}",
        "",
        "This is a policy-analysis lens over existing evidence outputs. It does not create a career success probability, final ranking, or policy prescription.",
        "",
        "## Youth Status",
        "",
        f"- New Taipei 18-35 population: {int(youth_context['ntpc_population_18_35']):,}, source scope `{youth_context['ntpc_population_age_scope']}`, harmonization `Exact`, period `{youth_context['ntpc_population_period']}`.",
        f"- Male: {int(youth_context['ntpc_population_male']):,}; female: {int(youth_context['ntpc_population_female']):,}.",
        f"- MOL 113 survey transition intention: {youth_context['mol_transition_intention_percent']}%, scope `15-29 youth workers`, harmonization `{youth_context['mol_transition_age_harmonization']}`, denominator `{youth_context['mol_transition_denominator']}`.",
        f"- MOL 113 survey training participation: {youth_context['mol_training_participation_percent']}%, scope `15-29 youth workers`, harmonization `{youth_context['mol_training_age_harmonization']}`, denominator `{youth_context['mol_training_denominator']}`.",
        f"- Training access barriers among non-participants: unknown course providers {youth_context['mol_no_course_info_percent']}%; fee too high {youth_context['mol_fee_barrier_percent']}%. These are Proxy national 15-29 indicators.",
        "- NTPC employment/unemployment CSV metadata remains unresolved and is not used for strong policy conclusions.",
        "",
        "Age-scope comparison:",
        "",
        markdown_table(youth_scope),
        "",
        "## Career Opportunity",
        "",
        f"- Structurally feasible paths in the integrated table: {len(feasible)} of {len(lens)}.",
        "- Feasibility remains separate from market opportunity and training burden.",
        "",
        markdown_table(lens[display_cols]),
        "",
        "## Market Demand",
        "",
        f"- Paths with job-level High-relevance TaiwanJobs evidence in existing outputs: {len(high_market)}.",
        f"- Paths with High=0 and therefore `公開市場證據不足`: {len(insufficient_market)}.",
        f"- Paths with aggregate market validation only, no existing High-relevance count: {len(aggregate_only)}.",
        "",
        "High-relevance market evidence paths:",
        "",
        markdown_table(
            high_market[
                [
                    "target_domain",
                    "target_occupation_name",
                    "high_relevance_job_count",
                    "high_relevance_demand_persons",
                    "salary_lower_median_monthly_high",
                    "salary_upper_median_monthly_high",
                    "salary_basis",
                ]
            ]
        ),
        "",
        "## Skill Gap",
        "",
        "Common missing-skill signals across integrated paths:",
        "",
        markdown_table(common_skills),
        "",
        "## Training Gap",
        "",
        f"- Paths marked Training gap: {len(training_gap)}.",
        f"- Paths with high learning burden: {len(high_burden)}.",
        "- Training coverage is reported only as potential course coverage.",
        "",
        markdown_table(
            lens[
                [
                    "target_domain",
                    "target_occupation_name",
                    "number_of_missing_skills",
                    "number_of_trainable_missing_skills_found",
                    "potential_training_coverage_ratio",
                    "matched_course_count",
                    "total_training_hours",
                    "estimated_direct_course_cost",
                    "training_gap_status",
                    "learning_burden",
                ]
            ]
        ),
        "",
        "## Data-Supported Policy Observations",
        "",
        *observations,
        "",
        "## Phase 8: Youth Transition Learning Ladder Candidates",
        "",
        "The following paths have enough skill/training evidence structure to be decomposed into learning steps in Phase 8. This is not a recommendation ranking.",
        "",
        markdown_table(phase8_candidates),
        "",
        "## Limits",
        "",
        "- No success probability is calculated.",
        "- No single career score is calculated.",
        "- High=0 means current public market evidence is insufficient, not that the career does not exist.",
        "- Potential training coverage does not mean skills are fully learned.",
        "- NTPC employment/unemployment metadata remains unresolved from existing files.",
    ]
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    lens, youth_context, youth_scope = build_policy_lens()
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    METHOD_MD.parent.mkdir(parents=True, exist_ok=True)
    lens.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    write_method()
    write_summary(lens, youth_context, youth_scope)
    print(f"Wrote {len(lens)} policy-lens rows to {OUTPUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote method to {METHOD_MD.relative_to(PROJECT_ROOT)}")
    print(f"Wrote summary to {OUTPUT_MD.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
