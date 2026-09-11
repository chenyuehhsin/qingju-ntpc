"""Runtime career matching built from the project's normalized O*NET skill table."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OCCUPATION_SKILLS_CSV = PROJECT_ROOT / "data/processed/career/occupation_skills.csv"
OCCUPATION_MARKET_CSV = PROJECT_ROOT / "data/processed/career/onet_taiwanjobs_occupation_mapping.csv"
REQUIRED_SKILL_THRESHOLD = 3.0

SOURCE_OCCUPATIONS = {
    "Registered Nurses": "Registered Nurses",
    "Administrative / Office Work": "Secretaries and Administrative Assistants, Except Legal, Medical, and Executive",
    "Retail / Store Service": "Retail Salespersons",
    "Customer Service": "Customer Service Representatives",
    "Marketing / Planning": "Market Research Analysts and Marketing Specialists",
}

DOMAIN_TARGETS = {
    "科技 / AI": [
        "Health Informatics Specialists",
        "Clinical Data Managers",
        "Data Scientists",
        "Computer Systems Analysts",
        "Web Developers",
        "Software Developers",
        "Database Administrators",
        "Information Security Analysts",
        "Operations Research Analysts",
    ],
    "美容 / 醫美 / 個人照護": [
        "First-Line Supervisors of Personal Service Workers",
        "Skincare Specialists",
        "Massage Therapists",
        "Hairdressers, Hairstylists, and Cosmetologists",
        "Manicurists and Pedicurists",
        "Makeup Artists, Theatrical and Performance",
        "Spa Managers",
    ],
    "數位行銷 / 電商": [
        "Market Research Analysts and Marketing Specialists",
        "Search Marketing Strategists",
        "Public Relations Specialists",
        "Advertising Sales Agents",
        "Web and Digital Interface Designers",
        "Graphic Designers",
        "Sales Managers",
    ],
    "行政 / 專案管理": [
        "Project Management Specialists",
        "Executive Secretaries and Executive Administrative Assistants",
        "Management Analysts",
        "Human Resources Specialists",
        "Training and Development Specialists",
        "Operations Research Analysts",
    ],
    "長照 / 健康促進": [
        "Nursing Assistants",
        "Community Health Workers",
        "Health Education Specialists",
        "Medical Assistants",
        "Medical Records Specialists",
        "Social and Human Service Assistants",
    ],
}


@lru_cache(maxsize=1)
def _load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    skills = pd.read_csv(OCCUPATION_SKILLS_CSV)
    market = pd.read_csv(OCCUPATION_MARKET_CSV)
    skills["importance_or_score"] = pd.to_numeric(skills["importance_or_score"], errors="coerce").fillna(0.0)
    skills["feature_id"] = skills["skill_type"].astype(str) + ":" + skills["skill_id"].astype(str)
    return skills, market


def build_dynamic_career_recommendations(
    source_key: str,
    domain_label: str,
    *,
    limit: int = 3,
) -> pd.DataFrame:
    """Rank domain candidates from the selected source occupation at request time."""
    skills, market = _load_inputs()
    source_name = SOURCE_OCCUPATIONS.get(source_key)
    targets = DOMAIN_TARGETS.get(domain_label, [])
    if not source_name or not targets:
        return pd.DataFrame()

    available_names = set(skills["occupation_name"].astype(str))
    if source_name not in available_names:
        return pd.DataFrame()
    targets = [name for name in targets if name in available_names and name != source_name]
    if not targets:
        return pd.DataFrame()

    feature_meta = (
        skills.drop_duplicates("feature_id").set_index("feature_id")[["skill_name", "skill_type"]].to_dict("index")
    )
    wide = skills.pivot_table(
        index="occupation_name",
        columns="feature_id",
        values="importance_or_score",
        aggfunc="max",
        fill_value=0.0,
    )
    source_vector = wide.loc[source_name]
    code_lookup = skills.drop_duplicates("occupation_name").set_index("occupation_name")["occupation_code"].astype(str)
    market_lookup = market.drop_duplicates("onet_occupation").set_index("onet_occupation")

    records = []
    for target_name in targets:
        target_vector = wide.loc[target_name]
        coverage, shared, partial, missing = _directional_match(source_vector, target_vector, feature_meta)
        cosine = _cosine_similarity(source_vector, target_vector)
        match_score = 0.72 * coverage + 0.28 * cosine
        span = _transition_span(coverage, len(missing))
        market_row = market_lookup.loc[target_name] if target_name in market_lookup.index else None
        market_fields = _market_fields(market_row)
        records.append(
            {
                "target_occupation_code": code_lookup.get(target_name, ""),
                "target_occupation_name": target_name,
                "transition_span_v4": span,
                "transition_span": span,
                "learning_burden_level": _learning_burden(span, len(missing)),
                "shared_top_skills": "; ".join(shared[:6]),
                "partially_covered_skills": "; ".join(partial[:5]),
                "missing_skills_v4": "; ".join(missing[:8]),
                "missing_skills": "; ".join(missing[:8]),
                "number_of_missing_skills": len(missing),
                "number_of_gap_skills": len(missing),
                "number_of_trainable_missing_skills_found": 0,
                "number_of_trainable_skills_found": 0,
                "training_coverage_ratio": np.nan,
                "gap_skill_training_coverage_ratio": np.nan,
                "scenario_6m_feasibility_estimate": _six_month_stage(span),
                "possible_income_interruption": "unknown",
                "transferable_skill_coverage": round(coverage, 4),
                "skill_similarity": round(cosine, 4),
                "dynamic_match_score": round(match_score, 4),
                "_evidence_source": "dynamic_skill_match",
                **market_fields,
            }
        )
    return (
        pd.DataFrame(records)
        .sort_values(["dynamic_match_score", "transferable_skill_coverage"], ascending=False, kind="stable")
        .head(limit)
        .reset_index(drop=True)
    )


def _directional_match(
    source: pd.Series,
    target: pd.Series,
    feature_meta: dict[str, dict[str, str]],
) -> tuple[float, list[str], list[str], list[str]]:
    type_coverages: list[float] = []
    shared_rows: list[tuple[float, str]] = []
    partial_rows: list[tuple[float, str]] = []
    missing_rows: list[tuple[float, str]] = []
    for skill_type in ("essential_skill", "transferable_skill", "knowledge"):
        feature_ids = [key for key, meta in feature_meta.items() if meta["skill_type"] == skill_type]
        required = target.reindex(feature_ids).fillna(0.0)
        required = required.loc[required.ge(REQUIRED_SKILL_THRESHOLD)]
        if required.empty:
            continue
        source_values = source.reindex(required.index).fillna(0.0)
        covered = np.minimum(source_values.to_numpy(float), required.to_numpy(float))
        type_coverages.append(float(covered.sum() / required.sum()))
        for feature_id, target_score in required.items():
            source_score = float(source_values.loc[feature_id])
            gap = max(float(target_score) - source_score, 0.0)
            name = str(feature_meta[feature_id]["skill_name"])
            detail = (
                f"{name} ({skill_type}: target {float(target_score):.2f}, "
                f"source {source_score:.2f}, gap {gap:.2f})"
            )
            if gap <= 0.25:
                shared_rows.append((min(source_score, float(target_score)), detail))
            elif gap < 0.75:
                partial_rows.append((gap, detail))
            else:
                missing_rows.append((gap, detail))
    coverage = float(np.mean(type_coverages)) if type_coverages else 0.0
    shared = [item for _, item in sorted(shared_rows, reverse=True)]
    partial = [item for _, item in sorted(partial_rows, reverse=True)]
    missing = [item for _, item in sorted(missing_rows, reverse=True)]
    return coverage, shared, partial, missing


def _cosine_similarity(source: pd.Series, target: pd.Series) -> float:
    source_values = source.to_numpy(dtype=float)
    target_values = target.to_numpy(dtype=float)
    denominator = float(np.linalg.norm(source_values) * np.linalg.norm(target_values))
    return float(np.dot(source_values, target_values) / denominator) if denominator else 0.0


def _transition_span(coverage: float, missing_count: int) -> str:
    if coverage >= 0.9 and missing_count <= 3:
        return "High skill reuse"
    if coverage >= 0.78 and missing_count <= 10:
        return "Partial skill reuse"
    return "Major reskilling"


def _learning_burden(span: str, missing_count: int) -> str:
    if span == "High skill reuse" and missing_count <= 4:
        return "Low"
    if span != "Major reskilling" and missing_count <= 9:
        return "Medium"
    return "High"


def _six_month_stage(span: str) -> str:
    return {
        "High skill reuse": "6 個月內可先完成職稱理解、履歷轉譯與入門技能補強",
        "Partial skill reuse": "6 個月內可完成基礎補強並累積一項作品或實作證據",
        "Major reskilling": "6 個月較適合作為基礎學習期，尚不足以推定完成轉職",
    }[span]


def _market_fields(row: pd.Series | None) -> dict[str, object]:
    if row is None:
        return {
            "market_validation_v4": "Weak",
            "mapping_confidence": "資料不足",
            "matched_job_count": 0,
            "total_demand_persons": 0,
            "salary_lower_median": np.nan,
            "salary_upper_median": np.nan,
            "salary_basis": "資料不足",
            "matched_titles": "",
            "manual_review_needed": "yes",
        }
    job_count = int(float(row.get("matched_job_count", 0) or 0))
    confidence = str(row.get("mapping_confidence", ""))
    signal = "Strong" if job_count > 0 and confidence == "High" else "Moderate" if job_count > 0 else "Weak"
    return {
        "market_validation_v4": signal,
        "mapping_confidence": confidence or "資料不足",
        "matched_job_count": job_count,
        "total_demand_persons": int(float(row.get("total_demand_persons", 0) or 0)),
        "salary_lower_median": row.get("salary_lower_median", np.nan),
        "salary_upper_median": row.get("salary_upper_median", np.nan),
        "salary_basis": row.get("salary_basis", "資料不足"),
        "matched_titles": row.get("matched_titles", ""),
        "manual_review_needed": row.get("manual_review_needed", "yes"),
    }
