from __future__ import annotations

import json
import math
from pathlib import Path
import shutil
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
    parse_number,
)
from src.data_loader import PROCESSED_CSV, RAW_DIR, find_files, read_xml_rows  # noqa: E402
from src.metrics import INDEX_WEIGHTS, RELIABILITY_CONFIG, SENSITIVITY_SCENARIOS  # noqa: E402

WEBSITE_DATA_DIR = PROJECT_ROOT / "website" / "data"
RAW_GEOJSON = PROJECT_ROOT / "data" / "raw" / "new_taipei_districts.geojson"


def clean_records(df: pd.DataFrame) -> list[dict]:
    records = df.astype(object).where(pd.notna(df), None).to_dict(orient="records")
    for record in records:
        for key, value in list(record.items()):
            if isinstance(value, float) and value.is_integer():
                record[key] = int(value)
    return records


def clean_json_value(value: object) -> object:
    if value is None:
        return None
    if value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        if value.is_integer():
            return int(value)
    if isinstance(value, dict):
        return {key: clean_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_json_value(item) for item in value]
    return value


def get_value(row: pd.Series, column: str | None) -> object:
    if column is None or column not in row.index:
        return None
    value = row[column]
    if pd.isna(value) or str(value).strip() == "":
        return None
    return value


def first_matching_column(df: pd.DataFrame, fragments: list[str]) -> str | None:
    for column in df.columns:
        compact = str(column).lower().replace(" ", "")
        if any(fragment.lower() in compact for fragment in fragments):
            return column
    return None


def salary_text(
    row: pd.Series,
    salary_min_col: str | None,
    salary_max_col: str | None,
    salary_col: str | None,
    salary_type_col: str | None,
) -> str | None:
    salary_type = get_value(row, salary_type_col)
    prefix = f"{salary_type} " if salary_type is not None else ""
    if salary_min_col or salary_max_col:
        low = get_value(row, salary_min_col)
        high = get_value(row, salary_max_col)
        low_num = parse_number(low) if low is not None else pd.NA
        high_num = parse_number(high) if high is not None else pd.NA
        if pd.notna(low_num) and pd.notna(high_num):
            return f"{prefix}{int(low_num):,}–{int(high_num):,}"
        if pd.notna(low_num):
            return f"{prefix}{int(low_num):,} 起"
        if pd.notna(high_num):
            return f"{prefix}最高 {int(high_num):,}"

    salary = get_value(row, salary_col)
    return str(salary) if salary is not None else None


def extract_job_records() -> dict[str, list[dict]]:
    jobs_by_district: dict[str, list[dict]] = {}
    for path in find_files(RAW_DIR, [".xml"]):
        df, _metadata = read_xml_rows(path)
        if df.empty:
            continue

        mapping = detect_mapping(df)
        if detect_dataset_kind(path, df, mapping) != "jobs":
            continue

        source_name = "台灣就業通" if "taiwanjobs" in str(path).lower() else "事求人"
        district_source = mapping.address or mapping.district
        url_col = first_matching_column(df, ["url_query", "view_url", "url"])
        updated_col = first_matching_column(df, ["trandate", "date_from", "announce_date"])
        deadline_col = first_matching_column(df, ["stop_date", "date_to"])
        work_type_col = mapping.work_type or first_matching_column(df, ["wk_type", "職務性質"])

        for _idx, row in df.iterrows():
            district = normalize_district(get_value(row, district_source))
            if pd.isna(district):
                continue

            address = get_value(row, mapping.address) or get_value(row, mapping.district)
            openings = parse_number(get_value(row, mapping.job_openings))
            salary_min = parse_number(get_value(row, mapping.salary_min))
            salary_max = parse_number(get_value(row, mapping.salary_max))
            job = {
                "source": source_name,
                "title": get_value(row, mapping.occupation),
                "company": get_value(row, mapping.company),
                "district": str(district),
                "address": address,
                "category": get_value(row, mapping.job_category),
                "openings": int(openings) if pd.notna(openings) else None,
                "salary_min": int(salary_min) if pd.notna(salary_min) else None,
                "salary_max": int(salary_max) if pd.notna(salary_max) else None,
                "salary_text": salary_text(row, mapping.salary_min, mapping.salary_max, mapping.salary, mapping.salary_type),
                "work_type": normalize_work_type(get_value(row, work_type_col)),
                "deadline": get_value(row, deadline_col),
                "updated_at": get_value(row, updated_col),
                "url": get_value(row, url_col),
            }
            jobs_by_district.setdefault(str(district), []).append(job)

    for district, jobs in jobs_by_district.items():
        jobs.sort(key=lambda item: (item["source"] != "台灣就業通", -(item["openings"] or 0), item["title"] or ""))

    return jobs_by_district


