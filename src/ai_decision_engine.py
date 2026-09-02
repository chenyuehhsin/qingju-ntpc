from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.data_cleaner import DISTRICT_ALIASES, STANDARD_DISTRICTS, normalize_district


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = PROJECT_ROOT / "website" / "data" / "youth_employment_map.json"
DEFAULT_HISTORY_PATH = PROJECT_ROOT / "website" / "data" / "youth_employment_history.json"

PERSONAL_MATCH_WEIGHTS: dict[str, float] = {
    "availability": 0.50,
    "salary": 0.20,
    "opportunity_index": 0.15,
    "reliability": 0.15,
}

ASSISTANT_PROVENANCE_NOTE = "AI 建議為資料輔助結果，不代表政府官方推薦。"

SUPPORTED_CONSTRAINTS = [
    "target_job_keyword",
    "target_category",
    "preferred_district",
    "minimum_salary",
    "maximum_salary",
    "work_type",
    "company_keyword",
]


@dataclass(frozen=True)
class Dataset:
    records: list[dict[str, Any]]
    jobs_by_district: dict[str, list[dict[str, Any]]]
    provenance: dict[str, Any]

    @property
    def all_jobs(self) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        for district, items in self.jobs_by_district.items():
            for item in items:
                row = dict(item)
                row["district"] = row.get("district") or district
                jobs.append(row)
        return jobs

    @property
    def record_by_district(self) -> dict[str, dict[str, Any]]:
        return {str(row.get("district")): row for row in self.records if row.get("district") in STANDARD_DISTRICTS}


def load_dataset(path: str | Path = DEFAULT_DATA_PATH) -> Dataset:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    records = [row for row in payload.get("records", []) if row.get("district") in STANDARD_DISTRICTS]
    jobs_by_district = {
        district: [job for job in payload.get("jobs_by_district", {}).get(district, []) if job.get("district", district) in STANDARD_DISTRICTS]
        for district in STANDARD_DISTRICTS
    }
    return Dataset(records=records, jobs_by_district=jobs_by_district, provenance=payload.get("provenance", {}))


def load_history(path: str | Path = DEFAULT_HISTORY_PATH) -> dict[str, Any] | None:
    history_path = Path(path)
    if not history_path.exists():
        return None
    return json.loads(history_path.read_text(encoding="utf-8"))


