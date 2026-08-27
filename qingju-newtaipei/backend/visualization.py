"""Plotly 地圖與散佈圖。"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


TYPE_COLORS = {
    "就業安居平衡型": "#16A085",
    "高機會高負擔型": "#E67E22",
    "低成本低機會型": "#5DADE2",
    "高負擔低機會型": "#A569BD",
    "資料不足": "#CBD5E1",
}

DIAGNOSIS_COLORS = {
    "青年承接平衡型": "#0F766E",
    "青年集中高負擔型": "#C2410C",
    "青年集中就業待查型": "#2563EB",
    "青年集中雙重待查型": "#BE123C",
    "就業吸引潛力型": "#16A34A",
    "高機會高負擔型": "#D97706",
    "低成本資源待查型": "#7C3AED",
    "高負擔資源待查型": "#9333EA",
    "資料待補型": "#94A3B8",
}


def load_geojson(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _fmt(value: object, prefix: str = "", suffix: str = "") -> str:
    return "資料不足" if pd.isna(value) else f"{prefix}{float(value):,.0f}{suffix}"


def make_choropleth(summary: pd.DataFrame, geojson: dict, mode: str) -> go.Figure:
    data = summary.copy()
    data["type_display"] = data["opportunity_housing_type"].fillna("資料不足")
    data["job_postings_display"] = data["job_postings"].map(lambda x: _fmt(x, suffix=" 筆"))
    data["hiring_display"] = data["hiring_count"].map(lambda x: _fmt(x, suffix=" 人"))
    data["company_display"] = data["company_count"].map(lambda x: _fmt(x, suffix=" 家"))
    data["salary_display"] = data["median_salary"].map(lambda x: _fmt(x, "NT$", "/月"))
    data["rent_display"] = data["median_rent"].map(lambda x: _fmt(x, "NT$", "/月"))
    data["average_rent_display"] = data["average_rent"].map(lambda x: _fmt(x, "NT$", "/月"))
    data["rental_count_display"] = data["rental_count"].map(lambda x: _fmt(x, suffix=" 件"))
    data["youth_display"] = data["estimated_youth_18_35"].map(lambda x: _fmt(x, suffix=" 人（推估）"))
    data["top_job_category"] = data["top_job_category"].fillna("資料不足")

    common_hover = {
        "district": True,
        "job_postings_display": True,
        "hiring_display": True,
        "company_display": True,
        "salary_display": True,
        "top_job_category": True,
        "rent_display": True,
        "average_rent_display": True,
        "rental_count_display": True,
        "youth_display": True,
    }
    labels = {
        "district": "行政區", "job_postings_display": "職缺筆數", "hiring_display": "求才人數",
        "company_display": "公司數", "salary_display": "月薪中位數", "top_job_category": "熱門職類",
        "rent_display": "租金中位數", "average_rent_display": "平均租金", "rental_count_display": "租賃案件數",
        "youth_display": "設籍18–35歲青年人口",
        "hiring_count": "求才人數", "median_rent": "租金中位數", "type_display": "類型",
    }
    if mode == "💼 工作機會":
        fig = px.choropleth_map(data, geojson=geojson, locations="district", featureidkey="properties.district",
            color="hiring_count", color_continuous_scale=["#E8F7F1", "#0F766E"], hover_data=common_hover,
            labels=labels, opacity=0.82)
        fig.update_layout(coloraxis_colorbar_title="求才人數")
    elif mode == "🏠 租屋成本":
        fig = px.choropleth_map(data, geojson=geojson, locations="district", featureidkey="properties.district",
            color="median_rent", color_continuous_scale=["#FFF4E6", "#C2410C"], hover_data=common_hover,
            labels=labels, opacity=0.82)
        fig.update_layout(coloraxis_colorbar_title="租金中位數")
    elif mode == "🧭 區域診斷":
        fig = px.choropleth_map(
            data, geojson=geojson, locations="district", featureidkey="properties.district",
            color="district_diagnosis", color_discrete_map=DIAGNOSIS_COLORS,
            category_orders={"district_diagnosis": list(DIAGNOSIS_COLORS)},
            hover_data=common_hover, labels=labels, opacity=0.84,
        )
        fig.update_layout(legend_title_text="青年落腳診斷")
    else:
        fig = px.choropleth_map(data, geojson=geojson, locations="district", featureidkey="properties.district",
            color="type_display", color_discrete_map=TYPE_COLORS, category_orders={"type_display": list(TYPE_COLORS)},
            hover_data=common_hover, labels=labels, opacity=0.84)
        fig.update_layout(legend_title_text="就業 × 安居類型")
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        map_style="carto-positron", map_zoom=8.1, map_center={"lat": 25.02, "lon": 121.53},
        margin={"r": 0, "t": 8, "l": 0, "b": 0}, height=590,
        hoverlabel={
            "bgcolor": "#111827",
            "bordercolor": "#334155",
            "font": {"color": "#F8FAFC", "size": 14},
        },
    )
    return fig


def make_scatter(summary: pd.DataFrame, thresholds: dict) -> go.Figure:
    data = summary.dropna(subset=["median_rent", "hiring_count"]).copy()
    fig = px.scatter(
        data, x="median_rent", y="hiring_count", text="district",
        size="job_postings", size_max=28,
        custom_data=["district", "median_rent", "hiring_count", "median_salary"],
        labels={"median_rent": "租金中位數（元／月）", "hiring_count": "求才人數（人）"},
    )
    fig.update_traces(
        textposition="top center",
        marker={"color": "#0F766E", "line": {"color": "#FFFFFF", "width": 1}},
        hovertemplate="<b>%{customdata[0]}</b><br>租金中位數：NT$%{customdata[1]:,.0f}<br>求才人數：%{customdata[2]:,.0f} 人<br>職缺月薪中位數：NT$%{customdata[3]:,.0f}<extra></extra>",
    )
    fig.add_vline(x=thresholds["median_rent"], line_dash="dash", line_color="#64748B")
    fig.add_hline(y=thresholds["median_hiring_count"], line_dash="dash", line_color="#64748B")
    fig.update_layout(height=570, margin={"l": 0, "r": 0, "t": 20, "b": 0}, plot_bgcolor="#F8FAFC")
    return fig