def analyze_job_data_quality(jobs_by_district: dict[str, list[dict]]) -> dict:
    jobs = [job for district_jobs in jobs_by_district.values() for job in district_jobs]
    total = len(jobs)
    fields = ["category", "salary_min", "salary_max", "work_type", "company", "openings"]

    def present(value: object) -> bool:
        try:
            if pd.isna(value):
                return False
        except (TypeError, ValueError):
            pass
        return value is not None and str(value).strip() != ""

    coverage = {}
    for field in fields:
        count = sum(1 for job in jobs if present(job.get(field)))
        coverage[field] = {
            "non_null_count": count,
            "coverage_percentage": round(count / total * 100, 1) if total else None,
        }

    def value_counts(field: str) -> list[dict]:
        series = pd.Series([job.get(field) for job in jobs])
        series = series.dropna()
        series = series[series.astype(str).str.strip() != ""]
        return [
            {"value": str(value), "count": int(count)}
            for value, count in series.astype(str).value_counts().items()
        ]

    return {
        "job_count": total,
        "field_coverage": coverage,
        "work_type_values": value_counts("work_type"),
        "category_values": value_counts("category"),
    }


def correlation_or_none(left: pd.Series, right: pd.Series) -> float | None:
    frame = pd.DataFrame({"left": pd.to_numeric(left, errors="coerce"), "right": pd.to_numeric(right, errors="coerce")}).dropna()
    if len(frame) < 2:
        return None
    return float(frame["left"].corr(frame["right"]))


def reliability_analysis(df: pd.DataFrame) -> dict:
    sample_columns = [
        "district",
        "youth_population_18_35",
        "job_postings",
        "job_openings",
        "salary_valid_count",
        "category_valid_count",
        "work_type_valid_count",
        "company_count",
        "salary_sample_size",
        "diversity_sample_size",
        "stability_sample_size",
    ]
    score_columns = [
        "district",
        "youth_employment_opportunity_index",
        "index_reliability_score",
        "index_reliability_level",
        "opportunity_reliability",
        "salary_reliability",
        "diversity_reliability",
        "stability_reliability",
        "index_rank_stability",
        "baseline_rank",
        "scenario_b_rank",
        "scenario_c_rank",
        "scenario_d_rank",
        "rank_min",
        "rank_max",
        "rank_range",
    ]
    top_rate_columns = ["district", "youth_population_18_35", "job_openings", "jobs_per_1000_youth"]
    high_index_cutoff = float(pd.to_numeric(df["youth_employment_opportunity_index"], errors="coerce").quantile(0.75))
    high_reliability_threshold = float(RELIABILITY_CONFIG["level_thresholds"]["high"])

    robust_high = df[
        (pd.to_numeric(df["youth_employment_opportunity_index"], errors="coerce") >= high_index_cutoff)
        & (pd.to_numeric(df["index_reliability_score"], errors="coerce") >= high_reliability_threshold)
    ][["district", "youth_employment_opportunity_index", "index_reliability_score", "index_reliability_level"]]
    high_index_low_reliability = df[
        (pd.to_numeric(df["youth_employment_opportunity_index"], errors="coerce") >= high_index_cutoff)
        & (df["index_reliability_level"] == "Low")
    ][["district", "youth_employment_opportunity_index", "index_reliability_score", "index_reliability_level"]]

    return {
        "sample_size_table": clean_records(df[sample_columns]),
        "reliability_table": clean_records(df[score_columns]),
        "small_denominator": {
            "correlations": {
                "youth_population_vs_jobs_per_1000_youth": correlation_or_none(df["youth_population_18_35"], df["jobs_per_1000_youth"]),
                "job_openings_vs_jobs_per_1000_youth": correlation_or_none(df["job_openings"], df["jobs_per_1000_youth"]),
            },
            "jobs_per_1000_youth_top_10": clean_records(
                df.sort_values("jobs_per_1000_youth", ascending=False).head(10)[top_rate_columns]
            ),
            "note": "Correlation is descriptive only and does not imply causality.",
        },
        "sensitivity_scenarios": SENSITIVITY_SCENARIOS,
        "high_index_cutoff": high_index_cutoff,
        "high_reliability_threshold": high_reliability_threshold,
        "robust_high_opportunity_districts": clean_records(robust_high),
        "high_index_low_reliability_districts": clean_records(high_index_low_reliability),
    }


