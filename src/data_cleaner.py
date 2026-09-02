from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


YOUTH_MIN_AGE = 18
YOUTH_MAX_AGE = 35

STANDARD_DISTRICTS: list[str] = [
    "板橋區",
    "三重區",
    "中和區",
    "永和區",
    "新莊區",
    "新店區",
    "樹林區",
    "鶯歌區",
    "三峽區",
    "淡水區",
    "汐止區",
    "瑞芳區",
    "土城區",
    "蘆洲區",
    "五股區",
    "泰山區",
    "林口區",
    "深坑區",
    "石碇區",
    "坪林區",
    "三芝區",
    "石門區",
    "八里區",
    "平溪區",
    "雙溪區",
    "貢寮區",
    "金山區",
    "萬里區",
    "烏來區",
]

DISTRICT_ALIASES: dict[str, str] = {
    district.removesuffix("區"): district for district in STANDARD_DISTRICTS
}
DISTRICT_ALIASES.update({district: district for district in STANDARD_DISTRICTS})


@dataclass(frozen=True)
class ColumnMapping:
    district: str | None = None
    age: str | None = None
    population: str | None = None
    job_openings: str | None = None
    salary: str | None = None
    salary_type: str | None = None
    salary_min: str | None = None
    salary_max: str | None = None
    job_category: str | None = None
    occupation: str | None = None
    industry: str | None = None
    company: str | None = None
    address: str | None = None
    work_type: str | None = None


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return unicodedata.normalize("NFKC", str(value)).strip()


def normalize_column_name(column: str) -> str:
    return re.sub(r"\s+", "", normalize_text(column)).lower()


def normalize_district(value: object) -> str | pd.NA:
    """Return a legal New Taipei district only for exact, deterministic matches."""
    text = normalize_text(value)
    if not text:
        return pd.NA

    compact = re.sub(r"\s+", "", text)
    if compact in DISTRICT_ALIASES:
        return DISTRICT_ALIASES[compact]

    matches = [district for district in STANDARD_DISTRICTS if district in compact]
    if len(matches) == 1:
        return matches[0]

    return pd.NA


def normalize_work_type(value: object) -> str | pd.NA:
    text = normalize_text(value)
    if not text:
        return pd.NA
    if "全職" in text:
        return "全職"
    if "兼職" in text:
        return "兼職"
    return pd.NA


def detect_column(columns: Iterable[str], keywords: Iterable[str]) -> str | None:
    normalized = [(column, normalize_column_name(column)) for column in columns]
    for keyword in keywords:
        key = normalize_column_name(keyword)
        for original, normalized_name in normalized:
            if key and key in normalized_name:
                return original
    return None


def detect_mapping(df: pd.DataFrame) -> ColumnMapping:
    columns = list(df.columns)

    district = detect_column(
        columns,
        ["site_id", "區域別", "行政區", "鄉鎮市區", "區別", "區域", "地區", "工作地區", "cityname", "district", "work_place"],
    )
    address = detect_column(columns, ["工作地址", "地址", "上班地點", "工作地點", "地點", "work_address", "cityname"])
    if district is None:
        district = address

    age = detect_column(columns, ["age", "年齡", "歲數", "年歲"])
    population = detect_column(columns, ["youth_population", "人口數", "人口", "人數"])
    job_openings = detect_column(
        columns,
        ["job_openings", "需求人數", "僱用人數", "雇用人數", "招募人數", "職缺人數", "需求名額", "名額", "job_person", "number_of"],
    )
    salary = detect_column(columns, ["avg_salary", "salary", "薪資", "待遇", "月薪"])
    salary_type = detect_column(columns, ["核薪方式", "salarycd", "salary_type"])
    salary_min = detect_column(columns, ["薪資範圍下限", "薪資下限", "最低薪資", "nt_l", "min_salary", "salary_min"])
    salary_max = detect_column(columns, ["薪資範圍上限", "薪資上限", "最高薪資", "nt_u", "max_salary", "salary_max"])
    job_category = detect_column(columns, ["職務大類別名稱", "職缺類別", "職務類別", "工作類別", "cjob_name1", "job_category", "person_kind"])
    occupation = detect_column(columns, ["職務名稱", "職業", "職稱", "工作職稱", "occupation", "occu_desc", "job_title", "title"])
    industry = detect_column(columns, ["產業", "行業", "industry"])
    company = detect_column(columns, ["公司名稱", "公司", "廠商名稱", "事業單位", "compname", "company", "org_name"])
    work_type = detect_column(columns, ["wk_type", "職務性質", "工作型態", "工作性質", "work_type"])

    return ColumnMapping(
        district=district,
        age=age,
        population=population,
        job_openings=job_openings,
        salary=salary,
        salary_type=salary_type,
        salary_min=salary_min,
        salary_max=salary_max,
        job_category=job_category,
        occupation=occupation,
        industry=industry,
        company=company,
        address=address,
        work_type=work_type,
    )


def parse_age(value: object) -> float | pd.NA:
    text = normalize_text(value)
    if not text:
        return pd.NA
    numbers = re.findall(r"\d+", text)
    if not numbers:
        return pd.NA
    return float(numbers[0])


def parse_number(value: object) -> float | pd.NA:
    if pd.isna(value):
        return pd.NA
    if isinstance(value, (int, float)):
        return float(value)
    text = normalize_text(value).replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return pd.NA
    return float(match.group(0))


def parse_salary(value: object) -> float | pd.NA:
    text = normalize_text(value).replace(",", "")
    if not text:
        return pd.NA
    numbers = [float(item) for item in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return pd.NA
    plausible_monthly = [number for number in numbers if number >= 1000]
    values = plausible_monthly or numbers
    return sum(values[:2]) / min(len(values), 2)


def youth_age_columns(df: pd.DataFrame) -> list[str]:
    result: list[str] = []
    for column in df.columns:
        name = normalize_column_name(column)
        numbers = [int(item) for item in re.findall(r"\d+", name)]
        if len(numbers) == 1 and YOUTH_MIN_AGE <= numbers[0] <= YOUTH_MAX_AGE:
            result.append(column)
        elif len(numbers) >= 2 and numbers[0] >= YOUTH_MIN_AGE and numbers[1] <= YOUTH_MAX_AGE:
            result.append(column)
    return result


def detect_dataset_kind(path: Path, df: pd.DataFrame, mapping: ColumnMapping) -> str:
    name = normalize_column_name(path.name)
    columns_text = " ".join(normalize_column_name(column) for column in df.columns)

    if any(token in name for token in ["job", "jobs", "employment", "職缺", "就業", "徵才"]):
        return "jobs"
    if any(token in columns_text for token in ["職缺", "薪資", "職務", "公司名稱", "雇用人數", "需求人數", "work_address", "job_person", "number_of"]):
        return "jobs"
    if any(token in name for token in ["population", "youth_population", "人口"]):
        return "population"
    if mapping.age or youth_age_columns(df):
        return "population"
    return "unknown"


def top_value(series: pd.Series) -> object:
    clean = series.dropna()
    clean = clean[clean.astype(str).str.strip() != ""]
    if clean.empty:
        return pd.NA
    return clean.value_counts().idxmax()
