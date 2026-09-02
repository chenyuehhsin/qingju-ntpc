from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_cleaner import (  # noqa: E402
    STANDARD_DISTRICTS,
    detect_dataset_kind,
    detect_mapping,
    normalize_district,
    normalize_work_type,
    parse_age,
    parse_number,
    parse_salary,
    top_value,
    youth_age_columns,
)
from src.data_loader import PROCESSED_DIR, RAW_DIR, find_files, read_csv, read_json_rows  # noqa: E402
from src.data_loader import read_xml_rows  # noqa: E402
from src.metrics import jobs_per_1000_youth  # noqa: E402
from src.metrics import (  # noqa: E402
    add_opportunity_index_scores,
    count_present,
    coverage_percentage,
    employment_stability_score,
    normalized_shannon_entropy,
)


def profile_csv(path: Path, df: pd.DataFrame, mapping) -> dict:
    null_counts = df.isna().sum().to_dict()
    return {
        "filename": str(path.relative_to(PROJECT_ROOT)),
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "first_5_rows": df.head(5).where(pd.notna(df.head(5)), None).to_dict(orient="records"),
        "missing_values": {str(key): int(value) for key, value in null_counts.items()},
        "duplicate_rows": int(df.duplicated().sum()),
            "detected_columns": {
                "district": mapping.district,
                "age": mapping.age,
                "job_openings": mapping.job_openings,
                "salary": mapping.salary,
                "salary_type": mapping.salary_type,
                "salary_min": mapping.salary_min,
            "salary_max": mapping.salary_max,
            "job_category": mapping.job_category,
            "occupation": mapping.occupation,
            "industry": mapping.industry,
            "company": mapping.company,
            "address": mapping.address,
            "work_type": mapping.work_type,
        },
    }


def numeric_sum(values: pd.Series) -> float | pd.NA:
    return pd.to_numeric(values, errors="coerce").sum(min_count=1)


def numeric_mean(values: pd.Series) -> float | pd.NA:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return pd.NA
    return float(numeric.mean())


def numeric_median(values: pd.Series) -> float | pd.NA:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return pd.NA
    return float(numeric.median())


def nonempty_nunique(values: pd.Series) -> int:
    clean = values.dropna()
    clean = clean[clean.astype(str).str.strip() != ""]
    return int(clean.nunique())


def build_population_by_district(source_frames: list[tuple[Path, pd.DataFrame, object, str, str]]) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []

    for path, df, mapping, kind, _source_type in source_frames:
        if kind != "population" or mapping.district is None:
            continue

        working = df.copy()
        working["district"] = working[mapping.district].map(normalize_district)
        working = working.dropna(subset=["district"])

        youth_columns = youth_age_columns(working)
        if youth_columns:
            numeric = working[youth_columns].apply(pd.to_numeric, errors="coerce")
            piece = pd.DataFrame(
                {
                    "district": working["district"],
                    "youth_population_18_35": numeric.sum(axis=1, min_count=1),
                    "population_source_file": path.name,
                }
            )
            pieces.append(piece)
            continue

        if mapping.age and mapping.population:
            working["_age"] = working[mapping.age].map(parse_age)
            working["_population"] = working[mapping.population].map(parse_number)
            youth = working[working["_age"].between(18, 35, inclusive="both")]
            piece = (
                youth.groupby("district", as_index=False)["_population"]
                .agg(numeric_sum)
                .rename(columns={"_population": "youth_population_18_35"})
            )
            piece["population_source_file"] = path.name
            pieces.append(piece)
            continue

        if mapping.population and "youth" in path.name.lower():
            working["_population"] = working[mapping.population].map(parse_number)
            piece = (
                working.groupby("district", as_index=False)["_population"]
                .agg(numeric_sum)
                .rename(columns={"_population": "youth_population_18_35"})
            )
            piece["population_source_file"] = path.name
            pieces.append(piece)

    if not pieces:
        return pd.DataFrame(columns=["district", "youth_population_18_35", "population_source_file"])

    combined = pd.concat(pieces, ignore_index=True)
    return (
        combined.groupby("district", as_index=False)
        .agg(
            youth_population_18_35=("youth_population_18_35", numeric_sum),
            population_source_file=("population_source_file", lambda values: ";".join(sorted(set(values)))),
        )
    )