def load_provenance(df: pd.DataFrame, jobs_by_district: dict[str, list[dict]]) -> dict:
    source_manifest_path = RAW_DIR / "source_manifest.json"
    taiwanjobs_manifest_path = RAW_DIR / "taiwanjobs_manifest.json"
    source_manifest = None
    taiwanjobs_manifest = None

    if source_manifest_path.exists():
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if taiwanjobs_manifest_path.exists():
        taiwanjobs_manifest = json.loads(taiwanjobs_manifest_path.read_text(encoding="utf-8"))

    population_sources = sorted(set(df["population_source_file"].dropna())) if "population_source_file" in df else []
    job_sources = sorted(
        {
            item
            for value in df["jobs_source_file"].dropna()
            for item in str(value).split(";")
            if item
        }
    ) if "jobs_source_file" in df else []

    return {
        "youth_definition": "18–35 歲",
        "processed_at": sorted(set(df["processed_at"].dropna()))[-1] if "processed_at" in df and df["processed_at"].notna().any() else None,
        "population_sources": population_sources,
        "job_sources": job_sources,
        "source_manifest": source_manifest,
        "taiwanjobs_manifest": taiwanjobs_manifest,
        "metric_definitions": {
            "job_postings": "職缺刊登筆數",
            "job_openings": "需求人數",
            "jobs_per_1000_youth": "job_openings / youth_population_18_35 * 1000",
            "avg_salary": "以可辨識的月薪資料計算平均值；時薪不混入月薪平均。",
        },
        "job_data_quality": analyze_job_data_quality(jobs_by_district),
        "opportunity_index": {
            "name": "青年就業機會指數 Youth Employment Opportunity Index v1",
            "status": "prototype composite indicator; not an official government index",
            "weights": INDEX_WEIGHTS,
            "normalization": "Opportunity 與 Salary 使用 29 區 percentile rank 轉為 0–100，降低單一極端值影響；Diversity 使用 normalized Shannon entropy；Stability 使用可辨識 work_type 中全職比例。",
            "missing_data": "dimension 為 null 時不當成 0；該區 composite index 只用有效 dimension，並將有效權重重新 normalize。",
            "dimensions": {
                "opportunity": "依 jobs_per_1000_youth 的 29 區 percentile rank 計算。",
                "salary": "依 median_salary 的 29 區 percentile rank 計算，只使用可解析月薪。",
                "diversity": "依 jobs_by_district.category 分布計算 normalized Shannon entropy。",
                "stability": "依可辨識 work_type 中全職職缺比例計算。",
            },
            "reliability": {
                "formula": "Dimension reliability uses log saturation: min(1, log(1+n) / log(1+threshold)) * 100, blended with field coverage where applicable.",
                "sample_thresholds": RELIABILITY_CONFIG["sample_thresholds"],
                "level_thresholds": RELIABILITY_CONFIG["level_thresholds"],
                "opportunity_components": RELIABILITY_CONFIG["opportunity_components"],
                "rank_stability": "index_rank_stability = (1 - rank_range / 28) * 100 across baseline and sensitivity scenarios.",
                "interpretation": "Reliability reflects data support and completeness, not employment quality.",
            },
            "sensitivity_scenarios": SENSITIVITY_SCENARIOS,
        },
    }


def main() -> int:
    WEBSITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(PROCESSED_CSV, encoding="utf-8-sig")
    df = df[df["district"].isin(STANDARD_DISTRICTS)].copy()
    jobs_by_district = extract_job_records()
    jobs_by_district = {district: jobs_by_district.get(district, []) for district in STANDARD_DISTRICTS}
    job_data_quality = analyze_job_data_quality(jobs_by_district)
    reliability = reliability_analysis(df)
    sample_size_path = PROJECT_ROOT / "data" / "processed" / "index_sample_size_analysis.csv"
    analysis_path = PROJECT_ROOT / "data" / "processed" / "index_reliability_analysis.json"
    sample_size_columns = [
        "district",
        "youth_population_18_35",
        "job_postings",
        "job_openings",
        "salary_valid_count",
        "category_valid_count",
        "work_type_valid_count",
        "company_count",
        "salary_sample_size",
        "diversity_sample_size",
        "stability_sample_size",
    ]
    df[sample_size_columns].to_csv(sample_size_path, index=False, encoding="utf-8-sig")
    (PROJECT_ROOT / "data" / "processed" / "job_data_quality.json").write_text(
        json.dumps(clean_json_value(job_data_quality), ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    analysis_path.write_text(
        json.dumps(clean_json_value(reliability), ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    payload = {
        "title": "新北市青年就業地圖",
        "youth_definition": "18–35 歲",
        "source_note": "青年人口來自內政部戶政司 ODRP014；職缺資料整合台灣就業通 OpenData 與行政院人事行政總處事求人資料。",
        "records": clean_records(df),
        "jobs_by_district": jobs_by_district,
        "provenance": load_provenance(df, jobs_by_district),
    }
    (WEBSITE_DATA_DIR / "youth_employment_map.json").write_text(
        json.dumps(clean_json_value(payload), ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )

    if RAW_GEOJSON.exists():
        shutil.copyfile(RAW_GEOJSON, WEBSITE_DATA_DIR / "new_taipei_districts.geojson")

    print(f"Wrote {WEBSITE_DATA_DIR / 'youth_employment_map.json'}")
    print(f"Wrote {PROJECT_ROOT / 'data' / 'processed' / 'job_data_quality.json'}")
    print(f"Wrote {sample_size_path}")
    print(f"Wrote {analysis_path}")
    if RAW_GEOJSON.exists():
        print(f"Wrote {WEBSITE_DATA_DIR / 'new_taipei_districts.geojson'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
