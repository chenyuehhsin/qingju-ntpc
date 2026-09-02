from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_cleaner import STANDARD_DISTRICTS
from src.data_loader import PROJECT_ROOT, PROCESSED_CSV, find_geojson, load_geojson, read_processed
from src.metrics import aggregate_rate


st.set_page_config(page_title="新北市青年就業地圖", layout="wide")


@st.cache_data
def load_data() -> pd.DataFrame:
    return read_processed(PROCESSED_CSV)


@st.cache_data
def load_available_geojson() -> tuple[dict | None, str | None, str | None]:
    candidates = [
        path
        for path in find_geojson(PROJECT_ROOT)
        if "new_taipei" in path.name.lower()
        or "district" in path.name.lower()
        or "行政區" in path.name
        or "新北" in path.name
    ]
    for path in candidates:
        geojson = load_geojson(path)
        property_name = detect_geojson_district_property(geojson)
        if property_name:
            return geojson, str(path), property_name
    return None, None, None


def detect_geojson_district_property(geojson: dict) -> str | None:
    features = geojson.get("features", [])
    if not features:
        return None
    properties = features[0].get("properties", {})
    for key in properties:
        values = [feature.get("properties", {}).get(key) for feature in features]
        if any(value in STANDARD_DISTRICTS for value in values):
            return key
    return None


def metric_total(series: pd.Series) -> float | pd.NA:
    return pd.to_numeric(series, errors="coerce").sum(min_count=1)


def format_number(value: object, decimals: int = 0) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "資料不足"
    return f"{numeric:,.{decimals}f}"


def metric_card(label: str, value: object, decimals: int = 0) -> None:
    st.metric(label, format_number(value, decimals))


def detail_value(df: pd.DataFrame, column: str) -> object:
    if column not in df.columns or df.empty:
        return pd.NA
    value = df.iloc[0][column]
    return value if pd.notna(value) and str(value).strip() else pd.NA


st.title("新北市青年就業地圖")

if not PROCESSED_CSV.exists():
    st.error("找不到 data/processed/youth_employment_map.csv，請先執行資料建置腳本。")
    st.code("python scripts/build_youth_employment_map.py")
    st.stop()

data = load_data()

for column in ["youth_population_18_35", "job_postings", "job_openings", "jobs_per_1000_youth", "avg_salary"]:
    if column in data.columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

total_youth = metric_total(data["youth_population_18_35"])
total_postings = metric_total(data["job_postings"])
total_openings = metric_total(data["job_openings"])
city_rate = aggregate_rate(data["job_openings"], data["youth_population_18_35"])

cols = st.columns(4)
with cols[0]:
    metric_card("新北市 18–35 歲青年人口", total_youth)
with cols[1]:
    metric_card("職缺刊登數", total_postings)
with cols[2]:
    metric_card("工作機會總數", total_openings)
with cols[3]:
    metric_card("每千名青年工作機會", city_rate, 2)

metric_options = {
    "青年人口": "youth_population_18_35",
    "工作機會": "job_openings",
    "每千名青年工作機會": "jobs_per_1000_youth",
}
if "avg_salary" in data.columns and data["avg_salary"].notna().any():
    metric_options["平均薪資"] = "avg_salary"

selected_metric_label = st.selectbox("地圖指標", list(metric_options.keys()))
selected_metric = metric_options[selected_metric_label]

geojson, geojson_path, geojson_property = load_available_geojson()
if geojson and geojson_property:
    fig = px.choropleth(
        data,
        geojson=geojson,
        locations="district",
        featureidkey=f"properties.{geojson_property}",
        color=selected_metric,
        hover_name="district",
        hover_data={
            "youth_population_18_35": ":,.0f",
            "job_openings": ":,.0f",
            "jobs_per_1000_youth": ":,.2f",
            "avg_salary": ":,.0f" if "avg_salary" in data.columns else False,
            "district": False,
        },
        color_continuous_scale="Viridis",
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r": 0, "t": 20, "l": 0, "b": 0})
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"GeoJSON: {geojson_path}")
else:
    st.warning("目前 repository 沒有可辨識的新北市行政區 GeoJSON；已保留載入介面，尚未使用來源不明的邊界資料。")

rank_cols = st.columns(2)
with rank_cols[0]:
    chart_data = data.dropna(subset=["job_openings"]).sort_values("job_openings", ascending=False).head(10)
    if chart_data.empty:
        st.info("尚無工作機會資料可繪製排名。")
    else:
        fig = px.bar(chart_data, x="job_openings", y="district", orientation="h", title="青年工作機會最多行政區")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

with rank_cols[1]:
    chart_data = data.dropna(subset=["jobs_per_1000_youth"]).sort_values("jobs_per_1000_youth", ascending=False).head(10)
    if chart_data.empty:
        st.info("尚無每千名青年工作機會資料可繪製排名。")
    else:
        fig = px.bar(
            chart_data,
            x="jobs_per_1000_youth",
            y="district",
            orientation="h",
            title="每千名青年工作機會最高行政區",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

selected_district = st.selectbox("行政區詳細資訊", data["district"].tolist())
district_row = data[data["district"] == selected_district]

detail_cols = st.columns(4)
with detail_cols[0]:
    metric_card("青年人口", detail_value(district_row, "youth_population_18_35"))
with detail_cols[1]:
    metric_card("職缺", detail_value(district_row, "job_postings"))
with detail_cols[2]:
    metric_card("工作機會", detail_value(district_row, "job_openings"))
with detail_cols[3]:
    metric_card("每千名青年工作機會", detail_value(district_row, "jobs_per_1000_youth"), 2)

st.subheader("資料細節")
detail_table = pd.DataFrame(
    [
        {"項目": "熱門職缺類別", "值": detail_value(district_row, "top_job_category")},
        {"項目": "熱門職業", "值": detail_value(district_row, "top_occupation")},
        {"項目": "熱門產業", "值": detail_value(district_row, "top_industry")},
        {"項目": "平均薪資", "值": format_number(detail_value(district_row, "avg_salary"))},
        {"項目": "薪資中位數", "值": format_number(detail_value(district_row, "median_salary"))},
        {"項目": "公司數", "值": format_number(detail_value(district_row, "company_count"))},
    ]
)
detail_table["值"] = detail_table["值"].apply(lambda value: "資料不足" if pd.isna(value) or str(value).strip() == "" else value)
st.table(detail_table)

with st.expander("整合資料表"):
    st.dataframe(data, use_container_width=True)