def build_jobs_by_district(source_frames: list[tuple[Path, pd.DataFrame, object, str, str]]) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []

    for path, df, mapping, kind, _source_type in source_frames:
        if kind != "jobs":
            continue

        district_source = mapping.address or mapping.district
        if district_source is None:
            continue

        working = df.copy()
        working["district"] = working[district_source].map(normalize_district)
        if working["district"].isna().all() and mapping.district and mapping.district != district_source:
            district_source = mapping.district
            working["district"] = working[district_source].map(normalize_district)
        working = working.dropna(subset=["district"])
        if working.empty:
            continue

        normalized = pd.DataFrame({"district": working["district"]})
        normalized["_job_posting"] = 1
        if mapping.job_openings:
            normalized["_job_openings"] = working[mapping.job_openings].map(parse_number)
        else:
            normalized["_job_openings"] = pd.NA

        if mapping.salary_min and mapping.salary_max:
            low = working[mapping.salary_min].map(parse_number)
            high = working[mapping.salary_max].map(parse_number)
            normalized["_salary"] = pd.concat([low, high], axis=1).mean(axis=1, skipna=True)
            if mapping.salary_type:
                monthly = working[mapping.salary_type].astype(str).str.contains("月薪", na=False)
                normalized.loc[~monthly, "_salary"] = pd.NA
        elif mapping.salary:
            normalized["_salary"] = working[mapping.salary].map(parse_salary)
        else:
            normalized["_salary"] = pd.NA

        normalized["_job_category"] = working[mapping.job_category] if mapping.job_category else pd.NA
        normalized["_occupation"] = working[mapping.occupation] if mapping.occupation else pd.NA
        normalized["_industry"] = working[mapping.industry] if mapping.industry else pd.NA
        normalized["_company"] = working[mapping.company] if mapping.company else pd.NA
        normalized["_work_type"] = working[mapping.work_type].map(normalize_work_type) if mapping.work_type else pd.NA
        normalized["_source_file"] = path.name
        pieces.append(normalized)

    if not pieces:
        return pd.DataFrame(
            columns=[
                "district",
                "job_postings",
                "job_openings",
                "avg_salary",
                "median_salary",
                "top_job_category",
                "top_occupation",
                "top_industry",
                "company_count",
                "category_count",
                "salary_valid_count",
                "category_valid_count",
                "work_type_valid_count",
                "salary_sample_size",
                "diversity_sample_size",
                "stability_sample_size",
                "salary_data_coverage",
                "category_data_coverage",
                "work_type_data_coverage",
                "job_diversity_score",
                "employment_stability_score",
                "jobs_source_file",
            ]
        )

    combined = pd.concat(pieces, ignore_index=True)
    return (
        combined.groupby("district", as_index=False)
        .agg(
            job_postings=("_job_posting", numeric_sum),
            job_openings=("_job_openings", numeric_sum),
            avg_salary=("_salary", numeric_mean),
            median_salary=("_salary", numeric_median),
            top_job_category=("_job_category", top_value),
            top_occupation=("_occupation", top_value),
            top_industry=("_industry", top_value),
            company_count=("_company", lambda values: int(values.dropna().nunique())),
            category_count=("_job_category", nonempty_nunique),
            salary_valid_count=("_salary", count_present),
            category_valid_count=("_job_category", count_present),
            work_type_valid_count=("_work_type", count_present),
            salary_data_coverage=("_salary", coverage_percentage),
            category_data_coverage=("_job_category", coverage_percentage),
            work_type_data_coverage=("_work_type", coverage_percentage),
            job_diversity_score=("_job_category", normalized_shannon_entropy),
            employment_stability_score=("_work_type", employment_stability_score),
            jobs_source_file=("_source_file", lambda values: ";".join(sorted(set(values.dropna())))),
        )
    )


