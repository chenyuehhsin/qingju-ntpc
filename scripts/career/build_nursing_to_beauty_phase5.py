#!/usr/bin/env python3
"""Phase 5 stress test: Registered Nurses -> Beauty / Aesthetic / Personal Care.

This script reuses the existing career evidence helpers but writes only Phase 5
outputs. It does not modify raw data, processed data, or the nursing->technology
v3.5/v4 outputs.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_career_transition_mvp import (  # noqa: E402
    NURSING_CODE,
    NURSING_TECH_CANDIDATES_V35_CSV,
    NURSING_TECH_TRAINING_V4_CSV,
    OBSERVATION_DATE,
    OCCUPATION_SKILLS_CSV,
    ONET_OCCUPATION_DATA,
    ONET_RELATED_OCCUPATIONS,
    OUTPUTS_CAREER,
    RAW_ONET,
    REQUIRED_SKILL_THRESHOLD,
    build_occupation_feasibility_profile,
    build_raw_skill_wide,
    build_weighted_similarity_matrix,
    credential_barrier,
    directional_skill_metrics,
    education_barrier,
    is_physician_like,
    load_taiwanjobs,
    load_training_courses,
    skill_gap_status,
    summarize_skill_names,
    taxonomy_distance,
    text_or_unknown,
    training_burden_level,
    training_experience_barrier,
)


TARGET_DOMAIN = "Beauty / Aesthetic / Personal Care"
PHASE5_CSV = OUTPUTS_CAREER / "nursing_to_beauty_candidates_phase5.csv"
PHASE5_MD = OUTPUTS_CAREER / "nursing_to_beauty_exploration_phase5.md"

ONET_TASK_STATEMENTS = RAW_ONET / "task_statements.csv"
ONET_JOB_TITLES = RAW_ONET / "job_titles.csv"
ONET_REPORTED_TITLES = RAW_ONET / "sample_of_reported_titles.csv"

BEAUTY_STRONG_TERMS = [
    "aesthetic",
    "aesthetics",
    "esthetician",
    "esthetic",
    "beauty",
    "cosmetology",
    "cosmetologist",
    "skincare",
    "skin care",
    "hairdresser",
    "hairstylist",
    "barber",
    "manicurist",
    "pedicurist",
    "nail technician",
    "makeup artist",
    "massage therapist",
    "spa",
    "beauty consultant",
    "beauty advisor",
    "personal care",
]
BEAUTY_HEALTH_TERMS = [
    "dermatology",
    "dermatologist",
    "skin",
    "hair",
    "nails",
    "laser hair removal",
    "electrologist",
    "therapeutic massage",
    "patient",
    "care",
]
BEAUTY_BUSINESS_TERMS = [
    "beauty consultant",
    "independent beauty consultant",
    "beauty shop manager",
    "spa manager",
    "spa coordinator",
]
BEAUTY_SERVICE_TERMS = [
    "salon",
    "shampoo",
    "facial",
    "scalp",
    "massage",
    "makeup",
    "nail",
    "appearance",
    "grooming",
    "cosmetic",
]

EXCLUDE_GENERATION_TERMS = [
    "aerospace",
    "atmospheric",
    "space",
    "dispatch",
    "animal",
    "pet",
    "veterinary",
    "costume",
    "newspaper",
    "spanish",
    "geospatial",
]

EXPLICIT_BEAUTY_TITLE_TERMS = [
    "spa managers",
    "dermatologists",
    "massage therapists",
    "barbers",
    "hairdressers",
    "hairstylists",
    "cosmetologists",
    "makeup artists",
    "manicurists",
    "pedicurists",
    "shampooers",
    "skincare specialists",
]

EXPLICIT_BEAUTY_ALIAS_TERMS = [
    "barbering instructor",
    "beauty culture teacher",
    "beauty consultant",
    "beauty shop manager",
    "beauty specialist",
    "clinical esthetician",
    "cosmetic chemist",
    "cosmetology inspector",
    "cosmetology instructor",
    "cosmetology teacher",
    "day spa manager",
    "esthetician",
    "hair salon manager",
    "independent beauty consultant",
    "makeup artistry instructor",
    "makeup artist",
    "massage therapy instructor",
    "medical esthetician",
    "medical massage therapist",
    "medical spa manager",
    "nail technician",
    "skin care instructor",
    "spa attendant",
    "spa coordinator",
    "spa director",
    "spa supervisor",
    "spa technician",
]


def normalize_text(value: object) -> str:
    return "" if pd.isna(value) else str(value)


def lower_text(value: object) -> str:
    return normalize_text(value).lower()


def contains_ascii_term(text: str, term: str) -> bool:
    escaped = re.escape(term.lower())
    if re.search(r"[a-z0-9]", term.lower()):
        return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text.lower()) is not None
    return term in text


def term_hits(text: str, terms: list[str]) -> list[str]:
    return sorted({term for term in terms if contains_ascii_term(text, term)}, key=lambda x: (-len(x), x))


def aggregate_onet_beauty_corpus(occupation_skills: pd.DataFrame) -> pd.DataFrame:
    occupations = pd.read_csv(ONET_OCCUPATION_DATA).rename(
        columns={
            "O*NET-SOC Code": "occupation_code",
            "Title": "occupation_name",
            "Description": "occupation_description",
        }
    )

    tasks = pd.read_csv(ONET_TASK_STATEMENTS).rename(columns={"O*NET-SOC Code": "occupation_code"})
    task_text = (
        tasks.groupby("occupation_code")["Task"]
        .apply(lambda values: " ".join(values.dropna().astype(str).head(30)))
        .reset_index(name="task_text")
    )

    required_skills = occupation_skills.loc[occupation_skills["importance_or_score"].ge(REQUIRED_SKILL_THRESHOLD)]
    skill_text = (
        required_skills.groupby("occupation_code")["skill_name"]
        .apply(lambda values: " ".join(sorted(set(values.dropna().astype(str)))))
        .reset_index(name="skill_text")
    )

    job_titles = pd.read_csv(ONET_JOB_TITLES).rename(columns={"O*NET-SOC Code": "occupation_code"})
    job_title_text = (
        job_titles.groupby("occupation_code")["Job Title"]
        .apply(lambda values: " ".join(values.dropna().astype(str).head(80)))
        .reset_index(name="job_title_text")
    )

    reported = pd.read_csv(ONET_REPORTED_TITLES).rename(columns={"O*NET-SOC Code": "occupation_code"})
    reported_text = (
        reported.groupby("occupation_code")["Reported Job Title"]
        .apply(lambda values: " ".join(values.dropna().astype(str).head(80)))
        .reset_index(name="reported_title_text")
    )

    corpus = occupations.merge(task_text, on="occupation_code", how="left")
    corpus = corpus.merge(skill_text, on="occupation_code", how="left")
    corpus = corpus.merge(job_title_text, on="occupation_code", how="left")
    corpus = corpus.merge(reported_text, on="occupation_code", how="left")
    for column in ["task_text", "skill_text", "job_title_text", "reported_title_text"]:
        corpus[column] = corpus[column].fillna("")
    return corpus


def beauty_retrieval_score(row: pd.Series) -> dict[str, object]:
    title = lower_text(row["occupation_name"])
    description = lower_text(row["occupation_description"])
    task_text = lower_text(row["task_text"])
    skill_text = lower_text(row["skill_text"])
    job_titles = lower_text(row["job_title_text"])
    reported_titles = lower_text(row["reported_title_text"])
    all_text = " ".join([title, description, task_text, skill_text, job_titles, reported_titles])

    if term_hits(title, EXCLUDE_GENERATION_TERMS):
        return {
            "target_domain_retrieval_score": 0.0,
            "target_domain_strong_hits": "",
            "target_domain_health_hits": "",
            "target_domain_service_hits": "",
            "target_domain_business_hits": "",
            "target_domain_title_alias_hits": "",
            "target_domain_evidence_fields": "",
        }

    strong_title = term_hits(title, BEAUTY_STRONG_TERMS + BEAUTY_HEALTH_TERMS)
    strong_description = term_hits(description, BEAUTY_STRONG_TERMS + BEAUTY_HEALTH_TERMS)
    strong_tasks = term_hits(task_text, BEAUTY_STRONG_TERMS + BEAUTY_HEALTH_TERMS + BEAUTY_SERVICE_TERMS)
    strong_skills = term_hits(skill_text, BEAUTY_STRONG_TERMS + BEAUTY_HEALTH_TERMS + BEAUTY_SERVICE_TERMS)
    alias_hits = term_hits(job_titles + " " + reported_titles, BEAUTY_STRONG_TERMS + BEAUTY_BUSINESS_TERMS + EXPLICIT_BEAUTY_ALIAS_TERMS)
    health_hits = term_hits(all_text, BEAUTY_HEALTH_TERMS)
    service_hits = term_hits(all_text, BEAUTY_SERVICE_TERMS)
    business_hits = term_hits(all_text, BEAUTY_BUSINESS_TERMS)

    score = (
        8.0 * len(strong_title)
        + 4.0 * len(strong_description)
        + 1.5 * len(strong_tasks)
        + 1.0 * len(strong_skills)
        + 5.0 * len(alias_hits)
        + 1.0 * len(health_hits)
        + 0.8 * len(service_hits)
        + 0.8 * len(business_hits)
    )
    major_group = str(row["occupation_code"])[:2]
    if major_group == "39":
        score += 8.0
    if str(row["occupation_code"]).startswith("31-9011"):
        score += 6.0
    if str(row["occupation_code"]).startswith("29-1213"):
        score += 5.0

    evidence_fields = []
    if strong_title:
        evidence_fields.append("title")
    if strong_description:
        evidence_fields.append("description")
    if strong_tasks:
        evidence_fields.append("tasks")
    if strong_skills:
        evidence_fields.append("skills")
    if alias_hits:
        evidence_fields.append("alternate_titles")

    return {
        "target_domain_retrieval_score": round(float(score), 3),
        "target_domain_strong_hits": "; ".join(sorted(set(strong_title + strong_description + alias_hits))),
        "target_domain_health_hits": "; ".join(health_hits),
        "target_domain_service_hits": "; ".join(service_hits),
        "target_domain_business_hits": "; ".join(business_hits),
        "target_domain_title_alias_hits": "; ".join(alias_hits),
        "target_domain_evidence_fields": "; ".join(evidence_fields),
    }


def beauty_primary_signal(row: pd.Series, score_info: dict[str, object]) -> str:
    code = str(row["occupation_code"])
    title = lower_text(row["occupation_name"])
    title_description = lower_text(row["occupation_name"]) + " " + lower_text(row["occupation_description"])
    alias_hits = str(score_info["target_domain_title_alias_hits"])
    explicit_title_hit = any(term in title for term in EXPLICIT_BEAUTY_TITLE_TERMS)
    explicit_alias_hit = any(term in alias_hits.lower() for term in EXPLICIT_BEAUTY_ALIAS_TERMS)

    if code.startswith("29-1213"):
        return "medical_aesthetic_or_skin_health"
    if code.startswith("31-9011") or "massage therapist" in title:
        return "bodywork_or_wellness_service"
    if code.startswith("39-") and explicit_title_hit:
        return "beauty_personal_care_service"
    if "cosmetic chemist" in alias_hits.lower():
        return "beauty_product_science"
    if "cosmetology inspector" in alias_hits.lower():
        return "beauty_credential_compliance"
    if any(term in alias_hits.lower() for term in ["cosmetology instructor", "cosmetology teacher", "skin care instructor", "barbering instructor", "beauty culture teacher", "makeup artistry instructor"]):
        return "beauty_training_education"
    if "spa manager" in title or "beauty shop manager" in alias_hits.lower():
        return "beauty_service_management"
    if any(term in alias_hits.lower() for term in ["beauty consultant", "beauty advisor", "independent beauty consultant"]):
        return "beauty_product_service_sales"
    if explicit_title_hit and any(term in title_description for term in ["skin", "hair", "nail", "beauty", "cosmetic"]):
        return "beauty_personal_care_service"
    if explicit_alias_hit:
        return "beauty_related_alias"
    return "weak_or_indirect"


def generate_beauty_candidates(occupation_skills: pd.DataFrame, max_candidates: int = 50) -> pd.DataFrame:
    corpus = aggregate_onet_beauty_corpus(occupation_skills)
    records: list[dict[str, object]] = []
    for _, row in corpus.iterrows():
        if row["occupation_code"] == NURSING_CODE:
            continue
        score_info = beauty_retrieval_score(row)
        primary_signal = beauty_primary_signal(row, score_info)
        include = (
            primary_signal
            in {
                "medical_aesthetic_or_skin_health",
                "bodywork_or_wellness_service",
                "beauty_personal_care_service",
                "beauty_service_management",
                "beauty_product_service_sales",
                "beauty_product_science",
                "beauty_credential_compliance",
            }
            and score_info["target_domain_retrieval_score"] >= 12.0
        )
        if include:
            records.append(
                {
                    "source_occupation_code": NURSING_CODE,
                    "source_occupation_name": "Registered Nurses",
                    "target_domain": TARGET_DOMAIN,
                    "target_occupation_code": row["occupation_code"],
                    "target_occupation_name": row["occupation_name"],
                    "target_occupation_description": row["occupation_description"],
                    "candidate_generation_method": "deterministic_onet_beauty_domain_keyword_retrieval_phase5",
                    "target_domain_primary_signal": primary_signal,
                    **score_info,
                }
            )
    candidates = pd.DataFrame.from_records(records)
    if candidates.empty:
        return candidates
    candidates = candidates.sort_values("target_domain_retrieval_score", ascending=False).head(max_candidates).copy()
    candidates.insert(0, "candidate_generation_rank", range(1, len(candidates) + 1))
    return candidates


def beauty_transition_span(
    target_title: str,
    primary_signal: str,
    coverage: float,
    gap: float,
    education_level: str,
    credential_level: str,
) -> str:
    title = target_title.lower()
    if is_physician_like(target_title):
        return "High skill reuse"
    if any(term in title for term in ["barber", "hairdresser", "hairstylist", "cosmetologist", "manicurist", "pedicurist", "makeup artist", "shampooer"]):
        return "Major reskilling"
    if any(term in title for term in ["skincare", "massage", "spa"]):
        return "Partial skill reuse" if coverage >= 0.65 else "Major reskilling"
    if primary_signal in {"beauty_product_service_sales", "beauty_product_science", "beauty_credential_compliance"}:
        return "Partial skill reuse" if coverage >= 0.65 else "Major reskilling"
    if coverage >= 0.85 and gap <= 0.45 and education_level in {"low", "medium", "unknown"}:
        return "High skill reuse"
    if coverage >= 0.65 and gap <= 0.90:
        return "Partial skill reuse"
    return "Major reskilling"


def classify_beauty_feasibility(target_title: str, target_profile: pd.Series, row: dict[str, object]) -> tuple[str, str, str]:
    target_doctoral = float(target_profile.get("education_doctoral_professional_share", 0.0) or 0.0)
    education = str(row["education_barrier"])
    training = str(row["training_experience_barrier"])
    credential = str(row["credential_barrier"])
    span = str(row["transition_span"])
    job_zone_difference = float(row["job_zone_difference"])

    if is_physician_like(target_title) or target_doctoral >= 35.0 or (education == "high" and credential == "high"):
        return (
            "exclude",
            "Infeasible / high-barrier",
            "High education or professional credential barrier; useful as a medical-aesthetic comparator, not a short-term transition path.",
        )
    if span == "High skill reuse" and education in {"low", "medium", "unknown"} and training in {"low", "medium"}:
        return (
            "candidate",
            "Adjacent candidate",
            "Uses nursing care/domain knowledge with no major upward education signal.",
        )
    if span == "Major reskilling" and education in {"low", "medium", "unknown"} and credential in {"low", "medium"} and job_zone_difference <= 0:
        return (
            "review",
            "Major-reskilling path",
            "Low O*NET skill reuse, but education/preparation barrier appears low enough to keep for user-driven cross-domain exploration.",
        )
    return (
        "review",
        "Bridge candidate",
        "Partial skill reuse or preparation uncertainty; needs training and Taiwan market validation.",
    )


def beauty_job_rule_for_title(title: str) -> dict[str, object]:
    title_lower = title.lower()
    rule = {
        "strong": [],
        "positive": [],
        "negative": ["照顧服務員", "傳送", "清潔", "櫃台行政", "行政人員", "餐飲", "獸醫", "照服員", "看護", "寵物"],
        "categories": [],
        "requires_strong": True,
        "requires_management": False,
        "requires_anchor_title_or_category_for_high": False,
        "review_reason": "",
    }
    if "dermatologist" in title_lower:
        rule.update(
            strong=["皮膚科醫師", "皮膚科"],
            positive=["醫師", "診所", "醫療", "雷射", "皮膚"],
            categories=["醫師", "醫療／美容／保健"],
            review_reason="Dermatologist is a physician occupation and requires manual review even if TaiwanJobs has generic clinic roles.",
        )
    elif "skincare" in title_lower:
        rule.update(
            strong=["美容師", "美容諮詢師", "護膚", "美體", "醫美", "美療", "芳療師"],
            positive=["美容", "保養", "療程", "皮膚", "客戶", "諮詢", "美體", "雷射"],
            categories=["美容技術員", "美療／芳療師", "醫療／美容／保健"],
            negative=["照顧服務員", "傳送", "清潔", "餐飲", "獸醫", "寵物"],
        )
    elif "massage" in title_lower:
        rule.update(
            strong=["按摩", "芳療師", "經絡", "推拿", "舒壓", "SPA", "spa"],
            positive=["芳療", "保健", "身體", "客戶", "療程", "養護"],
            categories=["美療／芳療師", "醫療／美容／保健"],
            negative=["照顧服務員", "傳送", "清潔", "獸醫", "寵物"],
        )
    elif any(term in title_lower for term in ["hairdresser", "hairstylist", "cosmetologist", "barber", "shampooer"]):
        rule.update(
            strong=["美髮", "髮型", "剪髮", "燙染", "染髮", "培訓設計師", "美髮助理", "美髮設計師"],
            positive=["沙龍", "造型", "設計師", "洗髮", "剪染", "技術員"],
            categories=["美髮技術員", "美髮類助理"],
            negative=["照顧服務員", "清潔", "獸醫", "寵物"],
        )
    elif "manicurist" in title_lower or "pedicurist" in title_lower:
        rule.update(
            strong=["美甲", "指甲", "凝膠", "手部保養"],
            positive=["彩繪", "沙龍", "造型", "客戶"],
            categories=["美容技術員", "美療／芳療師"],
            negative=["照顧服務員", "清潔", "獸醫", "寵物"],
        )
    elif "makeup" in title_lower:
        rule.update(
            strong=["彩妝", "化妝", "新秘", "整體造型"],
            positive=["造型", "美容", "保養品", "專櫃", "門市", "客戶"],
            categories=["美容技術員", "專櫃／門市", "賣場（人員／儲備幹部）"],
            negative=["照顧服務員", "清潔", "獸醫", "寵物"],
            requires_anchor_title_or_category_for_high=True,
        )
    elif "spa" in title_lower or "manager" in title_lower or "supervisor" in title_lower:
        rule.update(
            strong=["SPA", "spa", "芳療", "美容", "美體", "美容諮詢師"],
            positive=["主管", "店長", "管理", "營運", "諮詢", "客戶"],
            categories=["美療／芳療師", "美容技術員", "經營／行政／總務"],
            requires_management="manager" in title_lower or "supervisor" in title_lower,
            negative=["照顧服務員", "傳送", "清潔", "獸醫", "寵物"],
            requires_anchor_title_or_category_for_high=True,
            review_reason="Spa/beauty management may appear as service staff in TaiwanJobs; management fit requires review.",
        )
    elif "door-to-door" in title_lower or "sales" in title_lower:
        rule.update(
            strong=["美容諮詢師", "醫美", "保養品", "化妝品", "彩妝", "藥妝"],
            positive=["銷售", "顧問", "門市", "專櫃", "產品", "客戶", "採購", "行銷"],
            categories=["業務／貿易／銷售", "專櫃／門市", "賣場（人員／儲備幹部）"],
            negative=["照顧服務員", "清潔", "獸醫", "長照系統", "寵物"],
            requires_anchor_title_or_category_for_high=True,
            review_reason="Beauty sales/consulting has unstable title localization; job-level QA keeps only anchored beauty jobs.",
        )
    else:
        rule.update(
            strong=["美容", "醫美", "芳療", "美髮", "美甲", "彩妝", "保養品"],
            positive=["服務", "客戶", "門市", "諮詢"],
            categories=["醫療／美容／保健", "業務／貿易／銷售"],
            review_reason="Generic beauty fallback; manual review needed.",
        )
    return rule


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword and keyword in text for keyword in keywords)


def score_beauty_job(job: pd.Series, rule: dict[str, object]) -> tuple[float, str, str]:
    strong = list(rule["strong"])
    positive = list(rule["positive"])
    negative = list(rule["negative"])
    categories = list(rule["categories"])
    title = str(job["OCCU_DESC（職務名稱）"])
    cjob1 = str(job["CJOB_NAME1（職務大類別名稱）"])
    cjob2 = str(job["CJOB_NAME2（職務小類別名稱）"])
    detail = str(job["JOB_DETAIL（工作內容）"])
    title_and_category = " ".join([title, cjob1, cjob2])
    all_text = " ".join([title, cjob1, cjob2, detail])

    if contains_any(title, negative) or contains_any(cjob2, negative):
        return 0.0, "Low", "excluded_negative_title_or_category"
    if contains_any(detail, negative) and not contains_any(title_and_category, strong):
        return 0.0, "Low", "excluded_negative_detail_without_anchor"

    strong_title = contains_any(title, strong)
    strong_category = contains_any(cjob2, strong)
    strong_detail = contains_any(detail, strong)
    if rule.get("requires_strong") and not (strong_title or strong_category or strong_detail):
        return 0.0, "Low", "no_strong_beauty_anchor"

    score = 0.0
    if strong_title:
        score += 0.55
    if strong_category:
        score += 0.38
    if strong_detail:
        score += 0.25
    score += min(sum(1 for keyword in positive if keyword in title) * 0.16, 0.30)
    score += min(sum(1 for keyword in positive if keyword in cjob2) * 0.12, 0.20)
    score += min(sum(1 for keyword in positive if keyword in detail) * 0.06, 0.24)
    if contains_any(cjob1, categories) or contains_any(cjob2, categories):
        score += 0.10
    if rule.get("requires_management") and not contains_any(title_and_category, ["主管", "店長", "管理", "營運", "經理"]):
        score = min(score, 0.47)
    if rule.get("requires_anchor_title_or_category_for_high") and not (strong_title or strong_category):
        score = min(score, 0.47)

    score = round(float(min(max(score, 0.0), 1.0)), 6)
    if score >= 0.72:
        return score, "High", ""
    if score >= 0.48:
        return score, "Medium", "medium_relevance_requires_manual_review"
    return score, "Low", "below_medium_relevance_threshold"


def summarize_job_examples(frame: pd.DataFrame, limit: int = 5) -> str:
    if frame.empty:
        return ""
    examples = []
    for record in frame.head(limit).to_dict("records"):
        salary = f"{record['SALARYCD（核薪方式）']} {record['NT_L（薪資範圍下限）']}-{record['NT_U（薪資範圍上限）']}"
        detail = str(record["JOB_DETAIL（工作內容）"]).replace("\n", " ").replace("\t", " ")
        if len(detail) > 90:
            detail = detail[:90] + "..."
        examples.append(
            f"{record['OCCU_DESC（職務名稱）']} | {record['COMPNAME（公司名稱）']} | {record['CITYNAME（工作地點）']} | {salary} | {detail} | {record['URL_QUERY（職缺資料URL）']}"
        )
    return " || ".join(examples)


def market_level(high_count: int, demand: int) -> str:
    if high_count >= 5 and demand >= 5:
        return "Strong"
    if high_count >= 2:
        return "Moderate"
    if high_count == 1:
        return "Weak"
    return "Insufficient public evidence"


def summarize_high_relevance_market(scored_jobs: pd.DataFrame) -> dict[str, object]:
    high = scored_jobs.loc[scored_jobs["job_relevance_confidence"].eq("High")].copy()
    medium = scored_jobs.loc[scored_jobs["job_relevance_confidence"].eq("Medium")].copy()
    monthly = high.loc[high["SALARYCD（核薪方式）"].eq("月薪")]
    lower = monthly["salary_lower_numeric"].dropna()
    upper = monthly["salary_upper_numeric"].dropna()
    demand = int(high["JOB_PERSON（雇用人數）"].sum()) if not high.empty else 0
    return {
        "taiwanjobs_high_relevance_job_count": int(len(high)),
        "taiwanjobs_medium_relevance_job_count": int(len(medium)),
        "total_demand_persons_high": demand,
        "salary_lower_median_high": "" if lower.empty else int(round(float(lower.median()))),
        "salary_upper_median_high": "" if upper.empty else int(round(float(upper.median()))),
        "salary_basis": "monthly_only_excludes_hourly_daily_piece_and_negotiated",
        "education_requirement_distribution_high": "" if high.empty else "; ".join(f"{k}:{v}" for k, v in high["EDGRDESC（最低學歷要求）"].value_counts().head(8).to_dict().items()),
        "experience_requirement_distribution_high": "" if high.empty else "; ".join(f"{k}:{v}" for k, v in high["EXPERIENCE（工作經驗）"].value_counts().head(8).to_dict().items()),
        "main_job_locations_high": "" if high.empty else "; ".join(f"{k}:{v}" for k, v in high["CITYNAME（工作地點）"].value_counts().head(8).to_dict().items()),
        "taiwan_market_evidence": market_level(len(high), demand),
        "high_relevance_job_examples": summarize_job_examples(high, 5),
        "medium_relevance_job_examples": summarize_job_examples(medium, 5),
    }


def beauty_course_terms(target_title: str, skill_name: str = "") -> list[str]:
    target_lower = target_title.lower()
    skill_lower = skill_name.lower()
    terms: set[str] = set()

    if any(term in target_lower for term in ["hairdresser", "hairstylist", "barber", "shampooer", "cosmetologist"]):
        return ["美髮", "髮型", "剪髮", "燙染", "沙龍", "頭皮", "洗髮"]
    if "manicurist" in target_lower or "pedicurist" in target_lower:
        return ["美甲", "指甲", "凝膠", "彩繪", "手部保養"]
    if "makeup" in target_lower:
        return ["彩妝", "化妝", "整體造型", "美容", "設計"]
    if "massage" in target_lower:
        return ["按摩", "芳療", "經絡", "推拿", "舒壓", "保健", "養護"]
    if any(term in target_lower for term in ["skincare", "dermatologist"]):
        return ["美容", "護膚", "保養", "美體", "醫美", "皮膚", "芳療", "保養品", "化妝品"]
    if "spa" in target_lower:
        return ["美容", "芳療", "SPA", "spa", "管理", "行銷", "門市", "顧問", "按摩", "舒壓"]
    if "sales" in target_lower or "retail" in target_lower or "door-to-door" in target_lower:
        return ["美容", "保養品", "化妝品", "行銷", "銷售", "門市", "顧問", "客服", "服務"]

    if any(term in skill_lower for term in ["medicine", "biology", "chemistry"]):
        terms.update(["美容", "護膚", "保養", "美體", "醫美", "皮膚", "芳療", "保養品", "化妝品"])
    if any(term in skill_lower for term in ["therapy", "counseling", "psychology"]):
        terms.update(["按摩", "芳療", "經絡", "推拿", "舒壓", "保健", "養護"])
    if any(term in skill_lower for term in ["fine arts", "design"]):
        terms.update(["彩妝", "化妝", "整體造型", "美容", "美甲", "設計"])
    if "manager" in target_lower or any(term in skill_lower for term in ["management", "administration"]):
        terms.update(["美容", "芳療", "SPA", "spa", "管理", "行銷", "門市", "顧問"])
    if any(term in skill_lower for term in ["sales", "marketing", "customer"]):
        terms.update(["美容", "保養品", "化妝品", "行銷", "銷售", "門市", "顧問", "客服", "服務"])
    if not terms:
        terms.update(["美容", "服務"])
    return sorted(terms, key=lambda value: (-len(value), value))


def match_course_to_beauty_skill(course_name: str, target_title: str, skill_name: str) -> tuple[float, str, str, str]:
    if "寵物" in course_name:
        return 0.0, "", "No match", "yes"
    terms = beauty_course_terms(target_title, skill_name)
    hits = [term for term in terms if term.lower() in course_name.lower()]
    if not hits:
        return 0.0, "", "No match", "yes"
    strong_hits = [term for term in hits if term in {"美容", "護膚", "醫美", "美甲", "美髮", "芳療", "按摩", "彩妝", "保養品", "化妝品"}]
    score = min(1.0, 0.18 * len(hits) + 0.22 * len(strong_hits))
    if score >= 0.75:
        confidence = "High"
    elif score >= 0.45:
        confidence = "Medium"
    else:
        return 0.0, "", "No match", "yes"
    return round(float(score), 3), "; ".join(hits[:12]), confidence, "no" if confidence == "High" else "yes"


def match_course_to_beauty_target(course_name: str, target_title: str) -> tuple[float, str, str, str]:
    if "寵物" in course_name:
        return 0.0, "", "No match", "yes"
    terms = beauty_course_terms(target_title)
    hits = [term for term in terms if term.lower() in course_name.lower()]
    if not hits:
        return 0.0, "", "No match", "yes"
    strong_hits = [term for term in hits if term in {"美容", "護膚", "醫美", "美甲", "美髮", "芳療", "按摩", "彩妝", "保養品", "化妝品"}]
    score = min(1.0, 0.16 * len(hits) + 0.24 * len(strong_hits))
    if score >= 0.72:
        confidence = "High"
    elif score >= 0.40:
        confidence = "Medium"
    else:
        return 0.0, "", "No match", "yes"
    return round(float(score), 3), "; ".join(hits[:12]), confidence, "no" if confidence == "High" else "yes"


def target_skill_gaps(target_code: str, target_title: str, raw_wide: pd.DataFrame, feature_meta: dict[str, dict[str, str]]) -> pd.DataFrame:
    source_vector = raw_wide.loc[NURSING_CODE]
    target_vector = raw_wide.loc[target_code]
    target_required = target_vector.loc[target_vector.ge(REQUIRED_SKILL_THRESHOLD)]
    records = []
    for feature_id, target_value in target_required.items():
        meta = feature_meta[feature_id]
        source_value = float(source_vector.get(feature_id, 0.0))
        gap = max(float(target_value) - source_value, 0.0)
        records.append(
            {
                "target_occupation_code": target_code,
                "target_occupation_name": target_title,
                "skill_id": feature_id.split(":", 1)[1],
                "skill_name": meta["skill_name"],
                "skill_type": meta["skill_type"],
                "target_importance": round(float(target_value), 3),
                "source_importance": round(source_value, 3),
                "raw_gap": round(gap, 3),
                "skill_gap_status": skill_gap_status(source_value, float(target_value)),
            }
        )
    gaps = pd.DataFrame.from_records(records)
    if gaps.empty:
        return pd.DataFrame(
            columns=[
                "target_occupation_code",
                "target_occupation_name",
                "skill_id",
                "skill_name",
                "skill_type",
                "target_importance",
                "source_importance",
                "raw_gap",
                "skill_gap_status",
            ]
        )
    order = {"missing": 0, "partially_covered": 1, "already_covered": 2}
    gaps["_order"] = gaps["skill_gap_status"].map(order).fillna(3)
    return gaps.sort_values(["_order", "raw_gap", "target_importance"], ascending=[True, False, False]).drop(columns=["_order"])


def map_training_for_target(target_gaps: pd.DataFrame, courses: pd.DataFrame, target_title: str) -> pd.DataFrame:
    trainable = target_gaps.loc[target_gaps["skill_gap_status"].isin(["missing", "partially_covered"])].copy()
    records = []
    for _, skill in trainable.iterrows():
        matches = []
        for _, course in courses.iterrows():
            score, hits, confidence, manual_review = match_course_to_beauty_skill(
                str(course["course_name"]),
                target_title,
                str(skill["skill_name"]),
            )
            if score <= 0:
                continue
            matches.append(
                {
                    "skill_id": skill["skill_id"],
                    "skill_name": skill["skill_name"],
                    "skill_gap_status": skill["skill_gap_status"],
                    "raw_gap": skill["raw_gap"],
                    "course_code": course["course_code"],
                    "course_name": course["course_name"],
                    "training_provider": course["training_provider"],
                    "location": course["location"],
                    "training_hours": course["training_hours"],
                    "fee_per_person": course["fee_per_person"],
                    "start_date": course["start_date"].date().isoformat() if not pd.isna(course["start_date"]) else "",
                    "end_date": course["end_date"].date().isoformat() if not pd.isna(course["end_date"]) else "",
                    "mapping_method": "deterministic_course_title_to_beauty_target_skill_keyword_phase5",
                    "mapping_score": score,
                    "mapping_terms_matched": hits,
                    "mapping_confidence": confidence,
                    "manual_review_needed": manual_review,
                }
            )
        matches = sorted(matches, key=lambda record: (-float(record["mapping_score"]), float(record["training_hours"]) if not pd.isna(record["training_hours"]) else 99999.0, str(record["course_name"])))[:5]
        records.extend(matches)
    target_matches = []
    for _, course in courses.iterrows():
        score, hits, confidence, manual_review = match_course_to_beauty_target(str(course["course_name"]), target_title)
        if score <= 0:
            continue
        target_matches.append(
            {
                "skill_id": "target_domain_training_area",
                "skill_name": "Beauty target-domain practical training area",
                "skill_gap_status": "target_domain_training_area",
                "raw_gap": "",
                "course_code": course["course_code"],
                "course_name": course["course_name"],
                "training_provider": course["training_provider"],
                "location": course["location"],
                "training_hours": course["training_hours"],
                "fee_per_person": course["fee_per_person"],
                "start_date": course["start_date"].date().isoformat() if not pd.isna(course["start_date"]) else "",
                "end_date": course["end_date"].date().isoformat() if not pd.isna(course["end_date"]) else "",
                "mapping_method": "deterministic_course_title_to_beauty_target_keyword_phase5",
                "mapping_score": score,
                "mapping_terms_matched": hits,
                "mapping_confidence": confidence,
                "manual_review_needed": manual_review,
            }
        )
    target_matches = sorted(target_matches, key=lambda record: (-float(record["mapping_score"]), float(record["training_hours"]) if not pd.isna(record["training_hours"]) else 99999.0, str(record["course_name"])))[:8]
    records.extend(target_matches)
    if not records:
        return pd.DataFrame()
    return pd.DataFrame.from_records(records).sort_values(["skill_gap_status", "skill_name", "mapping_score"], ascending=[True, True, False])


def summarize_training(target_mapping: pd.DataFrame, missing_skill_ids: set[str], transition_span_value: str) -> dict[str, object]:
    if target_mapping.empty:
        missing_count = len(missing_skill_ids)
        return {
            "number_of_missing_skills": missing_count,
            "number_of_trainable_missing_skills_found": 0,
            "training_coverage_ratio_missing_skills": 0.0 if missing_count else 1.0,
            "training_course_count": 0,
            "total_training_hours": "",
            "estimated_direct_course_cost": "",
            "subsidy_information": "unknown",
            "scheduling_information": "unknown",
            "matched_training_courses": "",
            "training_availability": "Unknown",
            "learning_burden": training_burden_level(missing_count, 0.0, "", "", transition_span_value),
        }

    eligible = target_mapping.loc[target_mapping["mapping_confidence"].isin(["High", "Medium"])].copy()
    missing_eligible = eligible.loc[eligible["skill_id"].isin(missing_skill_ids)]
    covered_missing = set(missing_eligible["skill_id"])
    ratio = round(len(covered_missing) / len(missing_skill_ids), 3) if missing_skill_ids else 1.0
    top_courses = eligible.sort_values(["course_code", "mapping_score"], ascending=[True, False]).drop_duplicates("course_code")
    top_courses = top_courses.sort_values(["mapping_confidence", "mapping_score", "training_hours"], ascending=[True, False, True]).head(8)
    hours = round(float(top_courses["training_hours"].dropna().sum()), 1) if not top_courses.empty else 0.0
    cost = round(float(top_courses["fee_per_person"].dropna().sum()), 1) if not top_courses.empty else 0.0
    if len(top_courses) >= 5:
        availability = "Strong"
    elif len(top_courses) >= 2:
        availability = "Moderate"
    elif len(top_courses) == 1:
        availability = "Weak"
    else:
        availability = "Unknown"
    course_examples = "; ".join(
        f"{record['course_name']} ({record['training_hours']}h, {record['fee_per_person']} TWD, {record['mapping_confidence']})"
        for record in top_courses.to_dict("records")
    )
    return {
        "number_of_missing_skills": len(missing_skill_ids),
        "number_of_trainable_missing_skills_found": len(covered_missing),
        "training_coverage_ratio_missing_skills": ratio,
        "training_course_count": int(len(top_courses)),
        "total_training_hours": hours,
        "estimated_direct_course_cost": cost,
        "subsidy_information": "unknown",
        "scheduling_information": "unknown",
        "matched_training_courses": course_examples,
        "training_availability": availability,
        "learning_burden": training_burden_level(len(missing_skill_ids), ratio, hours, cost, transition_span_value),
    }


def interpretation_note(row: dict[str, object]) -> str:
    if row["feasibility_level"] == "Infeasible / high-barrier":
        return "Medical/clinical adjacency is visible, but education and credential barriers dominate."
    if row["transition_span"] == "Major reskilling" and row["education_barrier"] in {"low", "medium", "unknown"}:
        return "Low skill similarity should not exclude this path; treat it as a user-driven major-reskilling option if training and market evidence are present."
    if row["transition_span"] == "Partial skill reuse":
        return "Nursing communication, care, anatomy, and client-service experience may transfer, but beauty-specific techniques still need training."
    return "Strongest reuse comes from clinical care and client trust, but Taiwan role localization still needs evidence."


def build_beauty_evidence(candidates: pd.DataFrame, occupation_skills: pd.DataFrame) -> pd.DataFrame:
    _, similarity_df = build_weighted_similarity_matrix(occupation_skills)
    raw_wide, feature_meta = build_raw_skill_wide(occupation_skills)
    profiles = build_occupation_feasibility_profile().set_index("occupation_code")
    source_profile = profiles.loc[NURSING_CODE]
    source_vector = raw_wide.loc[NURSING_CODE]
    courses, _ = load_training_courses()
    jobs = load_taiwanjobs()

    related = pd.read_csv(ONET_RELATED_OCCUPATIONS).rename(
        columns={
            "O*NET-SOC Code": "occupation_code",
            "Related O*NET-SOC Code": "target_occupation_code",
            "Relatedness Tier": "related_tier",
            "Index": "related_index",
        }
    )
    related_lookup = related.loc[related["occupation_code"].eq(NURSING_CODE)].set_index("target_occupation_code")[
        ["related_tier", "related_index"]
    ].to_dict("index")

    records = []
    for _, candidate in candidates.iterrows():
        target_code = str(candidate["target_occupation_code"])
        target_title = str(candidate["target_occupation_name"])
        if target_code not in similarity_df.columns or target_code not in raw_wide.index or target_code not in profiles.index:
            continue
        target_profile = profiles.loc[target_code]
        target_vector = raw_wide.loc[target_code]
        coverage, gap = directional_skill_metrics(source_vector, target_vector, feature_meta)
        education_level, education_notes = education_barrier(source_profile, target_profile, target_title)
        training_level, training_notes = training_experience_barrier(source_profile, target_profile)
        credential_level = credential_barrier(target_profile, target_title)
        span = beauty_transition_span(
            target_title,
            str(candidate["target_domain_primary_signal"]),
            coverage,
            gap,
            education_level,
            credential_level,
        )
        related_support = related_lookup.get(target_code)
        same_major, same_family, taxonomy_level = taxonomy_distance(
            NURSING_CODE,
            target_code,
            "yes" if related_support else "no",
            related_support["related_tier"] if related_support else "",
        )
        job_zone_difference = target_profile["job_zone"] - source_profile["job_zone"]

        gaps = target_skill_gaps(target_code, target_title, raw_wide, feature_meta)
        missing = gaps.loc[gaps["skill_gap_status"].eq("missing")]
        partial = gaps.loc[gaps["skill_gap_status"].eq("partially_covered")]
        covered = gaps.loc[gaps["skill_gap_status"].eq("already_covered")]
        training_mapping = map_training_for_target(gaps, courses, target_title)
        training_summary = summarize_training(training_mapping, set(missing["skill_id"]), span)

        rule = beauty_job_rule_for_title(target_title)
        scored_jobs = jobs.copy()
        scored = scored_jobs.apply(lambda row: score_beauty_job(row, rule), axis=1, result_type="expand")
        scored_jobs["job_relevance_score"] = scored[0]
        scored_jobs["job_relevance_confidence"] = scored[1]
        scored_jobs["job_relevance_review_reason"] = scored[2]
        scored_jobs = scored_jobs.loc[scored_jobs["job_relevance_confidence"].isin(["High", "Medium"])].sort_values(
            "job_relevance_score",
            ascending=False,
        )
        market_summary = summarize_high_relevance_market(scored_jobs)

        record = {
            **candidate.to_dict(),
            "skill_similarity": round(float(similarity_df.loc[NURSING_CODE, target_code]), 6),
            "transferable_skill_coverage": round(coverage, 6),
            "target_skill_gap": round(gap, 6),
            "transition_span": span,
            "related_support": "yes" if related_support else "no",
            "related_tier": related_support["related_tier"] if related_support else "",
            "related_index": int(related_support["related_index"]) if related_support else "",
            "source_job_zone": int(source_profile["job_zone"]) if not pd.isna(source_profile["job_zone"]) else "",
            "target_job_zone": int(target_profile["job_zone"]) if not pd.isna(target_profile["job_zone"]) else "",
            "job_zone_difference": int(job_zone_difference) if not pd.isna(job_zone_difference) else 0,
            "source_modal_education": text_or_unknown(source_profile.get("education_modal_label", "")),
            "target_modal_education": text_or_unknown(target_profile.get("education_modal_label", "")),
            "education_barrier": education_level,
            "education_barrier_notes": education_notes,
            "training_experience_barrier": training_level,
            "training_experience_barrier_notes": training_notes,
            "credential_barrier": credential_level,
            "same_major_group": same_major,
            "same_occupation_family": same_family,
            "onet_related_support": "yes" if related_support else "no",
            "taxonomy_distance_level": taxonomy_level,
            "already_covered_skills": summarize_skill_names(covered, 8),
            "partially_covered_skills": summarize_skill_names(partial, 8),
            "missing_skills": summarize_skill_names(missing, 8),
            "job_mapping_method": "deterministic_taiwanjobs_job_level_beauty_alias_relevance_phase5",
            "job_mapping_positive_aliases": "; ".join(list(rule["strong"]) + list(rule["positive"])),
            "job_mapping_review_reason": rule["review_reason"],
            **market_summary,
            **training_summary,
        }
        flag, level, notes = classify_beauty_feasibility(target_title, target_profile, record)
        record["feasibility_flag"] = flag
        record["feasibility_level"] = level
        record["feasibility_notes"] = notes
        record["interpretation_note"] = interpretation_note(record)
        records.append(record)

    result = pd.DataFrame.from_records(records)
    if result.empty:
        return result
    flag_order = {"candidate": 0, "review": 1, "exclude": 2}
    span_order = {"High skill reuse": 0, "Partial skill reuse": 1, "Major reskilling": 2}
    market_order = {"Strong": 0, "Moderate": 1, "Weak": 2, "Insufficient public evidence": 3}
    result["_flag_order"] = result["feasibility_flag"].map(flag_order).fillna(9)
    result["_span_order"] = result["transition_span"].map(span_order).fillna(9)
    result["_market_order"] = result["taiwan_market_evidence"].map(market_order).fillna(9)
    result = result.sort_values(
        ["_flag_order", "_market_order", "_span_order", "target_domain_retrieval_score"],
        ascending=[True, True, True, False],
    ).drop(columns=["_flag_order", "_span_order", "_market_order"])
    result.insert(0, "phase5_evidence_rank", range(1, len(result) + 1))
    return result


def compare_with_tech(result: pd.DataFrame) -> dict[str, object]:
    summary: dict[str, object] = {
        "tech_available": False,
    }
    if NURSING_TECH_CANDIDATES_V35_CSV.exists():
        tech = pd.read_csv(NURSING_TECH_CANDIDATES_V35_CSV)
        summary.update(
            {
                "tech_available": True,
                "tech_rows": len(tech),
                "tech_span_counts": tech.get("transition_span", pd.Series(dtype=str)).value_counts().to_dict(),
                "tech_skill_similarity_median": round(float(pd.to_numeric(tech.get("skill_similarity"), errors="coerce").median()), 3),
                "tech_market_counts": tech.get("market_validation", pd.Series(dtype=str)).value_counts().to_dict(),
            }
        )
    if NURSING_TECH_TRAINING_V4_CSV.exists():
        training = pd.read_csv(NURSING_TECH_TRAINING_V4_CSV)
        summary["tech_training_available"] = True
        summary["tech_training_rows"] = len(training)
        if "learning_burden" in training.columns:
            summary["tech_learning_burden_counts"] = training["learning_burden"].value_counts().to_dict()
    summary.update(
        {
            "beauty_rows": len(result),
            "beauty_span_counts": result["transition_span"].value_counts().to_dict(),
            "beauty_skill_similarity_median": round(float(pd.to_numeric(result["skill_similarity"], errors="coerce").median()), 3),
            "beauty_market_counts": result["taiwan_market_evidence"].value_counts().to_dict(),
            "beauty_training_counts": result["training_availability"].value_counts().to_dict(),
        }
    )
    return summary


def format_counts(counts: dict[str, object]) -> str:
    if not counts:
        return "none"
    return "; ".join(f"{key}: {value}" for key, value in counts.items())


def md_value(value: object, fallback: str = "none") -> str:
    if pd.isna(value) or value == "":
        return fallback
    return str(value)


def write_phase5_md(result: pd.DataFrame, comparison: dict[str, object]) -> None:
    lines = [
        "# Nursing to Beauty Phase 5 Stress Test",
        "",
        f"Source occupation: `Registered Nurses` (`{NURSING_CODE}`)",
        f"Target domain: `{TARGET_DOMAIN}`",
        f"Observation date for TaiwanJobs/training availability: `{OBSERVATION_DATE.date().isoformat()}`",
        "",
        "This is a stress test for user-driven cross-domain exploration. It does not modify the nursing->technology outputs and does not calculate transition success probability, policy recommendations, or a single career score.",
        "",
        "## Method",
        "",
        "- Candidate generation uses local O*NET occupation title/description, tasks, required skills/knowledge, job titles, and sample reported titles.",
        "- Retrieval is deterministic keyword scoring for beauty, aesthetics, personal care, skin/hair/nail, spa, massage, and beauty sales/management aliases.",
        "- Every generated candidate is passed through the existing evidence dimensions: skill similarity, RN->target directional skill coverage/gap, education/credential/training barriers, O*NET taxonomy distance, O*NET Related Occupations support, TaiwanJobs job-level relevance QA, and training title matching.",
        "- Low `skill_similarity` is not an exclusion rule. If preparation barriers are low and training supply exists, the path is retained as a `Major-reskilling path` for exploration.",
        "",
        "## Candidate Evidence Summary",
        "",
        "| Candidate | Span | Feasibility | Skill similarity | Coverage | Gap | TW market | Training | High jobs | Medium jobs |",
        "|---|---:|---|---:|---:|---:|---|---|---:|---:|",
    ]
    for record in result.to_dict("records"):
        lines.append(
            f"| {record['target_occupation_name']} | {record['transition_span']} | {record['feasibility_level']} | "
            f"{record['skill_similarity']:.3f} | {record['transferable_skill_coverage']:.3f} | {record['target_skill_gap']:.3f} | "
            f"{record['taiwan_market_evidence']} | {record['training_availability']} | "
            f"{record['taiwanjobs_high_relevance_job_count']} | {record['taiwanjobs_medium_relevance_job_count']} |"
        )

    lines.extend(
        [
            "",
            "## Representative TaiwanJobs Evidence",
            "",
            "Only High relevance jobs are counted in the main market evidence. Medium relevance jobs are retained as review candidates and excluded from salary/demand statistics.",
            "",
        ]
    )
    for record in result.to_dict("records"):
        high_examples = md_value(
            record["high_relevance_job_examples"],
            "No High relevance jobs. Current public market data is insufficient; this does not mean the career does not exist.",
        )
        medium_examples = md_value(record["medium_relevance_job_examples"])
        lines.extend(
            [
                f"### {record['target_occupation_name']}",
                "",
                f"- High relevance jobs: {record['taiwanjobs_high_relevance_job_count']}",
                f"- Medium review candidates: {record['taiwanjobs_medium_relevance_job_count']}",
                f"- Demand persons counted from High relevance only: {record['total_demand_persons_high']}",
                f"- Monthly salary median range from High relevance only: {md_value(record['salary_lower_median_high'], 'insufficient monthly salary')} - {md_value(record['salary_upper_median_high'], 'insufficient monthly salary')}",
                f"- High examples: {high_examples}",
                f"- Medium examples: {medium_examples}",
                "",
            ]
        )

    lines.extend(
        [
            "## Training Evidence",
            "",
            "Training data has course title, hours, fee, provider, location, and dates, but no full syllabus. Course-to-skill mapping is deterministic title matching and should be manually reviewed before learner-facing recommendations.",
            "",
        ]
    )
    for record in result.to_dict("records"):
        lines.extend(
            [
                f"### {record['target_occupation_name']}",
                "",
                f"- Missing skills: {record['number_of_missing_skills']}",
                f"- Missing skills with matched course evidence: {record['number_of_trainable_missing_skills_found']}",
                f"- Training coverage ratio over missing skills: {record['training_coverage_ratio_missing_skills']}",
                f"- Top matched courses: {md_value(record['matched_training_courses'])}",
                f"- Total hours across top unique courses: {md_value(record['total_training_hours'], 'unknown')}",
                f"- Estimated direct course cost: {md_value(record['estimated_direct_course_cost'], 'unknown')}",
                f"- Learning burden: {record['learning_burden']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Nursing -> Tech vs Nursing -> Beauty",
            "",
            f"- Nursing->tech candidate rows: {comparison.get('tech_rows', 'unknown')}; span counts: {format_counts(comparison.get('tech_span_counts', {}))}; median skill similarity: {comparison.get('tech_skill_similarity_median', 'unknown')}.",
            f"- Nursing->beauty candidate rows: {comparison.get('beauty_rows', 'unknown')}; span counts: {format_counts(comparison.get('beauty_span_counts', {}))}; median skill similarity: {comparison.get('beauty_skill_similarity_median', 'unknown')}.",
            f"- Nursing->beauty market evidence counts: {format_counts(comparison.get('beauty_market_counts', {}))}.",
            f"- Nursing->beauty training availability counts: {format_counts(comparison.get('beauty_training_counts', {}))}.",
            "",
            "Reusable nursing abilities in beauty paths: client trust, care communication, service orientation, anatomy/skin/body knowledge for skincare or massage-related work, and clinical credibility for medical-aesthetic contexts.",
            "",
            "Skills usually needing relearning: hands-on beauty techniques, hair/nail/makeup craft, spa/salon operations, beauty product sales, aesthetic service consultation, and business/retail execution.",
            "",
            "Algorithm stress-test finding: global O*NET similarity would naturally favor healthcare-adjacent roles and under-surface low-similarity but low-barrier beauty service paths. Target-domain candidate generation plus training/market evidence is necessary when the user intentionally wants to cross domains.",
            "",
            "Suggested method adjustments: keep `skill_similarity` as evidence, not a gate; add a transition-intent mode that can retain low-similarity/low-barrier candidates; require job-level market QA; distinguish High relevance jobs from Medium review candidates; and add Taiwan-specific occupation aliases for domains where O*NET titles do not localize cleanly.",
            "",
            "## Limitations",
            "",
            "- O*NET is a US occupation taxonomy and may not map cleanly to Taiwan beauty/aesthetic titles.",
            "- TaiwanJobs sample size and occupation labels can miss localized roles, especially medical aesthetics and beauty consulting.",
            "- Training data has course titles but no complete syllabus, so course-skill coverage is potential evidence, not proof that a skill is fully covered.",
            "- This output is not a transition success probability and does not rank final recommendations.",
        ]
    )
    PHASE5_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if not OCCUPATION_SKILLS_CSV.exists():
        raise FileNotFoundError(f"Missing {OCCUPATION_SKILLS_CSV}; run the v1 occupation-skill pipeline first.")
    OUTPUTS_CAREER.mkdir(parents=True, exist_ok=True)
    occupation_skills = pd.read_csv(OCCUPATION_SKILLS_CSV)
    candidates = generate_beauty_candidates(occupation_skills, max_candidates=50)
    result = build_beauty_evidence(candidates, occupation_skills)
    result.to_csv(PHASE5_CSV, index=False, encoding="utf-8")
    comparison = compare_with_tech(result)
    write_phase5_md(result, comparison)
    print(f"Wrote {PHASE5_CSV.relative_to(Path.cwd())} rows={len(result)}")
    print(f"Wrote {PHASE5_MD.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()