def has_number(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def number_or_none(value: Any) -> float | None:
    return float(value) if has_number(value) else None


def median(values: list[float]) -> float | None:
    clean = sorted(value for value in values if has_number(value))
    if not clean:
        return None
    mid = len(clean) // 2
    if len(clean) % 2:
        return float(clean[mid])
    return float((clean[mid - 1] + clean[mid]) / 2)


def normalize_score(value: Any) -> float | None:
    numeric = number_or_none(value)
    if numeric is None:
        return None
    return max(0.0, min(100.0, numeric))


def min_max_scores(values_by_key: dict[str, float]) -> dict[str, float]:
    if not values_by_key:
        return {}
    values = list(values_by_key.values())
    low = min(values)
    high = max(values)
    if high == low:
        return {key: 100.0 for key in values_by_key}
    return {key: (value - low) / (high - low) * 100 for key, value in values_by_key.items()}


CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "兩": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def parse_chinese_number(text: str) -> float | None:
    if not text:
        return None
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return float(text)
    if text in CHINESE_DIGITS:
        return float(CHINESE_DIGITS[text])
    if "十" in text:
        left, _, right = text.partition("十")
        tens = CHINESE_DIGITS.get(left, 1 if left == "" else None)
        ones = CHINESE_DIGITS.get(right, 0 if right == "" else None)
        if tens is not None and ones is not None:
            return float(tens * 10 + ones)
    total = 0
    for char in text:
        if char not in CHINESE_DIGITS:
            return None
        total = total * 10 + CHINESE_DIGITS[char]
    return float(total)


def parse_salary_amounts(query: str) -> tuple[int | None, int | None]:
    text = query.replace(",", "").replace("，", "")
    minimum: int | None = None
    maximum: int | None = None

    amount_pattern = r"(\d+(?:\.\d+)?|[零〇一二兩三四五六七八九十]+)\s*(萬|千)?"
    for match in re.finditer(amount_pattern, text):
        raw, unit = match.groups()
        number = parse_chinese_number(raw)
        if number is None:
            continue
        amount = number
        if unit == "萬":
            amount *= 10000
        elif unit == "千":
            amount *= 1000
        if amount < 1000 and ("薪" in text or "工資" in text):
            amount *= 10000

        window = text[max(0, match.start() - 8) : min(len(text), match.end() + 8)]
        if any(token in window for token in ["至少", "以上", "不低於", "起", ">=", "高於"]):
            minimum = int(amount)
        elif any(token in window for token in ["最高", "以下", "以內", "不超過", "<="]):
            maximum = int(amount)
        elif "薪" in window or "月薪" in window:
            minimum = int(amount)

    return minimum, maximum


def available_categories(jobs: list[dict[str, Any]]) -> list[str]:
    return sorted({str(job["category"]) for job in jobs if job.get("category")})


def category_from_query(query: str, categories: list[str]) -> str | None:
    aliases = {
        "資訊": ["資訊", "軟體", "系統", "工程師", "程式"],
        "餐飲": ["餐飲", "旅遊", "休閒"],
        "醫療": ["醫療", "美容", "保健"],
        "製造": ["製造", "品管", "環衛"],
        "物流": ["物流", "運輸", "資材"],
        "行政": ["行政", "總務", "經營"],
        "客服": ["客服", "門市"],
        "營建": ["營建", "製圖", "施作"],
        "業務": ["業務", "貿易", "銷售"],
        "清潔": ["清潔", "家事", "托育"],
    }
    for category in categories:
        if category and category in query:
            return category
    for trigger, fragments in aliases.items():
        if trigger in query or any(fragment in query for fragment in fragments):
            for category in categories:
                if any(fragment in category for fragment in fragments):
                    return category
    return None


def parse_constraints(query: str, jobs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    jobs = jobs or []
    compact = re.sub(r"\s+", "", query)
    preferred_district = None
    for alias, district in DISTRICT_ALIASES.items():
        if alias and alias in compact:
            preferred_district = district
            break

    minimum_salary, maximum_salary = parse_salary_amounts(compact)
    work_type = "全職" if "全職" in compact else "兼職" if "兼職" in compact else None
    target_category = category_from_query(compact, available_categories(jobs))

    company_keyword = None
    company_match = re.search(r"([\w\u4e00-\u9fff]{2,20}公司)", compact)
    if company_match:
        company_keyword = company_match.group(1)

    keyword = None
    for token in ["資訊", "軟體", "工程師", "程式", "餐飲", "醫療", "製造", "物流", "行政", "客服", "門市", "業務"]:
        if token in compact:
            keyword = token
            break

    return {
        "target_job_keyword": keyword,
        "target_category": target_category,
        "preferred_district": preferred_district,
        "minimum_salary": minimum_salary,
        "maximum_salary": maximum_salary,
        "work_type": work_type,
        "company_keyword": company_keyword,
    }


def salary_midpoint(job: dict[str, Any]) -> float | None:
    low = number_or_none(job.get("salary_min"))
    high = number_or_none(job.get("salary_max"))
    if low is not None and high is not None:
        return (low + high) / 2
    return low if low is not None else high


def salary_matches(job: dict[str, Any], constraints: dict[str, Any]) -> bool:
    minimum = constraints.get("minimum_salary")
    maximum = constraints.get("maximum_salary")
    low = number_or_none(job.get("salary_min"))
    high = number_or_none(job.get("salary_max"))
    if minimum is not None:
        if low is None:
            return False
        if low < float(minimum):
            return False
    if maximum is not None:
        comparable = low if low is not None else high
        if comparable is None or comparable > float(maximum):
            return False
    return True


def job_matches(job: dict[str, Any], constraints: dict[str, Any], *, allow_unknown_salary: bool = False) -> bool:
    category = constraints.get("target_category")
    keyword = constraints.get("target_job_keyword")
    work_type = constraints.get("work_type")
    company = constraints.get("company_keyword")

    if category and job.get("category") != category:
        return False
    haystack = " ".join(str(job.get(field) or "") for field in ["title", "company", "category", "address", "source"])
    if keyword and keyword not in haystack:
        return False
    if work_type and job.get("work_type") != work_type:
        return False
    if company and company not in str(job.get("company") or ""):
        return False
    if constraints.get("minimum_salary") is not None or constraints.get("maximum_salary") is not None:
        if allow_unknown_salary and salary_midpoint(job) is None:
            return True
        return salary_matches(job, constraints)
    return True


def public_job_fields(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": job.get("source"),
        "title": job.get("title"),
        "company": job.get("company"),
        "district": job.get("district"),
        "address": job.get("address"),
        "category": job.get("category"),
        "openings": job.get("openings"),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "salary_text": job.get("salary_text"),
        "work_type": job.get("work_type"),
        "deadline": job.get("deadline"),
        "updated_at": job.get("updated_at"),
        "url": job.get("url"),
    }


def aggregate_matches(dataset: Dataset, constraints: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    strict_matches = [job for job in dataset.all_jobs if job_matches(job, constraints)]
    secondary_salary_unknown = []
    if constraints.get("minimum_salary") is not None or constraints.get("maximum_salary") is not None:
        secondary_salary_unknown = [
            job
            for job in dataset.all_jobs
            if job_matches(job, constraints, allow_unknown_salary=True) and salary_midpoint(job) is None
        ]

    by_district: dict[str, dict[str, Any]] = {}
    records = dataset.record_by_district
    for district in STANDARD_DISTRICTS:
        jobs = [job for job in strict_matches if job.get("district") == district]
        salaries = [value for value in (salary_midpoint(job) for job in jobs) if value is not None]
        by_district[district] = {
            "district": district,
            "matching_job_postings": len(jobs),
            "matching_job_openings": sum(int(job.get("openings") or 0) for job in jobs),
            "matching_company_count": len({job.get("company") for job in jobs if job.get("company")}),
            "matching_median_salary": median(salaries),
            "matching_salary_known_count": len(salaries),
            "matching_jobs": [public_job_fields(job) for job in sorted(jobs, key=lambda row: (-(row.get("openings") or 0), row.get("title") or ""))[:12]],
            "district_metrics": records.get(district, {}),
        }
    return by_district, strict_matches, secondary_salary_unknown


def personal_scores(aggregates: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    candidate_map = {district: row for district, row in aggregates.items() if row["matching_job_postings"] > 0}
    availability_raw = {
        district: row["matching_job_openings"] * 0.7 + row["matching_job_postings"] * 0.3 for district, row in candidate_map.items()
    }
    availability_scores = min_max_scores(availability_raw)
    salary_values = {
        district: row["matching_median_salary"] for district, row in candidate_map.items() if row["matching_median_salary"] is not None
    }
    salary_scores = min_max_scores(salary_values)

    recommendations: list[dict[str, Any]] = []
    for district, row in candidate_map.items():
        metrics = row["district_metrics"]
        components = {
            "availability": availability_scores.get(district, 0.0),
            "salary": salary_scores.get(district, 0.0) if salary_scores else None,
            "opportunity_index": normalize_score(metrics.get("youth_employment_opportunity_index")),
            "reliability": normalize_score(metrics.get("index_reliability_score")),
        }
        present = [(name, value) for name, value in components.items() if value is not None]
        weight_sum = sum(PERSONAL_MATCH_WEIGHTS[name] for name, _value in present)
        score = sum(float(value) * PERSONAL_MATCH_WEIGHTS[name] / weight_sum for name, value in present) if weight_sum else None
        recommendations.append(
            {
                "district": district,
                "personal_match_score": round(score, 1) if score is not None else None,
                "score_components": {name: round(value, 1) if value is not None else None for name, value in components.items()},
                "matching_job_postings": row["matching_job_postings"],
                "matching_job_openings": row["matching_job_openings"],
                "matching_company_count": row["matching_company_count"],
                "matching_median_salary": row["matching_median_salary"],
                "opportunity_index": metrics.get("youth_employment_opportunity_index"),
                "reliability": metrics.get("index_reliability_score"),
                "reliability_level": metrics.get("index_reliability_level"),
                "rank_stability": metrics.get("index_rank_stability"),
                "matching_jobs": row["matching_jobs"],
            }
        )

    return sorted(
        recommendations,
        key=lambda row: (
            row["personal_match_score"] if row["personal_match_score"] is not None else -1,
            row["matching_job_openings"],
            row["matching_job_postings"],
        ),
        reverse=True,
    )


def top_by_metric(dataset: Dataset, metric: str, limit: int = 10, reliability_level: str | None = None) -> list[dict[str, Any]]:
    rows = [row for row in dataset.records if has_number(row.get(metric))]
    if reliability_level:
        rows = [row for row in rows if row.get("index_reliability_level") == reliability_level]
    rows.sort(key=lambda row: float(row[metric]), reverse=True)
    return [
        {
            "district": row.get("district"),
            "value": row.get(metric),
            "youth_population_18_35": row.get("youth_population_18_35"),
            "job_openings": row.get("job_openings"),
            "jobs_per_1000_youth": row.get("jobs_per_1000_youth"),
            "opportunity_index": row.get("youth_employment_opportunity_index"),
            "reliability": row.get("index_reliability_score"),
            "reliability_level": row.get("index_reliability_level"),
            "rank_stability": row.get("index_rank_stability"),
        }
        for row in rows[:limit]
    ]


def compare_districts(dataset: Dataset, districts: list[str]) -> list[dict[str, Any]]:
    records = dataset.record_by_district
    result = []
    for district in districts[:2]:
        row = records.get(district)
        if not row:
            continue
        result.append(
            {
                "district": district,
                "youth_population_18_35": row.get("youth_population_18_35"),
                "job_postings": row.get("job_postings"),
                "job_openings": row.get("job_openings"),
                "jobs_per_1000_youth": row.get("jobs_per_1000_youth"),
                "avg_salary": row.get("avg_salary"),
                "median_salary": row.get("median_salary"),
                "company_count": row.get("company_count"),
                "opportunity_index": row.get("youth_employment_opportunity_index"),
                "reliability": row.get("index_reliability_score"),
                "reliability_level": row.get("index_reliability_level"),
            }
        )
    return result


def districts_in_query(query: str) -> list[str]:
    found: list[str] = []
    compact = re.sub(r"\s+", "", query)
    for alias, district in DISTRICT_ALIASES.items():
        if alias and alias in compact and district not in found:
            found.append(district)
    return found


def high_index_cutoff(dataset: Dataset) -> float:
    values = sorted(float(row["youth_employment_opportunity_index"]) for row in dataset.records if has_number(row.get("youth_employment_opportunity_index")))
    if not values:
        return 0.0
    return values[int((len(values) - 1) * 0.75)]


def classify_intent(query: str, constraints: dict[str, Any]) -> str:
    text = re.sub(r"\s+", "", query)
    district_count = len(districts_in_query(text))
    has_constraints = any(constraints.get(key) for key in ["target_job_keyword", "target_category", "minimum_salary", "maximum_salary", "work_type", "company_keyword"])
    if any(token in text for token in ["幾月資料", "資料月份", "資料日期", "更新日期", "什麼時候", "何時更新", "來源時間", "資料多新"]):
        return "data_freshness"
    if any(token in text for token in ["增加最多", "成長最快", "正在增加", "趨勢", "最近", "下降", "減少"]):
        if "職類" in text or "類" in text and ("資訊" in text or "餐飲" in text or "需求" in text):
            return "category_trend"
        if district_count >= 1:
            return "district_trend"
        return "district_growth_ranking"
    if district_count >= 2 and any(token in text.lower() for token in ["比", "vs", "VS"]):
        return "compare_districts"
    if any(token in text for token in ["為什麼", "原因", "怎麼會"]):
        return "explain_district"
    if "工作機會最多" in text:
        return "rank_job_openings"
    if "可靠度" in text and ("高" in text or "highest" in text.lower()) and ("指數" in text or "index" in text.lower()):
        return "high_index_high_reliability"
    if ("機會" in text or "index" in text.lower() or "指數" in text) and "可靠度" in text and ("不高" in text or "低" in text or "小心" in text):
        return "high_index_low_reliability"
    if "青年人口多" in text and ("工作機會" in text or "相對少" in text):
        return "population_high_openings_low"
    if "需求高" in text and "薪資" in text:
        return "openings_high_salary_low"
    if "資源" in text or "政策" in text or "關注" in text:
        return "policy_attention"
    if has_constraints:
        return "personalized_recommendation"
    return "general_recommendation"


def build_answer(result: dict[str, Any]) -> str:
    intent = result["intent"]
    if intent == "data_freshness":
        temporal = result.get("temporal_evidence", {})
        return (
            f"目前網站使用的 snapshot_month 是 {temporal.get('latest_snapshot') or '尚待確認'}。"
            f"青年人口來源月份是 {temporal.get('population_reference_month') or '尚待確認'}，"
            f"職缺資料下載時間是 {temporal.get('jobs_snapshot_as_of') or temporal.get('jobs_downloaded_at') or '尚待確認'}，"
            f"職缺列最新參考日期是 {temporal.get('jobs_reference_date') or '尚待確認'}。"
            f"processed_at 只代表系統處理時間：{temporal.get('processed_at') or '尚待確認'}。"
        )
    if intent in {"district_trend", "district_growth_ranking", "category_trend"}:
        trend = result.get("trend_evidence")
        if trend and trend.get("reason"):
            return trend["reason"]
        recs = result.get("recommendations", [])[:5]
        if not recs:
            return "目前尚無足夠歷史資料進行趨勢比較。"
        if intent == "district_trend":
            item = recs[0]
            return (
                f"{item.get('district')}相較 {item.get('previous_period')}，{item.get('current_period')} 工作機會為 "
                f"{format_number_text(item.get('current_value'), 0)} 人，前期為 {format_number_text(item.get('previous_value'), 0)} 人，"
                f"變化 {format_number_text(item.get('absolute_change'), 0)} 人，MoM {format_number_text(item.get('percentage_change'), 1)}%，"
                f"趨勢標籤：{item.get('trend_label') or '暫無資料'}。"
            )
        if intent == "category_trend":
            lines = ["目前職類需求變化如下："]
            for index, item in enumerate(recs, start=1):
                lines.append(
                    f"{index}. {item.get('district')} {item.get('category')}：需求 {format_number_text(item.get('current_value'), 0)} 人，"
                    f"變化 {format_number_text(item.get('absolute_change'), 0)} 人，MoM {format_number_text(item.get('percentage_change'), 1)}%，"
                    f"{item.get('trend_label') or '暫無資料'}"
                )
            return "\n".join(lines)
        lines = ["這個月工作機會增加最多的行政區："]
        for index, item in enumerate(recs, start=1):
            lines.append(
                f"{index}. {item.get('district')}：工作機會 {format_number_text(item.get('job_openings'), 0)} 人，"
                f"MoM {format_number_text(item.get('job_openings_mom_pct'), 1)}%，{item.get('trend_label') or '暫無資料'}"
            )
        return "\n".join(lines)

    if intent == "personalized_recommendation":
        recs = result.get("recommendations", [])[:3]
        if not recs:
            return "目前沒有找到符合條件的職缺。薪資條件只使用可解析薪資資料，未知薪資不會被視為符合。"
        lines = ["依目前職缺資料，我會優先看："]
        for index, rec in enumerate(recs, start=1):
            warning = "；但資料可靠度偏低，建議搭配實際職缺逐筆確認" if rec.get("reliability_level") == "Low" else ""
            lines.extend(
                [
                    f"{index}. {rec['district']}",
                    f"匹配職缺：{rec['matching_job_postings']} 筆，需求人數：{rec['matching_job_openings']} 人，公司數：{rec['matching_company_count']}",
                    f"薪資中位數：{format_money_text(rec.get('matching_median_salary'))}，青年就業機會指數：{format_number_text(rec.get('opportunity_index'), 1)}，資料可靠度：{format_number_text(rec.get('reliability'), 1)}{warning}",
                ]
            )
        lines.append("注意事項：本結果依目前已收錄職缺計算，不代表所有市場職缺。")
        return "\n".join(lines)

    if intent == "compare_districts":
        comparisons = result.get("comparison", [])
        if len(comparisons) < 2:
            return "目前資料不足以完成兩個行政區比較。"
        a, b = comparisons
        better = max(comparisons, key=lambda row: number_or_none(row.get("opportunity_index")) or -1)
        return (
            f"{a['district']}與{b['district']}比較：目前青年就業機會指數較高的是{better['district']}。"
            f"{a['district']}工作機會 {format_number_text(a.get('job_openings'), 0)} 人、每千青年 {format_number_text(a.get('jobs_per_1000_youth'), 1)}；"
            f"{b['district']}工作機會 {format_number_text(b.get('job_openings'), 0)} 人、每千青年 {format_number_text(b.get('jobs_per_1000_youth'), 1)}。"
        )

    if intent == "explain_district":
        row = result.get("district_explanation")
        if not row:
            return "目前資料不足以判斷。"
        warning = ""
        if row.get("reliability_level") == "Low":
            warning = " 不過資料可靠度偏低，因此不建議只根據 Index 做決策。"
        return (
            f"{row['district']}的青年就業機會指數為 {format_number_text(row.get('opportunity_index'), 1)}，"
            f"資料可靠度為 {format_number_text(row.get('reliability'), 1)}（{row.get('reliability_level') or '暫無資料'}）。"
            f"工作機會 {format_number_text(row.get('job_openings'), 0)} 人、每千名青年工作機會 {format_number_text(row.get('jobs_per_1000_youth'), 1)}、"
            f"薪資分數 {format_number_text(row.get('salary_score'), 1)}、職類多樣性 {format_number_text(row.get('job_diversity_score'), 1)}。{warning}"
        )

    recs = result.get("recommendations", [])[:5]
    if not recs:
        return "目前資料不足以判斷。"
    if intent == "high_index_low_reliability":
        prefix = "目前看起來機會較高、但資料可靠度偏低的行政區："
    elif intent == "high_index_high_reliability":
        prefix = "目前資料同時顯示較高機會與較高資料支持度的行政區："
    elif intent == "rank_job_openings":
        prefix = "目前工作機會最多的行政區："
    elif intent in {"population_high_openings_low", "openings_high_salary_low", "policy_attention"}:
        prefix = "目前資料顯示可能值得進一步關注的行政區："
    else:
        prefix = "依目前資料可優先觀察："
    lines = [prefix]
    for index, rec in enumerate(recs, start=1):
        lines.append(
            f"{index}. {rec['district']}：工作機會 {format_number_text(rec.get('job_openings'), 0)} 人，"
            f"Index {format_number_text(rec.get('opportunity_index'), 1)}，可靠度 {format_number_text(rec.get('reliability'), 1)}"
        )
    return "\n".join(lines)


def format_number_text(value: Any, digits: int) -> str:
    if not has_number(value):
        return "暫無資料"
    return f"{float(value):,.{digits}f}"


def format_money_text(value: Any) -> str:
    if not has_number(value):
        return "暫無資料"
    return f"NT$ {float(value):,.0f}"


def district_metric_evidence(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "district": row.get("district"),
        "youth_population_18_35": row.get("youth_population_18_35"),
        "job_postings": row.get("job_postings"),
        "job_openings": row.get("job_openings"),
        "jobs_per_1000_youth": row.get("jobs_per_1000_youth"),
        "avg_salary": row.get("avg_salary"),
        "median_salary": row.get("median_salary"),
        "company_count": row.get("company_count"),
        "top_job_category": row.get("top_job_category"),
        "top_occupation": row.get("top_occupation"),
        "opportunity_score": row.get("opportunity_score"),
        "salary_score": row.get("salary_score"),
        "job_diversity_score": row.get("job_diversity_score"),
        "employment_stability_score": row.get("employment_stability_score"),
        "opportunity_index": row.get("youth_employment_opportunity_index"),
        "reliability": row.get("index_reliability_score"),
        "reliability_level": row.get("index_reliability_level"),
        "rank_stability": row.get("index_rank_stability"),
        "baseline_rank": row.get("baseline_rank"),
        "rank_min": row.get("rank_min"),
        "rank_max": row.get("rank_max"),
        "rank_range": row.get("rank_range"),
    }


def policy_insight(dataset: Dataset, intent: str) -> list[dict[str, Any]]:
    rows = dataset.records
    cutoff = high_index_cutoff(dataset)
    if intent == "high_index_low_reliability":
        selected = [
            district_metric_evidence(row)
            for row in rows
            if has_number(row.get("youth_employment_opportunity_index"))
            and float(row["youth_employment_opportunity_index"]) >= cutoff
            and row.get("index_reliability_level") == "Low"
        ]
        return sorted(selected, key=lambda row: float(row.get("opportunity_index") or 0), reverse=True)
    if intent == "high_index_high_reliability":
        selected = [
            district_metric_evidence(row)
            for row in rows
            if has_number(row.get("youth_employment_opportunity_index"))
            and float(row["youth_employment_opportunity_index"]) >= cutoff
            and row.get("index_reliability_level") == "High"
        ]
        return sorted(selected, key=lambda row: float(row.get("opportunity_index") or 0), reverse=True)
    if intent == "population_high_openings_low":
        selected = [district_metric_evidence(row) for row in rows if has_number(row.get("youth_population_18_35")) and has_number(row.get("jobs_per_1000_youth"))]
        selected.sort(key=lambda row: (float(row["youth_population_18_35"]), -float(row["jobs_per_1000_youth"])), reverse=True)
        return selected[:10]
    if intent == "openings_high_salary_low":
        selected = [district_metric_evidence(row) for row in rows if has_number(row.get("job_openings")) and has_number(row.get("salary_score"))]
        selected.sort(key=lambda row: (float(row["job_openings"]), -float(row["salary_score"])), reverse=True)
        return selected[:10]
    if intent == "policy_attention":
        selected = [district_metric_evidence(row) for row in rows if has_number(row.get("youth_population_18_35")) and has_number(row.get("jobs_per_1000_youth"))]
        selected.sort(key=lambda row: (float(row["youth_population_18_35"]), -float(row["jobs_per_1000_youth"]), -(float(row.get("reliability") or 0))), reverse=True)
        return selected[:10]
    return []


def history_periods(history: dict[str, Any] | None) -> list[str]:
    if not history:
        return []
    manifest_periods = history.get("history_manifest", {}).get("available_periods")
    return list(manifest_periods or history.get("periods", []))


def temporal_evidence(history: dict[str, Any] | None, dataset: Dataset | None = None) -> dict[str, Any]:
    periods = history_periods(history)
    latest = periods[-1] if periods else None
    latest_rows = [
        row for row in (history or {}).get("records", [])
        if row.get("snapshot_month") == latest
    ]
    first = latest_rows[0] if latest_rows else {}
    provenance = dataset.provenance if dataset else {}
    return {
        "latest_snapshot": latest,
        "available_periods": periods,
        "period_count": len(periods),
        "snapshot_as_of": first.get("snapshot_as_of"),
        "population_reference_month": first.get("population_reference_month"),
        "population_downloaded_at": first.get("population_downloaded_at"),
        "jobs_reference_date": first.get("jobs_reference_date"),
        "jobs_snapshot_as_of": first.get("jobs_snapshot_as_of"),
        "jobs_downloaded_at": first.get("jobs_downloaded_at"),
        "previous_available_period": first.get("previous_available_period"),
        "period_gap_months": first.get("period_gap_months"),
        "population_data_freshness_status": first.get("population_data_freshness_status"),
        "population_lag_months": first.get("population_lag_months"),
        "jobs_data_freshness_status": first.get("jobs_data_freshness_status"),
        "jobs_lag_months": first.get("jobs_lag_months"),
        "processed_at": first.get("processed_at") or provenance.get("processed_at"),
        "history_manifest": (history or {}).get("history_manifest"),
    }


def history_ready(history: dict[str, Any] | None) -> bool:
    return len(history_periods(history)) >= 2


def no_trend_result(history: dict[str, Any] | None) -> dict[str, Any]:
    periods = history_periods(history)
    return {
        "current_period": periods[-1] if periods else None,
        "previous_period": periods[-2] if len(periods) >= 2 else None,
        "period_count": len(periods),
        "forecast_readiness": history.get("forecast_readiness") if history else {"period_count": 0, "level": "insufficient", "label": "尚不足"},
        "reason": "目前尚無足夠歷史資料進行趨勢比較。",
    }


def trend_record_evidence(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "snapshot_month": row.get("snapshot_month"),
        "district": row.get("district"),
        "current_period": row.get("snapshot_month"),
        "job_postings": row.get("job_postings"),
        "job_openings": row.get("job_openings"),
        "jobs_per_1000_youth": row.get("jobs_per_1000_youth"),
        "median_salary": row.get("median_salary"),
        "opportunity_index": row.get("youth_employment_opportunity_index"),
        "job_postings_mom_pct": row.get("job_postings_mom_pct"),
        "job_openings_mom_pct": row.get("job_openings_mom_pct"),
        "salary_mom_pct": row.get("salary_mom_pct"),
        "jobs_per_1000_youth_mom_pct": row.get("jobs_per_1000_youth_mom_pct"),
        "index_mom_change": row.get("index_mom_change"),
        "trend_label": row.get("job_opportunity_trend"),
        "demand_growth_signal": row.get("demand_growth_signal"),
    }


def district_trend(dataset: Dataset, history: dict[str, Any] | None, query: str) -> dict[str, Any]:
    if not history_ready(history):
        return no_trend_result(history)
    periods = history_periods(history)
    district = districts_in_query(query)[0] if districts_in_query(query) else None
    current_period = periods[-1]
    previous_period = periods[-2]
    current = next((row for row in history.get("records", []) if row.get("snapshot_month") == current_period and row.get("district") == district), None)
    previous = next((row for row in history.get("records", []) if row.get("snapshot_month") == previous_period and row.get("district") == district), None)
    if not current or not previous:
        return {"current_period": current_period, "previous_period": previous_period, "district": district, "reason": "目前資料不足以判斷。"}
    evidence = trend_record_evidence(current)
    evidence.update(
        {
            "previous_period": previous_period,
            "current_value": current.get("job_openings"),
            "previous_value": previous.get("job_openings"),
            "absolute_change": (number_or_none(current.get("job_openings")) or 0) - (number_or_none(previous.get("job_openings")) or 0)
            if has_number(current.get("job_openings")) and has_number(previous.get("job_openings"))
            else None,
            "percentage_change": current.get("job_openings_mom_pct"),
        }
    )
    return evidence


def district_growth_ranking(history: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not history_ready(history):
        return []
    periods = history_periods(history)
    current_period = periods[-1]
    rows = [trend_record_evidence(row) for row in history.get("records", []) if row.get("snapshot_month") == current_period]
    rows = [row for row in rows if has_number(row.get("job_openings_mom_pct"))]
    return sorted(rows, key=lambda row: float(row["job_openings_mom_pct"]), reverse=True)


def category_trend(history: dict[str, Any] | None, query: str) -> list[dict[str, Any]]:
    if not history_ready(history):
        return []
    periods = history_periods(history)
    current_period = periods[-1]
    rows = [row for row in history.get("category_history", []) if row.get("snapshot_month") == current_period]
    if "資訊" in query:
        rows = [row for row in rows if "資訊" in str(row.get("category") or "")]
    elif "餐飲" in query:
        rows = [row for row in rows if "餐飲" in str(row.get("category") or "")]
    rows = [row for row in rows if has_number(row.get("job_openings_mom_pct"))]
    rows = sorted(rows, key=lambda row: float(row["job_openings_mom_pct"]), reverse=True)
    return [
        {
            "current_period": row.get("snapshot_month"),
            "previous_period": periods[-2],
            "district": row.get("district"),
            "category": row.get("category"),
            "current_value": row.get("job_openings"),
            "absolute_change": row.get("absolute_openings_change"),
            "percentage_change": row.get("job_openings_mom_pct"),
            "trend_label": row.get("demand_growth_signal"),
        }
        for row in rows[:10]
    ]


def answer_query(query: str, data_path: str | Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
    trimmed = query.strip()
    if len(trimmed) > 500:
        trimmed = trimmed[:500]
    dataset = load_dataset(data_path)
    history = load_history()
    temporal = temporal_evidence(history, dataset)
    constraints = parse_constraints(trimmed, dataset.all_jobs)
    intent = classify_intent(trimmed, constraints)
    result: dict[str, Any] = {
        "query": trimmed,
        "intent": intent,
        "parsed_constraints": constraints,
        "supported_constraints": SUPPORTED_CONSTRAINTS,
        "personal_match_weights": PERSONAL_MATCH_WEIGHTS,
        "recommendations": [],
        "matching_jobs": [],
        "secondary_salary_unknown_jobs": [],
        "evidence": {},
        "provenance": {
            "youth_definition": dataset.provenance.get("youth_definition", "18–35 歲"),
            "data_scope": "新北市29區",
            "processed_at": dataset.provenance.get("processed_at"),
            "historical_period_count": len(history_periods(history)),
            "latest_snapshot": history_periods(history)[-1] if history_periods(history) else None,
            "forecast_readiness": history.get("forecast_readiness") if history else None,
            "temporal": temporal,
            "source_note": dataset.provenance.get("source_note") or "使用目前 repository provenance",
            "assistant_note": ASSISTANT_PROVENANCE_NOTE,
        },
    }

    if intent == "data_freshness":
        result["temporal_evidence"] = temporal
        result["evidence"] = {"temporal": temporal}
    elif intent in {"district_trend", "district_growth_ranking", "category_trend"} and not history_ready(history):
        result["trend_evidence"] = no_trend_result(history)
        result["evidence"] = {"trend": result["trend_evidence"]}
    elif intent == "district_trend":
        trend = district_trend(dataset, history, trimmed)
        result["trend_evidence"] = trend
        result["recommendations"] = [trend] if not trend.get("reason") else []
        result["evidence"] = {"trend": trend}
    elif intent == "district_growth_ranking":
        result["recommendations"] = district_growth_ranking(history)
        result["evidence"] = {"trend_ranking": result["recommendations"]}
    elif intent == "category_trend":
        result["recommendations"] = category_trend(history, trimmed)
        result["evidence"] = {"category_trend": result["recommendations"]}
    elif intent == "personalized_recommendation":
        aggregates, strict_matches, secondary = aggregate_matches(dataset, constraints)
        recommendations = personal_scores(aggregates)[:5]
        result["recommendations"] = recommendations
        result["matching_jobs"] = [public_job_fields(job) for job in strict_matches[:40]]
        result["secondary_salary_unknown_jobs"] = [public_job_fields(job) for job in secondary[:20]]
        result["evidence"] = {"district_aggregates": [rec for rec in recommendations], "strict_match_count": len(strict_matches)}
    elif intent == "compare_districts":
        districts = districts_in_query(trimmed)
        result["comparison"] = compare_districts(dataset, districts)
        result["recommendations"] = result["comparison"]
        result["evidence"] = {"comparison": result["comparison"]}
    elif intent == "explain_district":
        districts = districts_in_query(trimmed)
        district = districts[0] if districts else constraints.get("preferred_district")
        row = dataset.record_by_district.get(district) if district else None
        result["district_explanation"] = district_metric_evidence(row) if row else None
        result["recommendations"] = [result["district_explanation"]] if result["district_explanation"] else []
        result["evidence"] = {"district": result["district_explanation"]}
    elif intent == "rank_job_openings":
        result["recommendations"] = top_by_metric(dataset, "job_openings", limit=10)
        result["evidence"] = {"metric": "job_openings", "ranking": result["recommendations"]}
    elif intent in {"high_index_low_reliability", "high_index_high_reliability", "population_high_openings_low", "openings_high_salary_low", "policy_attention"}:
        result["recommendations"] = policy_insight(dataset, intent)
        result["evidence"] = {"policy_insight": result["recommendations"]}
    else:
        result["recommendations"] = top_by_metric(dataset, "youth_employment_opportunity_index", limit=5, reliability_level="High")
        result["evidence"] = {"metric": "youth_employment_opportunity_index", "ranking": result["recommendations"]}

    result["temporal_evidence"] = temporal
    if isinstance(result.get("evidence"), dict):
        result["evidence"]["temporal"] = temporal
    result["answer"] = build_answer(result)
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the deterministic youth employment AI decision engine.")
    parser.add_argument("query", help="Natural-language query in Traditional Chinese.")
    parser.add_argument("--data", default=str(DEFAULT_DATA_PATH), help="Path to youth_employment_map.json.")
    args = parser.parse_args()
    print(json.dumps(answer_query(args.query, args.data), ensure_ascii=False, indent=2))