def build_dataset() -> tuple[pd.DataFrame, list[dict]]:
    raw_csvs = find_files(RAW_DIR, [".csv"])
    raw_jsons = [
        path
        for path in find_files(RAW_DIR, [".json"])
        if path.name not in {"source_manifest.json", "ris_openapi_docs.json"}
    ]
    raw_xmls = find_files(RAW_DIR, [".xml"])
    source_frames: list[tuple[Path, pd.DataFrame, object, str, str]] = []
    profiles: list[dict] = []

    for path in raw_csvs:
        df = read_csv(path)
        mapping = detect_mapping(df)
        kind = detect_dataset_kind(path, df, mapping)
        source_frames.append((path, df, mapping, kind, "csv"))
        csv_profile = profile_csv(path, df, mapping)
        csv_profile["dataset_kind"] = kind
        csv_profile["source_type"] = "csv"
        profiles.append(csv_profile)

    for path in raw_jsons:
        df, metadata = read_json_rows(path)
        if df.empty:
            continue
        mapping = detect_mapping(df)
        kind = detect_dataset_kind(path, df, mapping)
        source_frames.append((path, df, mapping, kind, "json"))
        json_profile = profile_csv(path, df, mapping)
        json_profile["dataset_kind"] = kind
        json_profile["source_type"] = "json"
        json_profile["metadata"] = metadata
        profiles.append(json_profile)

    for path in raw_xmls:
        df, metadata = read_xml_rows(path)
        mapping = detect_mapping(df)
        kind = detect_dataset_kind(path, df, mapping)
        source_frames.append((path, df, mapping, kind, "xml"))
        xml_profile = profile_csv(path, df, mapping)
        xml_profile["dataset_kind"] = kind
        xml_profile["source_type"] = "xml"
        xml_profile["metadata"] = metadata
        profiles.append(xml_profile)

    base = pd.DataFrame({"district": STANDARD_DISTRICTS})
    population = build_population_by_district(source_frames)
    jobs = build_jobs_by_district(source_frames)

    result = base.merge(population, on="district", how="left").merge(jobs, on="district", how="left")
    result["jobs_per_1000_youth"] = [
        jobs_per_1000_youth(openings, youth)
        for openings, youth in zip(result["job_openings"], result["youth_population_18_35"], strict=False)
    ]
    result["salary_sample_size"] = result["salary_valid_count"]
    result["diversity_sample_size"] = result["category_valid_count"]
    result["stability_sample_size"] = result["work_type_valid_count"]
    result = add_opportunity_index_scores(result)
    result["processed_at"] = datetime.now().isoformat(timespec="seconds")

    ordered_columns = [
        "district",
        "youth_population_18_35",
        "job_postings",
        "job_openings",
        "jobs_per_1000_youth",
        "avg_salary",
        "median_salary",
        "top_job_category",
        "top_occupation",
        "top_industry",
        "company_count",
        "category_count",
        "salary_valid_count",
        "category_valid_count",
        "work_type_valid_count",
        "salary_sample_size",
        "diversity_sample_size",
        "stability_sample_size",
        "salary_data_coverage",
        "category_data_coverage",
        "work_type_data_coverage",
        "opportunity_score",
        "salary_score",
        "job_diversity_score",
        "employment_stability_score",
        "youth_employment_opportunity_index",
        "index_coverage",
        "index_available_dimensions",
        "opportunity_reliability",
        "salary_reliability",
        "diversity_reliability",
        "stability_reliability",
        "index_reliability_score",
        "index_reliability_level",
        "baseline_index",
        "scenario_b_index",
        "scenario_c_index",
        "scenario_d_index",
        "baseline_rank",
        "scenario_b_rank",
        "scenario_c_rank",
        "scenario_d_rank",
        "rank_min",
        "rank_max",
        "rank_range",
        "index_rank_stability",
        "population_source_file",
        "jobs_source_file",
        "processed_at",
    ]
    for column in ordered_columns:
        if column not in result.columns:
            result[column] = pd.NA

    return result[ordered_columns], profiles


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output, profiles = build_dataset()
    output_path = PROCESSED_DIR / "youth_employment_map.csv"
    profile_path = PROCESSED_DIR / "source_data_profile.json"

    output.to_csv(output_path, index=False, encoding="utf-8-sig")
    profile_path.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {output_path}")
    print(f"Rows: {len(output)}")
    print(f"Raw source files profiled: {len(profiles)}")
    if not profiles:
        print("No raw CSV/XML files found under data/raw; data metrics are left as NaN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
