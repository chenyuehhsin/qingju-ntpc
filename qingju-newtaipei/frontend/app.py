from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.recommendation import build_category_metrics, recommend_districts
from backend.visualization import load_geojson, make_choropleth, make_scatter

SUMMARY_PATH = ROOT / "data/processed/district_summary.csv"
PROFILE_PATH = ROOT / "data/processed/data_profile.json"
GEOJSON_PATH = ROOT / "data/processed/new_taipei_districts.geojson"
JOBS_PATH = ROOT / "data/raw/new_taipei_jobs.csv"

st.set_page_config(page_title="青聚新北｜青年就業 × 安居機會地圖", page_icon="🗺️", layout="wide")
st.markdown(
    """
    <style>
    .stApp {background: #F7FAF9; color: #17352F;}
    .block-container {max-width: 1500px; padding-top: 2rem;}
    .hero {padding: 1.25rem 1.5rem; border-radius: 22px; background: linear-gradient(120deg,#0F766E,#115E59); color:white; margin-bottom:1rem;}
    .hero h1 {margin:0; font-size:2.25rem;} .hero h2 {margin:.3rem 0 .7rem; font-size:1.25rem; font-weight:500; opacity:.92;}
    .hero p {margin:0; max-width:850px; opacity:.88;}
    .detail-card {background:white; padding:1.25rem; border:1px solid #DCE8E4; border-radius:18px; box-shadow:0 8px 24px rgba(15,118,110,.06);}
    .detail-card h2 {margin-top:0;} .detail-card h3 {font-size:1rem; color:#0F766E; margin:.9rem 0 .25rem;}
    .metric-line {display:flex; justify-content:space-between; gap:1rem; padding:.25rem 0; border-bottom:1px dashed #E2E8F0;}
    div[data-testid="stPlotlyChart"] {background:white; border:1px solid #E2E8F0; border-radius:18px; overflow:hidden;}
    [data-testid="stMetricValue"] {color:#17352F !important;}
    [data-testid="stMetricLabel"] {color:#475569 !important;}
    .stButton > button, [data-testid="stFormSubmitButton"] > button {
        background:#0F766E !important;
        color:#FFFFFF !important;
        border:1px solid #0F766E !important;
    }
    .stButton > button p, [data-testid="stFormSubmitButton"] > button p {color:#FFFFFF !important;}
    .stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
        background:#115E59 !important;
        border-color:#115E59 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data() -> tuple[pd.DataFrame, dict, dict, list[str], pd.DataFrame]:
    summary = pd.read_csv(SUMMARY_PATH, encoding="utf-8-sig")
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    jobs = pd.read_csv(JOBS_PATH, encoding="utf-8-sig", usecols=["district", "CJOB_NAME1", "JOB_PERSON"])
    categories = sorted(
        category for category in jobs["CJOB_NAME1"].dropna().astype(str).str.strip().unique() if category
    )
    return summary, profile, load_geojson(GEOJSON_PATH), categories, build_category_metrics(jobs)


def display_number(value: object, prefix: str = "", suffix: str = "") -> str:
    return "資料不足" if pd.isna(value) else f"{prefix}{float(value):,.0f}{suffix}"


if not SUMMARY_PATH.exists() or not PROFILE_PATH.exists():
    st.error("尚未建立摘要資料。請先執行 `python build_data.py`。")
    st.stop()
if not GEOJSON_PATH.exists():
    st.error("缺少行政區界線：`data/processed/new_taipei_districts.geojson`。請依 README 執行 GeoJSON 準備步驟。")
    st.stop()

summary, profile, geojson, job_categories, category_metrics = load_data()
st.markdown(
    """<div class="hero"><h1>青聚新北</h1><h2>以我的工作和生活條件，新北哪些行政區適合落腳？</h2>
    <p>輸入工作條件、可接受居住成本與最大通勤時間，取得3個可解釋的行政區建議，並在地圖比較工作機會與租屋成本。</p></div>""",
    unsafe_allow_html=True,
)


district_options = ["尚未指定", *summary["district"].tolist()]
category_options = ["不限職類", *job_categories]
defaults = {
    "budget": 20_000,
    "job_category": "不限職類",
    "work_district": "尚未指定",
    "commute_limit": 45,
}
preferences = {**defaults, **st.session_state.get("user_preferences", {})}

with st.container(border=True):
    st.subheader("告訴我們你的落腳條件")
    st.caption("推薦目前會使用租屋預算與職類；工作地點及大眾運輸通勤上限已保留，待29區交通時間資料完成後納入。")
    with st.form("preference_form", border=False):
        work_col, housing_col, commute_col = st.columns(3, gap="large")
        with work_col:
            st.markdown("#### 1. 工作")
            job_category = st.selectbox(
                "希望從事的職類", category_options,
                index=category_options.index(preferences["job_category"]) if preferences["job_category"] in category_options else 0,
            )
            work_district = st.selectbox(
                "工作地點", district_options,
                index=district_options.index(preferences["work_district"]) if preferences["work_district"] in district_options else 0,
                help="指定預計上班行政區；將用於大眾運輸通勤條件。",
            )
        with housing_col:
            st.markdown("#### 2. 可接受居住成本")
            budget = st.number_input(
                "每月最高租屋預算", min_value=5_000, max_value=80_000,
                value=int(preferences["budget"]), step=1_000,
            )
            st.caption("推薦會比較各區租金中位數與你的預算差額。")
        with commute_col:
            st.markdown("#### 3. 最大通勤時間")
            commute_options = [30, 45, 60, 90, 120]
            commute_limit = st.selectbox(
                "大眾運輸最長單程時間", commute_options,
                index=commute_options.index(int(preferences["commute_limit"])) if int(preferences["commute_limit"]) in commute_options else 1,
                format_func=lambda minutes: f"{minutes} 分鐘內",
                help="住家到工作地的單程大眾運輸時間。交通矩陣完成前先保存、不計分。",
            )
            st.caption("住家 → 工作地；單程，不是每日來回。")
        submitted = st.form_submit_button("找出適合落腳的行政區", type="primary", width="stretch")

    if submitted:
        preferences = {
            "budget": int(budget), "job_category": job_category,
            "work_district": work_district, "commute_limit": int(commute_limit),
        }
        st.session_state["user_preferences"] = preferences
        st.success("已依目前可計算的租屋預算與職類產生3個建議。")

    st.caption(
        f"目前條件：{preferences['job_category']}｜工作地點：{preferences['work_district']}｜"
        f"租屋預算 NT${preferences['budget']:,}／月｜大眾運輸單程 {preferences['commute_limit']} 分鐘內"
    )

if "user_preferences" in st.session_state:
    recommendations, recommendation_metadata = recommend_districts(
        summary,
        category_metrics,
        budget=int(preferences["budget"]),
        job_category=preferences["job_category"],
    )
    st.subheader("3個適合落腳的行政區建議")
    st.caption("先以租屋預算、符合職類的公開工作機會與租賃資料量排序；結果會清楚說明符合條件與需要取捨之處。")
    st.warning("大眾運輸通勤時間尚未計入排名。交通資料完成前，這3區是初步建議，不代表已符合你設定的通勤上限。")
    if recommendation_metadata["fully_matched_count"] < 3:
        st.warning(
            f"目前只有 {recommendation_metadata['fully_matched_count']} 區同時符合預算與職類；"
            "其餘結果為取捨方案，可能超出預算或缺少該職類職缺。"
        )

    recommendation_columns = st.columns(3, gap="medium")
    for (_, row), column in zip(recommendations.iterrows(), recommendation_columns):
        with column:
            with st.container(border=True):
                st.markdown(f"### {int(row['recommendation_rank'])}. {row['district']}")
                st.info(row["match_status"])
                budget_delta = (
                    f"預算餘額 {row['budget_gap']:,.0f} 元"
                    if row["within_budget"]
                    else f"超出預算 {-row['budget_gap']:,.0f} 元"
                )
                st.metric(
                    "租金中位數",
                    f"{row['median_rent']:,.0f} 元／月",
                    delta=budget_delta,
                    delta_color="normal" if row["within_budget"] else "inverse",
                )
                st.metric("符合職類公開職缺", f"{row['matched_job_postings']:,.0f} 筆", help="公開職缺不是完整就業市場，也不是實際錄取人數。")
                st.write(f"**推薦原因：** {row['recommendation_reason']}")
                commute_target = preferences["work_district"]
                st.caption(
                    "🚌 通勤：尚未指定工作地點" if commute_target == "尚未指定"
                    else f"🚌 前往{commute_target}的大眾運輸時間待交通資料完成後計算；上限為{preferences['commute_limit']}分鐘。"
                )
                st.caption(
                    f"租賃案件 {row['rental_count']:,.0f} 件｜資料可信度：{row['evidence_level']}"
                )
                if st.button("在地圖查看", key=f"show_{row['district']}", width="stretch"):
                    st.session_state["selected_district"] = row["district"]
                    st.rerun()

    with st.expander("查看推薦計算明細"):
        details = recommendations[
            [
                "recommendation_rank",
                "district",
                "median_rent",
                "matched_job_postings",
                "matched_hiring_count",
                "affordability_score",
                "job_match_score",
                "evidence_score",
                "recommendation_score",
            ]
        ].copy()
        details.columns = [
            "排名",
            "行政區",
            "租金中位數",
            "符合職類職缺數",
            "符合職類求才人數",
            "預算分數",
            "職類分數",
            "資料量分數",
            "推薦參考分數",
        ]
        st.dataframe(details.round(1), hide_index=True, width="stretch")
mode = st.segmented_control(
    "地圖指標", ["💼 工作機會", "🏠 租屋成本"], default="💼 工作機會",
    selection_mode="single", label_visibility="collapsed",
)
mode = mode or "💼 工作機會"

map_col, card_col = st.columns([2.25, 1], gap="large")
with map_col:
    st.caption("點選行政區查看詳細資料；灰色區域代表資料不足。")
    event = st.plotly_chart(make_choropleth(summary, geojson, mode), width="stretch", on_select="rerun", selection_mode="points", key=f"district_map_{mode}")

clicked = None
if event and getattr(event, "selection", None) and event.selection.points:
    clicked = event.selection.points[0].get("location")
if clicked in summary["district"].tolist():
    st.session_state["selected_district"] = clicked
selected_default = st.session_state.get("selected_district", "板橋區")

with card_col:
    selected = st.selectbox("行政區", summary["district"].tolist(), index=summary["district"].tolist().index(selected_default))
    st.session_state["selected_district"] = selected
    row = summary.loc[summary["district"].eq(selected)].iloc[0]
    category = row["top_job_category"] if pd.notna(row["top_job_category"]) else "資料不足"
    st.markdown(
        f"""<div class="detail-card"><h2>{selected}</h2>
        <h3>💼 就業</h3>
        <div class="metric-line"><span>職缺數</span><b>{display_number(row['job_postings'], suffix=' 筆')}</b></div>
        <div class="metric-line"><span>求才人數</span><b>{display_number(row['hiring_count'], suffix=' 人')}</b></div>
        <div class="metric-line"><span>公司數</span><b>{display_number(row['company_count'], suffix=' 家')}</b></div>
        <div class="metric-line"><span>職缺月薪中位數</span><b>{display_number(row['median_salary'], prefix='NT$', suffix='/月')}</b></div>
        <div class="metric-line"><span>熱門職類</span><b>{category}</b></div>
        <h3>🏠 安居</h3>
        <div class="metric-line"><span>租金中位數</span><b>{display_number(row['median_rent'], prefix='NT$', suffix='/月')}</b></div>
        <div class="metric-line"><span>平均租金</span><b>{display_number(row['average_rent'], prefix='NT$', suffix='/月')}</b></div>
        <div class="metric-line"><span>租賃案件數</span><b>{display_number(row['rental_count'], suffix=' 件')}</b></div>
        </div>""",
        unsafe_allow_html=True,
    )

st.subheader("新北 29 區工作機會 × 租屋成本散佈圖")
st.caption("虛線為有資料行政區的中位數；圓點大小代表職缺筆數。散佈位置呈現區際相對差異，不是宜居排名。")
st.plotly_chart(make_scatter(summary, profile["thresholds"]), width="stretch")


st.divider()
source_col, update_col = st.columns(2)
with source_col:
    st.markdown("### 資料來源")
    st.markdown("就業：勞動部勞動力發展署－台灣就業通網站職缺清單 Open Data API  \n租屋：新北市政府地政局－不動產實價登錄資訊（租賃案件）  \n青年人口：內政部社會經濟資料服務平台－五歲年齡組人口統計")
with update_col:
    st.markdown("### 資料時間")
    st.write(f"職缺資料最後更新日期：{profile['jobs'].get('latest_date') or '資料不足'}")
    st.write(f"租屋資料最後更新日期：{profile['housing'].get('latest_date') or '資料不足'}")
    st.write(f"青年人口資料期別：{profile['youth']['periods'][-1]}")

with st.expander("資料口徑與限制"):
    st.markdown(
        """
        - 18–35歲人口不是官方單歲精確值：以15–19歲取2／5、20–34歲全數、35–39歲取1／5推估；20–34歲另保留精確加總值。
        - 青年人口依戶籍地址統計，不等於實際居住人口；外地戶籍租屋青年無法由本資料辨識。
        - 本 Prototype 呈現公開職缺與公開租賃登錄的區際比較，不代表青年實際所得、真實租金負擔率或居住推薦。
        - 職缺薪資中位數僅納入月薪／每月核薪資料；時薪、日薪及論件計酬不混入。
        - 租賃資料排除土地、純車位、非正值與明顯極端月租；房屋加車位案件會扣除登錄車位租金。
        - 公開資料的案件量與涵蓋程度各區不同；「資料不足」不等於該區沒有工作或租屋。
        """
    )
