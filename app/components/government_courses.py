"""就業轉職｜政府課程 × 就業需求.

All figures come from existing processed datasets:
- Government training courses: data/processed/career/career_training_skill_mapping.csv
- Employment demand: data/processed/employment/new_taipei_employment_summary.csv
- Youth training signals (MOL 15-29 proxy): outputs/career/career_policy_lens_phase7.csv

No values are fabricated; unavailable dimensions are omitted rather than invented.
"""
from __future__ import annotations

from html import escape

import pandas as pd
import plotly.express as px
import streamlit as st

TEAL = "#2E9E6B"
BLUE = "#257FBE"
AMBER = "#D99436"

_IC_BOOK = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4h11a2 2 0 0 1 2 2v14H7a2 2 0 0 0-2 2z"/><path d="M18 6v14"/></svg>'
_IC_CLOCK = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>'
_IC_COIN = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v10M9.5 9.5h4a1.8 1.8 0 0 1 0 3.6h-3a1.8 1.8 0 0 0 0 3.6h4"/></svg>'
_IC_BRIEF = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>'


def _inject_courses_styles() -> None:
    if st.session_state.get("_gov_courses_styles_injected"):
        return
    st.session_state._gov_courses_styles_injected = True
    st.markdown(
        """
        <style>
        .qj-kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:0.8rem;margin:0.2rem 0 1.1rem;}
        .qj-kpi{background:#ffffff;border:1px solid #E3EDE7;border-radius:16px;padding:0.9rem 1rem;
            box-shadow:0 2px 8px rgba(23,50,77,0.05);display:flex;gap:0.7rem;align-items:flex-start;}
        .qj-kpi-ic{width:2.5rem;height:2.5rem;border-radius:12px;display:flex;align-items:center;
            justify-content:center;background:#EAF6FF;color:#257FBE;flex:0 0 auto;}
        .qj-kpi-body{min-width:0;}
        .qj-kpi-value{font-size:1.55rem;font-weight:900;color:#17324D;line-height:1.1;overflow-wrap:anywhere;}
        .qj-kpi-label{color:#4F5F65;font-size:0.86rem;font-weight:800;margin-top:0.16rem;}
        .qj-kpi-sub{color:#8A97A0;font-size:0.74rem;margin-top:0.12rem;line-height:1.35;}
        .qj-gc-card{background:#ffffff;border:1px solid #E3EDE7;border-radius:16px;padding:0.9rem 1rem 0.6rem;
            box-shadow:0 2px 8px rgba(23,50,77,0.05);margin-bottom:0.8rem;}
        .qj-gc-card-title{color:#17324D;font-size:1.02rem;font-weight:850;}
        .qj-gc-card-sub{color:#8A97A0;font-size:0.78rem;margin:0.1rem 0 0.2rem;line-height:1.4;}
        .qj-gc-pending{background:#FBF7EC;border:1px dashed #E4CF9B;border-radius:14px;padding:0.9rem 1rem;
            color:#8A6D2F;font-size:0.9rem;line-height:1.5;margin-bottom:0.8rem;}
        .qj-gc-pending b{color:#6C5320;}
        @media(max-width:900px){.qj-kpi-grid{grid-template-columns:1fr 1fr;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _kpi_html(icon: str, value: str, label: str, sub: str) -> str:
    return (
        '<div class="qj-kpi">'
        f'<div class="qj-kpi-ic">{icon}</div>'
        '<div class="qj-kpi-body">'
        f'<div class="qj-kpi-value">{escape(value)}</div>'
        f'<div class="qj-kpi-label">{escape(label)}</div>'
        f'<div class="qj-kpi-sub">{escape(sub)}</div>'
        "</div></div>"
    )


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def render_government_courses(
    course_mapping: pd.DataFrame,
    employment_summary: pd.DataFrame,
    career_policy: pd.DataFrame,
) -> None:
    _inject_courses_styles()

    st.markdown(
        """
        <div class="qj-career-header">
            <h1 class="qj-visually-hidden">就業轉職</h1>
            <div class="qj-page-intro">整合政府職訓課程供給與新北就業需求，作為青年轉職與政策設計的第一層事實基礎。所有數字均來自既有資料集，缺資料的維度不臆造。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="qj-section-title">政府課程 × 就業需求</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="qj-section-copy">左側是目前可對應到 O*NET 技能缺口的職訓課程供給，右側是新北 29 區的就業需求訊號；下方保留護理師薪資／工時／少子化的資料接口。</div>',
        unsafe_allow_html=True,
    )

    courses = course_mapping.copy()
    unique_courses = courses.drop_duplicates(subset=["course_code"]).copy()
    unique_courses["training_hours"] = _num(unique_courses["training_hours"])
    unique_courses["fee_per_person"] = _num(unique_courses["fee_per_person"])

    emp = employment_summary.copy()
    emp["hiring_count"] = _num(emp["hiring_count"])
    emp["job_postings"] = _num(emp["job_postings"])
    emp["median_salary"] = _num(emp["median_salary"])

    total_courses = int(unique_courses["course_code"].nunique())
    median_hours = unique_courses["training_hours"].median()
    median_fee = unique_courses["fee_per_person"].median()
    total_hiring = emp["hiring_count"].sum(skipna=True)

    context = career_policy.iloc[0] if not career_policy.empty else None
    training_pct = float(context["mol_training_participation_percent"]) if context is not None else None
    no_course_pct = float(context["mol_no_course_info_percent"]) if context is not None else None
    fee_pct = float(context["mol_fee_barrier_percent"]) if context is not None else None

    kpi = (
        '<div class="qj-kpi-grid">'
        + _kpi_html(_IC_BOOK, f"{total_courses}", "可對應職訓課程數", "對應 O*NET 技能缺口的產業人才投資課程")
        + _kpi_html(_IC_CLOCK, f"{median_hours:.0f} 小時" if pd.notna(median_hours) else "—", "課程時數中位數", "單門課程；非累計轉職時數")
        + _kpi_html(_IC_COIN, f"NT$ {median_fee:,.0f}" if pd.notna(median_fee) else "—", "單門課程費用中位數", "課程直接費用；不含生活成本")
        + _kpi_html(_IC_BRIEF, f"{total_hiring:,.0f} 人" if pd.notna(total_hiring) else "—", "新北求才人數", "TaiwanJobs 新北 29 區職缺 snapshot")
        + "</div>"
    )
    st.markdown(kpi, unsafe_allow_html=True)

    supply_col, demand_col = st.columns(2, gap="medium")

    with supply_col:
        st.markdown(
            '<div class="qj-gc-card-title">課程供給：時數 × 費用</div>'
            '<div class="qj-gc-card-sub">每點為一門課程（依 course_code 去重）。</div>',
            unsafe_allow_html=True,
        )
        scatter_df = unique_courses.dropna(subset=["training_hours", "fee_per_person"])
        if scatter_df.empty:
            st.info("目前沒有可繪製的課程時數／費用資料。")
        else:
            fig = px.scatter(
                scatter_df,
                x="training_hours",
                y="fee_per_person",
                hover_name="course_name",
                custom_data=["training_provider", "location"],
                labels={"training_hours": "課程時數（小時）", "fee_per_person": "課程費用（NT$）"},
            )
            fig.update_traces(
                marker={"color": TEAL, "size": 10, "line": {"color": "#FFFFFF", "width": 1}, "opacity": 0.85},
                hovertemplate="<b>%{hovertext}</b><br>時數：%{x:.0f} 小時<br>費用：NT$%{y:,.0f}<br>單位：%{customdata[0]}<br>地點：%{customdata[1]}<extra></extra>",
            )
            fig.update_layout(height=330, margin={"l": 0, "r": 0, "t": 10, "b": 0}, plot_bgcolor="#F8FAFC")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            '<div class="qj-gc-card-title">課程供給最多的技能缺口</div>'
            '<div class="qj-gc-card-sub">依對應課程數排序（Top 10）；技能名稱為 O*NET 原始名稱。</div>',
            unsafe_allow_html=True,
        )
        skill_supply = (
            courses.groupby("skill_name")["course_code"].nunique().sort_values(ascending=False).head(10).reset_index()
        )
        skill_supply.columns = ["skill_name", "course_count"]
        if skill_supply.empty:
            st.info("目前沒有可統計的技能對應課程。")
        else:
            fig = px.bar(
                skill_supply.sort_values("course_count"),
                x="course_count",
                y="skill_name",
                orientation="h",
                labels={"course_count": "對應課程數", "skill_name": "技能（O*NET）"},
            )
            fig.update_traces(marker_color=BLUE, hovertemplate="%{y}<br>對應課程：%{x} 門<extra></extra>")
            fig.update_layout(height=340, margin={"l": 0, "r": 0, "t": 10, "b": 0}, plot_bgcolor="#F8FAFC")
            st.plotly_chart(fig, use_container_width=True)

    with demand_col:
        st.markdown(
            '<div class="qj-gc-card-title">就業需求：各區求才人數</div>'
            '<div class="qj-gc-card-sub">新北 29 區 TaiwanJobs 求才人數（Top 12）；非就業率或錄取機率。</div>',
            unsafe_allow_html=True,
        )
        demand = emp.dropna(subset=["hiring_count"]).sort_values("hiring_count", ascending=False).head(12)
        if demand.empty:
            st.info("目前沒有可繪製的就業需求資料。")
        else:
            fig = px.bar(
                demand.sort_values("hiring_count"),
                x="hiring_count",
                y="district",
                orientation="h",
                custom_data=["job_postings", "company_count", "median_salary", "top_job_category"],
                labels={"hiring_count": "求才人數", "district": "行政區"},
            )
            fig.update_traces(
                marker_color=TEAL,
                hovertemplate="<b>%{y}</b><br>求才人數：%{x:,.0f} 人<br>職缺數：%{customdata[0]:,.0f}<br>公司數：%{customdata[1]:,.0f}<br>月薪中位數：NT$%{customdata[2]:,.0f}<br>熱門類別：%{customdata[3]}<extra></extra>",
            )
            fig.update_layout(height=330, margin={"l": 0, "r": 0, "t": 10, "b": 0}, plot_bgcolor="#F8FAFC")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            '<div class="qj-gc-card-title">青年參訓與障礙（MOL 15–29 Proxy）</div>'
            '<div class="qj-gc-card-sub">全台 15–29 青年勞工調查，作為需求脈絡；非新北 18–35。</div>',
            unsafe_allow_html=True,
        )
        if context is None or any(v is None for v in (training_pct, no_course_pct, fee_pct)):
            st.info("目前沒有可顯示的 MOL 參訓訊號。")
        else:
            mol = pd.DataFrame(
                {
                    "指標": ["近一年有參訓", "不知道課程在哪", "費用太高負擔不起"],
                    "百分比": [training_pct, no_course_pct, fee_pct],
                }
            )
            fig = px.bar(mol, x="指標", y="百分比", labels={"百分比": "百分比 (%)", "指標": ""})
            fig.update_traces(
                marker_color=[TEAL, AMBER, AMBER],
                text=[f"{v:.1f}%" for v in mol["百分比"]],
                textposition="outside",
                hovertemplate="%{x}<br>%{y:.1f}%<extra></extra>",
            )
            fig.update_layout(height=340, margin={"l": 0, "r": 0, "t": 10, "b": 20}, plot_bgcolor="#F8FAFC", yaxis_range=[0, 100])
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="qj-section-title" style="margin-top:0.6rem;">課程清單</div>', unsafe_allow_html=True)
    st.caption("依 course_code 去重的職訓課程；欄位直接來自產業人才投資方案課程資料。")
    table = unique_courses[
        ["course_name", "training_provider", "location", "training_hours", "fee_per_person", "start_date", "end_date"]
    ].sort_values("fee_per_person", ascending=False)
    st.dataframe(
        table,
        hide_index=True,
        use_container_width=True,
        height=360,
        column_config={
            "course_name": st.column_config.TextColumn("課程名稱", width="large"),
            "training_provider": st.column_config.TextColumn("開課單位", width="medium"),
            "location": st.column_config.TextColumn("地點", width="small"),
            "training_hours": st.column_config.NumberColumn("時數", format="%.0f"),
            "fee_per_person": st.column_config.NumberColumn("費用", format="NT$ %.0f"),
            "start_date": st.column_config.TextColumn("開訓日", width="small"),
            "end_date": st.column_config.TextColumn("結訓日", width="small"),
        },
    )

    st.markdown('<div class="qj-section-title" style="margin-top:0.6rem;">護理師轉職儀表板（資料接口）</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="qj-gc-pending">
            <b>待接資料：</b>護理師薪資時序、工時、少子化（出生數／生育率）等圖表需要官方公開資料，目前 repo 尚未收錄，依專案規範不臆造。
            接上來源（如衛福部護理人力統計、勞動部職類別薪資調查與工時統計、內政部／主計總處出生與生育率）後，
            這一區會以與上方相同的圖表風格呈現，並接上可讀取這些真實數據的 AI 政策助理。
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("資料來源與限制", expanded=False):
        st.markdown(
            """
            <div class="qj-note">
            <b>職訓課程</b>：產業人才投資方案課程（2026-09 snapshot）；title-based 對應到 O*NET 技能缺口，為 derived evidence，非課綱評估。<br>
            <b>就業需求</b>：TaiwanJobs 新北 29 區職缺 snapshot（2026-08-25）；求才人數、職缺數、公司數與月薪中位數為 derived，不是就業率、錄取機率或就業保證。<br>
            <b>青年參訓訊號</b>：MOL 15–29 青年勞工調查 Proxy，作為需求脈絡，非新北 18–35。<br>
            本頁不產生轉職成功率、補助金額或正式政策排序。
            </div>
            """,
            unsafe_allow_html=True,
        )
