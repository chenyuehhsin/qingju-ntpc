#!/usr/bin/env python3
"""Phase 6 youth data inventory, age harmonization, and first-pass statistics.

Raw data is read-only. All derived artifacts are written to docs/,
data/processed/career/youth/, and outputs/career/youth_statistics/.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import charset_normalizer
import pandas as pd
import pdfplumber

PROJECT_CACHE_DIR = Path(tempfile.gettempdir()) / "qingju_ntpc_cache"
os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_CACHE_DIR / "xdg"))
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_CACHE_DIR / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
from matplotlib import pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_YOUTH = PROJECT_ROOT / "data" / "raw" / "career" / "youth"
PROCESSED_YOUTH = PROJECT_ROOT / "data" / "processed" / "career" / "youth"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "career" / "youth_statistics"
DOCS_DIR = PROJECT_ROOT / "docs"
SUMMARY_MD = PROJECT_ROOT / "outputs" / "career" / "youth_statistics_phase6.md"
INVENTORY_MD = DOCS_DIR / "youth_data_inventory.md"
HARMONIZATION_MD = DOCS_DIR / "youth_age_harmonization.md"

POPULATION_CSV = RAW_YOUTH / "population_single_age_by_area_2026.csv"
EDUCATION_CSV = RAW_YOUTH / "ntpc_education_by_age.csv"
EMPLOYED_CSV = RAW_YOUTH / "ntpc_employed_age_structure.csv"
UNEMPLOYMENT_CSV = RAW_YOUTH / "ntpc_unemployment_rate_by_age.csv"
MOL_PDF = RAW_YOUTH / "mol_youth_employment_survey_113.pdf"

OBSERVATION_DATE = "2026-09-02"

AGE_SEX_COLUMN_MAP = {
    2: ("15-24", "male"),
    3: ("15-24", "female"),
    4: ("25-29", "male"),
    5: ("25-29", "female"),
    6: ("30-34", "male"),
    7: ("30-34", "female"),
    8: ("35-39", "male"),
    9: ("35-39", "female"),
    10: ("40-44", "male"),
    11: ("40-44", "female"),
    12: ("45-49", "male"),
    13: ("45-49", "female"),
    14: ("50-54", "male"),
    15: ("50-54", "female"),
    16: ("55-59", "male"),
    17: ("55-59", "female"),
    18: ("60-64", "male"),
    19: ("60-64", "female"),
    20: ("65+", "male"),
    21: ("65+", "female"),
}

PDF_STATS = [
    ("job_search_preparation", "初次尋職前有做過準備", 58.1, "all", "page 19-20"),
    ("job_search_preparation", "增加打工或實習經驗", 25.2, "all", "page 19-20"),
    ("job_search_preparation", "考取專業證照", 24.3, "all", "page 19-20"),
    ("job_search_preparation", "找師長、親友諮詢就業方向", 19.8, "all", "page 19-20"),
    ("job_search_preparation", "做職業興趣分析", 14.6, "all", "page 19-20"),
    ("job_search_preparation", "參加職業訓練增加技能", 4.2, "all", "page 19-20"),
    ("job_info", "認為就業資訊有助於初次尋職", 85.4, "all", "page 21"),
    ("job_info", "面試或求職技巧", 70.0, "among helpful info responses", "page 21"),
    ("job_info", "就業市場與情勢分析", 56.3, "among helpful info responses", "page 21"),
    ("job_info", "熱門行職業介紹", 30.1, "among helpful info responses", "page 21"),
    ("job_info", "職業訓練訊息", 29.6, "among helpful info responses", "page 21"),
    ("job_info", "撰寫中英文履歷技巧", 25.6, "among helpful info responses", "page 21"),
    ("first_job_factor", "工作穩定性", 51.6, "all", "page 22"),
    ("first_job_factor", "薪資及福利", 46.7, "all", "page 22"),
    ("first_job_factor", "通勤方便", 33.3, "all", "page 22"),
    ("first_job_factor", "能學以致用", 31.7, "all", "page 22"),
    ("first_job_factor", "能學習到知識技能", 29.2, "all", "page 22"),
    ("job_search_difficulty", "初次尋職曾遭遇困難", 46.4, "all", "page 23"),
    ("job_search_difficulty", "不知道自己適合做哪方面工作", 53.3, "among difficulty responses", "page 23"),
    ("job_search_difficulty", "經歷不足", 46.0, "among difficulty responses", "page 23"),
    ("job_search_difficulty", "求職面試技巧不足或不會寫履歷", 36.0, "among difficulty responses", "page 23"),
    ("job_search_difficulty", "技能不足", 31.0, "among difficulty responses", "page 23"),
    ("job_transition", "有打算轉換工作", 33.9, "all", "page 25"),
    ("job_transition", "薪資及福利不符期望", 53.4, "among transition-intention responses", "page 25"),
    ("job_transition", "工作無發展前景", 35.2, "among transition-intention responses", "page 25"),
    ("job_transition", "想更換工作地點", 27.6, "among transition-intention responses", "page 25"),
    ("credential", "持有證照", 63.6, "all", "page 26"),
    ("credential", "電腦與資訊相關證照", 23.7, "among certificate holders", "page 26"),
    ("training", "近一年有參加教育訓練", 50.8, "all", "page 27"),
    ("training", "專業技術訓練", 58.1, "among training participants", "page 27"),
    ("training", "電腦相關課程", 13.0, "among training participants", "page 27"),
    ("training_barrier", "工作太忙，沒有時間參加", 36.2, "among non-participants", "page 27"),
    ("training_barrier", "不知道哪裡有提供訓練課程的機構", 20.8, "among non-participants", "page 27"),
    ("training_barrier", "沒有適合的訓練課程", 11.5, "among non-participants", "page 27"),
    ("training_barrier", "參加訓練的費用太高，負擔不起", 8.1, "among non-participants", "page 27"),
]


@dataclass
class InventoryRow:
    filename: str
    source: str
    year_or_period: str
    geography: str
    age_scope: str
    rows: int | str
    columns: str
    encoding: str
    harmonization_status: str
    intended_use: str
    notes: str


def configure_matplotlib() -> None:
    candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            fm.fontManager.addfont(candidate)
            prop = fm.FontProperties(fname=candidate)
            plt.rcParams["font.family"] = prop.get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 160


def detect_encoding(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return "PDF binary"
    data = path.read_bytes()
    result = charset_normalizer.from_bytes(data).best()
    return (result.encoding if result and result.encoding else "unknown").lower()


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def clean_numeric(value: object) -> float:
    if pd.isna(value):
        return 0.0
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "---"}:
        return 0.0
    return float(text)


def parse_roc_period(text: str) -> tuple[int | None, int | None]:
    match = re.search(r"(\d+)年(?:\s+(\d+)月)?", text)
    if not match:
        return None, None
    year = int(match.group(1))
    month = int(match.group(2)) if match.group(2) else None
    return year, month


def build_inventory() -> pd.DataFrame:
    rows: list[InventoryRow] = []

    population = read_csv(POPULATION_CSV)
    parts = population["人口數"].astype(str).str.split("/", expand=True).apply(lambda s: s.str.strip())
    periods = ", ".join(parts[0].dropna().drop_duplicates().astype(str).tolist())
    areas = parts[1].dropna().drop_duplicates().astype(str).tolist()
    area_summary = f"全台區域別 + {len([a for a in areas if a != '區域別總計'])} county/city areas"
    rows.append(
        InventoryRow(
            filename=POPULATION_CSV.name,
            source="not available in file; filename indicates population by single age and area",
            year_or_period=periods,
            geography=area_summary,
            age_scope="single age 0-100+; 18-35 is exactly derivable",
            rows=len(population),
            columns=", ".join(population.columns),
            encoding=detect_encoding(POPULATION_CSV),
            harmonization_status="Exact for 18-35",
            intended_use="New Taipei 18-35 population size and age/sex structure",
            notes="Filename says 2026, but row labels show ROC 109 / 2020 periods. Phase 6 uses row labels as the data period.",
        )
    )

    education = read_csv(EDUCATION_CSV)
    age_groups = ", ".join(education["itemvalue2"].astype(str).str.strip().drop_duplicates().tolist())
    rows.append(
        InventoryRow(
            filename=EDUCATION_CSV.name,
            source="not available in file; filename indicates New Taipei education by age",
            year_or_period=f"{int(education['field1'].min())}-{int(education['field1'].max())}",
            geography="新北市",
            age_scope=age_groups,
            rows=len(education),
            columns=", ".join(education.columns),
            encoding=detect_encoding(EDUCATION_CSV),
            harmonization_status="Partial / Proxy for 18-35",
            intended_use="Education-related age/sex table; named degree categories require external metadata confirmation",
            notes="Raw headers are generic itemvalue columns; Phase 6 does not infer named education-degree categories.",
        )
    )

    employed = read_csv(EMPLOYED_CSV)
    rows.append(
        InventoryRow(
            filename=EMPLOYED_CSV.name,
            source="not available in file; filename indicates New Taipei employed age structure",
            year_or_period=f"{int(employed['field1'].min())}-{int(employed['field1'].max())}",
            geography="新北市",
            age_scope="20 numeric percent columns; official age/sex labels are not present in the raw file. Alternating age-sex pairs are a provisional pattern inference only.",
            rows=len(employed),
            columns=", ".join(employed.columns),
            encoding=detect_encoding(EMPLOYED_CSV),
            harmonization_status="Proxy for 18-35; official labels unresolved",
            intended_use="Descriptive employment age-structure trend only; not an employment-rate measure",
            notes="Alternating columns sum to about 100% by side, but official age/sex metadata is absent from the raw CSV.",
        )
    )

    unemployment = read_csv(UNEMPLOYMENT_CSV)
    rows.append(
        InventoryRow(
            filename=UNEMPLOYMENT_CSV.name,
            source="not available in file; filename indicates New Taipei unemployment rate by age",
            year_or_period=f"{int(unemployment['field1'].min())}-{int(unemployment['field1'].max())}",
            geography="新北市",
            age_scope="20 numeric rate columns; official age/sex labels are not present in the raw file. Alternating age-sex pairs are a provisional pattern inference only.",
            rows=len(unemployment),
            columns=", ".join(unemployment.columns),
            encoding=detect_encoding(UNEMPLOYMENT_CSV),
            harmonization_status="Proxy for 18-35; official labels unresolved",
            intended_use="Descriptive unemployment-rate trend using provisional age groups",
            notes="Rates are not aggregated to 18-35 because labor-force denominators by single age and official column labels are not available in the raw CSV.",
        )
    )

    pdf_rows = "unknown"
    page_count = "unknown"
    source = "Ministry of Labor, 113年15-29歲青年勞工就業狀況調查報告"
    try:
        with pdfplumber.open(MOL_PDF) as pdf:
            page_count = str(len(pdf.pages))
            all_text = "\n".join((page.extract_text() or "") for page in pdf.pages)
            urls = list(dict.fromkeys(re.findall(r"https?://\S+", all_text)))
            if urls:
                source = f"{source}; source URLs in PDF: {'; '.join(urls)}"
    except Exception as exc:  # pragma: no cover - defensive for damaged PDFs
        source = f"{source}; PDF read error: {exc}"
    rows.append(
        InventoryRow(
            filename=MOL_PDF.name,
            source=source,
            year_or_period="ROC 113 / 2024 survey, published ROC 114 / 2025",
            geography="全台; regional grouping available, 北部 includes 新北市 but is not New Taipei-only",
            age_scope="15-29 youth workers",
            rows=pdf_rows,
            columns=f"{page_count} PDF pages; text/tables rather than CSV columns",
            encoding=detect_encoding(MOL_PDF),
            harmonization_status="Proxy for 18-35",
            intended_use="Job-search, transition intention, credential, and training participation statistics",
            notes="Use as national 15-29 labor survey evidence only; not New Taipei 18-35.",
        )
    )

    return pd.DataFrame([row.__dict__ for row in rows])


def build_population_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = read_csv(POPULATION_CSV)
    parts = raw["人口數"].astype(str).str.split("/", expand=True).apply(lambda s: s.str.strip())
    parsed = raw.copy()
    parsed["period"] = parts[0]
    parsed["area"] = parts[1]
    parsed["sex"] = parts[2]
    parsed["roc_year"] = parsed["period"].map(lambda x: parse_roc_period(str(x))[0])
    parsed["month"] = parsed["period"].map(lambda x: parse_roc_period(str(x))[1])
    parsed["year"] = parsed["roc_year"].map(lambda x: int(x) + 1911 if pd.notna(x) else pd.NA)

    age_cols = [col for col in raw.columns if re.match(r"\d+歲_統計$", col)]
    long = parsed[["period", "roc_year", "year", "month", "area", "sex"] + age_cols].melt(
        id_vars=["period", "roc_year", "year", "month", "area", "sex"],
        value_vars=age_cols,
        var_name="age_label",
        value_name="population",
    )
    long["age"] = long["age_label"].str.extract(r"(\d+)").astype(int)
    long["population"] = long["population"].map(clean_numeric).astype(int)
    long["age_scope"] = "single age"
    long = long[["period", "roc_year", "year", "month", "area", "sex", "age", "population", "age_scope"]]

    latest_month = (
        long[(long["area"] == "新北市") & (long["sex"].isin(["性別總計", "男", "女"])) & (long["month"].notna())]
        [["period", "roc_year", "year", "month"]]
        .drop_duplicates()
        .sort_values(["roc_year", "month"])
        .tail(1)
        .iloc[0]
    )
    latest = long[
        (long["area"] == "新北市")
        & (long["period"] == latest_month["period"])
        & (long["sex"].isin(["性別總計", "男", "女"]))
        & (long["age"].between(18, 35))
    ]
    summary = (
        latest.groupby(["period", "roc_year", "year", "area", "sex"], as_index=False)["population"]
        .sum()
        .rename(columns={"population": "population_18_35"})
    )
    summary["age_scope"] = "18-35 exact single-age sum"
    total = summary.loc[summary["sex"] == "性別總計", "population_18_35"].iloc[0]
    summary["share_of_18_35_total"] = summary["population_18_35"] / total

    scopes = [
        ("18-35", 18, 35, "Exact"),
        ("15-29", 15, 29, "Proxy / MOL survey comparator"),
        ("20-34", 20, 34, "Partial subset"),
        ("15-39", 15, 39, "Broad proxy"),
    ]
    scope_rows: list[dict[str, object]] = []
    for label, start, end, status in scopes:
        value = long[
            (long["area"] == "新北市")
            & (long["period"] == latest_month["period"])
            & (long["sex"] == "性別總計")
            & (long["age"].between(start, end))
        ]["population"].sum()
        scope_rows.append(
            {
                "period": latest_month["period"],
                "area": "新北市",
                "age_scope": label,
                "harmonization_status": status,
                "population": int(value),
            }
        )
    scope_comparison = pd.DataFrame(scope_rows)
    return long, summary, scope_comparison


def build_education_table() -> pd.DataFrame:
    raw = read_csv(EDUCATION_CSV).copy()
    raw["age_group"] = raw["itemvalue2"].astype(str).str.strip()
    raw["sex"] = raw["itemvalue3"].astype(str).str.strip()
    raw = raw.rename(columns={"field1": "year"})
    value_cols = [col for col in raw.columns if col.startswith("itemvalue") and col not in {"itemvalue2", "itemvalue3"}]
    for col in value_cols:
        raw[col] = raw[col].map(clean_numeric)
    long = raw[["year", "age_group", "sex"] + value_cols].melt(
        id_vars=["year", "age_group", "sex"],
        value_vars=value_cols,
        var_name="raw_education_column",
        value_name="value",
    )
    long["geography"] = "新北市"
    long["age_harmonization_status"] = long["age_group"].map(
        {
            "20~24歲": "Partial subset of 18-35",
            "25~29歲": "Partial subset of 18-35",
            "30~34歲": "Partial subset of 18-35",
            "15~19歲": "Proxy; includes 15-17 and misses age 18-only separation",
            "35~39歲": "Proxy; includes 36-39",
        }
    ).fillna("Outside youth target or total")
    long["category_label_status"] = "raw header only; named education-degree label unavailable in source CSV"
    return long[
        [
            "year",
            "geography",
            "age_group",
            "sex",
            "raw_education_column",
            "value",
            "age_harmonization_status",
            "category_label_status",
        ]
    ]


def build_labor_proxy_table(path: Path, value_name: str) -> pd.DataFrame:
    raw = read_csv(path).rename(columns={"field1": "year"})
    records = []
    for _, row in raw.iterrows():
        for col in raw.columns:
            if col == "year":
                continue
            index_match = re.search(r"(\d+)$", col)
            if not index_match:
                continue
            idx = int(index_match.group(1))
            age_group, sex = AGE_SEX_COLUMN_MAP[idx]
            records.append(
                {
                    "year": int(row["year"]),
                    "source_file": path.name,
                    "raw_column": col,
                    "inferred_age_group": age_group,
                    "sex": sex,
                    value_name: float(clean_numeric(row[col])),
                    "age_harmonization_status": "Proxy for 18-35",
                    "label_confidence": "unresolved; provisional pattern inference, official metadata absent from raw CSV",
                }
            )
    return pd.DataFrame(records)


def build_pdf_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    topics = [
        ("初次尋職前做過的準備", "job search preparation", "table 19 / report table 11", "pages 19-20, 83"),
        ("認為對初次尋職有幫助的就業資訊", "job-search information needs", "table 20 / report table 13", "pages 21, 85"),
        ("初次尋職時選擇工作的考慮因素", "job choice factors", "table 21 / report table 14", "page 22"),
        ("初次尋職遭遇的困難", "job-search barriers", "table 22 / report table 15", "page 23"),
        ("青年勞工打算轉換工作情形", "transition intention and reasons", "table 27 / report table 18", "pages 25, 95"),
        ("青年勞工持有證照情形", "credential holding", "table 29 / report table 20", "pages 26, 102-105"),
        ("青年勞工過去一年參加教育訓練情形", "training participation and barriers", "table 30 / figure 8", "pages 27, 107-109"),
    ]
    topics_df = pd.DataFrame(
        [
            {
                "source_file": MOL_PDF.name,
                "survey_age_scope": "15-29 youth workers",
                "geography": "全台; not New Taipei-only",
                "topic": topic,
                "relevance": relevance,
                "table_reference": table_ref,
                "extractable_pages": pages,
                "age_harmonization_status": "Proxy for 18-35",
            }
            for topic, relevance, table_ref, pages in topics
        ]
    )
    stats_df = pd.DataFrame(
        [
            {
                "source_file": MOL_PDF.name,
                "survey_period": "ROC 113 / 2024-10",
                "survey_age_scope": "15-29 youth workers",
                "geography": "全台",
                "category": category,
                "indicator": indicator,
                "percent": percent,
                "denominator_note": denominator,
                "source_location": page,
                "age_harmonization_status": "Proxy for 18-35",
            }
            for category, indicator, percent, denominator, page in PDF_STATS
        ]
    )
    return topics_df, stats_df


def save_chart_population_age(pop_long: pd.DataFrame) -> Path:
    latest = pop_long[
        (pop_long["area"] == "新北市")
        & (pop_long["sex"] == "性別總計")
        & (pop_long["period"] == "109年 10月")
        & (pop_long["age"].between(18, 35))
    ].copy()
    path = OUTPUT_DIR / "ntpc_population_18_35_by_age_109_10.png"
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(latest["age"], latest["population"], color="#2f7d57")
    ax.set_title("新北市 18-35 歲人口：單齡結構（Exact，109年10月）")
    ax.set_xlabel("年齡")
    ax.set_ylabel("人口數")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def save_chart_population_sex(pop_summary: pd.DataFrame) -> Path:
    chart = pop_summary[pop_summary["sex"].isin(["男", "女"])].copy()
    path = OUTPUT_DIR / "ntpc_population_18_35_by_sex_109_10.png"
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.bar(chart["sex"], chart["population_18_35"], color=["#3f8f67", "#77b58a"])
    ax.set_title("新北市 18-35 歲人口：性別結構（Exact，109年10月）")
    ax.set_xlabel("性別")
    ax.set_ylabel("人口數")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def save_chart_population_scope(scope_comparison: pd.DataFrame) -> Path:
    path = OUTPUT_DIR / "ntpc_population_age_scope_comparison_109_10.png"
    colors = ["#2f7d57" if label == "Exact" else "#a5b9aa" for label in scope_comparison["harmonization_status"]]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.bar(scope_comparison["age_scope"], scope_comparison["population"], color=colors)
    ax.set_title("新北市青年年齡範圍人口比較（實際 scope，109年10月）")
    ax.set_xlabel("年齡範圍")
    ax.set_ylabel("人口數")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def save_chart_employed_proxy(employed_long: pd.DataFrame) -> Path:
    youth_groups = ["15-24", "25-29", "30-34", "35-39"]
    chart = employed_long[employed_long["inferred_age_group"].isin(youth_groups)].copy()
    grouped = chart.groupby(["year", "sex"], as_index=False)["employed_share_percent"].sum()
    path = OUTPUT_DIR / "ntpc_employed_youth_proxy_trend_2006_2024.png"
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for sex, color in [("male", "#2f7d57"), ("female", "#77b58a")]:
        series = grouped[grouped["sex"] == sex]
        ax.plot(series["year"], series["employed_share_percent"], marker="o", linewidth=1.8, color=color, label=sex)
    ax.set_title("新北就業者年齡結構：15-39 provisional proxy share（2006-2024）")
    ax.set_xlabel("年")
    ax.set_ylabel("就業者占比加總（%）")
    ax.legend(title="sex")
    ax.grid(axis="y", alpha=0.25)
    fig.text(
        0.01,
        0.01,
        "Age scope uses unresolved provisional column mapping; this is age structure, not youth employment rate.",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path)
    plt.close(fig)
    return path


def save_chart_unemployment_proxy(unemployment_long: pd.DataFrame) -> Path:
    youth_groups = ["15-24", "25-29", "30-34", "35-39"]
    chart = unemployment_long[unemployment_long["inferred_age_group"].isin(youth_groups)].copy()
    grouped = chart.groupby(["year", "inferred_age_group"], as_index=False)["unemployment_rate_percent"].mean()
    path = OUTPUT_DIR / "ntpc_unemployment_youth_proxy_trend_2006_2024.png"
    fig, ax = plt.subplots(figsize=(9, 4.8))
    colors = ["#2f7d57", "#589d75", "#86bd93", "#c6a15b"]
    for group, color in zip(youth_groups, colors):
        series = grouped[grouped["inferred_age_group"] == group]
        ax.plot(series["year"], series["unemployment_rate_percent"], marker="o", linewidth=1.8, color=color, label=group)
    ax.set_title("新北青年相關年齡組失業率趨勢（provisional sex average proxy，2006-2024）")
    ax.set_xlabel("年")
    ax.set_ylabel("失業率（%）")
    ax.legend(title="inferred age group")
    ax.grid(axis="y", alpha=0.25)
    fig.text(0.01, 0.01, "Age scope uses unresolved provisional column mapping; not aggregated 18-35.", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path)
    plt.close(fig)
    return path


def save_chart_pdf_training(pdf_stats: pd.DataFrame) -> Path:
    labels = [
        "有打算轉換工作",
        "近一年有參加教育訓練",
        "認為就業資訊有助於初次尋職",
        "技能不足",
        "不知道哪裡有提供訓練課程的機構",
        "參加訓練的費用太高，負擔不起",
    ]
    chart = pdf_stats[pdf_stats["indicator"].isin(labels)].copy()
    chart["indicator"] = pd.Categorical(chart["indicator"], categories=labels, ordered=True)
    chart = chart.sort_values("indicator")
    path = OUTPUT_DIR / "mol_youth_job_transition_training_stats_113.png"
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    ax.barh(chart["indicator"], chart["percent"], color="#2f7d57")
    ax.set_title("勞動部 113 年 15-29 歲青年勞工：尋職／轉職／訓練相關指標")
    ax.set_xlabel("%")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    fig.text(0.01, 0.01, "Age scope: 15-29 youth workers, national survey; not New Taipei 18-35.", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path)
    plt.close(fig)
    return path


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    frame = df.copy()
    frame = frame.fillna("")
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


def write_inventory_doc(inventory: pd.DataFrame) -> None:
    lines = [
        "# Youth Data Inventory",
        "",
        f"Generated: {OBSERVATION_DATE}",
        "",
        "Scope: `data/raw/career/youth/`. Raw files were only read, not modified.",
        "",
        markdown_table(
            inventory[
                [
                    "filename",
                    "source",
                    "year_or_period",
                    "geography",
                    "age_scope",
                    "rows",
                    "encoding",
                    "harmonization_status",
                    "intended_use",
                ]
            ]
        ),
        "",
        "## Column Inventory",
        "",
    ]
    for _, row in inventory.iterrows():
        lines.extend([f"### {row['filename']}", "", f"- Columns/pages: {row['columns']}", f"- Notes: {row['notes']}", ""])
    INVENTORY_MD.write_text("\n".join(lines), encoding="utf-8")


def write_harmonization_doc(scope_comparison: pd.DataFrame) -> None:
    lines = [
        "# Youth Age Harmonization Rules",
        "",
        f"Generated: {OBSERVATION_DATE}",
        "",
        "Target policy-analysis age concept: 18-35.",
        "",
        "## Rule Classes",
        "",
        "- Exact: the raw file has single-year ages or exact bins that can be summed to 18-35 without interpolation.",
        "- Partial: the raw file covers only part of 18-35, such as 20-34. It must be labeled as a subset, not as 18-35.",
        "- Proxy: the raw file uses nearby or official groups, such as 15-29, 15-24, or 35-39. It can support context but cannot be relabeled as 18-35.",
        "",
        "## Applied Rules",
        "",
        "| Dataset | Rule | Phase 6 treatment |",
        "|---|---|---|",
        "| `population_single_age_by_area_2026.csv` | Exact | Sum single ages 18 through 35 for New Taipei. |",
        "| `ntpc_education_by_age.csv` | Partial / Proxy | Use official bins as-is. 20-34 is a partial subset; 15-39 is a broad proxy. Named education-category labels are unavailable in the raw CSV. |",
        "| `ntpc_employed_age_structure.csv` | Proxy / unresolved labels | Raw headers do not confirm official age/sex labels. Current long output keeps provisional column mapping for QA only. Treat as age-structure context, not youth employment rate. |",
        "| `ntpc_unemployment_rate_by_age.csv` | Proxy / unresolved labels | Raw headers do not confirm official age/sex labels. Plot provisional groups separately; do not average into an 18-35 rate without denominators and metadata. |",
        "| `mol_youth_employment_survey_113.pdf` | Proxy | Use as national 15-29 youth-worker survey evidence. Do not treat as New Taipei 18-35. |",
        "",
        "## New Taipei Population Scope Comparison",
        "",
        markdown_table(scope_comparison),
        "",
        "## Guardrails",
        "",
        "- Do not treat 15-24, 15-29, 20-34, 35-39, or 15-39 as exact 18-35.",
        "- Do not interpolate single ages into grouped labor-market rates in Phase 6.",
        "- When source headers are generic, keep raw column names and mark inferred labels unresolved until official metadata is available.",
    ]
    HARMONIZATION_MD.write_text("\n".join(lines), encoding="utf-8")


def write_summary_doc(
    inventory: pd.DataFrame,
    pop_summary: pd.DataFrame,
    scope_comparison: pd.DataFrame,
    education_long: pd.DataFrame,
    employed_long: pd.DataFrame,
    unemployment_long: pd.DataFrame,
    pdf_topics: pd.DataFrame,
    pdf_stats: pd.DataFrame,
    chart_paths: list[Path],
) -> None:
    ntpc_total = int(pop_summary.loc[pop_summary["sex"] == "性別總計", "population_18_35"].iloc[0])
    ntpc_male = int(pop_summary.loc[pop_summary["sex"] == "男", "population_18_35"].iloc[0])
    ntpc_female = int(pop_summary.loc[pop_summary["sex"] == "女", "population_18_35"].iloc[0])
    male_share = ntpc_male / ntpc_total * 100
    female_share = ntpc_female / ntpc_total * 100
    pop_period = str(pop_summary["period"].iloc[0])

    youth_ages = read_csv(POPULATION_CSV)
    # Reuse processed long to get largest single ages.
    pop_long = pd.read_csv(PROCESSED_YOUTH / "ntpc_population_single_age_phase6.csv")
    age_rank = (
        pop_long[
            (pop_long["area"] == "新北市")
            & (pop_long["period"] == pop_period)
            & (pop_long["sex"] == "性別總計")
            & (pop_long["age"].between(18, 35))
        ]
        .sort_values("population", ascending=False)
        .head(5)[["age", "population"]]
    )

    employed_proxy = (
        employed_long[employed_long["inferred_age_group"].isin(["15-24", "25-29", "30-34", "35-39"])]
        .groupby(["year", "sex"], as_index=False)["employed_share_percent"]
        .sum()
    )
    employed_2006 = employed_proxy[employed_proxy["year"] == 2006].set_index("sex")["employed_share_percent"]
    employed_2024 = employed_proxy[employed_proxy["year"] == 2024].set_index("sex")["employed_share_percent"]

    unemployment_proxy = unemployment_long[
        unemployment_long["inferred_age_group"].isin(["15-24", "25-29", "30-34", "35-39"])
    ].copy()
    unemp_2024 = (
        unemployment_proxy[unemployment_proxy["year"] == 2024]
        .groupby("inferred_age_group")["unemployment_rate_percent"]
        .mean()
        .reset_index()
    )

    pdf_highlights = pdf_stats[
        pdf_stats["indicator"].isin(
            [
                "有打算轉換工作",
                "近一年有參加教育訓練",
                "認為就業資訊有助於初次尋職",
                "技能不足",
                "不知道哪裡有提供訓練課程的機構",
                "參加訓練的費用太高，負擔不起",
            ]
        )
    ][["indicator", "percent", "denominator_note", "survey_age_scope"]]

    education_latest = education_long[
        (education_long["year"] == education_long["year"].max())
        & (education_long["sex"] == "計")
        & (education_long["age_group"].isin(["15~19歲", "20~24歲", "25~29歲", "30~34歲", "35~39歲"]))
        & (education_long["raw_education_column"] == "itemvalue4")
    ][["age_group", "value", "age_harmonization_status"]]

    lines = [
        "# Youth Statistics Phase 6",
        "",
        f"Generated: {OBSERVATION_DATE}",
        "",
        "This is a first-pass youth evidence inventory and descriptive analysis. It does not change raw data, v1-v4 career methodology, UI, or policy recommendations.",
        "",
        "## Files Used",
        "",
        markdown_table(inventory[["filename", "harmonization_status", "intended_use"]]),
        "",
        "## First-Pass Findings",
        "",
        f"1. New Taipei has {ntpc_total:,} residents aged 18-35 in the exact single-age population table for `{pop_period}`; the split is {male_share:.1f}% male and {female_share:.1f}% female.",
        "2. Age-scope choice materially changes the denominator: the 15-29 proxy is much smaller than 18-35, while the 15-39 broad proxy is much larger.",
        f"3. Within the New Taipei employed-age-structure table, the provisional 15-39 proxy share declined from 2006 to 2024 for both column sides labeled male/female by pattern inference ({employed_2006.get('male', float('nan')):.1f}% to {employed_2024.get('male', float('nan')):.1f}% and {employed_2006.get('female', float('nan')):.1f}% to {employed_2024.get('female', float('nan')):.1f}%). This describes age composition within employed people, not a youth employment-rate decline.",
        "4. In the provisional 2024 unemployment proxy, the 15-24 column group is highest; rates are lower in the 25-29, 30-34, and 35-39 provisional groups.",
        "5. The MOL 113 national 15-29 youth-worker survey provides directly relevant signals for career exploration: transition intention, job-search barriers, credential holding, and training participation/barriers.",
        "",
        "## New Taipei 18-35 Population",
        "",
        f"- Exact source: `population_single_age_by_area_2026.csv`, using row labels for `{pop_period}`.",
        f"- New Taipei age 18-35 population: {ntpc_total:,}.",
        f"- Male: {ntpc_male:,} ({male_share:.1f}%). Female: {ntpc_female:,} ({female_share:.1f}%).",
        "",
        "Largest single-age cohorts within 18-35:",
        "",
        markdown_table(age_rank),
        "",
        "Age-scope comparison, showing why proxy ranges must not be relabeled as 18-35:",
        "",
        markdown_table(scope_comparison),
        "",
        "## Employment Trend",
        "",
        "The New Taipei employed-age table uses generic raw headers. Phase 6 keeps a provisional age-sex mapping because alternating columns sum to about 100% by side, but the official column labels are unresolved from existing files. This can describe age-structure change only; it is not a youth employment-rate measure.",
        "",
        f"- Provisional 15-39 share on the column side labeled male by pattern inference: {employed_2006.get('male', float('nan')):.1f}% in 2006 to {employed_2024.get('male', float('nan')):.1f}% in 2024.",
        f"- Provisional 15-39 share on the column side labeled female by pattern inference: {employed_2006.get('female', float('nan')):.1f}% in 2006 to {employed_2024.get('female', float('nan')):.1f}% in 2024.",
        "- Interpretation guardrail: this is an employed-population age-structure share, not the employment rate of young people.",
        "",
        "## Unemployment Trend",
        "",
        "The unemployment table is shown by provisional age groups because official column labels are absent from existing files. No 18-35 aggregate unemployment rate is calculated because labor-force denominators by single age and confirmed metadata are not available.",
        "",
        "2024 youth-related unemployment-rate proxies, averaged across the male/female columns only for compact display:",
        "",
        markdown_table(unemp_2024),
        "",
        "## Education Structure",
        "",
        "`ntpc_education_by_age.csv` covers New Taipei from 1998-2024 and uses official age bins. It can support 20-34 partial-subset analysis and 15-39 broad-proxy context, but not exact 18-35. The raw file does not include named education-category labels; Phase 6 therefore preserves raw `itemvalue*` columns and does not claim a degree-level structure such as university / senior high / junior college.",
        "",
        "Latest available official age-bin population totals in the education table, using `itemvalue4` as the reported total column:",
        "",
        markdown_table(education_latest),
        "",
        "## MOL 113 Survey Extractable Topics",
        "",
        "The PDF is a national 15-29 youth-worker survey. It is useful for job-search, transition, credential, and training context, but it is not New Taipei 18-35.",
        "",
        markdown_table(pdf_topics[["topic", "relevance", "extractable_pages", "age_harmonization_status"]]),
        "",
        "Selected extracted statistics:",
        "",
        markdown_table(pdf_highlights),
        "",
        "## Charts",
        "",
    ]
    for path in chart_paths:
        lines.append(f"- `{path.relative_to(PROJECT_ROOT)}`")
    lines.extend(
        [
            "",
        "## Data Limitations",
        "",
        "- Exact 18-35 is available only for the population single-age table.",
        "- Employment and unemployment age labels are unresolved from existing files; current long outputs use provisional pattern inference only.",
        "- Education degree-category labels are not present in the raw CSV headers, so named degree composition remains a manual-review item.",
        "- MOL 113 survey results are national 15-29 youth-worker statistics and should not be interpreted as New Taipei 18-35.",
        "",
        "## Career Policy Lens-Ready Inputs",
        "",
        "These are descriptive inputs that can be connected to a later Career Policy Lens without making policy recommendations in Phase 6:",
        "",
        "- Exact New Taipei 18-35 denominator and sex/age structure.",
        "- Age-scope harmonization flags so later analysis can separate Exact, Partial, and Proxy evidence.",
        "- Youth-related employment and unemployment trends only after unresolved labor-table column labels are confirmed.",
        "- MOL survey indicators on job-search uncertainty, transition intention, credential holding, training participation, and training access barriers.",
        "- Manual-review needs for education category metadata and labor-table column labels.",
    ]
    )
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    configure_matplotlib()
    PROCESSED_YOUTH.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    inventory = build_inventory()
    population_long, population_summary, scope_comparison = build_population_tables()
    education_long = build_education_table()
    employed_long = build_labor_proxy_table(EMPLOYED_CSV, "employed_share_percent")
    unemployment_long = build_labor_proxy_table(UNEMPLOYMENT_CSV, "unemployment_rate_percent")
    pdf_topics, pdf_stats = build_pdf_tables()

    inventory.to_csv(PROCESSED_YOUTH / "youth_data_inventory_phase6.csv", index=False, encoding="utf-8-sig")
    population_long.to_csv(PROCESSED_YOUTH / "ntpc_population_single_age_phase6.csv", index=False, encoding="utf-8-sig")
    population_summary.to_csv(
        PROCESSED_YOUTH / "ntpc_population_18_35_summary_phase6.csv", index=False, encoding="utf-8-sig"
    )
    scope_comparison.to_csv(
        PROCESSED_YOUTH / "ntpc_population_age_scope_comparison_phase6.csv", index=False, encoding="utf-8-sig"
    )
    education_long.to_csv(PROCESSED_YOUTH / "ntpc_education_by_age_phase6_long.csv", index=False, encoding="utf-8-sig")
    employed_long.to_csv(
        PROCESSED_YOUTH / "ntpc_employed_age_structure_phase6_long.csv", index=False, encoding="utf-8-sig"
    )
    unemployment_long.to_csv(
        PROCESSED_YOUTH / "ntpc_unemployment_rate_by_age_phase6_long.csv", index=False, encoding="utf-8-sig"
    )
    pdf_topics.to_csv(PROCESSED_YOUTH / "mol_youth_employment_survey_topics_phase6.csv", index=False, encoding="utf-8-sig")
    pdf_stats.to_csv(PROCESSED_YOUTH / "mol_youth_employment_survey_stats_phase6.csv", index=False, encoding="utf-8-sig")

    chart_paths = [
        save_chart_population_age(population_long),
        save_chart_population_sex(population_summary),
        save_chart_employed_proxy(employed_long),
        save_chart_unemployment_proxy(unemployment_long),
        save_chart_pdf_training(pdf_stats),
    ]

    write_inventory_doc(inventory)
    write_harmonization_doc(scope_comparison)
    write_summary_doc(
        inventory,
        population_summary,
        scope_comparison,
        education_long,
        employed_long,
        unemployment_long,
        pdf_topics,
        pdf_stats,
        chart_paths,
    )

    print(f"Wrote {len(inventory)} inventory rows")
    print(f"Wrote processed CSVs to {PROCESSED_YOUTH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {len(chart_paths)} charts to {OUTPUT_DIR.relative_to(PROJECT_ROOT)}")
    print(f"Wrote docs: {INVENTORY_MD.relative_to(PROJECT_ROOT)}, {HARMONIZATION_MD.relative_to(PROJECT_ROOT)}")
    print(f"Wrote summary: {SUMMARY_MD.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
