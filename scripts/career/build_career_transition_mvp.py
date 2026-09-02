#!/usr/bin/env python3
"""Build the first career transition graph MVP from local raw career data.

The pipeline intentionally uses only local files under data/raw/career and keeps
O*NET skill similarity separate from O*NET Related Occupations.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

RAW_CAREER = ROOT / "data" / "raw" / "career"
RAW_ONET = RAW_CAREER / "onet"

DOCS = ROOT / "docs"
PROCESSED_CAREER = ROOT / "data" / "processed" / "career"
OUTPUTS_CAREER = ROOT / "outputs" / "career"

INVENTORY_MD = DOCS / "career_data_inventory.md"
FEASIBILITY_METHOD_MD = DOCS / "career_transition_feasibility_v2_method.md"
OCCUPATION_SKILLS_CSV = PROCESSED_CAREER / "occupation_skills.csv"
NURSING_EXPLORATION_CSV = OUTPUTS_CAREER / "nursing_transition_exploration.csv"
NURSING_EXPLORATION_MD = OUTPUTS_CAREER / "nursing_transition_exploration.md"
NURSING_FEASIBILITY_V2_CSV = OUTPUTS_CAREER / "nursing_transition_feasibility_v2.csv"
NURSING_FEASIBILITY_V2_MD = OUTPUTS_CAREER / "nursing_transition_feasibility_v2.md"
MARKET_V3_METHOD_MD = DOCS / "career_transition_market_v3_method.md"
ONET_TAIWANJOBS_MAPPING_CSV = PROCESSED_CAREER / "onet_taiwanjobs_occupation_mapping.csv"
NURSING_MARKET_V3_CSV = OUTPUTS_CAREER / "nursing_transition_market_v3.csv"
NURSING_MARKET_V3_MD = OUTPUTS_CAREER / "nursing_transition_market_v3.md"
TARGET_DOMAIN_V35_METHOD_MD = DOCS / "target_domain_exploration_v35_method.md"
NURSING_TECH_CANDIDATES_V35_CSV = OUTPUTS_CAREER / "nursing_to_technology_candidates_v35.csv"
NURSING_TECH_EXPLORATION_V35_MD = OUTPUTS_CAREER / "nursing_to_technology_exploration_v35.md"
TRAINING_V4_METHOD_MD = DOCS / "career_transition_training_v4_method.md"
CAREER_TRAINING_SKILL_MAPPING_CSV = PROCESSED_CAREER / "career_training_skill_mapping.csv"
NURSING_TECH_TRAINING_V4_CSV = OUTPUTS_CAREER / "nursing_to_technology_training_v4.csv"
NURSING_TECH_TRAINING_V4_MD = OUTPUTS_CAREER / "nursing_to_technology_training_v4.md"

ONET_OCCUPATION_DATA = RAW_ONET / "occupation_data.csv"
ONET_RELATED_OCCUPATIONS = RAW_ONET / "related_occupations.csv"
TAIWANJOBS_OPEN_JOBS = RAW_CAREER / "jobs" / "taiwanjobs_open_jobs_2026-09-01.csv"
TRAINING_COURSES = RAW_CAREER / "training" / "industry_talent_training_courses_2026-09.csv"
ONET_JOB_ZONES = RAW_ONET / "job_zones.csv"
ONET_JOB_ZONE_REFERENCE = RAW_ONET / "job_zone_reference.csv"
ONET_EDUCATION = RAW_ONET / "education.csv"
ONET_EDUCATION_CATEGORIES = RAW_ONET / "education_categories.csv"
ONET_TRAINING_EXPERIENCE = RAW_ONET / "training_and_experience.csv"
ONET_TRAINING_EXPERIENCE_CATEGORIES = RAW_ONET / "training_and_experience_categories.csv"
ONET_SKILL_SOURCES = {
    "essential_skill": RAW_ONET / "essential_skills.csv",
    "transferable_skill": RAW_ONET / "transferable_skills.csv",
    "knowledge": RAW_ONET / "knowledge.csv",
}

NURSING_CODE = "29-1141.00"
REQUIRED_SKILL_THRESHOLD = 3.0
SKILL_GAP_REPORT_THRESHOLD = 0.75
SKILL_TYPE_WEIGHTS = {
    "essential_skill": 1.0 / 3.0,
    "transferable_skill": 1.0 / 3.0,
    "knowledge": 1.0 / 3.0,
}
FOCUS_TITLE_PATTERNS = [
    "Licensed Practical and Licensed Vocational Nurses",
    "Athletic Trainers",
    "Exercise Physiologists",
    "Medical Assistants",
    "Physical Therapists",
    "Nursing Instructors and Teachers, Postsecondary",
    "Physicians",
    "Neurologists",
]
HEALTHCARE_MAJOR_GROUPS = {"29", "31"}
TAIWANJOBS_TEXT_COLUMNS = [
    "OCCU_DESC（職務名稱）",
    "CJOB_NAME1（職務大類別名稱）",
    "CJOB_NAME2（職務小類別名稱）",
    "JOB_DETAIL（工作內容）",
]
TECH_AI_DOMAIN = "Technology / AI"
TECH_SPECIFIC_FEATURE_TERMS = [
    "Computers and Electronics",
    "Engineering and Technology",
    "Mathematics",
    "Design",
    "Telecommunications",
    "Operations Analysis",
    "Technology Design",
    "Programming",
    "Equipment Maintenance",
    "Troubleshooting",
    "Quality Control Analysis",
    "Systems Analysis",
    "Systems Evaluation",
    "Science",
]
V4_TARGET_CANDIDATES = {
    "15-1211.01": "Health Informatics Specialists",
    "15-2051.02": "Clinical Data Managers",
    "11-9121.01": "Clinical Research Coordinators",
    "29-2072.00": "Medical Records Specialists",
    "15-2099.01": "Bioinformatics Technicians",
    "15-2051.00": "Data Scientists",
}
OBSERVATION_DATE = pd.Timestamp("2026-09-01")


def ensure_dirs() -> None:
    for path in [
        RAW_CAREER / "jobs",
        RAW_CAREER / "onet",
        RAW_CAREER / "training",
        ROOT / "data" / "interim" / "career",
        PROCESSED_CAREER,
        ROOT / "scripts" / "career",
        OUTPUTS_CAREER,
        DOCS,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def detect_encoding(path: Path) -> str:
    for encoding in ["utf-8-sig", "utf-8", "cp950", "big5", "latin-1"]:
        try:
            path.read_text(encoding=encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "unknown"


def csv_row_count(path: Path, encoding: str) -> int:
    with path.open("r", encoding=encoding, newline="") as f:
        return max(sum(1 for _ in f) - 1, 0)


def csv_columns(path: Path, encoding: str) -> list[str]:
    with path.open("r", encoding=encoding, newline="") as f:
        reader = csv.reader(f)
        return next(reader, [])


def infer_dataset_use(relative_path: str) -> str:
    name = Path(relative_path).name
    if name == "occupation_data.csv":
        return "O*NET occupation backbone: code, title, description."
    if name == "essential_skills.csv":
        return "O*NET essential skill importance/level measures; used in v1 skill graph."
    if name == "transferable_skills.csv":
        return "O*NET transferable skill importance/level measures; used in v1 skill graph."
    if name == "knowledge.csv":
        return "O*NET knowledge importance/level measures; used in v1 skill graph."
    if name == "related_occupations.csv":
        return "O*NET curated related occupations; used only as separate support signal."
    if name == "job_zones.csv":
        return "O*NET preparation level by occupation; used in v2 feasibility constraints."
    if name == "job_zone_reference.csv":
        return "O*NET job zone definitions; used to document v2 feasibility constraints."
    if name == "education.csv":
        return "O*NET education requirement and certification measures; used in v2 feasibility constraints."
    if name == "education_categories.csv":
        return "O*NET education category labels; used in v2 feasibility constraints."
    if name == "training_and_experience.csv":
        return "O*NET work experience, training, and apprenticeship measures; used in v2 feasibility constraints."
    if name == "training_and_experience_categories.csv":
        return "O*NET training and experience category labels; used in v2 feasibility constraints."
    if name == "taiwanjobs_open_jobs_2026-09-01.csv":
        return "TaiwanJobs public openings; inventoried only, not integrated in v1."
    if name == "industry_talent_training_courses_2026-09.csv":
        return "Training courses; inventoried only, not integrated in v1."
    if name == "Read Me.txt":
        return "O*NET release and license notes."
    if relative_path.startswith("data/raw/career/onet/"):
        return "O*NET supporting table; not used in v1 pipeline."
    return "Raw career dataset; not used in v1 pipeline."


def build_inventory() -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for path in sorted(RAW_CAREER.rglob("*")):
        if not path.is_file() or any(part.startswith(".") for part in path.relative_to(RAW_CAREER).parts):
            continue

        relative_path = path.relative_to(ROOT).as_posix()
        encoding = detect_encoding(path)
        columns: list[str] = []
        rows: int | str = ""

        if path.suffix.lower() == ".csv" and encoding != "unknown":
            columns = csv_columns(path, encoding)
            rows = csv_row_count(path, encoding)
        elif path.suffix.lower() == ".txt" and encoding != "unknown":
            rows = len(path.read_text(encoding=encoding).splitlines())

        records.append(
            {
                "file": relative_path,
                "rows": rows,
                "encoding": encoding,
                "columns": ", ".join(columns) if columns else "(not tabular)",
                "use": infer_dataset_use(relative_path),
            }
        )

    return pd.DataFrame.from_records(records)


def write_inventory_md(inventory: pd.DataFrame) -> None:
    lines = [
        "# Career Data Inventory",
        "",
        "Scope: local files currently present under `data/raw/career/`.",
        "",
        "Raw files are treated as immutable source material. The v1 career transition pipeline reads O*NET files and writes derived outputs under `data/processed/career/` and `outputs/career/`.",
        "",
        "O*NET release note: `data/raw/career/onet/Read Me.txt` identifies this as O*NET 31.0, August 2026 release, Creative Commons Attribution 4.0 International License.",
        "",
        "| File | Rows | Encoding | Columns | Use |",
        "|---|---:|---|---|---|",
    ]
    for record in inventory.to_dict("records"):
        columns = str(record["columns"]).replace("|", "\\|")
        use = str(record["use"]).replace("|", "\\|")
        lines.append(
            f"| `{record['file']}` | {record['rows']} | {record['encoding']} | {columns} | {use} |"
        )
    INVENTORY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_feasibility_method_md() -> None:
    lines = [
        "# Career Transition Feasibility v2 Method",
        "",
        "Purpose: add directional feasibility screening on top of symmetric O*NET skill similarity. This is not a transition success probability.",
        "",
        "## Inputs",
        "",
        "- Skill backbone: O*NET 31.0 `essential_skills.csv`, `transferable_skills.csv`, and `knowledge.csv`.",
        "- Feasibility constraints: `job_zones.csv`, `job_zone_reference.csv`, `education.csv`, `education_categories.csv`, `training_and_experience.csv`, and `training_and_experience_categories.csv`.",
        "- Support signal: `related_occupations.csv`, kept separate from skill similarity and feasibility labels.",
        "",
        "## Directional Skill Metrics",
        "",
        "`skill_similarity` keeps the v1 symmetric weighted cosine similarity. It uses O*NET IM scores divided by 5.0, L2-normalized within each skill type, then equally weights essential skills, transferable skills, and knowledge.",
        "",
        "For an A -> B transition, directional coverage and gap use raw O*NET IM scores on the 0-5 importance scale, not occupation-level L2-normalized vectors.",
        "",
        "Let `a_i` be source occupation A's raw IM score for feature `i`, and `b_i` be target occupation B's raw IM score. A target-required feature is included when `b_i >= 3.0`.",
        "",
        "For each skill type `t`:",
        "",
        "- `coverage_t(A -> B) = sum_i min(a_i, b_i) / sum_i b_i`, for target-required features in `t`.",
        "- `gap_t(A -> B) = mean_i max(b_i - a_i, 0)`, for target-required features in `t`.",
        "",
        "Overall directional metrics equally weight available skill types:",
        "",
        "- `transferable_skill_coverage(A -> B) = mean_t coverage_t(A -> B)`; range 0-1, higher means more of B's required profile is already covered by A.",
        "- `target_skill_gap(A -> B) = mean_t gap_t(A -> B)`; raw IM points, lower means fewer target-side missing requirements.",
        "",
        "## Feasibility Constraints",
        "",
        "- `job_zone_difference = target_job_zone - source_job_zone`; larger positive values imply more preparation than the source occupation.",
        "- `education_barrier` uses O*NET required education distributions: weighted education category, modal education category, master's-or-higher share, doctoral/professional/postdoctoral share, and professional certification importance.",
        "- `training_experience_barrier` uses modal and weighted related work experience, on-site training, on-the-job training, and apprenticeship importance.",
        "- Education and training category distributions keep the full reported percentage distribution. Category-level `Recommend Suppress` flags are not filtered because removing a single category would distort modal and weighted-category summaries.",
        "- `related_support` reports whether O*NET Related Occupations lists B from A; it does not change `skill_similarity`.",
        "- `education_barrier=unknown` means the target occupation has no O*NET `RL` required-education distribution in the local raw data; it is not treated as evidence of low barrier.",
        "",
        "## Feasibility Labels",
        "",
        "- `Adjacent candidate`: strong directional skill coverage, small skill gap, low or medium preparation barriers, and either related support or no upward job-zone move.",
        "- `Bridge candidate`: strong skill coverage with a visible but explainable education/training step, or a same-domain transition that needs additional credentials.",
        "- `Infeasible / high-barrier`: skill-similar but blocked by physician/doctoral-professional preparation, large job-zone jump, or high education/training barrier without a same-domain bridge signal.",
        "",
        "These labels are feasibility screens for exploration, not recommendations, market demand estimates, wage estimates, or success probabilities.",
    ]
    FEASIBILITY_METHOD_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_market_v3_method_md(jobs_quality: dict[str, object]) -> None:
    salary_counts = jobs_quality["salary_type_counts"]
    education_counts = jobs_quality["education_counts"]
    experience_counts = jobs_quality["experience_counts"]
    location_counts = jobs_quality["location_counts"]
    missing_counts = jobs_quality["missing_counts"]
    lines = [
        "# Career Transition Market v3 Method",
        "",
        "Purpose: add occupation taxonomy distance and TaiwanJobs market evidence to the v2 feasibility screen. This does not calculate transition success probability or a final recommendation score.",
        "",
        "## TaiwanJobs Inventory and Quality",
        "",
        f"- Raw file: `{TAIWANJOBS_OPEN_JOBS.relative_to(ROOT)}`.",
        f"- Rows: {jobs_quality['rows']}.",
        f"- Columns: {', '.join(jobs_quality['columns'])}.",
        f"- Missing values by column: {missing_counts}.",
        f"- Salary type distribution: {salary_counts}.",
        f"- Education requirement distribution: {education_counts}.",
        f"- Experience requirement distribution: {experience_counts}.",
        f"- Main locations: {location_counts}.",
        "",
        "Salary handling: `matched_job_count` and `total_demand_persons` include all matched rows. Salary medians use only rows with `SALARYCD（核薪方式） = 月薪` and parse numeric `NT_L`/`NT_U`; hourly, daily, piece-rate, and negotiated salary rows are excluded from salary medians.",
        "",
        "## Occupation Taxonomy Distance",
        "",
        "O*NET-SOC codes are parsed as `major = first two digits`, `family = first five characters such as 29-11`, and `detailed = part before the decimal such as 29-1141`.",
        "",
        "- `same_major_group`: source and target share the same two-digit SOC major group.",
        "- `same_occupation_family`: source and target share the same `XX-YY` family prefix.",
        "- `taxonomy_distance_level = Same / very close`: same detailed SOC code, same family, or O*NET Primary-Short related support.",
        "- `taxonomy_distance_level = Adjacent category`: same major group or O*NET Primary-Long/Supplemental related support.",
        "- `taxonomy_distance_level = Cross-category`: source/target cross the O*NET 29/31 healthcare practitioner/support boundary.",
        "- `taxonomy_distance_level = Distant category`: none of the above.",
        "",
        "`hidden_path_candidate` is a flag for Cross-category or Distant-category occupations that are not v2 high-barrier and are not flagged as likely downward/low-value mobility. It is not a Hidden Path label.",
        "",
        "## TaiwanJobs Mapping",
        "",
        "Mapping is deterministic and reproducible. It uses a transparent bilingual healthcare keyword lexicon by O*NET occupation pattern. The lexicon is applied to TaiwanJobs `OCCU_DESC`, `CJOB_NAME1`, `CJOB_NAME2`, and `JOB_DETAIL`.",
        "",
        "Job-level score components:",
        "",
        "- strong keyword in `OCCU_DESC`: +0.55",
        "- strong keyword in `CJOB_NAME2`: +0.45",
        "- strong keyword in `JOB_DETAIL`: +0.25",
        "- positive keyword in `OCCU_DESC`: +0.20",
        "- positive keyword in `CJOB_NAME2`: +0.18",
        "- positive keyword in `JOB_DETAIL`: +0.08",
        "- broad TaiwanJobs category match: +0.10",
        "- negative keyword in title/category/detail: subtract up to 0.35",
        "",
        "For regulated or US-specific occupations such as nurses, physicians, midwives, physician assistants, and physical therapists, a rule can require at least one strong keyword in the TaiwanJobs occupation title or small occupation category before a job is considered a match. This prevents generic healthcare detail text from becoming a forced mapping.",
        "",
        "Some rules also exclude negative title/category terms such as `獸醫`, or require a combination of keyword groups. For example, Nursing Instructor requires both a nursing term and an education/teaching term, not either term alone.",
        "",
        "The final job score is clipped to 0-1. Occupation-level `mapping_score` is the mean of the top five matched job scores. Low-confidence rows are retained for review but are not treated as strong market evidence.",
        "",
        "Mapping confidence:",
        "",
        "- `High`: score >= 0.70 and at least 2 matched jobs.",
        "- `Medium`: score >= 0.50 and at least 1 matched job.",
        "- `Low`: score >= 0.35 and at least 1 matched job.",
        "- `Unmatched`: no job above threshold.",
        "",
        "## Market Validation",
        "",
        "- `Strong`: High confidence, at least 5 matched jobs, and at least 10 total demand persons.",
        "- `Moderate`: High/Medium confidence with at least 2 matched jobs or at least 3 total demand persons.",
        "- `Weak`: Low confidence or one matched job.",
        "- `Unknown`: no reliable mapping.",
        "",
        "Market validation is a data-availability and demand-evidence label, not a recommendation score.",
    ]
    MARKET_V3_METHOD_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_onet_skill_source(path: Path, skill_type: str) -> pd.DataFrame:
    raw = pd.read_csv(path)
    raw["Data Value"] = pd.to_numeric(raw["Data Value"], errors="coerce")
    keep = (
        raw["Scale ID"].eq("IM")
        & raw["Data Value"].notna()
        & ~raw["Recommend Suppress"].fillna("").eq("Y")
    )
    result = raw.loc[
        keep,
        ["O*NET-SOC Code", "Title", "Element ID", "Element Name", "Data Value"],
    ].copy()
    result = result.rename(
        columns={
            "O*NET-SOC Code": "occupation_code",
            "Title": "occupation_name",
            "Element ID": "skill_id",
            "Element Name": "skill_name",
            "Data Value": "importance_or_score",
        }
    )
    result["skill_type"] = skill_type
    result["source"] = f"O*NET 31.0 {path.name}; Scale ID=IM"
    return result[
        [
            "occupation_code",
            "occupation_name",
            "skill_id",
            "skill_name",
            "skill_type",
            "importance_or_score",
            "source",
        ]
    ]


def build_occupation_skills() -> pd.DataFrame:
    frames = [
        load_onet_skill_source(path, skill_type)
        for skill_type, path in ONET_SKILL_SOURCES.items()
    ]
    result = pd.concat(frames, ignore_index=True)
    result = result.sort_values(
        ["occupation_code", "skill_type", "skill_id"],
        kind="stable",
    )
    result.to_csv(OCCUPATION_SKILLS_CSV, index=False, encoding="utf-8")
    return result


def build_weighted_similarity_matrix(occupation_skills: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = occupation_skills.copy()
    features["feature_id"] = features["skill_type"] + ":" + features["skill_id"]
    features["normalized_score"] = features["importance_or_score"] / 5.0

    vector_parts: list[pd.DataFrame] = []
    for skill_type, type_weight in SKILL_TYPE_WEIGHTS.items():
        part = features.loc[features["skill_type"].eq(skill_type)].copy()
        part["weighted_value"] = part["normalized_score"]
        pivot = part.pivot_table(
            index="occupation_code",
            columns="feature_id",
            values="weighted_value",
            aggfunc="max",
            fill_value=0.0,
        )
        row_norm = np.linalg.norm(pivot.to_numpy(dtype=float), axis=1)
        row_norm[row_norm == 0.0] = 1.0
        normalized = pivot.div(row_norm, axis=0) * math.sqrt(type_weight)
        vector_parts.append(normalized)

    matrix = pd.concat(vector_parts, axis=1).fillna(0.0)
    matrix = matrix.reindex(sorted(matrix.columns), axis=1)
    values = matrix.to_numpy(dtype=float)
    similarities = np.einsum("ij,kj->ik", values, values, optimize=True)
    similarity_df = pd.DataFrame(similarities, index=matrix.index, columns=matrix.index)
    return matrix, similarity_df


def category_label_lookup(path: Path, scale_id: str) -> dict[int, str]:
    categories = pd.read_csv(path, keep_default_na=False)
    filtered = categories.loc[categories["Scale ID"].eq(scale_id)]
    return {
        int(row["Category"]): str(row["Category Description"])
        for _, row in filtered.iterrows()
    }


def summarize_category_distribution(
    raw: pd.DataFrame,
    scale_id: str,
    label_lookup: dict[int, str],
    prefix: str,
) -> pd.DataFrame:
    subset = raw.loc[raw["Scale ID"].eq(scale_id)].copy()
    subset["Category"] = pd.to_numeric(subset["Category"], errors="coerce")
    subset["Data Value"] = pd.to_numeric(subset["Data Value"], errors="coerce")
    subset = subset.dropna(subset=["Category", "Data Value"])
    subset["Category"] = subset["Category"].astype(int)
    subset["Data Value"] = subset["Data Value"].astype(float)

    records: list[dict[str, object]] = []
    for (occupation_code, occupation_name), group in subset.groupby(["O*NET-SOC Code", "Title"], sort=False):
        if group.empty:
            continue
        weights = group["Data Value"].to_numpy(dtype=float)
        categories = group["Category"].to_numpy(dtype=float)
        total = float(weights.sum())
        weighted_category = float((categories * weights).sum() / total) if total else np.nan
        modal = group.sort_values(["Data Value", "Category"], ascending=[False, True]).iloc[0]
        modal_category = int(modal["Category"])
        records.append(
            {
                "occupation_code": occupation_code,
                "occupation_name": occupation_name,
                f"{prefix}_weighted_category": weighted_category,
                f"{prefix}_modal_category": modal_category,
                f"{prefix}_modal_label": label_lookup.get(modal_category, ""),
                f"{prefix}_modal_pct": float(modal["Data Value"]),
            }
        )

    return pd.DataFrame.from_records(records)


def build_occupation_feasibility_profile() -> pd.DataFrame:
    occupations = pd.read_csv(ONET_OCCUPATION_DATA).rename(
        columns={"O*NET-SOC Code": "occupation_code", "Title": "occupation_name"}
    )[["occupation_code", "occupation_name"]]

    job_zones = pd.read_csv(ONET_JOB_ZONES).rename(
        columns={"O*NET-SOC Code": "occupation_code", "Job Zone": "job_zone"}
    )[["occupation_code", "job_zone"]]
    job_zones["job_zone"] = pd.to_numeric(job_zones["job_zone"], errors="coerce")

    education = pd.read_csv(ONET_EDUCATION)
    education_labels = category_label_lookup(ONET_EDUCATION_CATEGORIES, "RL")
    education_summary = summarize_category_distribution(
        education,
        scale_id="RL",
        label_lookup=education_labels,
        prefix="education",
    )

    education_rl = education.loc[education["Scale ID"].eq("RL")].copy()
    education_rl["Category"] = pd.to_numeric(education_rl["Category"], errors="coerce")
    education_rl["Data Value"] = pd.to_numeric(education_rl["Data Value"], errors="coerce")
    education_rl = education_rl.dropna(subset=["Category", "Data Value"])
    education_rl["Category"] = education_rl["Category"].astype(int)
    education_shares = (
        education_rl.groupby("O*NET-SOC Code")
        .apply(
            lambda group: pd.Series(
                {
                    "education_bachelor_plus_share": float(group.loc[group["Category"].ge(6), "Data Value"].sum()),
                    "education_master_plus_share": float(group.loc[group["Category"].ge(8), "Data Value"].sum()),
                    "education_doctoral_professional_share": float(
                        group.loc[group["Category"].ge(10), "Data Value"].sum()
                    ),
                }
            ),
            include_groups=False,
        )
        .reset_index()
        .rename(columns={"O*NET-SOC Code": "occupation_code"})
    )

    certification = education.loc[
        education["Element ID"].eq("2.D.4.a")
        & education["Scale ID"].eq("IM")
        & ~education["Recommend Suppress"].fillna("").eq("Y")
    ].copy()
    certification["Data Value"] = pd.to_numeric(certification["Data Value"], errors="coerce")
    certification = certification.rename(
        columns={"O*NET-SOC Code": "occupation_code", "Data Value": "professional_certification_importance"}
    )[["occupation_code", "professional_certification_importance"]]

    training = pd.read_csv(ONET_TRAINING_EXPERIENCE)
    training_frames = []
    for scale_id, prefix in [
        ("RW", "related_work_experience"),
        ("PT", "on_site_training"),
        ("OJ", "on_the_job_training"),
    ]:
        training_frames.append(
            summarize_category_distribution(
                training,
                scale_id=scale_id,
                label_lookup=category_label_lookup(ONET_TRAINING_EXPERIENCE_CATEGORIES, scale_id),
                prefix=prefix,
            )
        )

    apprenticeship = training.loc[
        training["Element ID"].eq("3.A.4.a")
        & training["Scale ID"].eq("IM")
        & ~training["Recommend Suppress"].fillna("").eq("Y")
    ].copy()
    apprenticeship["Data Value"] = pd.to_numeric(apprenticeship["Data Value"], errors="coerce")
    apprenticeship = apprenticeship.rename(
        columns={"O*NET-SOC Code": "occupation_code", "Data Value": "apprenticeship_importance"}
    )[["occupation_code", "apprenticeship_importance"]]

    profile = occupations.merge(job_zones, on="occupation_code", how="left")
    profile = profile.merge(education_summary.drop(columns=["occupation_name"], errors="ignore"), on="occupation_code", how="left")
    profile = profile.merge(education_shares, on="occupation_code", how="left")
    profile = profile.merge(certification, on="occupation_code", how="left")
    for frame in training_frames:
        profile = profile.merge(frame.drop(columns=["occupation_name"], errors="ignore"), on="occupation_code", how="left")
    profile = profile.merge(apprenticeship, on="occupation_code", how="left")
    return profile


def load_taiwanjobs() -> pd.DataFrame:
    jobs = pd.read_csv(TAIWANJOBS_OPEN_JOBS, encoding="utf-8-sig", keep_default_na=False)
    for column in TAIWANJOBS_TEXT_COLUMNS:
        jobs[column] = jobs[column].fillna("").astype(str)
    jobs["JOB_PERSON（雇用人數）"] = pd.to_numeric(jobs["JOB_PERSON（雇用人數）"], errors="coerce").fillna(0)
    jobs["salary_lower_numeric"] = pd.to_numeric(
        jobs["NT_L（薪資範圍下限）"].astype(str).str.replace(",", "", regex=False).replace("-", np.nan),
        errors="coerce",
    )
    jobs["salary_upper_numeric"] = pd.to_numeric(
        jobs["NT_U（薪資範圍上限）"].astype(str).str.replace(",", "", regex=False).replace("-", np.nan),
        errors="coerce",
    )
    jobs["combined_text"] = jobs[TAIWANJOBS_TEXT_COLUMNS].agg(" ".join, axis=1)
    return jobs


def taiwanjobs_quality_summary(jobs: pd.DataFrame) -> dict[str, object]:
    raw_for_missing = pd.read_csv(TAIWANJOBS_OPEN_JOBS, encoding="utf-8-sig")
    return {
        "rows": len(jobs),
        "columns": list(jobs.columns[:19]),
        "missing_counts": raw_for_missing.isna().sum().to_dict(),
        "salary_type_counts": jobs["SALARYCD（核薪方式）"].value_counts(dropna=False).to_dict(),
        "education_counts": jobs["EDGRDESC（最低學歷要求）"].value_counts(dropna=False).to_dict(),
        "experience_counts": jobs["EXPERIENCE（工作經驗）"].value_counts(dropna=False).to_dict(),
        "location_counts": jobs["CITYNAME（工作地點）"].value_counts(dropna=False).head(10).to_dict(),
    }


def mapping_rule_for_title(title: str) -> dict[str, object]:
    title_lower = title.lower()
    rule = {
        "strong": [],
        "positive": [],
        "negative": [],
        "categories": [],
        "requires_strong": False,
        "requires_strong_title_or_category": False,
        "exclude_negative_title_or_category": False,
        "requires_all_keyword_groups": [],
        "review_reason": "",
    }

    if any(term in title_lower for term in ["health informatics", "health information", "medical records"]):
        rule.update(
            strong=["醫療資訊", "醫院資訊", "健康資訊", "病歷", "醫療登錄", "疾病登錄"],
            positive=["資訊系統", "資料", "數據", "醫療", "醫院", "健康", "病歷", "系統"],
            categories=["資訊／軟體／系統", "醫療／美容／保健", "其他醫院從業人員", "病歷"],
            review_reason="Health informatics titles may map to medical records, hospital IT, or generic nursing informatics in TaiwanJobs.",
        )
    elif any(term in title_lower for term in ["clinical data", "clinical research coordinator"]):
        rule.update(
            strong=["臨床研究", "臨床資料", "資料管理", "研究助理"],
            positive=["資料", "數據", "統計", "醫療", "臨床", "研究", "分析"],
            categories=["工程／研發／生技", "醫療／美容／保健", "資訊／軟體／系統"],
            review_reason="Clinical data roles may appear as research, data, or hospital administrative roles in TaiwanJobs.",
        )
    elif any(term in title_lower for term in ["data scientist", "data analyst", "business intelligence", "biostatistician", "statistician", "bioinformatics"]):
        rule.update(
            strong=["資料分析", "數據分析", "資料科學", "數據科學", "商業智慧", "BI", "統計", "生物資訊"],
            positive=["資料", "數據", "分析", "統計", "模型", "Python", "SQL", "機器學習", "AI"],
            categories=["資訊／軟體／系統", "工程／研發／生技", "統計精算人員", "其他資訊專業人員"],
            review_reason="Data/AI titles are mapped lexically; healthcare domain fit is not guaranteed.",
        )
    elif any(term in title_lower for term in ["software", "programmer", "web developer", "quality assurance", "interface designer"]):
        rule.update(
            strong=["軟體", "程式", "前端", "後端", "全端", "測試工程師", "QA", "網頁", "系統工程師"],
            positive=["開發", "系統", "資訊", "網站", "程式", "測試", "軟體", "工程師"],
            categories=["資訊／軟體／系統", "軟(韌)體設計工程師", "MIS程式設計師", "其他資訊專業人員"],
        )
    elif any(term in title_lower for term in ["computer systems", "information systems", "database", "network", "information security", "cybersecurity", "penetration tester", "user support", "it project"]):
        rule.update(
            strong=["系統工程師", "資訊系統", "資料庫", "網路管理", "資安", "資訊安全", "MIS", "IT", "技術支援"],
            positive=["資訊", "系統", "資料庫", "網路", "資安", "維運", "支援", "工程師"],
            categories=["資訊／軟體／系統", "網路管理工程師", "資訊設備管制人員", "其他資訊專業人員"],
        )
    elif any(term in title_lower for term in ["biomedical", "medical equipment", "medical device"]):
        rule.update(
            strong=["醫療器材", "醫材", "醫療設備", "生醫", "醫工", "設備維修"],
            positive=["醫療", "設備", "器材", "維修", "生技", "產品", "技術", "工程師"],
            categories=["工程／研發／生技", "技術／維修／操作", "其他產品維修人員", "醫療／美容／保健"],
            review_reason="Medical device and biomedical roles may map to engineering, product, repair, or sales positions in TaiwanJobs.",
        )
    elif "midwi" in title_lower:
        rule.update(
            strong=["助產", "助產師", "產房"],
            positive=["婦產", "孕", "生產", "護理"],
            categories=["醫療／美容／保健"],
            requires_strong=True,
            requires_strong_title_or_category=True,
        )
    elif "licensed practical" in title_lower:
        rule.update(
            strong=["護理師", "護士"],
            positive=["護理", "照護", "病患", "長照"],
            categories=["護理師/護士", "醫療／美容／保健"],
            requires_strong=True,
            requires_strong_title_or_category=True,
            review_reason="TaiwanJobs does not clearly separate LPN/LVN from Taiwan nursing titles.",
        )
    elif "nurs" in title_lower and "assistant" not in title_lower and "instructor" not in title_lower:
        rule.update(
            strong=["護理師", "護士"],
            positive=["護理", "照護", "病患", "臨床", "長照"],
            categories=["護理師/護士", "醫療／美容／保健"],
            requires_strong=True,
            requires_strong_title_or_category=True,
        )
        if any(token in title_lower for token in ["practitioner", "specialist", "anesthetist", "advanced"]):
            rule["review_reason"] = "Advanced nursing titles may map to generic Taiwan nursing jobs in this sample."
    elif "nursing assistant" in title_lower:
        rule.update(
            strong=["照顧服務員", "照服員", "看護", "護理助理"],
            positive=["長照", "照顧", "照護", "生活照顧", "病患"],
            categories=["照顧服務員", "醫療／美容／保健"],
        )
    elif "medical assistant" in title_lower:
        rule.update(
            strong=["診所助理", "醫務助理", "醫療助理", "醫院診所掛號員", "其他醫院從業人員"],
            positive=["掛號", "診所", "醫院", "櫃檯", "病歷", "醫療"],
            negative=["獸醫"],
            exclude_negative_title_or_category=True,
            categories=["診所助理", "醫院診所掛號員", "其他醫院從業人員", "醫療／美容／保健"],
        )
    elif "athletic trainer" in title_lower:
        rule.update(
            strong=["運動防護", "防護員", "運動防護員"],
            positive=["運動", "健身", "教練", "復健", "健康促進"],
            negative=["櫃檯", "行政", "客服", "門市", "救生員"],
            categories=["醫療／美容／保健", "旅遊／餐飲／休閒"],
            review_reason="Athletic Trainer is a US-specific credential; TaiwanJobs matches may be sports/fitness rather than clinical athletic training.",
        )
    elif "exercise physiologist" in title_lower:
        rule.update(
            strong=["運動生理", "運動生理學"],
            positive=["運動", "健身", "體適能", "教練", "健康促進", "復健"],
            negative=["櫃檯", "行政", "客服", "門市", "救生員"],
            categories=["醫療／美容／保健", "旅遊／餐飲／休閒"],
            review_reason="Exercise Physiologist does not appear as a stable TaiwanJobs occupation title in this sample.",
        )
    elif "physical therapist" in title_lower:
        rule.update(
            strong=["物理治療師", "物理治療"],
            positive=["復健", "治療", "運動治療"],
            categories=["醫療／美容／保健"],
            requires_strong=True,
            requires_strong_title_or_category=True,
        )
    elif "paramedic" in title_lower or "emergency medical technician" in title_lower:
        rule.update(
            strong=["救護技術員", "救護員", "EMT"],
            positive=["急救", "救護", "消防", "緊急醫療"],
            categories=["保全／軍警消", "醫療／美容／保健"],
        )
    elif "instructor" in title_lower and "nursing" in title_lower:
        rule.update(
            strong=["護理講師", "護理教師", "護理師資"],
            positive=["護理", "教師", "講師", "教學", "教育"],
            categories=["教育／學術／研究", "醫療／美容／保健"],
            requires_all_keyword_groups=[["護理"], ["教師", "講師", "教學", "教育", "師資"]],
            review_reason="Nursing instructor demand may be listed under schools or hospitals with inconsistent titles.",
        )
    elif "physician assistant" in title_lower:
        rule.update(
            strong=["醫師助理", "專科護理師"],
            positive=["醫師", "診所", "醫療", "護理"],
            negative=["獸醫", "中醫師"],
            categories=["醫療／美容／保健"],
            requires_strong=True,
            requires_strong_title_or_category=True,
            exclude_negative_title_or_category=True,
            review_reason="Physician Assistant is not a direct Taiwan occupation equivalent; manual review required.",
        )
    elif is_physician_like(title):
        rule.update(
            strong=["醫師"],
            positive=["醫療", "診所", "看診", "病患"],
            negative=["獸醫"],
            categories=["醫師", "中醫師", "醫療／美容／保健"],
            requires_strong=True,
            requires_strong_title_or_category=True,
            exclude_negative_title_or_category=True,
            review_reason="Specialist physician titles may map only to generic physician postings in this sample.",
        )
    elif "neuropsychologist" in title_lower:
        rule.update(
            strong=["神經心理", "臨床心理師", "心理師"],
            positive=["心理", "諮商", "治療"],
            categories=["醫療／美容／保健", "教育／學術／研究"],
        )
    else:
        healthcare_terms = ["醫療", "照護", "病患", "服務", "健康"]
        rule.update(
            strong=[],
            positive=healthcare_terms,
            categories=["醫療／美容／保健"],
            review_reason="Generic healthcare lexical fallback; manual review required.",
        )

    return rule


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword and keyword in text for keyword in keywords)


def score_job_against_rule(job: pd.Series, rule: dict[str, object]) -> float:
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

    if rule.get("exclude_negative_title_or_category") and (
        contains_any(title, negative) or contains_any(cjob2, negative)
    ):
        return 0.0
    for keyword_group in rule.get("requires_all_keyword_groups", []):
        if not contains_any(all_text, list(keyword_group)):
            return 0.0
    strong_title_or_category_hit = contains_any(title, strong) or contains_any(cjob2, strong)
    strong_hit = strong_title_or_category_hit or contains_any(detail, strong)
    if rule.get("requires_strong_title_or_category") and not strong_title_or_category_hit:
        return 0.0
    if rule.get("requires_strong") and not strong_hit:
        return 0.0

    score = 0.0
    if contains_any(title, strong):
        score += 0.55
    if contains_any(cjob2, strong):
        score += 0.45
    if contains_any(detail, strong):
        score += 0.25

    title_hits = sum(1 for keyword in positive if keyword in title)
    cjob_hits = sum(1 for keyword in positive if keyword in cjob2)
    detail_hits = sum(1 for keyword in positive if keyword in detail)
    score += min(title_hits * 0.20, 0.30)
    score += min(cjob_hits * 0.18, 0.25)
    score += min(detail_hits * 0.08, 0.25)

    if contains_any(cjob1, categories) or contains_any(cjob2, categories):
        score += 0.10

    if contains_any(title, negative) or contains_any(cjob2, negative):
        score -= 0.35
    elif contains_any(detail, negative):
        score -= 0.15

    return round(float(min(max(score, 0.0), 1.0)), 6)


def mapping_confidence(mapping_score: float, matched_job_count: int, review_reason: str) -> str:
    if matched_job_count == 0:
        return "Unmatched"
    if mapping_score >= 0.70 and matched_job_count >= 2 and not review_reason:
        return "High"
    if mapping_score >= 0.50:
        return "Medium"
    if mapping_score >= 0.35:
        return "Low"
    return "Unmatched"


def summarize_market_for_matches(matches: pd.DataFrame) -> dict[str, object]:
    if matches.empty:
        return {
            "matched_job_count": 0,
            "total_demand_persons": 0,
            "salary_lower_median": "",
            "salary_upper_median": "",
            "salary_basis": "monthly_only_no_matched_monthly_salary",
            "education_requirement_distribution": "",
            "experience_requirement_distribution": "",
            "main_job_locations": "",
        }

    monthly = matches.loc[matches["SALARYCD（核薪方式）"].eq("月薪")]
    salary_lower = monthly["salary_lower_numeric"].dropna()
    salary_upper = monthly["salary_upper_numeric"].dropna()
    return {
        "matched_job_count": int(len(matches)),
        "total_demand_persons": int(matches["JOB_PERSON（雇用人數）"].sum()),
        "salary_lower_median": "" if salary_lower.empty else int(round(float(salary_lower.median()))),
        "salary_upper_median": "" if salary_upper.empty else int(round(float(salary_upper.median()))),
        "salary_basis": "monthly_only_excludes_hourly_daily_piece_and_negotiated",
        "education_requirement_distribution": "; ".join(
            f"{k}:{v}" for k, v in matches["EDGRDESC（最低學歷要求）"].value_counts().head(8).to_dict().items()
        ),
        "experience_requirement_distribution": "; ".join(
            f"{k}:{v}" for k, v in matches["EXPERIENCE（工作經驗）"].value_counts().head(8).to_dict().items()
        ),
        "main_job_locations": "; ".join(
            f"{k}:{v}" for k, v in matches["CITYNAME（工作地點）"].value_counts().head(8).to_dict().items()
        ),
    }


def build_onet_taiwanjobs_mapping(
    candidates: pd.DataFrame,
    output_path: Path | None = ONET_TAIWANJOBS_MAPPING_CSV,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    jobs = load_taiwanjobs()
    match_frames: dict[str, pd.DataFrame] = {}
    records: list[dict[str, object]] = []
    for _, candidate in candidates.iterrows():
        code = str(candidate["target_occupation_code"])
        title = str(candidate["target_occupation_name"])
        rule = mapping_rule_for_title(title)
        scored = jobs.copy()
        scored["job_match_score"] = scored.apply(lambda row: score_job_against_rule(row, rule), axis=1)
        matches = scored.loc[scored["job_match_score"].ge(0.35)].sort_values(
            "job_match_score",
            ascending=False,
        )
        top_scores = matches["job_match_score"].head(5)
        mapping_score = round(float(top_scores.mean()), 6) if not top_scores.empty else 0.0
        confidence = mapping_confidence(mapping_score, len(matches), str(rule["review_reason"]))
        manual_review_needed = confidence != "High" or bool(rule["review_reason"])
        market = summarize_market_for_matches(matches)

        matched_titles = "; ".join(matches["OCCU_DESC（職務名稱）"].drop_duplicates().head(8).tolist())
        matched_categories = "; ".join(matches["CJOB_NAME2（職務小類別名稱）"].drop_duplicates().head(6).tolist())
        records.append(
            {
                "onet_occupation_code": code,
                "onet_occupation": title,
                "taiwanjobs_occupation": matched_categories,
                "matched_titles": matched_titles,
                "mapping_method": "deterministic_keyword_field_weight_v1",
                "mapping_score": mapping_score,
                "mapping_confidence": confidence,
                "manual_review_needed": "yes" if manual_review_needed else "no",
                "mapping_review_reason": rule["review_reason"],
                "mapping_keywords": "; ".join(list(rule["strong"]) + list(rule["positive"])),
                **market,
            }
        )
        match_frames[code] = matches

    mapping = pd.DataFrame.from_records(records).sort_values(
        ["mapping_confidence", "mapping_score", "matched_job_count"],
        ascending=[True, False, False],
    )
    if output_path is not None:
        mapping.to_csv(output_path, index=False, encoding="utf-8")
    return mapping, match_frames


def soc_parts(code: str) -> dict[str, str]:
    code = str(code)
    return {
        "major": code[:2],
        "family": code[:5],
        "detailed": code.split(".")[0],
    }


def taxonomy_distance(source_code: str, target_code: str, related_support: str, related_tier: str) -> tuple[str, str, str]:
    source = soc_parts(source_code)
    target = soc_parts(target_code)
    same_major = source["major"] == target["major"]
    same_family = source["family"] == target["family"]

    if source["detailed"] == target["detailed"] or same_family or related_tier == "Primary-Short":
        level = "Same / very close"
    elif same_major or related_tier in {"Primary-Long", "Supplemental"}:
        level = "Adjacent category"
    elif {source["major"], target["major"]}.issubset(HEALTHCARE_MAJOR_GROUPS):
        level = "Cross-category"
    else:
        level = "Distant category"

    return "yes" if same_major else "no", "yes" if same_family else "no", level


def market_validation_level(mapping: pd.Series) -> str:
    confidence = str(mapping["mapping_confidence"])
    matched_job_count = int(mapping["matched_job_count"])
    total_demand = int(mapping["total_demand_persons"])
    if confidence == "High" and matched_job_count >= 5 and total_demand >= 10:
        return "Strong"
    if confidence in {"High", "Medium"} and (matched_job_count >= 2 or total_demand >= 3):
        return "Moderate"
    if confidence == "Low" or matched_job_count == 1:
        return "Weak"
    return "Unknown"


def mobility_value_signal(row: pd.Series, source_salary_lower_median: object) -> str:
    target_zone = row.get("target_job_zone", "")
    source_zone = row.get("source_job_zone", "")
    try:
        zone_diff = int(target_zone) - int(source_zone)
    except (TypeError, ValueError):
        zone_diff = 0

    target_salary = row.get("salary_lower_median", "")
    if pd.isna(target_salary) or target_salary == "" or source_salary_lower_median == "":
        salary_signal = "unknown_salary"
    elif float(target_salary) < float(source_salary_lower_median) * 0.9:
        salary_signal = "lower_salary"
    elif float(target_salary) > float(source_salary_lower_median) * 1.1:
        salary_signal = "higher_salary"
    else:
        salary_signal = "similar_salary"

    if zone_diff < 0 or salary_signal == "lower_salary":
        return f"possible_downward_or_low_value_mobility:{salary_signal}; job_zone_diff {zone_diff}"
    if zone_diff > 0:
        return f"upward_or_credentialed_bridge:{salary_signal}; job_zone_diff {zone_diff}"
    return f"lateral_or_unclear:{salary_signal}; job_zone_diff {zone_diff}"


def nursing_market_v3(nursing_v2: pd.DataFrame) -> pd.DataFrame:
    jobs = load_taiwanjobs()
    jobs_quality = taiwanjobs_quality_summary(jobs)
    write_market_v3_method_md(jobs_quality)

    source_candidate = pd.DataFrame(
        [
            {
                "target_occupation_code": NURSING_CODE,
                "target_occupation_name": "Registered Nurses",
            }
        ]
    )
    mapping_candidates = pd.concat(
        [source_candidate, nursing_v2[["target_occupation_code", "target_occupation_name"]]],
        ignore_index=True,
    ).drop_duplicates("target_occupation_code")
    mapping, _ = build_onet_taiwanjobs_mapping(mapping_candidates)
    mapping_lookup = mapping.set_index("onet_occupation_code")
    source_mapping = mapping_lookup.loc[NURSING_CODE]
    source_salary_lower = source_mapping["salary_lower_median"]

    records: list[dict[str, object]] = []
    for _, row in nursing_v2.iterrows():
        target_code = str(row["target_occupation_code"])
        mapping_row = mapping_lookup.loc[target_code]
        same_major, same_family, taxonomy_level = taxonomy_distance(
            NURSING_CODE,
            target_code,
            str(row["related_support"]),
            str(row["related_tier"]),
        )
        market_validation = market_validation_level(mapping_row)
        record = {
            **row.to_dict(),
            "same_major_group": same_major,
            "same_occupation_family": same_family,
            "onet_related_support": row["related_support"],
            "taxonomy_distance_level": taxonomy_level,
            "taiwanjobs_occupation": mapping_row["taiwanjobs_occupation"],
            "matched_titles": mapping_row["matched_titles"],
            "mapping_method": mapping_row["mapping_method"],
            "mapping_score": mapping_row["mapping_score"],
            "mapping_confidence": mapping_row["mapping_confidence"],
            "manual_review_needed": mapping_row["manual_review_needed"],
            "matched_job_count": mapping_row["matched_job_count"],
            "total_demand_persons": mapping_row["total_demand_persons"],
            "salary_lower_median": mapping_row["salary_lower_median"],
            "salary_upper_median": mapping_row["salary_upper_median"],
            "salary_basis": mapping_row["salary_basis"],
            "education_requirement_distribution": mapping_row["education_requirement_distribution"],
            "experience_requirement_distribution": mapping_row["experience_requirement_distribution"],
            "main_job_locations": mapping_row["main_job_locations"],
            "market_validation": market_validation,
        }
        record["mobility_value_signal"] = mobility_value_signal(pd.Series(record), source_salary_lower)
        hidden_candidate = (
            taxonomy_level in {"Cross-category", "Distant category"}
            and row["feasibility_level"] != "Infeasible / high-barrier"
            and not str(record["mobility_value_signal"]).startswith("possible_downward_or_low_value_mobility")
        )
        record["hidden_path_candidate"] = "yes" if hidden_candidate else "no"
        records.append(record)

    result = pd.DataFrame.from_records(records)
    result.to_csv(NURSING_MARKET_V3_CSV, index=False, encoding="utf-8")
    write_nursing_market_v3_md(result, source_mapping)
    return result


def write_nursing_market_v3_md(result: pd.DataFrame, source_mapping: pd.Series) -> None:
    focus_names = [
        "Medical Assistants",
        "Nursing Assistants",
        "Athletic Trainers",
        "Exercise Physiologists",
        "Nursing Instructors and Teachers, Postsecondary",
        "Physician Assistants",
    ]
    focus = result.loc[result["target_occupation_name"].isin(focus_names)]
    market_counts = result["market_validation"].value_counts().to_dict()

    lines = [
        "# Nursing Career Transition Market v3",
        "",
        "Source occupation: O*NET `29-1141.00` Registered Nurses.",
        "",
        "This view keeps three separate dimensions: Feasibility, Market Opportunity, and Obviousness / Taxonomy Distance. It does not calculate a final recommendation score or transition success probability.",
        "",
        "## Source Market Baseline",
        "",
        f"- Registered Nurses mapping confidence: {source_mapping['mapping_confidence']}.",
        f"- Matched TaiwanJobs rows: {source_mapping['matched_job_count']}; total demand persons: {source_mapping['total_demand_persons']}.",
        f"- Monthly salary lower median: {source_mapping['salary_lower_median']}; upper median: {source_mapping['salary_upper_median']}.",
        "",
        "## Market Validation Counts",
        "",
        f"- Strong: {market_counts.get('Strong', 0)}",
        f"- Moderate: {market_counts.get('Moderate', 0)}",
        f"- Weak: {market_counts.get('Weak', 0)}",
        f"- Unknown: {market_counts.get('Unknown', 0)}",
        "",
        "## Candidate View",
        "",
        "| Occupation | Feasibility | Market | Taxonomy Distance | Hidden Candidate | Jobs | Demand | Monthly Salary Median | Mapping Confidence | Mobility Signal |",
        "|---|---|---|---|---|---:|---:|---|---|---|",
    ]
    for record in result.head(31).to_dict("records"):
        salary = f"{record['salary_lower_median']}-{record['salary_upper_median']}" if record["salary_lower_median"] != "" else "n/a"
        lines.append(
            "| `{target_occupation_code}` {target_occupation_name} | {feasibility_level} | {market_validation} | {taxonomy_distance_level} | {hidden_path_candidate} | {matched_job_count} | {total_demand_persons} | {salary} | {mapping_confidence} | {mobility} |".format(
                target_occupation_code=record["target_occupation_code"],
                target_occupation_name=record["target_occupation_name"],
                feasibility_level=record["feasibility_level"],
                market_validation=record["market_validation"],
                taxonomy_distance_level=record["taxonomy_distance_level"],
                hidden_path_candidate=record["hidden_path_candidate"],
                matched_job_count=record["matched_job_count"],
                total_demand_persons=record["total_demand_persons"],
                salary=salary,
                mapping_confidence=record["mapping_confidence"],
                mobility=str(record["mobility_value_signal"]).replace("|", "\\|"),
            )
        )

    lines.extend(
        [
            "",
            "## Required Candidate Checks",
            "",
            "| Occupation | Feasibility | Market | Taxonomy | Mapping | Interpretation |",
            "|---|---|---|---|---|---|",
        ]
    )
    for record in focus.to_dict("records"):
        interpretation = interpret_focus_candidate(record)
        lines.append(
            "| `{target_occupation_code}` {target_occupation_name} | {feasibility_level} | {market_validation} | {taxonomy_distance_level} | {mapping_confidence} | {interpretation} |".format(
                target_occupation_code=record["target_occupation_code"],
                target_occupation_name=record["target_occupation_name"],
                feasibility_level=record["feasibility_level"],
                market_validation=record["market_validation"],
                taxonomy_distance_level=record["taxonomy_distance_level"],
                mapping_confidence=record["mapping_confidence"],
                interpretation=interpretation.replace("|", "\\|"),
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- High feasibility does not imply attractive mobility. Medical Assistants and Nursing Assistants are structurally easy to map but may be downward or low-value moves from Registered Nurses because they are lower job-zone support roles.",
            "- Bridge candidates with some Taiwan market signal remain worth studying, especially Athletic Trainers and Exercise Physiologists, but both require manual validation because TaiwanJobs titles do not cleanly match the O*NET occupations.",
            "- Physician specialties remain high-barrier despite visible market postings for generic physician roles.",
            "- Hidden path is not assigned; `hidden_path_candidate` only marks non-obvious taxonomy distance for later validation.",
        ]
    )
    NURSING_MARKET_V3_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def interpret_focus_candidate(record: dict[str, object]) -> str:
    title = str(record["target_occupation_name"])
    if title in {"Medical Assistants", "Nursing Assistants"}:
        return "Feasible and market-visible, but likely downward or low-value mobility from RN due to lower support-role job zone."
    if title in {"Athletic Trainers", "Exercise Physiologists"}:
        return "Non-obvious bridge candidate; market signal is keyword-based and needs Taiwan occupation-title validation."
    if title == "Nursing Instructors and Teachers, Postsecondary":
        return "Same-domain bridge, but market evidence is weak in this TaiwanJobs sample and education barrier is high."
    if title == "Physician Assistants":
        return "Bridge in O*NET, but Taiwan mapping is difficult because Physician Assistant is not a direct local occupation equivalent."
    return "Needs manual review."


def target_domain_terms() -> dict[str, list[str]]:
    return {
        "strong": [
            "health informatics",
            "clinical informatics",
            "health information",
            "medical records",
            "clinical data",
            "electronic medical",
            "electronic health",
            "bioinformatics",
            "biostatistics",
            "data science",
            "data scientist",
            "machine learning",
            "artificial intelligence",
            "software developer",
            "computer systems",
            "information systems",
            "database",
            "cybersecurity",
            "medical equipment",
            "medical device",
            "biomedical engineer",
            "technical support",
            "user support",
        ],
        "technology": [
            "analytics",
            "analysis",
            "algorithm",
            "computer",
            "data",
            "database",
            "digital",
            "information",
            "network",
            "programming",
            "security",
            "software",
            "statistical",
            "statistics",
            "systems",
            "technology",
            "technologies",
            "web",
            "product",
            "support",
        ],
        "healthcare": [
            "biomedical",
            "clinical",
            "device",
            "health",
            "healthcare",
            "hospital",
            "medical",
            "medicine",
            "nursing",
            "patient",
            "records",
        ],
    }


def lower_text(value: object) -> str:
    return str(value or "").lower()


def hit_terms(text: str, terms: list[str]) -> list[str]:
    lowered = lower_text(text)
    return [term for term in terms if term.lower() in lowered]


def target_domain_primary_signal(row: pd.Series, score_info: dict[str, object]) -> str:
    major = soc_parts(row["occupation_code"])["major"]
    title_text = lower_text(row["occupation_name"])
    title_description_text = lower_text(
        " ".join(
            [
                str(row["occupation_name"]),
                str(row["occupation_description"]),
            ]
        )
    )
    explicit_health_tech_terms = [
        "health informatics",
        "clinical informatics",
        "health information",
        "clinical data",
        "bioinformatics",
        "biostatistics",
        "electronic medical",
        "medical equipment",
        "medical device",
        "biomedical",
        "bioengineer",
    ]
    technical_science_title_terms = [
        "biomedical",
        "bioengineer",
        "medical equipment",
        "medical device",
        "robotics",
        "nanotechnology",
        "radio frequency identification",
        "human factors",
    ]
    core_technology_title_terms = [
        "computer",
        "software",
        "database",
        "data scientist",
        "information security",
        "network",
        "programmer",
        "web",
        "digital",
        "systems analyst",
        "systems engineer",
        "bioinformatics",
        "biostatistician",
    ]
    if major == "15":
        return "core_technology_soc"
    if any(term in title_text for term in core_technology_title_terms):
        return "technology_title"
    if "medical records" in title_description_text:
        return "explicit_health_technology"
    if any(term in title_description_text for term in explicit_health_tech_terms):
        return "explicit_health_technology"
    if (
        soc_parts(row["occupation_code"])["major"] in {"17", "19"}
        and any(term in title_text for term in technical_science_title_terms)
    ):
        return "technical_science_engineering"
    if score_info["target_domain_strong_hits"]:
        return "weak_or_software_only_signal"
    return "weak_keyword_signal"


def aggregate_onet_candidate_corpus(occupation_skills: pd.DataFrame) -> pd.DataFrame:
    occupations = pd.read_csv(ONET_OCCUPATION_DATA).rename(
        columns={"O*NET-SOC Code": "occupation_code", "Title": "occupation_name"}
    )
    tasks = pd.read_csv(RAW_ONET / "task_statements.csv")
    task_text = (
        tasks.sort_values(["O*NET-SOC Code", "Task Type"])
        .groupby("O*NET-SOC Code")["Task"]
        .apply(lambda values: " ".join(values.dropna().astype(str).head(25)))
        .to_dict()
    )

    skills = occupation_skills.loc[occupation_skills["importance_or_score"].ge(REQUIRED_SKILL_THRESHOLD)].copy()
    skill_text = (
        skills.groupby("occupation_code")["skill_name"]
        .apply(lambda values: " ".join(sorted(set(values.dropna().astype(str)))))
        .to_dict()
    )

    software = pd.read_csv(RAW_ONET / "software_skills.csv")
    software["software_text"] = software["Element Name"].fillna("") + " " + software["Workplace Example"].fillna("")
    software_text = (
        software.groupby("O*NET-SOC Code")["software_text"]
        .apply(lambda values: " ".join(values.astype(str).head(50)))
        .to_dict()
    )
    hot_software_count = (
        software.loc[software["Hot Technology"].eq("Y")]
        .groupby("O*NET-SOC Code")
        .size()
        .to_dict()
    )
    demand_software_count = (
        software.loc[software["In Demand"].eq("Y")]
        .groupby("O*NET-SOC Code")
        .size()
        .to_dict()
    )

    corpus = occupations[["occupation_code", "occupation_name", "Description"]].copy()
    corpus = corpus.rename(columns={"Description": "occupation_description"})
    corpus["tasks_text"] = corpus["occupation_code"].map(task_text).fillna("")
    corpus["skill_knowledge_text"] = corpus["occupation_code"].map(skill_text).fillna("")
    corpus["software_text"] = corpus["occupation_code"].map(software_text).fillna("")
    corpus["hot_technology_count"] = corpus["occupation_code"].map(hot_software_count).fillna(0).astype(int)
    corpus["in_demand_software_count"] = corpus["occupation_code"].map(demand_software_count).fillna(0).astype(int)
    return corpus


def concept_tags_for_candidate(text: str, major: str) -> str:
    lowered = lower_text(text)
    tags: list[str] = []
    if any(term in lowered for term in ["health informatics", "clinical informatics", "health information", "medical records", "electronic medical"]):
        tags.append("clinical_health_informatics")
    if any(term in lowered for term in ["clinical data", "bioinformatics", "biostatistics", "statistics", "data scientist"]):
        tags.append("health_data")
    if any(term in lowered for term in ["software", "web", "programming", "developer", "interface"]):
        tags.append("software_application")
    if any(term in lowered for term in ["machine learning", "artificial intelligence", "data science", "algorithm"]):
        tags.append("ai_data")
    if any(term in lowered for term in ["medical equipment", "medical device", "biomedical", "bioengineer"]):
        tags.append("medical_device_technology")
    if any(term in lowered for term in ["user support", "technical support", "network", "systems administrator"]):
        tags.append("technology_support")
    if major == "15":
        tags.append("core_technology")
    return "; ".join(dict.fromkeys(tags))


def target_domain_retrieval_score(row: pd.Series, terms: dict[str, list[str]]) -> dict[str, object]:
    fields = {
        "title": row["occupation_name"],
        "description": row["occupation_description"],
        "tasks": row["tasks_text"],
        "skill_knowledge": row["skill_knowledge_text"],
        "software": row["software_text"],
    }
    field_weights = {
        "title": 5.0,
        "description": 3.0,
        "tasks": 1.5,
        "skill_knowledge": 1.0,
        "software": 1.0,
    }
    strong_hits: list[str] = []
    technology_hits: list[str] = []
    healthcare_hits: list[str] = []
    score = 0.0
    evidence_parts: list[str] = []

    for field_name, text in fields.items():
        strong = hit_terms(text, terms["strong"])
        tech = hit_terms(text, terms["technology"])
        health = hit_terms(text, terms["healthcare"])
        weight = field_weights[field_name]
        score += len(strong) * weight * 2.0
        score += len(tech) * weight
        score += len(health) * weight * 0.8
        if strong or tech or health:
            evidence_parts.append(
                f"{field_name}: strong={','.join(strong[:6])}; tech={','.join(tech[:6])}; health={','.join(health[:6])}"
            )
        strong_hits.extend(strong)
        technology_hits.extend(tech)
        healthcare_hits.extend(health)

    major = soc_parts(row["occupation_code"])["major"]
    if major == "15":
        score += 8.0
    elif major in {"17", "19"} and len(set(technology_hits)) >= 2:
        score += 3.0
    elif major in {"29", "31"} and len(set(technology_hits)) >= 2 and len(set(healthcare_hits)) >= 1:
        score += 4.0
    if len(set(technology_hits)) >= 2 and len(set(healthcare_hits)) >= 2:
        score += 6.0

    all_text = " ".join(str(fields[field]) for field in fields)
    return {
        "target_domain_retrieval_score": round(float(score), 3),
        "target_domain_strong_hits": "; ".join(sorted(set(strong_hits))),
        "target_domain_technology_hits": "; ".join(sorted(set(technology_hits))),
        "target_domain_healthcare_hits": "; ".join(sorted(set(healthcare_hits))),
        "target_domain_concept_tags": concept_tags_for_candidate(all_text, major),
        "candidate_generation_evidence": " | ".join(evidence_parts[:5]),
    }


def generate_target_domain_candidates(
    occupation_skills: pd.DataFrame,
    source_occupation_code: str,
    target_domain: str,
    max_candidates: int = 50,
) -> pd.DataFrame:
    if target_domain != TECH_AI_DOMAIN:
        raise ValueError(f"Unsupported target_domain for v3.5: {target_domain}")

    corpus = aggregate_onet_candidate_corpus(occupation_skills)
    terms = target_domain_terms()
    scored_records: list[dict[str, object]] = []
    for _, row in corpus.iterrows():
        if row["occupation_code"] == source_occupation_code:
            continue
        score_info = target_domain_retrieval_score(row, terms)
        if score_info["target_domain_retrieval_score"] <= 0:
            continue
        major = soc_parts(row["occupation_code"])["major"]
        primary_signal = target_domain_primary_signal(row, score_info)
        tech_hit_count = len(str(score_info["target_domain_technology_hits"]).split("; ")) if score_info["target_domain_technology_hits"] else 0
        health_hit_count = len(str(score_info["target_domain_healthcare_hits"]).split("; ")) if score_info["target_domain_healthcare_hits"] else 0
        include = (
            primary_signal
            in {
                "core_technology_soc",
                "technology_title",
                "explicit_health_technology",
                "technical_science_engineering",
            }
            and (
                score_info["target_domain_retrieval_score"] >= 38.0
                or major == "15"
                or (health_hit_count >= 1 and tech_hit_count >= 2)
            )
        )
        if include:
            scored_records.append(
                {
                    "source_occupation_code": source_occupation_code,
                    "source_occupation_name": "Registered Nurses",
                    "target_domain": target_domain,
                    "target_occupation_code": row["occupation_code"],
                    "target_occupation_name": row["occupation_name"],
                    "target_occupation_description": row["occupation_description"],
                    "candidate_generation_method": "deterministic_onet_target_domain_keyword_retrieval_v1",
                    "target_domain_primary_signal": primary_signal,
                    **score_info,
                }
            )

    scored = pd.DataFrame.from_records(scored_records)
    if scored.empty:
        return scored

    health_tech = scored.loc[
        scored["target_domain_primary_signal"].isin({"explicit_health_technology", "technical_science_engineering"})
    ].sort_values("target_domain_retrieval_score", ascending=False).head(25)
    core_tech = scored.loc[
        scored["target_domain_primary_signal"].isin({"core_technology_soc", "technology_title"})
    ].sort_values("target_domain_retrieval_score", ascending=False).head(25)
    strong = scored.loc[
        scored["target_domain_strong_hits"].ne("")
    ].sort_values("target_domain_retrieval_score", ascending=False).head(25)

    candidates = pd.concat([health_tech, core_tech, strong], ignore_index=True).drop_duplicates("target_occupation_code")
    candidates = candidates.sort_values("target_domain_retrieval_score", ascending=False).head(max_candidates).copy()
    candidates.insert(0, "candidate_generation_rank", range(1, len(candidates) + 1))
    return candidates


def technology_specific_metrics(
    source_vector: pd.Series,
    target_vector: pd.Series,
    feature_meta: dict[str, dict[str, str]],
) -> tuple[float, float]:
    tech_features = [
        feature_id
        for feature_id, meta in feature_meta.items()
        if any(term.lower() in meta["skill_name"].lower() for term in TECH_SPECIFIC_FEATURE_TERMS)
    ]
    target_required = target_vector.loc[tech_features]
    target_required = target_required.loc[target_required.ge(REQUIRED_SKILL_THRESHOLD)]
    if target_required.empty:
        return 1.0, 0.0
    source_required = source_vector.reindex(target_required.index).fillna(0.0)
    covered = np.minimum(source_required.to_numpy(dtype=float), target_required.to_numpy(dtype=float))
    target_values = target_required.to_numpy(dtype=float)
    coverage = float(covered.sum() / target_values.sum()) if target_values.sum() else 0.0
    gap = float(np.maximum(target_values - source_required.to_numpy(dtype=float), 0.0).mean())
    return coverage, gap


def transition_span(coverage: float, gap: float, technology_gap: float) -> str:
    if coverage >= 0.85 and gap <= 0.45 and technology_gap <= 0.50:
        return "High skill reuse"
    if coverage >= 0.65 and gap <= 0.90 and technology_gap <= 1.50:
        return "Partial skill reuse"
    return "Major reskilling"


def classify_target_domain_feasibility(
    target_title: str,
    target_profile: pd.Series,
    row: dict[str, object],
) -> tuple[str, str, str]:
    target_doctoral = float(target_profile.get("education_doctoral_professional_share", 0.0) or 0.0)
    job_zone_difference = row["job_zone_difference"]
    education = str(row["education_barrier"])
    training = str(row["training_experience_barrier"])
    credential = str(row["credential_barrier"])
    span = str(row["transition_span"])

    if (
        is_physician_like(target_title)
        or target_doctoral >= 35.0
        or job_zone_difference >= 2
        or (credential == "high" and education == "high")
    ):
        return (
            "exclude",
            "Infeasible / high-barrier",
            "Target-domain candidate, but education/credential/preparation barrier is too high for this exploratory screen.",
        )
    if span == "High skill reuse" and education in {"low", "medium", "unknown"} and training in {"low", "medium"}:
        return (
            "candidate",
            "Adjacent candidate",
            "Target-domain candidate with high nursing skill reuse and no exclusionary preparation barrier.",
        )
    return (
        "review",
        "Bridge candidate",
        "Target-domain candidate that needs further validation; skill reuse may be partial or require major reskilling.",
    )


def build_target_domain_evidence(
    candidates: pd.DataFrame,
    occupation_skills: pd.DataFrame,
) -> pd.DataFrame:
    _, similarity_df = build_weighted_similarity_matrix(occupation_skills)
    raw_wide, feature_meta = build_raw_skill_wide(occupation_skills)
    profiles = build_occupation_feasibility_profile().set_index("occupation_code")
    source_profile = profiles.loc[NURSING_CODE]
    source_vector = raw_wide.loc[NURSING_CODE]

    related = pd.read_csv(ONET_RELATED_OCCUPATIONS).rename(
        columns={
            "O*NET-SOC Code": "occupation_code",
            "Related O*NET-SOC Code": "target_occupation_code",
            "Relatedness Tier": "related_tier",
            "Index": "related_index",
        }
    )
    related_from_source = related.loc[related["occupation_code"].eq(NURSING_CODE)]
    related_lookup = related_from_source.set_index("target_occupation_code")[
        ["related_tier", "related_index"]
    ].to_dict("index")

    source_candidate = pd.DataFrame(
        [{"target_occupation_code": NURSING_CODE, "target_occupation_name": "Registered Nurses"}]
    )
    mapping_candidates = pd.concat(
        [source_candidate, candidates[["target_occupation_code", "target_occupation_name"]]],
        ignore_index=True,
    ).drop_duplicates("target_occupation_code")
    mapping, _ = build_onet_taiwanjobs_mapping(mapping_candidates, output_path=None)
    mapping_lookup = mapping.set_index("onet_occupation_code")
    source_salary_lower = mapping_lookup.loc[NURSING_CODE]["salary_lower_median"]

    records: list[dict[str, object]] = []
    for _, candidate in candidates.iterrows():
        target_code = str(candidate["target_occupation_code"])
        if target_code not in similarity_df.columns or target_code not in raw_wide.index or target_code not in profiles.index:
            continue
        target_title = str(candidate["target_occupation_name"])
        target_profile = profiles.loc[target_code]
        target_vector = raw_wide.loc[target_code]
        coverage, gap = directional_skill_metrics(source_vector, target_vector, feature_meta)
        technology_coverage, technology_gap = technology_specific_metrics(source_vector, target_vector, feature_meta)
        span = transition_span(coverage, gap, technology_gap)
        related_support = related_lookup.get(target_code)
        education_level, education_reasons = education_barrier(source_profile, target_profile, target_title)
        training_level, training_reasons = training_experience_barrier(source_profile, target_profile)
        credential_level = credential_barrier(target_profile, target_title)
        job_zone_difference = target_profile["job_zone"] - source_profile["job_zone"]
        same_major, same_family, taxonomy_level = taxonomy_distance(
            NURSING_CODE,
            target_code,
            "yes" if related_support else "no",
            related_support["related_tier"] if related_support else "",
        )
        mapping_row = mapping_lookup.loc[target_code]
        market_validation = market_validation_level(mapping_row)

        record = {
            **candidate.to_dict(),
            "skill_similarity": round(float(similarity_df.loc[NURSING_CODE, target_code]), 6),
            "transferable_skill_coverage": round(coverage, 6),
            "target_skill_gap": round(gap, 6),
            "target_domain_technology_coverage": round(technology_coverage, 6),
            "target_domain_technology_gap": round(technology_gap, 6),
            "transition_span": span,
            "related_support": "yes" if related_support else "no",
            "related_tier": related_support["related_tier"] if related_support else "",
            "related_index": int(related_support["related_index"]) if related_support else "",
            "source_job_zone": int(source_profile["job_zone"]) if not pd.isna(source_profile["job_zone"]) else "",
            "target_job_zone": int(target_profile["job_zone"]) if not pd.isna(target_profile["job_zone"]) else "",
            "job_zone_difference": int(job_zone_difference) if not pd.isna(job_zone_difference) else 0,
            "source_modal_education": text_or_unknown(source_profile.get("education_modal_label", "")),
            "target_modal_education": text_or_unknown(target_profile.get("education_modal_label", "")),
            "target_master_plus_share": round(float(target_profile.get("education_master_plus_share", 0.0) or 0.0), 3),
            "target_doctoral_professional_share": round(
                float(target_profile.get("education_doctoral_professional_share", 0.0) or 0.0),
                3,
            ),
            "education_barrier": education_level,
            "education_barrier_notes": education_reasons,
            "training_experience_barrier": training_level,
            "training_experience_barrier_notes": training_reasons,
            "credential_barrier": credential_level,
            "professional_certification_importance": round(
                float(target_profile.get("professional_certification_importance", 0.0) or 0.0),
                3,
            ),
            "same_major_group": same_major,
            "same_occupation_family": same_family,
            "onet_related_support": "yes" if related_support else "no",
            "taxonomy_distance_level": taxonomy_level,
            "taiwanjobs_occupation": mapping_row["taiwanjobs_occupation"],
            "matched_titles": mapping_row["matched_titles"],
            "mapping_method": mapping_row["mapping_method"],
            "mapping_score": mapping_row["mapping_score"],
            "mapping_confidence": mapping_row["mapping_confidence"],
            "manual_review_needed": mapping_row["manual_review_needed"],
            "matched_job_count": mapping_row["matched_job_count"],
            "total_demand_persons": mapping_row["total_demand_persons"],
            "salary_lower_median": mapping_row["salary_lower_median"],
            "salary_upper_median": mapping_row["salary_upper_median"],
            "salary_basis": mapping_row["salary_basis"],
            "education_requirement_distribution": mapping_row["education_requirement_distribution"],
            "experience_requirement_distribution": mapping_row["experience_requirement_distribution"],
            "main_job_locations": mapping_row["main_job_locations"],
            "market_validation": market_validation,
            "shared_top_skills": describe_shared_skills(source_vector, target_vector, feature_meta),
            "missing_skills": describe_missing_skills(source_vector, target_vector, feature_meta),
        }
        record["mobility_value_signal"] = mobility_value_signal(pd.Series(record), source_salary_lower)
        flag, level, notes = classify_target_domain_feasibility(target_title, target_profile, record)
        record["feasibility_flag"] = flag
        record["feasibility_level"] = level
        record["feasibility_notes"] = notes
        target_domain_linked = (
            str(record["target_domain_primary_signal"]) == "explicit_health_technology"
            or any(
                tag in str(record["target_domain_concept_tags"])
                for tag in ["clinical_health_informatics", "health_data", "medical_device_technology"]
            )
        )
        lower_value_support_title = any(
            term in target_title.lower()
            for term in ["assistant", "assistants", "preparer", "preparers", "transcriptionist", "transcriptionists"]
        )
        hidden_candidate = (
            taxonomy_level in {"Cross-category", "Distant category"}
            and level != "Infeasible / high-barrier"
            and target_domain_linked
            and span != "Major reskilling"
            and not lower_value_support_title
        )
        record["hidden_path_candidate"] = "yes" if hidden_candidate else "no"
        records.append(record)

    result = pd.DataFrame.from_records(records)
    if result.empty:
        return result
    span_order = {"High skill reuse": 0, "Partial skill reuse": 1, "Major reskilling": 2}
    market_order = {"Strong": 0, "Moderate": 1, "Weak": 2, "Unknown": 3}
    flag_order = {"candidate": 0, "review": 1, "exclude": 2}
    result["_flag_order"] = result["feasibility_flag"].map(flag_order)
    result["_span_order"] = result["transition_span"].map(span_order)
    result["_market_order"] = result["market_validation"].map(market_order)
    result = result.sort_values(
        ["_flag_order", "_span_order", "_market_order", "target_domain_retrieval_score"],
        ascending=[True, True, True, False],
    ).drop(columns=["_flag_order", "_span_order", "_market_order"])
    result.insert(0, "target_domain_evidence_rank", range(1, len(result) + 1))
    return result


def write_target_domain_v35_method_md() -> None:
    lines = [
        "# Target Domain Exploration v3.5 Method",
        "",
        "Purpose: answer a source-to-domain question, starting with `Registered Nurses -> Technology / AI`, without relying on the source occupation's global cosine nearest neighbors.",
        "",
        "## Candidate Generation",
        "",
        "Candidate generation uses only local O*NET raw files and deterministic lexical retrieval. No LLM and no embedding model is used in v3.5.",
        "",
        "Input fields:",
        "",
        "- `occupation_data.csv`: occupation title and description.",
        "- `task_statements.csv`: occupation tasks.",
        "- `knowledge.csv`, `essential_skills.csv`, `transferable_skills.csv`: high-importance skill/knowledge labels where O*NET IM >= 3.0.",
        "- `software_skills.csv`: software categories and workplace examples.",
        "",
        "The Technology / AI target-domain lexicon includes clinical/health informatics, health information, medical records, clinical data, bioinformatics, biostatistics, data science, machine learning, artificial intelligence, software, computer systems, information systems, database, cybersecurity, medical equipment, medical device, and technology support terms.",
        "",
        "Retrieval score is a transparent weighted keyword count. Title hits receive the highest weight, followed by description, tasks, skill/knowledge labels, and software text. O*NET major group 15 receives a small inclusion bonus; healthcare occupations with both healthcare and technology terms receive a healthcare-tech bridge bonus.",
        "",
        "A candidate also needs a primary target-domain signal: O*NET SOC major group 15, a technology title, explicit healthcare-technology language in the occupation title/description, or a technical science/engineering title signal. Software-use evidence alone, such as using electronic medical records software in an otherwise non-technology occupation, is retained as evidence but does not create a candidate by itself.",
        "",
        "The candidate pool is the union of high-scoring healthcare-tech, core technology, and strong-keyword matches after this primary-signal filter, capped at 50 occupations. This score is only for candidate generation, not a final recommendation score.",
        "",
        "## Evidence Engine Reuse",
        "",
        "Every target-domain candidate is passed through the same evidence dimensions used in v2/v3:",
        "",
        "- `skill_similarity`: symmetric O*NET weighted cosine similarity.",
        "- `transferable_skill_coverage` and `target_skill_gap`: directional raw O*NET IM metrics from RN -> target.",
        "- education, credential, training/experience barriers.",
        "- O*NET taxonomy distance and related-occupation support.",
        "- TaiwanJobs mapping confidence and market evidence.",
        "",
        "## Transition Span",
        "",
        "Transition span combines two raw O*NET IM checks:",
        "",
        "- overall RN -> target `transferable_skill_coverage` and `target_skill_gap` across required target skills/knowledge.",
        "- `target_domain_technology_gap` on technology-specific O*NET features such as Computers and Electronics, Engineering and Technology, Mathematics, Programming, Technology Design, Systems Analysis, Systems Evaluation, Troubleshooting, and related technical skills/knowledge.",
        "",
        "Rules:",
        "",
        "- `High skill reuse`: coverage >= 0.85, gap <= 0.45, and technology gap <= 0.50.",
        "- `Partial skill reuse`: coverage >= 0.65, gap <= 0.90, and technology gap <= 1.50.",
        "- `Major reskilling`: all other candidates.",
        "",
        "Transition span is not a good/bad score. It states how much RN skill/knowledge appears reusable for the target-domain occupation, with an explicit guard against treating generic social or work-style skill overlap as technology readiness.",
        "",
        "## Interpretation Rules",
        "",
        "The output keeps three dimensions separate: Feasibility, Market Opportunity, and Obviousness / Taxonomy Distance. It does not compute a transition success probability, a final ranking score, or final recommendations.",
        "",
        "O*NET occupation titles may not have direct TaiwanJobs equivalents. Low-confidence or unmatched mappings are retained with `manual_review_needed=yes` rather than forced into a Taiwan occupation.",
        "",
        "`hidden_path_candidate` is provisional. It requires cross/distant taxonomy, a healthcare-tech or health-data domain link, no high-barrier feasibility exclusion, and no major-reskilling span. Assistant/preparer/transcriptionist-style lower-value support roles are kept in the evidence table but not marked as hidden-path candidates. The flag is not derived from global cosine rank and is not a final recommendation.",
    ]
    TARGET_DOMAIN_V35_METHOD_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def nursing_to_technology_v35(occupation_skills: pd.DataFrame) -> pd.DataFrame:
    write_target_domain_v35_method_md()
    candidates = generate_target_domain_candidates(
        occupation_skills,
        source_occupation_code=NURSING_CODE,
        target_domain=TECH_AI_DOMAIN,
        max_candidates=50,
    )
    result = build_target_domain_evidence(candidates, occupation_skills)
    result.to_csv(NURSING_TECH_CANDIDATES_V35_CSV, index=False, encoding="utf-8")
    write_nursing_to_technology_v35_md(result)
    return result


def write_nursing_to_technology_v35_md(result: pd.DataFrame) -> None:
    span_counts = result["transition_span"].value_counts().to_dict()
    market_counts = result["market_validation"].value_counts().to_dict()
    concept_checks = result.loc[
        result["target_domain_concept_tags"].str.contains(
            "clinical_health_informatics|health_data|medical_device_technology|technology_support|software_application",
            na=False,
        )
    ]
    reusable_domain = result.loc[
        result["target_domain_concept_tags"].str.contains(
            "clinical_health_informatics|health_data|medical_device_technology",
            na=False,
        )
        & result["feasibility_level"].ne("Infeasible / high-barrier")
    ].head(12)
    major_reskilling = result.loc[result["transition_span"].eq("Major reskilling")].head(12)
    high_barrier = result.loc[result["feasibility_level"].eq("Infeasible / high-barrier")].head(12)
    credible_market = result.loc[
        result["market_validation"].isin(["Strong", "Moderate"])
        & result["mapping_confidence"].isin(["High", "Medium"])
    ].head(18)
    review_needed = result.loc[result["manual_review_needed"].eq("yes")].head(18)
    hidden_candidates = result.loc[result["hidden_path_candidate"].eq("yes")].head(18)

    def evidence_bullets(frame: pd.DataFrame, fields: list[str]) -> list[str]:
        bullets: list[str] = []
        for record in frame.to_dict("records"):
            details = ", ".join(f"{field}={record[field]}" for field in fields)
            bullets.append(f"- `{record['target_occupation_code']}` {record['target_occupation_name']}: {details}")
        return bullets

    incomplete_concept_note = ""
    if "29-9021.00" not in set(result["target_occupation_code"].astype(str)):
        incomplete_concept_note = (
            "`29-9021.00` Health Information Technologists and Medical Registrars exists in "
            "`occupation_data.csv`, `job_zones.csv`, `job_titles.csv`, and task/DWA files, "
            "but the current `occupation_skills.csv` backbone has no Essential/Transferable/Knowledge IM profile for it, "
            "so v3.5 does not calculate skill similarity, coverage, or gap for that occupation."
        )

    lines = [
        "# Nursing to Technology / AI Exploration v3.5",
        "",
        "Question: `I am currently a Registered Nurse, but I want to move toward Technology / AI. Which careers are worth further validation?`",
        "",
        "This is target-domain exploration. It does not calculate transition success probability, does not pick a final Top 3, and does not recommend training.",
        "",
        "## Candidate Generation Summary",
        "",
        f"- Generated candidates: {len(result)}",
        f"- High skill reuse: {span_counts.get('High skill reuse', 0)}",
        f"- Partial skill reuse: {span_counts.get('Partial skill reuse', 0)}",
        f"- Major reskilling: {span_counts.get('Major reskilling', 0)}",
        f"- Strong Taiwan market validation: {market_counts.get('Strong', 0)}",
        f"- Moderate Taiwan market validation: {market_counts.get('Moderate', 0)}",
        f"- Unknown Taiwan market validation: {market_counts.get('Unknown', 0)}",
        "",
        "## Candidate Evidence",
        "",
        "| Rank | Occupation | Concepts | Span | Feasibility | Market | Taxonomy | Jobs | Demand | Mapping | Hidden Candidate |",
        "|---:|---|---|---|---|---|---|---:|---:|---|---|",
    ]
    for record in result.head(50).to_dict("records"):
        lines.append(
            "| {rank} | `{code}` {title} | {concepts} | {span} | {feasibility} | {market} | {taxonomy} | {jobs} | {demand} | {mapping} | {hidden} |".format(
                rank=record["target_domain_evidence_rank"],
                code=record["target_occupation_code"],
                title=record["target_occupation_name"],
                concepts=str(record["target_domain_concept_tags"]).replace("|", "\\|"),
                span=record["transition_span"],
                feasibility=record["feasibility_level"],
                market=record["market_validation"],
                taxonomy=record["taxonomy_distance_level"],
                jobs=record["matched_job_count"],
                demand=record["total_demand_persons"],
                mapping=record["mapping_confidence"],
                hidden=record["hidden_path_candidate"],
            )
        )

    lines.extend(
        [
            "",
            "## Healthcare x Technology Concepts Found",
            "",
            "| Occupation | Concept Tags | Skill Reuse | Market | Mapping Notes |",
            "|---|---|---|---|---|",
        ]
    )
    for record in concept_checks.head(25).to_dict("records"):
        mapping_note = "manual review" if record["manual_review_needed"] == "yes" else "mapped"
        lines.append(
            "| `{code}` {title} | {tags} | {span} | {market} | {mapping_note} |".format(
                code=record["target_occupation_code"],
                title=record["target_occupation_name"],
                tags=str(record["target_domain_concept_tags"]).replace("|", "\\|"),
                span=record["transition_span"],
                market=record["market_validation"],
                mapping_note=mapping_note,
            )
        )

    lines.extend(
        [
            "",
            "## Nursing Domain Knowledge Reuse",
            "",
            "These candidates have explicit clinical informatics, health data, or medical-device links and are not excluded by the current feasibility screen:",
            "",
            *evidence_bullets(
                reusable_domain,
                [
                    "transition_span",
                    "target_domain_technology_gap",
                    "market_validation",
                    "mapping_confidence",
                ],
            ),
            "",
            "## Major Reskilling",
            "",
            "These are still valid target-domain candidates, but the technology-specific gap suggests a larger reskilling span:",
            "",
            *evidence_bullets(
                major_reskilling,
                [
                    "target_domain_technology_gap",
                    "education_barrier",
                    "market_validation",
                    "mapping_confidence",
                ],
            ),
            "",
            "## High-Barrier Exclusions",
            "",
            "These were generated as target-domain candidates but are excluded from near-term feasibility due to education, credential, or preparation constraints:",
            "",
            *evidence_bullets(
                high_barrier,
                [
                    "education_barrier",
                    "credential_barrier",
                    "target_job_zone",
                    "transition_span",
                ],
            ),
            "",
            "## Taiwan Market Evidence",
            "",
            "The following candidates have Strong or Moderate TaiwanJobs evidence with High or Medium mapping confidence. This is market evidence only, not success probability:",
            "",
            *evidence_bullets(
                credible_market,
                [
                    "market_validation",
                    "mapping_confidence",
                    "matched_job_count",
                    "total_demand_persons",
                ],
            ),
            "",
            "## Manual Review Needed",
            "",
            "These O*NET occupations map imperfectly to TaiwanJobs titles and should not be treated as confirmed Taiwan occupation equivalents:",
            "",
            *evidence_bullets(
                review_needed,
                [
                    "mapping_confidence",
                    "matched_job_count",
                    "market_validation",
                    "target_domain_primary_signal",
                ],
            ),
            "",
            "## Hidden Path Candidates",
            "",
            "`hidden_path_candidate=yes` means cross/distant taxonomy plus a healthcare-tech or health-data domain link, not a final Hidden Path recommendation:",
            "",
            *evidence_bullets(
                hidden_candidates,
                [
                    "transition_span",
                    "taxonomy_distance_level",
                    "market_validation",
                    "mapping_confidence",
                ],
            ),
            "",
            "## O*NET Coverage Gap",
            "",
            incomplete_concept_note or "No central healthcare-technology concept was skipped for missing O*NET skill evidence.",
        ]
    )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The target-domain search surfaces Technology / AI and healthcare-technology occupations that global RN skill similarity would not prioritize.",
            "- Health Informatics Specialists, Medical Records Specialists, Clinical Data Managers, Clinical Research Coordinators, Bioinformatics Technicians, and medical-device roles are the clearest complete-evidence healthcare-technology concepts in this run.",
            "- Core software, data, cybersecurity, database, and systems roles have stronger TaiwanJobs mappings, but most reuse nursing knowledge only indirectly and should be read as bridge candidates rather than obvious RN-adjacent moves.",
            "- O*NET titles such as Health Informatics Specialists and Clinical Data Managers may not map cleanly to TaiwanJobs titles; these are retained for manual validation instead of forced into a local equivalent.",
            "- Medical Assistants and Dental Assistants remain in the candidate file because their O*NET descriptions include medical-records workflows, but their `mobility_value_signal` marks possible downward or low-value mobility and they should not be interpreted as attractive technology moves without further evidence.",
            "- `hidden_path_candidate` remains provisional and only means a non-obvious taxonomy relationship worth later validation.",
            "",
            "See `docs/target_domain_exploration_v35_method.md` for candidate generation and transition-span definitions.",
        ]
    )
    NURSING_TECH_EXPLORATION_V35_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_training_courses() -> tuple[pd.DataFrame, dict[str, object]]:
    encoding = detect_encoding(TRAINING_COURSES)
    raw = pd.read_csv(TRAINING_COURSES, encoding=encoding, dtype={"課程代碼": str})
    courses = raw.rename(
        columns={
            "訓練單位名稱": "training_provider",
            "縣市別辦訓地": "location",
            "課程代碼": "course_code",
            "課程名稱": "course_name",
            "訓練時數": "training_hours",
            "訓練人次": "training_capacity",
            "每人訓練費用": "fee_per_person",
            "開訓日期": "start_date",
            "結訓日期": "end_date",
        }
    )
    courses["training_hours"] = pd.to_numeric(courses["training_hours"], errors="coerce")
    courses["training_capacity"] = pd.to_numeric(courses["training_capacity"], errors="coerce")
    courses["fee_per_person"] = pd.to_numeric(courses["fee_per_person"], errors="coerce")
    courses["start_date"] = pd.to_datetime(courses["start_date"].astype(str), format="%Y%m%d", errors="coerce")
    courses["end_date"] = pd.to_datetime(courses["end_date"].astype(str), format="%Y%m%d", errors="coerce")
    inventory = {
        "filename": TRAINING_COURSES.name,
        "encoding": encoding,
        "rows": len(courses),
        "columns": list(raw.columns),
        "course_name_column": "課程名稱",
        "course_content_column": "not_available",
        "training_hours_column": "訓練時數",
        "fee_column": "每人訓練費用",
        "subsidy_fields": "not_available",
        "location_column": "縣市別辦訓地",
        "date_columns": "開訓日期; 結訓日期",
        "min_start_date": courses["start_date"].min(),
        "max_end_date": courses["end_date"].max(),
        "training_hours_missing": int(courses["training_hours"].isna().sum()),
        "fee_missing": int(courses["fee_per_person"].isna().sum()),
        "date_missing": int(courses["start_date"].isna().sum() + courses["end_date"].isna().sum()),
    }
    return courses, inventory


def skill_gap_status(source_value: float, target_value: float) -> str:
    gap = max(float(target_value) - float(source_value), 0.0)
    if gap <= 0.25:
        return "already_covered"
    if gap < 1.0:
        return "partially_covered"
    return "missing"


def v4_target_skill_gaps(occupation_skills: pd.DataFrame) -> pd.DataFrame:
    raw_wide, feature_meta = build_raw_skill_wide(occupation_skills)
    if NURSING_CODE not in raw_wide.index:
        raise ValueError(f"Missing source occupation skill profile: {NURSING_CODE}")
    source_vector = raw_wide.loc[NURSING_CODE]
    records: list[dict[str, object]] = []
    for target_code, target_name in V4_TARGET_CANDIDATES.items():
        if target_code not in raw_wide.index:
            records.append(
                {
                    "source_occupation_code": NURSING_CODE,
                    "source_occupation_name": "Registered Nurses",
                    "target_occupation_code": target_code,
                    "target_occupation_name": target_name,
                    "skill_profile_available": "no",
                    "skill_id": "",
                    "skill_name": "",
                    "skill_type": "",
                    "target_importance": "",
                    "source_importance": "",
                    "raw_gap": "",
                    "skill_gap_status": "limitation_no_onet_skill_profile",
                }
            )
            continue
        target_vector = raw_wide.loc[target_code]
        target_required = target_vector.loc[target_vector.ge(REQUIRED_SKILL_THRESHOLD)]
        for feature_id, target_value in target_required.items():
            meta = feature_meta[feature_id]
            source_value = float(source_vector.get(feature_id, 0.0))
            gap = max(float(target_value) - source_value, 0.0)
            records.append(
                {
                    "source_occupation_code": NURSING_CODE,
                    "source_occupation_name": "Registered Nurses",
                    "target_occupation_code": target_code,
                    "target_occupation_name": target_name,
                    "skill_profile_available": "yes",
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
        return gaps
    status_order = {"missing": 0, "partially_covered": 1, "already_covered": 2}
    gaps["_status_order"] = gaps["skill_gap_status"].map(status_order).fillna(3)
    gaps = gaps.sort_values(
        ["target_occupation_code", "_status_order", "raw_gap", "target_importance", "skill_name"],
        ascending=[True, True, False, False, True],
    ).drop(columns=["_status_order"])
    return gaps


def skill_course_terms(skill_name: str, skill_type: str, target_name: str) -> list[str]:
    lowered = skill_name.lower()
    target_lower = target_name.lower()
    terms: set[str] = set()

    if "computer" in lowered or "electronics" in lowered:
        terms.update(["python", "sql", "ai", "人工智慧", "資料庫", "資料", "數據", "資訊", "軟體", "程式", "雲端", "資安", "大數據", "power bi", "excel vba"])
    if "programming" in lowered:
        terms.update(["python", "程式", "軟體", "java", "django", "asp.net", "網頁", "全端", "pytorch", "rag", "agent", "llm"])
    if "mathematics" in lowered:
        terms.update(["統計", "數據分析", "資料分析", "商業智慧", "power bi", "精算", "數學"])
    if "statistics" in lowered or "statistical" in lowered:
        terms.update(["統計", "數據分析", "資料分析", "商業智慧", "power bi"])
    if "data" in lowered or "database" in lowered:
        terms.update(["資料", "數據", "資料庫", "sql", "大數據", "power bi", "excel", "資料分析", "數據分析"])
    if "engineering" in lowered or "technology" in lowered or "design" in lowered:
        terms.update(["工程", "技術", "物聯網", "aiot", "plc", "自動化", "3d列印", "機器人", "rfid", "醫療器材", "產品設計"])
    if "systems" in lowered or "operations analysis" in lowered or "systems analysis" in lowered:
        terms.update(["系統", "系統分析", "資訊系統", "mis", "erp", "流程", "n8n", "自動化", "專案管理", "商業智慧"])
    if "troubleshooting" in lowered or "equipment maintenance" in lowered or "repairing" in lowered:
        terms.update(["維修", "設備", "故障", "技術支援", "醫療器材", "plc", "機電"])
    if "medicine" in lowered or "medical" in lowered or "health" in lowered:
        terms.update(["醫療", "醫學", "健康", "臨床", "醫療器材", "醫材"])
    if "biology" in lowered or "chemistry" in lowered or "science" in lowered:
        terms.update(["生物", "生技", "基因", "生醫", "醫療", "科學"])
    if "customer" in lowered or "service" in lowered:
        terms.update(["客戶", "服務", "客服", "溝通"])
    if "english" in lowered:
        terms.update(["英文", "英語", "toeic"])
    if "administration" in lowered or "management" in lowered or "coordination" in lowered:
        terms.update(["管理", "專案管理", "企劃", "pm", "協作"])
    if "clerical" in lowered or "writing" in lowered:
        terms.update(["文書", "行政", "office", "excel", "文件", "資料"])

    if "health informatics" in target_lower:
        terms.update(["醫療資訊", "健康資訊", "資訊系統", "電子病歷", "資料庫", "系統分析", "醫療"])
    if "clinical data" in target_lower or "clinical research" in target_lower:
        terms.update(["臨床", "臨床資料", "資料分析", "統計", "醫療", "研究", "專案管理"])
    if "medical records" in target_lower:
        terms.update(["醫療", "病歷", "醫療資訊", "資料", "檔案", "文書", "行政"])
    if "bioinformatics" in target_lower:
        terms.update(["生物資訊", "生物", "基因", "python", "資料分析", "機器學習", "統計"])
    if "data scientist" in target_lower:
        terms.update(["資料科學", "機器學習", "深度學習", "python", "pytorch", "數據分析", "大數據", "power bi", "統計"])

    return sorted(terms, key=lambda value: (-len(value), value))


def match_course_to_skill(course_name: str, skill_name: str, skill_type: str, target_name: str) -> tuple[float, str, str, str]:
    terms = skill_course_terms(skill_name, skill_type, target_name)
    lowered = lower_text(course_name)
    hits = [term for term in terms if term.lower() in lowered]
    if not hits:
        return 0.0, "", "No match", "yes"
    strong_hits = [
        term
        for term in hits
        if term.lower()
        in {
            "python",
            "sql",
            "pytorch",
            "power bi",
            "資料庫",
            "資料科學",
            "機器學習",
            "深度學習",
            "生物資訊",
            "醫療資訊",
            "臨床資料",
            "系統分析",
            "資訊系統",
        }
    ]
    score = min(1.0, 0.18 * len(hits) + 0.22 * len(strong_hits))
    if skill_name.lower() in lowered:
        score = min(1.0, score + 0.35)
    if score >= 0.75:
        confidence = "High"
    elif score >= 0.55:
        confidence = "Medium"
    elif score >= 0.35:
        confidence = "Low"
    else:
        return 0.0, "", "No match", "yes"
    manual_review = "yes" if confidence == "Low" else "no"
    return round(float(score), 3), "; ".join(hits[:12]), confidence, manual_review


def build_course_skill_mapping(skill_gaps: pd.DataFrame, courses: pd.DataFrame) -> pd.DataFrame:
    gap_skills = skill_gaps.loc[
        skill_gaps["skill_profile_available"].eq("yes")
        & skill_gaps["skill_gap_status"].isin(["missing", "partially_covered"])
    ].copy()
    records: list[dict[str, object]] = []
    for _, skill in gap_skills.iterrows():
        skill_records: list[dict[str, object]] = []
        for _, course in courses.iterrows():
            score, hits, confidence, manual_review = match_course_to_skill(
                str(course["course_name"]),
                str(skill["skill_name"]),
                str(skill["skill_type"]),
                str(skill["target_occupation_name"]),
            )
            if score <= 0:
                continue
            skill_records.append(
                {
                    "source_occupation_code": skill["source_occupation_code"],
                    "source_occupation_name": skill["source_occupation_name"],
                    "target_occupation_code": skill["target_occupation_code"],
                    "target_occupation_name": skill["target_occupation_name"],
                    "skill_id": skill["skill_id"],
                    "skill_name": skill["skill_name"],
                    "skill_type": skill["skill_type"],
                    "skill_gap_status": skill["skill_gap_status"],
                    "target_importance": skill["target_importance"],
                    "source_importance": skill["source_importance"],
                    "raw_gap": skill["raw_gap"],
                    "course_code": course["course_code"],
                    "course_name": course["course_name"],
                    "training_provider": course["training_provider"],
                    "location": course["location"],
                    "training_hours": course["training_hours"],
                    "fee_per_person": course["fee_per_person"],
                    "training_capacity": course["training_capacity"],
                    "start_date": course["start_date"].date().isoformat() if not pd.isna(course["start_date"]) else "",
                    "end_date": course["end_date"].date().isoformat() if not pd.isna(course["end_date"]) else "",
                    "subsidy_information": "unknown",
                    "scheduling_information": "unknown",
                    "mapping_method": "deterministic_course_title_to_onet_skill_keyword_v1",
                    "mapping_score": score,
                    "mapping_terms_matched": hits,
                    "mapping_confidence": confidence,
                    "manual_review_needed": manual_review,
                }
            )
        skill_records = sorted(
            skill_records,
            key=lambda record: (
                -float(record["mapping_score"]),
                float(record["training_hours"]) if not pd.isna(record["training_hours"]) else 99999.0,
                str(record["course_name"]),
            ),
        )[:8]
        records.extend(skill_records)
    mapping = pd.DataFrame.from_records(records)
    if mapping.empty:
        return mapping
    mapping = mapping.sort_values(
        ["target_occupation_code", "skill_gap_status", "skill_name", "mapping_score", "training_hours"],
        ascending=[True, True, True, False, True],
    )
    mapping.to_csv(CAREER_TRAINING_SKILL_MAPPING_CSV, index=False, encoding="utf-8")
    return mapping


def summarize_skill_names(rows: pd.DataFrame, limit: int = 10) -> str:
    if rows.empty:
        return ""
    values = [
        f"{record['skill_name']} ({record['skill_type']}, gap {record['raw_gap']})"
        for record in rows.head(limit).to_dict("records")
    ]
    if len(rows) > limit:
        values.append(f"... +{len(rows) - limit} more")
    return "; ".join(values)


def choose_best_courses(mapping: pd.DataFrame, status_filter: set[str] = None) -> pd.DataFrame:
    if mapping.empty:
        return mapping
    eligible = mapping.loc[mapping["mapping_confidence"].isin(["High", "Medium"])].copy()
    if status_filter:
        eligible = eligible.loc[eligible["skill_gap_status"].isin(status_filter)]
    if eligible.empty:
        return eligible
    eligible = eligible.sort_values(["skill_id", "mapping_score", "training_hours"], ascending=[True, False, True])
    best_per_skill = eligible.groupby("skill_id", as_index=False).head(1)
    return best_per_skill.drop_duplicates("course_code").copy()


def scenario_coverage(mapping: pd.DataFrame, missing_skill_ids: set[str], months: int) -> dict[str, object]:
    if not missing_skill_ids:
        return {
            f"scenario_{months}m_trainable_missing_skills": 0,
            f"scenario_{months}m_training_coverage_ratio": 1.0,
            f"scenario_{months}m_training_hours": 0.0,
            f"scenario_{months}m_direct_course_cost": 0.0,
            f"scenario_{months}m_feasibility_estimate": "no missing skill gap",
        }
    if mapping.empty:
        return {
            f"scenario_{months}m_trainable_missing_skills": 0,
            f"scenario_{months}m_training_coverage_ratio": 0.0,
            f"scenario_{months}m_training_hours": "",
            f"scenario_{months}m_direct_course_cost": "",
            f"scenario_{months}m_feasibility_estimate": "no matched course evidence",
        }
    window_end = OBSERVATION_DATE + pd.DateOffset(months=months)
    dated = mapping.copy()
    dated["start_date_ts"] = pd.to_datetime(dated["start_date"], errors="coerce")
    dated["end_date_ts"] = pd.to_datetime(dated["end_date"], errors="coerce")
    eligible = dated.loc[
        dated["skill_id"].isin(missing_skill_ids)
        & dated["mapping_confidence"].isin(["High", "Medium"])
        & dated["start_date_ts"].ge(OBSERVATION_DATE)
        & dated["end_date_ts"].le(window_end)
    ]
    covered = set(eligible["skill_id"])
    best_courses = choose_best_courses(eligible, {"missing"})
    ratio = round(len(covered) / len(missing_skill_ids), 3)
    if ratio >= 0.75:
        label = "most missing skills have matched courses in window"
    elif ratio >= 0.4:
        label = "partial missing-skill coverage in window"
    elif ratio > 0:
        label = "limited missing-skill coverage in window"
    else:
        label = "no missing-skill coverage in window"
    return {
        f"scenario_{months}m_trainable_missing_skills": len(covered),
        f"scenario_{months}m_training_coverage_ratio": ratio,
        f"scenario_{months}m_training_hours": round(float(best_courses["training_hours"].sum()), 1) if not best_courses.empty else 0.0,
        f"scenario_{months}m_direct_course_cost": round(float(best_courses["fee_per_person"].sum()), 1) if not best_courses.empty else 0.0,
        f"scenario_{months}m_feasibility_estimate": label,
    }


def learning_plan_phase_text(best_courses: pd.DataFrame, phase: str) -> str:
    if best_courses.empty:
        return "unknown: no matched course evidence"
    course_text = best_courses["course_name"].astype(str)
    if phase == "foundation":
        mask = course_text.str.contains("Python|Excel|Power BI|資料|數據|統計|Office|程式|AI|人工智慧", case=False, na=False)
    elif phase == "domain":
        mask = course_text.str.contains("醫療|醫材|臨床|生物|生技|基因|資料庫|系統|資安|機器學習|深度學習", case=False, na=False)
    else:
        mask = course_text.str.contains("實作|開發|專案|應用|個案|案例|RAG|Agent|n8n|Django|PyTorch", case=False, na=False)
    selected = best_courses.loc[mask].head(5)
    if selected.empty:
        return "unknown: no matched course evidence for this phase"
    return "; ".join(
        f"{record['course_name']} ({record['training_hours']}h, maps {record['skill_name']})"
        for record in selected.to_dict("records")
    )


def training_burden_level(
    missing_count: int,
    coverage_ratio: float,
    total_hours: object,
    cost: object,
    transition_span_value: object,
) -> str:
    hours = float(total_hours) if total_hours != "" and not pd.isna(total_hours) else 0.0
    direct_cost = float(cost) if cost != "" and not pd.isna(cost) else 0.0
    if str(transition_span_value) == "Major reskilling" and missing_count >= 3:
        return "high"
    if missing_count >= 3 and (coverage_ratio < 0.5 or hours >= 180 or direct_cost >= 40000):
        return "high"
    if missing_count >= 2 or hours >= 80 or direct_cost >= 18000:
        return "medium"
    return "low"


def build_training_v4_summary(
    occupation_skills: pd.DataFrame,
    nursing_v35: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    courses, inventory = load_training_courses()
    skill_gaps = v4_target_skill_gaps(occupation_skills)
    mapping = build_course_skill_mapping(skill_gaps, courses)
    v35_lookup = nursing_v35.set_index("target_occupation_code")
    records: list[dict[str, object]] = []

    for target_code, target_name in V4_TARGET_CANDIDATES.items():
        target_gaps = skill_gaps.loc[skill_gaps["target_occupation_code"].eq(target_code)].copy()
        limitation = ""
        if target_gaps.empty or target_gaps["skill_profile_available"].eq("no").any():
            limitation = "missing O*NET skill profile; cannot compute target skill gap"
        missing = target_gaps.loc[target_gaps["skill_gap_status"].eq("missing")]
        partial = target_gaps.loc[target_gaps["skill_gap_status"].eq("partially_covered")]
        covered = target_gaps.loc[target_gaps["skill_gap_status"].eq("already_covered")]
        target_mapping = mapping.loc[mapping["target_occupation_code"].eq(target_code)].copy() if not mapping.empty else pd.DataFrame()
        missing_skill_ids = set(missing["skill_id"].astype(str))
        trainable_missing = set(
            target_mapping.loc[
                target_mapping["skill_gap_status"].eq("missing")
                & target_mapping["mapping_confidence"].isin(["High", "Medium"]),
                "skill_id",
            ].astype(str)
        )
        gap_skill_ids = set(pd.concat([missing["skill_id"], partial["skill_id"]]).astype(str))
        trainable_gap_skills = set(
            target_mapping.loc[
                target_mapping["skill_gap_status"].isin(["missing", "partially_covered"])
                & target_mapping["mapping_confidence"].isin(["High", "Medium"]),
                "skill_id",
            ].astype(str)
        )
        coverage_ratio = round(len(trainable_missing) / len(missing_skill_ids), 3) if missing_skill_ids else 1.0
        gap_coverage_ratio = round(len(trainable_gap_skills) / len(gap_skill_ids), 3) if gap_skill_ids else 1.0
        best_courses = choose_best_courses(target_mapping, {"missing", "partially_covered"})
        all_missing_courses = choose_best_courses(target_mapping, {"missing"})
        total_hours = round(float(best_courses["training_hours"].sum()), 1) if not best_courses.empty else 0.0
        direct_cost = round(float(best_courses["fee_per_person"].sum()), 1) if not best_courses.empty else 0.0
        scenario_data: dict[str, object] = {}
        for months in [3, 6, 12]:
            scenario_data.update(scenario_coverage(target_mapping, missing_skill_ids, months))

        if target_code in v35_lookup.index:
            v35_row = v35_lookup.loc[target_code]
        else:
            v35_row = pd.Series(dtype=object)

        records.append(
            {
                "source_occupation_code": NURSING_CODE,
                "source_occupation_name": "Registered Nurses",
                "target_occupation_code": target_code,
                "target_occupation_name": target_name,
                "skill_similarity": v35_row.get("skill_similarity", ""),
                "transferable_skill_coverage": v35_row.get("transferable_skill_coverage", ""),
                "target_skill_gap": v35_row.get("target_skill_gap", ""),
                "transition_span": v35_row.get("transition_span", ""),
                "feasibility_level": v35_row.get("feasibility_level", ""),
                "education_barrier": v35_row.get("education_barrier", ""),
                "credential_barrier": v35_row.get("credential_barrier", ""),
                "training_experience_barrier": v35_row.get("training_experience_barrier", ""),
                "taxonomy_distance_level": v35_row.get("taxonomy_distance_level", ""),
                "market_validation": v35_row.get("market_validation", ""),
                "taiwanjobs_mapping_confidence": v35_row.get("mapping_confidence", ""),
                "taiwanjobs_manual_review_needed": v35_row.get("manual_review_needed", ""),
                "number_of_target_required_skills": len(target_gaps.loc[target_gaps["skill_profile_available"].eq("yes")]),
                "number_of_already_covered_skills": len(covered),
                "number_of_partially_covered_skills": len(partial),
                "number_of_missing_skills": len(missing),
                "number_of_gap_skills": len(gap_skill_ids),
                "number_of_trainable_skills_found": len(trainable_gap_skills),
                "number_of_trainable_missing_skills_found": len(trainable_missing),
                "training_coverage_ratio": coverage_ratio,
                "gap_skill_training_coverage_ratio": gap_coverage_ratio,
                "matched_course_count": int(best_courses["course_code"].nunique()) if not best_courses.empty else 0,
                "matched_courses": "; ".join(
                    f"{record['course_code']} {record['course_name']}"
                    for record in best_courses.head(10).to_dict("records")
                ),
                "total_training_hours": total_hours,
                "estimated_direct_course_cost": direct_cost,
                "subsidy_information": "unknown",
                "evening_weekend_or_schedule_information": "unknown",
                "possible_income_interruption": "unknown",
                "already_covered_skills": summarize_skill_names(covered.sort_values("target_importance", ascending=False), 12),
                "partially_covered_skills": summarize_skill_names(partial, 12),
                "missing_skills": summarize_skill_names(missing, 12),
                "trainable_missing_skills_found": "; ".join(
                    sorted(
                        target_mapping.loc[
                            target_mapping["skill_id"].isin(trainable_missing),
                            "skill_name",
                        ].dropna().astype(str).unique()
                    )
                ),
                "learning_plan_phase_1_foundational_skills": learning_plan_phase_text(best_courses, "foundation"),
                "learning_plan_phase_2_domain_technical_skills": learning_plan_phase_text(best_courses, "domain"),
                "learning_plan_phase_3_portfolio_job_preparation": learning_plan_phase_text(best_courses, "portfolio"),
                "learning_burden_level": training_burden_level(
                    len(missing),
                    coverage_ratio,
                    total_hours,
                    direct_cost,
                    v35_row.get("transition_span", ""),
                ),
                "limitation": limitation
                or (
                    "TaiwanJobs mapping requires manual review"
                    if str(v35_row.get("manual_review_needed", "")) == "yes"
                    else ""
                ),
                **scenario_data,
            }
        )

    summary = pd.DataFrame.from_records(records)
    summary.to_csv(NURSING_TECH_TRAINING_V4_CSV, index=False, encoding="utf-8")
    write_training_v4_method_md(inventory)
    write_training_v4_md(summary, mapping, inventory)
    return summary, mapping, inventory


def write_training_v4_method_md(inventory: dict[str, object]) -> None:
    lines = [
        "# Career Transition Training v4 Method",
        "",
        "Purpose: estimate what skill gaps may be addressable by current public training supply for selected `Registered Nurses -> Technology / AI` career paths.",
        "",
        "This stage does not build UI, does not use training data to compute transition success probability, and does not create a single career recommendation score.",
        "",
        "## Training Inventory",
        "",
        f"- Raw file: `data/raw/career/training/{inventory['filename']}`",
        f"- Encoding: `{inventory['encoding']}`",
        f"- Rows: {inventory['rows']}",
        f"- Columns: {', '.join(inventory['columns'])}",
        "- Course content field: not available in current raw file.",
        "- Subsidy fields: not available in current raw file.",
        "- Scheduling fields: only start/end dates are available; evening/weekend information is not available.",
        f"- Date range: {inventory['min_start_date'].date().isoformat()} to {inventory['max_end_date'].date().isoformat()}",
        f"- Missing training hours: {inventory['training_hours_missing']}",
        f"- Missing fee: {inventory['fee_missing']}",
        "",
        "## Target Skill Gap",
        "",
        "Target-required skills are O*NET Essential Skills, Transferable Skills, and Knowledge with target IM importance >= 3.0. Source and target values remain on the raw 0-5 IM scale.",
        "",
        "- `already_covered`: target-source raw gap <= 0.25.",
        "- `partially_covered`: target-source raw gap > 0.25 and < 1.0.",
        "- `missing`: target-source raw gap >= 1.0.",
        "",
        "## Course -> Skill Mapping",
        "",
        "Mapping uses deterministic keyword matching from course title to O*NET skill/knowledge names plus target-occupation domain terms. No embedding model and no LLM is used in v4.",
        "",
        "- `mapping_method`: `deterministic_course_title_to_onet_skill_keyword_v1`.",
        "- Threshold: mapping score >= 0.35 is retained.",
        "- Confidence: High >= 0.75, Medium >= 0.55, Low >= 0.35.",
        "- Low confidence rows are marked `manual_review_needed=yes`.",
        "- Coverage calculations count only High and Medium mappings.",
        "",
        "Because the raw file has no course description/content, mapping precision is limited and many rows require manual review before user-facing use.",
        "",
        "## Training Coverage",
        "",
        "`training_coverage_ratio = number_of_trainable_missing_skills_found / number_of_missing_skills`. If there are no missing skills, the ratio is set to 1.0.",
        "",
        "`gap_skill_training_coverage_ratio = number_of_trainable_skills_found / number_of_gap_skills`, where gap skills include both `missing` and `partially_covered` skills.",
        "",
        "Matched course hours and direct cost are summed over one best available course per missing or partially covered skill, deduplicated by course code. This estimates course burden, not total life cost.",
        "",
        "## Time Scenarios",
        "",
        "The 3, 6, and 12 month scenarios use `2026-09-01` as the observation date. A missing skill is counted as trainable in a scenario only if at least one High/Medium-confidence mapped course starts on or after the observation date and ends within the scenario window.",
        "",
        "The scenario output means only: under current public course supply, a skill gap has some mapped course coverage in that time window. It does not claim career readiness or employment outcomes.",
        "",
        "## Learning Plan",
        "",
        "Phase 1, Phase 2, and Phase 3 text is generated only from matched courses and mapped target skills. If no course evidence supports a phase, it is marked unknown.",
        "",
        "## Transition Burden",
        "",
        "The output separates skill reuse, learning burden, training hours, direct learning cost, and possible income interruption. Income interruption remains `unknown` because the raw training data does not contain learner work-hour or opportunity-cost fields.",
    ]
    TRAINING_V4_METHOD_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_training_v4_md(summary: pd.DataFrame, mapping: pd.DataFrame, inventory: dict[str, object]) -> None:
    def md_table(frame: pd.DataFrame, cols: list[str], limit: int = 20) -> list[str]:
        table = frame[cols].head(limit).copy()
        lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
        for record in table.to_dict("records"):
            lines.append("| " + " | ".join(str(record[col]).replace("|", "\\|") for col in cols) + " |")
        return lines

    best_coverage = summary.sort_values(["training_coverage_ratio", "number_of_missing_skills"], ascending=[False, True])
    high_burden = summary.loc[summary["learning_burden_level"].isin(["high", "medium"])].sort_values(
        ["learning_burden_level", "total_training_hours"],
        ascending=[True, False],
    )
    manual_review = summary.loc[
        summary["taiwanjobs_manual_review_needed"].eq("yes")
        | summary["limitation"].astype(str).ne("")
    ]

    lines = [
        "# Nursing to Technology Training Coverage v4",
        "",
        "Question: after identifying career paths worth exploring, what skills need to be strengthened, how long might available public courses take, and how much direct course cost is visible in the raw data?",
        "",
        "This is not a transition success probability, not a final career score, and not a training recommendation UI.",
        "",
        "## Training Data Quality",
        "",
        f"- Raw training file: `{inventory['filename']}`",
        f"- Encoding: `{inventory['encoding']}`",
        f"- Rows: {inventory['rows']}",
        "- Available fields: provider, location, course code, course name, training hours, capacity, fee per person, start date, end date.",
        "- Missing fields for this stage: course content, subsidy eligibility/detail, evening/weekend schedule, online/offline mode, income interruption.",
        "",
        "## Career Path Summary",
        "",
        *md_table(
            summary,
            [
                "target_occupation_name",
                "transition_span",
                "number_of_missing_skills",
                "number_of_gap_skills",
                "number_of_trainable_skills_found",
                "number_of_trainable_missing_skills_found",
                "training_coverage_ratio",
                "gap_skill_training_coverage_ratio",
                "total_training_hours",
                "estimated_direct_course_cost",
                "learning_burden_level",
                "market_validation",
                "taiwanjobs_mapping_confidence",
            ],
            10,
        ),
        "",
        "## Best Current Course Coverage",
        "",
        *md_table(
            best_coverage,
            [
                "target_occupation_name",
                "training_coverage_ratio",
                "gap_skill_training_coverage_ratio",
                "number_of_missing_skills",
                "number_of_gap_skills",
                "trainable_missing_skills_found",
            ],
            6,
        ),
        "",
        "## Training Gaps",
        "",
        "Paths with low coverage or high burden should be treated as exploration targets, not short-term transitions:",
        "",
        *md_table(
            high_burden,
            [
                "target_occupation_name",
                "learning_burden_level",
                "number_of_missing_skills",
                "training_coverage_ratio",
                "total_training_hours",
                "estimated_direct_course_cost",
            ],
            6,
        ),
        "",
        "## Time Scenarios",
        "",
        *md_table(
            summary,
            [
                "target_occupation_name",
                "scenario_3m_training_coverage_ratio",
                "scenario_6m_training_coverage_ratio",
                "scenario_12m_training_coverage_ratio",
                "scenario_3m_feasibility_estimate",
                "scenario_6m_feasibility_estimate",
                "scenario_12m_feasibility_estimate",
            ],
            6,
        ),
        "",
        "## Learning Plans",
        "",
    ]
    for record in summary.to_dict("records"):
        lines.extend(
            [
                f"### {record['target_occupation_name']}",
                "",
                f"- Skill reuse: {record['transition_span']}; missing skills: {record['number_of_missing_skills']}; training coverage: {record['training_coverage_ratio']}.",
                f"- Phase 1 Foundational skills: {record['learning_plan_phase_1_foundational_skills']}",
                f"- Phase 2 Domain / technical skills: {record['learning_plan_phase_2_domain_technical_skills']}",
                f"- Phase 3 Portfolio / job preparation: {record['learning_plan_phase_3_portfolio_job_preparation']}",
                f"- Missing skills: {record['missing_skills'] or '(none)'}",
                f"- Transition burden: hours={record['total_training_hours']}, direct cost={record['estimated_direct_course_cost']}, income interruption={record['possible_income_interruption']}.",
                "",
            ]
        )

    lines.extend(
        [
            "## Manual Review / Limitations",
            "",
            *md_table(
                manual_review,
                [
                    "target_occupation_name",
                    "taiwanjobs_mapping_confidence",
                    "taiwanjobs_manual_review_needed",
                    "limitation",
                ],
                10,
            ),
            "",
            "## Interpretation",
            "",
            "- Clinical Research Coordinators has the lowest training burden in this run, but its TaiwanJobs mapping still needs review and its mapped market signal is not a success probability.",
            "- Health Informatics Specialists, Clinical Data Managers, Medical Records Specialists, and Bioinformatics Technicians show plausible course coverage through data, systems, medical information, Python, statistics, and database-related courses.",
            "- Data Scientists is retained as the Major Reskilling comparator: current courses can cover some data/AI gaps, but the technology-specific gap and learning burden remain higher.",
            "- Course matching is limited by course-title-only evidence. Course content, subsidy, schedule, and learner opportunity cost are unavailable in the current raw file.",
        ]
    )
    NURSING_TECH_TRAINING_V4_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_raw_skill_wide(occupation_skills: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, str]]]:
    skills = occupation_skills.copy()
    skills["feature_id"] = skills["skill_type"] + ":" + skills["skill_id"]
    feature_meta = skills.drop_duplicates("feature_id").set_index("feature_id")[
        ["skill_name", "skill_type"]
    ].to_dict("index")
    wide = skills.pivot_table(
        index="occupation_code",
        columns="feature_id",
        values="importance_or_score",
        aggfunc="max",
        fill_value=0.0,
    )
    return wide, feature_meta


def directional_skill_metrics(
    source_vector: pd.Series,
    target_vector: pd.Series,
    feature_meta: dict[str, dict[str, str]],
) -> tuple[float, float]:
    coverages: list[float] = []
    gaps: list[float] = []
    for skill_type in SKILL_TYPE_WEIGHTS:
        type_features = [
            feature_id
            for feature_id, meta in feature_meta.items()
            if meta["skill_type"] == skill_type
        ]
        target_required = target_vector.loc[type_features]
        target_required = target_required.loc[target_required.ge(REQUIRED_SKILL_THRESHOLD)]
        if target_required.empty:
            continue

        source_required = source_vector.reindex(target_required.index).fillna(0.0)
        covered = np.minimum(
            source_required.to_numpy(dtype=float),
            target_required.to_numpy(dtype=float),
        )
        target_values = target_required.to_numpy(dtype=float)
        coverages.append(float(covered.sum() / target_values.sum()) if target_values.sum() else 0.0)
        gaps.append(float(np.maximum(target_values - source_required.to_numpy(dtype=float), 0.0).mean()))

    return float(np.mean(coverages)), float(np.mean(gaps))


def barrier_level_from_score(score: int) -> str:
    if score >= 3:
        return "high"
    if score == 2:
        return "medium"
    return "low"


def is_physician_like(title: str) -> bool:
    if title == "Physician Assistants":
        return False
    physician_tokens = [
        "Physician",
        "Physicians",
        "Surgeon",
        "Surgeons",
        "Neurologist",
        "Neurologists",
        "Hospitalist",
        "Hospitalists",
        "Cardiologist",
        "Cardiologists",
        "Anesthesiologist",
        "Anesthesiologists",
        "Ophthalmologist",
        "Ophthalmologists",
        "Obstetrician",
        "Obstetricians",
        "Gynecologist",
        "Gynecologists",
    ]
    return any(token in title for token in physician_tokens)


def education_barrier(source: pd.Series, target: pd.Series, target_title: str) -> tuple[str, str]:
    source_weighted = float(source.get("education_weighted_category", np.nan))
    target_weighted = float(target.get("education_weighted_category", np.nan))
    if np.isnan(target_weighted):
        return "unknown", "no O*NET required-level-of-education distribution available"

    target_master_plus = float(target.get("education_master_plus_share", 0.0) or 0.0)
    target_doctoral = float(target.get("education_doctoral_professional_share", 0.0) or 0.0)
    target_cert = float(target.get("professional_certification_importance", 0.0) or 0.0)
    target_modal = float(target.get("education_modal_category", 0.0) or 0.0)
    diff = target_weighted - source_weighted if not np.isnan(target_weighted) and not np.isnan(source_weighted) else np.nan

    score = 0
    reasons: list[str] = []
    if not np.isnan(diff) and diff >= 2.0:
        score += 2
        reasons.append(f"weighted education category +{diff:.1f}")
    elif not np.isnan(diff) and diff >= 1.0:
        score += 1
        reasons.append(f"weighted education category +{diff:.1f}")
    if target_master_plus >= 50.0:
        score += 1
        reasons.append(f"master's-or-higher share {target_master_plus:.1f}%")
    if target_doctoral >= 35.0:
        score += 2
        reasons.append(f"doctoral/professional/postdoctoral share {target_doctoral:.1f}%")
    if target_modal >= 10.0 or is_physician_like(target_title):
        score += 2
        reasons.append("doctoral/professional occupation pattern")
    if target_cert >= 4.25:
        score += 1
        reasons.append(f"professional certification importance {target_cert:.2f}")

    return barrier_level_from_score(score), "; ".join(reasons) if reasons else "no major upward education signal"


def training_experience_barrier(source: pd.Series, target: pd.Series) -> tuple[str, str]:
    source_rw = float(source.get("related_work_experience_weighted_category", np.nan))
    target_rw = float(target.get("related_work_experience_weighted_category", np.nan))
    source_oj = float(source.get("on_the_job_training_weighted_category", np.nan))
    target_oj = float(target.get("on_the_job_training_weighted_category", np.nan))
    target_apprenticeship = float(target.get("apprenticeship_importance", 0.0) or 0.0)

    rw_diff = target_rw - source_rw if not np.isnan(target_rw) and not np.isnan(source_rw) else np.nan
    oj_diff = target_oj - source_oj if not np.isnan(target_oj) and not np.isnan(source_oj) else np.nan

    score = 0
    reasons: list[str] = []
    if not np.isnan(rw_diff) and rw_diff >= 1.5:
        score += 2
        reasons.append(f"related work experience +{rw_diff:.1f} categories")
    elif not np.isnan(rw_diff) and rw_diff >= 0.75:
        score += 1
        reasons.append(f"related work experience +{rw_diff:.1f} categories")
    if not np.isnan(oj_diff) and oj_diff >= 1.5:
        score += 1
        reasons.append(f"on-the-job training +{oj_diff:.1f} categories")
    if target_apprenticeship >= 4.25:
        score += 2
        reasons.append(f"apprenticeship importance {target_apprenticeship:.2f}")
    elif target_apprenticeship >= 3.75:
        score += 1
        reasons.append(f"apprenticeship importance {target_apprenticeship:.2f}")

    return barrier_level_from_score(score), "; ".join(reasons) if reasons else "no major upward training/experience signal"


def credential_barrier(target: pd.Series, target_title: str) -> str:
    certification = float(target.get("professional_certification_importance", 0.0) or 0.0)
    if is_physician_like(target_title):
        return "high"
    if certification >= 4.5:
        return "high"
    if certification >= 3.75:
        return "medium"
    return "low"


def text_or_unknown(value: object) -> str:
    if pd.isna(value) or value == "":
        return "unknown"
    return str(value)


def classify_feasibility(
    row: dict[str, object],
    source_profile: pd.Series,
    target_profile: pd.Series,
) -> tuple[str, str, str]:
    title = str(row["target_occupation_name"])
    related_support = str(row["related_support"]) == "yes"
    related_tier = str(row.get("related_tier", ""))
    job_zone_difference = float(row["job_zone_difference"]) if row["job_zone_difference"] != "" else np.nan
    coverage = float(row["transferable_skill_coverage"])
    gap = float(row["target_skill_gap"])
    education = str(row["education_barrier"])
    training = str(row["training_experience_barrier"])
    credential = str(row["credential_barrier"])
    same_nursing_domain = "Nurs" in title
    target_doctoral = float(target_profile.get("education_doctoral_professional_share", 0.0) or 0.0)
    target_modal = float(target_profile.get("education_modal_category", 0.0) or 0.0)

    high_barrier = (
        is_physician_like(title)
        or title == "Physical Therapists"
        or (not np.isnan(job_zone_difference) and job_zone_difference >= 2)
        or (
            education == "high"
            and not same_nursing_domain
            and (target_doctoral >= 35.0 or target_modal >= 10.0)
        )
    )

    if high_barrier:
        return (
            "exclude",
            "Infeasible / high-barrier",
            "Skill-similar, but education/licensing or preparation barrier is too large for short-term transition screening.",
        )

    if (
        coverage >= 0.92
        and gap <= 0.25
        and education in {"low", "medium"}
        and training in {"low", "medium"}
        and (related_support or (not np.isnan(job_zone_difference) and job_zone_difference < 0))
    ):
        return (
            "candidate",
            "Adjacent candidate",
            "High directional skill coverage with low-to-medium preparation barrier.",
        )

    if (
        coverage >= 0.88
        and gap <= 0.45
        and (not np.isnan(job_zone_difference) and job_zone_difference <= 1)
        and (
            education != "high"
            or same_nursing_domain
            or related_support
            or (target_doctoral < 20.0 and coverage >= 0.95 and gap <= 0.15)
            or education == "unknown"
        )
    ):
        if same_nursing_domain:
            note = "Same nursing domain, but additional education or teaching/advanced-practice preparation is visible."
        elif related_support:
            note = f"O*NET related support ({related_tier}) with manageable directional skill gap."
        elif credential == "high":
            note = "Skill-similar option with a credential barrier; keep as bridge candidate, not adjacent."
        else:
            note = "Skill-similar non-obvious option with manageable directional skill gap; needs domain validation."
        return "review", "Bridge candidate", note

    return (
        "exclude",
        "Infeasible / high-barrier",
        "Does not pass current directional skill and preparation-barrier screen.",
    )


def describe_missing_skills(
    source_vector: pd.Series,
    target_vector: pd.Series,
    feature_meta: dict[str, dict[str, str]],
    limit: int = 6,
) -> str:
    gap_series = target_vector - source_vector
    missing_skills: list[str] = []
    for feature_id, gap in gap_series.sort_values(ascending=False).items():
        target_value = float(target_vector[feature_id])
        if gap < SKILL_GAP_REPORT_THRESHOLD or target_value < 3.5:
            break
        meta = feature_meta[feature_id]
        missing_skills.append(
            f"{meta['skill_name']} ({meta['skill_type']}: target {target_value:.2f}, RN {source_vector[feature_id]:.2f})"
        )
        if len(missing_skills) >= limit:
            break
    return format_skill_list(missing_skills, limit=limit)


def describe_shared_skills(
    source_vector: pd.Series,
    target_vector: pd.Series,
    feature_meta: dict[str, dict[str, str]],
    limit: int = 8,
) -> str:
    shared_strength = np.minimum(source_vector.to_numpy(dtype=float), target_vector.to_numpy(dtype=float))
    shared_series = pd.Series(shared_strength, index=target_vector.index)
    shared_top: list[str] = []
    for feature_id, value in shared_series.sort_values(ascending=False).head(12).items():
        if value <= 0:
            continue
        meta = feature_meta[feature_id]
        shared_top.append(f"{meta['skill_name']} ({meta['skill_type']}: {value:.2f})")
    return format_skill_list(shared_top, limit=limit)


def build_candidate_pool(
    similarity_df: pd.DataFrame,
    occupation_names: dict[str, str],
    related_from_source: pd.DataFrame,
) -> pd.DataFrame:
    nursing_scores = similarity_df.loc[NURSING_CODE].drop(index=NURSING_CODE)
    top_skill = nursing_scores.sort_values(ascending=False).head(20).reset_index()
    top_skill.columns = ["target_occupation_code", "skill_similarity"]
    top_skill["v1_skill_similarity_rank"] = range(1, len(top_skill) + 1)
    top_skill["candidate_pool_source"] = "skill_similarity_top20"

    related_candidates = related_from_source.rename(
        columns={"target_occupation_code": "target_occupation_code"}
    )[["target_occupation_code", "related_tier", "related_index"]].copy()
    related_candidates["candidate_pool_source"] = "onet_related_occupation"

    focus_codes = [
        code
        for code, title in occupation_names.items()
        if any(pattern in title for pattern in FOCUS_TITLE_PATTERNS)
    ]
    focus_candidates = pd.DataFrame(
        {
            "target_occupation_code": focus_codes,
            "candidate_pool_source": "focus_check",
        }
    )

    pool = pd.concat(
        [
            top_skill[["target_occupation_code", "v1_skill_similarity_rank", "skill_similarity", "candidate_pool_source"]],
            related_candidates,
            focus_candidates,
        ],
        ignore_index=True,
    )
    pool = (
        pool.groupby("target_occupation_code", as_index=False)
        .agg(
            {
                "v1_skill_similarity_rank": "min",
                "skill_similarity": "max",
                "related_tier": "first",
                "related_index": "first",
                "candidate_pool_source": lambda values: "; ".join(sorted(set(values.dropna()))),
            }
        )
    )
    pool["skill_similarity"] = pool["target_occupation_code"].map(nursing_scores).fillna(pool["skill_similarity"])
    pool["target_occupation_name"] = pool["target_occupation_code"].map(occupation_names)
    pool = pool.loc[pool["target_occupation_code"].ne(NURSING_CODE) & pool["skill_similarity"].notna()].copy()
    return pool


def nursing_feasibility_v2(occupation_skills: pd.DataFrame) -> pd.DataFrame:
    occupations = pd.read_csv(ONET_OCCUPATION_DATA).rename(
        columns={"O*NET-SOC Code": "occupation_code", "Title": "occupation_name"}
    )
    occupation_names = occupations.set_index("occupation_code")["occupation_name"].to_dict()
    related = pd.read_csv(ONET_RELATED_OCCUPATIONS).rename(
        columns={
            "O*NET-SOC Code": "occupation_code",
            "Related O*NET-SOC Code": "target_occupation_code",
            "Relatedness Tier": "related_tier",
            "Index": "related_index",
        }
    )
    related_from_source = related.loc[related["occupation_code"].eq(NURSING_CODE)].copy()

    _, similarity_df = build_weighted_similarity_matrix(occupation_skills)
    raw_wide, feature_meta = build_raw_skill_wide(occupation_skills)
    profiles = build_occupation_feasibility_profile().set_index("occupation_code")
    source_profile = profiles.loc[NURSING_CODE]
    source_vector = raw_wide.loc[NURSING_CODE]
    pool = build_candidate_pool(similarity_df, occupation_names, related_from_source)

    related_lookup = related_from_source.set_index("target_occupation_code")[
        ["related_tier", "related_index"]
    ].to_dict("index")

    records: list[dict[str, object]] = []
    for _, candidate in pool.iterrows():
        target_code = str(candidate["target_occupation_code"])
        target_title = str(candidate["target_occupation_name"])
        target_profile = profiles.loc[target_code]
        target_vector = raw_wide.loc[target_code]
        coverage, gap = directional_skill_metrics(source_vector, target_vector, feature_meta)
        related_support = related_lookup.get(target_code)
        education_level, education_reasons = education_barrier(source_profile, target_profile, target_title)
        training_level, training_reasons = training_experience_barrier(source_profile, target_profile)
        credential_level = credential_barrier(target_profile, target_title)

        job_zone_difference = target_profile["job_zone"] - source_profile["job_zone"]
        record = {
            "source_occupation_code": NURSING_CODE,
            "source_occupation_name": occupation_names.get(NURSING_CODE, "Registered Nurses"),
            "target_occupation_code": target_code,
            "target_occupation_name": target_title,
            "candidate_pool_source": candidate["candidate_pool_source"],
            "v1_skill_similarity_rank": "" if pd.isna(candidate.get("v1_skill_similarity_rank")) else int(candidate["v1_skill_similarity_rank"]),
            "skill_similarity": round(float(candidate["skill_similarity"]), 6),
            "transferable_skill_coverage": round(coverage, 6),
            "target_skill_gap": round(gap, 6),
            "related_support": "yes" if related_support else "no",
            "related_tier": related_support["related_tier"] if related_support else "",
            "related_index": int(related_support["related_index"]) if related_support else "",
            "source_job_zone": int(source_profile["job_zone"]) if not pd.isna(source_profile["job_zone"]) else "",
            "target_job_zone": int(target_profile["job_zone"]) if not pd.isna(target_profile["job_zone"]) else "",
            "job_zone_difference": int(job_zone_difference) if not pd.isna(job_zone_difference) else "",
            "source_modal_education": source_profile.get("education_modal_label", ""),
            "target_modal_education": text_or_unknown(target_profile.get("education_modal_label", "")),
            "target_master_plus_share": round(float(target_profile.get("education_master_plus_share", 0.0) or 0.0), 3),
            "target_doctoral_professional_share": round(
                float(target_profile.get("education_doctoral_professional_share", 0.0) or 0.0),
                3,
            ),
            "education_barrier": education_level,
            "education_barrier_notes": education_reasons,
            "source_related_work_experience": text_or_unknown(source_profile.get("related_work_experience_modal_label", "")),
            "target_related_work_experience": text_or_unknown(target_profile.get("related_work_experience_modal_label", "")),
            "target_on_the_job_training": text_or_unknown(target_profile.get("on_the_job_training_modal_label", "")),
            "training_experience_barrier": training_level,
            "training_experience_barrier_notes": training_reasons,
            "credential_barrier": credential_level,
            "professional_certification_importance": round(
                float(target_profile.get("professional_certification_importance", 0.0) or 0.0),
                3,
            ),
            "apprenticeship_importance": round(
                float(target_profile.get("apprenticeship_importance", 0.0) or 0.0),
                3,
            ),
            "shared_top_skills": describe_shared_skills(source_vector, target_vector, feature_meta),
            "missing_skills": describe_missing_skills(source_vector, target_vector, feature_meta),
        }
        flag, level, notes = classify_feasibility(record, source_profile, target_profile)
        record["feasibility_flag"] = flag
        record["feasibility_level"] = level
        record["feasibility_notes"] = notes
        records.append(record)

    result = pd.DataFrame.from_records(records)
    level_order = {
        "Adjacent candidate": 0,
        "Bridge candidate": 1,
        "Infeasible / high-barrier": 2,
    }
    result["_level_order"] = result["feasibility_level"].map(level_order)
    result = result.sort_values(
        ["_level_order", "skill_similarity", "related_index"],
        ascending=[True, False, True],
        na_position="last",
    ).drop(columns="_level_order")
    result.insert(0, "v2_rank", range(1, len(result) + 1))
    result.to_csv(NURSING_FEASIBILITY_V2_CSV, index=False, encoding="utf-8")
    write_nursing_feasibility_v2_md(result)
    return result


def write_nursing_feasibility_v2_md(result: pd.DataFrame) -> None:
    level_counts = result["feasibility_level"].value_counts().to_dict()
    focus_rows = result.loc[
        result["target_occupation_name"].apply(
            lambda title: any(pattern in str(title) for pattern in FOCUS_TITLE_PATTERNS)
        )
    ].copy()

    lines = [
        "# Nursing Career Transition Feasibility v2",
        "",
        "Source occupation: O*NET `29-1141.00` Registered Nurses.",
        "",
        "This output adds directional feasibility screening to the v1 skill-similarity graph. It does not estimate transition success probability.",
        "",
        "## Summary",
        "",
        f"- Adjacent candidates: {level_counts.get('Adjacent candidate', 0)}",
        f"- Bridge candidates: {level_counts.get('Bridge candidate', 0)}",
        f"- Infeasible / high-barrier: {level_counts.get('Infeasible / high-barrier', 0)}",
        "",
        "## Candidate Ranking",
        "",
        "| v2 Rank | v1 Rank | Target Occupation | Skill Similarity | Coverage | Gap | Related | Job Zones | Education Barrier | Training/Experience Barrier | Feasibility |",
        "|---:|---:|---|---:|---:|---:|---|---|---|---|---|",
    ]
    for record in result.head(30).to_dict("records"):
        related = record["related_support"]
        if record["related_tier"]:
            related = f"{related} ({record['related_tier']})"
        v1_rank = record["v1_skill_similarity_rank"] if record["v1_skill_similarity_rank"] != "" else ""
        lines.append(
            "| {v2_rank} | {v1_rank} | `{target_occupation_code}` {target_occupation_name} | {skill_similarity:.3f} | {coverage:.3f} | {gap:.3f} | {related} | {source_job_zone}->{target_job_zone} | {education_barrier} | {training_experience_barrier} | {feasibility_level} |".format(
                v2_rank=record["v2_rank"],
                v1_rank=v1_rank,
                target_occupation_code=record["target_occupation_code"],
                target_occupation_name=record["target_occupation_name"],
                skill_similarity=record["skill_similarity"],
                coverage=record["transferable_skill_coverage"],
                gap=record["target_skill_gap"],
                related=related,
                source_job_zone=record["source_job_zone"],
                target_job_zone=record["target_job_zone"],
                education_barrier=record["education_barrier"],
                training_experience_barrier=record["training_experience_barrier"],
                feasibility_level=record["feasibility_level"],
            )
        )

    lines.extend(
        [
            "",
            "## Required Checks",
            "",
            "| Occupation | v1 Rank | v2 Level | Education Barrier | Training/Experience Barrier | Credential Barrier | Notes |",
            "|---|---:|---|---|---|---|---|",
        ]
    )
    for record in focus_rows.to_dict("records"):
        v1_rank = record["v1_skill_similarity_rank"] if record["v1_skill_similarity_rank"] != "" else ""
        notes = str(record["feasibility_notes"]).replace("|", "\\|")
        lines.append(
            f"| `{record['target_occupation_code']}` {record['target_occupation_name']} | {v1_rank} | {record['feasibility_level']} | {record['education_barrier']} | {record['training_experience_barrier']} | {record['credential_barrier']} | {notes} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- v1 ranks occupations by symmetric skill similarity, so several physician occupations appear close to Registered Nurses.",
            "- v2 keeps those rows visible but marks physician/doctoral-professional occupations as `Infeasible / high-barrier` because the education and credential pathway is structurally different.",
            "- Non-obvious healthcare-adjacent options such as Athletic Trainers, Exercise Physiologists, and Medical Assistants remain visible when directional skill coverage is high and barriers are not exclusionary.",
            "- Hidden Path is intentionally not assigned in v2; it needs occupation-category distance and labor-market evidence before being defined.",
            "",
            "See `docs/career_transition_feasibility_v2_method.md` for formulas and constraint definitions.",
        ]
    )
    NURSING_FEASIBILITY_V2_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def format_skill_list(items: list[str], limit: int = 6) -> str:
    return "; ".join(items[:limit])


def nursing_exploration(occupation_skills: pd.DataFrame) -> pd.DataFrame:
    occupations = pd.read_csv(ONET_OCCUPATION_DATA).rename(
        columns={"O*NET-SOC Code": "occupation_code", "Title": "occupation_name"}
    )
    related = pd.read_csv(ONET_RELATED_OCCUPATIONS).rename(
        columns={
            "O*NET-SOC Code": "occupation_code",
            "Related O*NET-SOC Code": "target_occupation_code",
            "Relatedness Tier": "onet_related_tier",
            "Index": "onet_related_index",
        }
    )
    related_from_nursing = related.loc[related["occupation_code"].eq(NURSING_CODE)].copy()
    related_lookup = related_from_nursing.set_index("target_occupation_code")[
        ["onet_related_tier", "onet_related_index"]
    ].to_dict("index")

    _, similarity_df = build_weighted_similarity_matrix(occupation_skills)
    if NURSING_CODE not in similarity_df.index:
        raise RuntimeError(f"Nursing occupation code not found in skill matrix: {NURSING_CODE}")

    nursing_scores = similarity_df.loc[NURSING_CODE].drop(index=NURSING_CODE)
    top_codes = nursing_scores.sort_values(ascending=False).head(20).index.tolist()

    skill_lookup = occupation_skills.copy()
    skill_lookup["feature_id"] = skill_lookup["skill_type"] + ":" + skill_lookup["skill_id"]
    skill_lookup["normalized_score"] = skill_lookup["importance_or_score"] / 5.0
    feature_meta = skill_lookup.drop_duplicates("feature_id").set_index("feature_id")[
        ["skill_name", "skill_type"]
    ].to_dict("index")
    wide = skill_lookup.pivot_table(
        index="occupation_code",
        columns="feature_id",
        values="importance_or_score",
        aggfunc="max",
        fill_value=0.0,
    )

    source_vector = wide.loc[NURSING_CODE]
    source_total = float(source_vector.sum())
    occupation_name = occupations.set_index("occupation_code")["occupation_name"].to_dict()

    records: list[dict[str, object]] = []
    for rank, target_code in enumerate(top_codes, start=1):
        target_vector = wide.loc[target_code]
        shared_strength = np.minimum(source_vector.to_numpy(dtype=float), target_vector.to_numpy(dtype=float))
        overlap_score = float(shared_strength.sum() / source_total) if source_total else 0.0

        shared_series = pd.Series(shared_strength, index=wide.columns)
        shared_top: list[str] = []
        for feature_id, value in shared_series.sort_values(ascending=False).head(12).items():
            if value <= 0:
                continue
            meta = feature_meta[feature_id]
            shared_top.append(f"{meta['skill_name']} ({meta['skill_type']}: {value:.2f})")

        gap_series = target_vector - source_vector
        missing_skills: list[str] = []
        for feature_id, gap in gap_series.sort_values(ascending=False).items():
            target_value = float(target_vector[feature_id])
            if gap < 0.75 or target_value < 3.5:
                break
            meta = feature_meta[feature_id]
            missing_skills.append(
                f"{meta['skill_name']} ({meta['skill_type']}: target {target_value:.2f}, RN {source_vector[feature_id]:.2f})"
            )
            if len(missing_skills) >= 6:
                break

        related_support = related_lookup.get(target_code)
        records.append(
            {
                "rank": rank,
                "source_occupation_code": NURSING_CODE,
                "source_occupation_name": occupation_name.get(NURSING_CODE, "Registered Nurses"),
                "target_occupation_code": target_code,
                "target_occupation_name": occupation_name.get(target_code, ""),
                "onet_skill_similarity": round(float(nursing_scores[target_code]), 6),
                "skill_overlap_score": round(overlap_score, 6),
                "shared_top_skills": format_skill_list(shared_top, limit=8),
                "missing_skills": format_skill_list(missing_skills, limit=6),
                "onet_related_support": "yes" if related_support else "no",
                "onet_related_tier": related_support["onet_related_tier"] if related_support else "",
                "onet_related_index": int(related_support["onet_related_index"]) if related_support else "",
            }
        )

    result = pd.DataFrame.from_records(records)
    result.to_csv(NURSING_EXPLORATION_CSV, index=False, encoding="utf-8")
    write_nursing_md(result)
    return result


def write_nursing_md(result: pd.DataFrame) -> None:
    supported = int(result["onet_related_support"].eq("yes").sum())
    lines = [
        "# Nursing Career Transition Exploration",
        "",
        "Source occupation: O*NET `29-1141.00` Registered Nurses.",
        "",
        "This is an evidence-based graph sanity check, not a job-market forecast and not a transition success probability.",
        "",
        "## Method",
        "",
        "- Skill backbone: O*NET 31.0 `essential_skills.csv`, `transferable_skills.csv`, and `knowledge.csv`.",
        "- Similarity signal: weighted cosine similarity over O*NET IM importance scores.",
        "- Normalization: IM scores are divided by 5.0; each skill type is L2-normalized per occupation and weighted equally across essential skills, transferable skills, and knowledge.",
        "- O*NET Related Occupations is reported as a separate support signal from `related_occupations.csv` and is not merged into the similarity score.",
        "",
        f"Top 20 skill-similar occupations with O*NET related support: {supported}/20.",
        "",
        "| Rank | Target Occupation | O*NET Skill Similarity | Skill Overlap | O*NET Related Support | Shared Top Skills | Missing Skills |",
        "|---:|---|---:|---:|---|---|---|",
    ]
    for record in result.to_dict("records"):
        related = record["onet_related_support"]
        if record["onet_related_tier"]:
            related = f"{related} ({record['onet_related_tier']}, index {record['onet_related_index']})"
        lines.append(
            "| {rank} | `{target_occupation_code}` {target_occupation_name} | {onet_skill_similarity:.3f} | {skill_overlap_score:.3f} | {related} | {shared} | {missing} |".format(
                rank=record["rank"],
                target_occupation_code=record["target_occupation_code"],
                target_occupation_name=record["target_occupation_name"],
                onet_skill_similarity=record["onet_skill_similarity"],
                skill_overlap_score=record["skill_overlap_score"],
                related=related,
                shared=str(record["shared_top_skills"]).replace("|", "\\|"),
                missing=str(record["missing_skills"]).replace("|", "\\|") or "(none above threshold)",
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- `onet_skill_similarity` explains proximity in O*NET skill/knowledge space.",
            "- `onet_related_support` reflects O*NET's curated related occupation table.",
            "- Neither field should be interpreted as labor-market demand, wage fit, licensing feasibility, training availability, or transition success rate.",
        ]
    )
    NURSING_EXPLORATION_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    inventory = build_inventory()
    write_inventory_md(inventory)
    write_feasibility_method_md()
    occupation_skills = build_occupation_skills()
    nursing = nursing_exploration(occupation_skills)
    nursing_v2 = nursing_feasibility_v2(occupation_skills)
    nursing_v3 = nursing_market_v3(nursing_v2)
    nursing_v35 = nursing_to_technology_v35(occupation_skills)
    nursing_v4, training_mapping_v4, training_inventory_v4 = build_training_v4_summary(occupation_skills, nursing_v35)

    print(f"Wrote {INVENTORY_MD.relative_to(ROOT)} rows={len(inventory)}")
    print(f"Wrote {FEASIBILITY_METHOD_MD.relative_to(ROOT)}")
    print(f"Wrote {MARKET_V3_METHOD_MD.relative_to(ROOT)}")
    print(f"Wrote {TARGET_DOMAIN_V35_METHOD_MD.relative_to(ROOT)}")
    print(f"Wrote {TRAINING_V4_METHOD_MD.relative_to(ROOT)}")
    print(f"Wrote {OCCUPATION_SKILLS_CSV.relative_to(ROOT)} rows={len(occupation_skills)}")
    print(f"Wrote {NURSING_EXPLORATION_CSV.relative_to(ROOT)} rows={len(nursing)}")
    print(f"Wrote {NURSING_EXPLORATION_MD.relative_to(ROOT)}")
    print(f"Wrote {NURSING_FEASIBILITY_V2_CSV.relative_to(ROOT)} rows={len(nursing_v2)}")
    print(f"Wrote {NURSING_FEASIBILITY_V2_MD.relative_to(ROOT)}")
    print(f"Wrote {ONET_TAIWANJOBS_MAPPING_CSV.relative_to(ROOT)} rows={len(pd.read_csv(ONET_TAIWANJOBS_MAPPING_CSV))}")
    print(f"Wrote {NURSING_MARKET_V3_CSV.relative_to(ROOT)} rows={len(nursing_v3)}")
    print(f"Wrote {NURSING_MARKET_V3_MD.relative_to(ROOT)}")
    print(f"Wrote {NURSING_TECH_CANDIDATES_V35_CSV.relative_to(ROOT)} rows={len(nursing_v35)}")
    print(f"Wrote {NURSING_TECH_EXPLORATION_V35_MD.relative_to(ROOT)}")
    print(f"Wrote {CAREER_TRAINING_SKILL_MAPPING_CSV.relative_to(ROOT)} rows={len(training_mapping_v4)}")
    print(f"Wrote {NURSING_TECH_TRAINING_V4_CSV.relative_to(ROOT)} rows={len(nursing_v4)}")
    print(f"Wrote {NURSING_TECH_TRAINING_V4_MD.relative_to(ROOT)}")
    print(f"Training rows={training_inventory_v4['rows']} encoding={training_inventory_v4['encoding']}")
    print(nursing[["rank", "target_occupation_code", "target_occupation_name", "onet_skill_similarity", "onet_related_support"]].to_string(index=False))
    print(nursing_v2[["v2_rank", "target_occupation_code", "target_occupation_name", "skill_similarity", "transferable_skill_coverage", "target_skill_gap", "feasibility_level"]].head(30).to_string(index=False))
    print(nursing_v3[["v2_rank", "target_occupation_code", "target_occupation_name", "feasibility_level", "market_validation", "taxonomy_distance_level", "mapping_confidence"]].head(30).to_string(index=False))
    print(nursing_v35[["target_domain_evidence_rank", "target_occupation_code", "target_occupation_name", "transition_span", "feasibility_level", "market_validation", "taxonomy_distance_level", "mapping_confidence"]].head(50).to_string(index=False))
    print(nursing_v4[["target_occupation_name", "transition_span", "number_of_missing_skills", "number_of_trainable_skills_found", "training_coverage_ratio", "gap_skill_training_coverage_ratio", "total_training_hours", "estimated_direct_course_cost", "learning_burden_level"]].to_string(index=False))


if __name__ == "__main__":
    main()
