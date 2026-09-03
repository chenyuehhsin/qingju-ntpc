from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREFERENCE_CSV = PROJECT_ROOT / "data" / "processed" / "integration" / "preference_recommendations_by_workplace.csv"
RENT_COMMUTE_CSV = PROJECT_ROOT / "data" / "processed" / "integration" / "rent_commute_candidates_by_workplace.csv"
LIVABILITY_CSV = PROJECT_ROOT / "data" / "processed" / "livability" / "livability_by_candidate.csv"
CANDIDATE_LOCATIONS_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "candidate_locations_expanded.csv"
COMMUTE_BY_WORKPLACE_CSV = PROJECT_ROOT / "data" / "processed" / "transport" / "commute_by_workplace.csv"
POLICY_LENS_CSV = PROJECT_ROOT / "data" / "processed" / "policy" / "policy_lens_v0.csv"
CAREER_POLICY_LENS_PHASE7_CSV = PROJECT_ROOT / "outputs" / "career" / "career_policy_lens_phase7.csv"
CAREER_POLICY_LENS_PHASE7_MD = PROJECT_ROOT / "outputs" / "career" / "career_policy_lens_phase7.md"
CAREER_V35_CANDIDATES_CSV = PROJECT_ROOT / "outputs" / "career" / "nursing_to_technology_candidates_v35.csv"
CAREER_V4_TRAINING_CSV = PROJECT_ROOT / "outputs" / "career" / "nursing_to_technology_training_v4.csv"
CAREER_BEAUTY_PHASE5_CSV = PROJECT_ROOT / "outputs" / "career" / "nursing_to_beauty_candidates_phase5.csv"
CAREER_TRAINING_MAPPING_CSV = PROJECT_ROOT / "data" / "processed" / "career" / "career_training_skill_mapping.csv"
CAREER_TAIWANJOBS_RAW_CSV = PROJECT_ROOT / "data" / "raw" / "career" / "jobs" / "taiwanjobs_open_jobs_2026-09-01.csv"
BOUNDARY_SHP = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "housing"
    / "boundaries"
    / "nlsc_town_boundary_twd97"
    / "TOWN_MOI_1120317.shp"
)

MODE_ORDER = ["省租型", "平衡型", "通勤型", "生活品質型"]
WORKPLACE_ORDER = [
    "gangqian_neihu",
    "taipei_city_hall_xinyi",
    "taipei_main_zhongzheng",
    "nangang_nangang",
    "xinban_special_district",
    "xinzhuang_fuduxin",
    "xizhi_science_park",
    "zhonghe_tech_park",
    "tucheng_industrial_park",
]
MODE_COLORS = {
    "省租型": "#78B995",
    "平衡型": "#6EA7C7",
    "通勤型": "#E8A05A",
    "生活品質型": "#A98BC8",
}
MODE_SOFT_COLORS = {
    "省租型": "#EAF6EF",
    "平衡型": "#EAF4FA",
    "通勤型": "#FFF1E3",
    "生活品質型": "#F2ECF8",
}
MODE_COPY = {
    "省租型": "適合願意增加通勤時間，以換取較低租金的使用者。",
    "平衡型": "在租金與通勤時間之間取得較佳折衷。",
    "通勤型": "適合最重視每日上下班時間的使用者。",
    "生活品質型": "優先考慮站點周邊餐飲、採買、休閒、文娛與醫療機能。",
}
LIVING_AREA_NAMES = {
    "板橋站": "板橋生活圈",
    "汐止車站": "汐止生活圈",
    "淡水站": "淡水生活圈",
    "樹林車站": "樹林生活圈",
    "大坪林站": "大坪林生活圈",
    "三峽北大特區": "三峽北大生活圈",
    "景安站": "景安生活圈",
    "頂溪站": "頂溪生活圈",
    "三重站": "三重生活圈",
    "泰山站": "泰山生活圈",
    "新莊站": "新莊生活圈",
    "蘆洲站": "蘆洲生活圈",
    "土城站": "土城生活圈",
    "鶯歌車站": "鶯歌生活圈",
    "林口站": "林口生活圈",
    "五股區公所": "五股生活圈",
}


def living_area(candidate_name: str) -> str:
    return LIVING_AREA_NAMES.get(candidate_name, candidate_name.replace("車站", "").replace("站", "") + "生活圈")


def money(value: float | int) -> str:
    return f"{float(value):,.0f}"


def minutes(value: float | int) -> str:
    return f"{float(value):.1f} min"


def reason_for(mode: str, row: pd.Series) -> str:
    if mode == "生活品質型":
        return "周邊生活機能 proxy 較突出，適合重視日常便利的使用者。"
    if mode == "通勤型":
        return "以縮短每日上下班時間為主要排序方向。"
    if mode == "平衡型":
        return "在租金與通勤時間之間取得較佳折衷。"
    return "以降低月租為主要排序方向，接受較長通勤換取省租。"


@st.cache_data(show_spinner=False)
def load_workplaces() -> pd.DataFrame:
    commute = pd.read_csv(COMMUTE_BY_WORKPLACE_CSV)
    workplaces = (
        commute[
            [
                "workplace_id",
                "workplace_name",
                "workplace_district",
                "workplace_lat",
                "workplace_lon",
                "workplace_station_operator",
                "workplace_station_uid",
            ]
        ]
        .drop_duplicates()
        .copy()
    )
    if len(workplaces) != len(WORKPLACE_ORDER):
        raise RuntimeError(f"Expected {len(WORKPLACE_ORDER)} workplaces, found {len(workplaces)}.")
    workplaces["_order"] = workplaces["workplace_id"].map({value: index for index, value in enumerate(WORKPLACE_ORDER)})
    if workplaces["_order"].isna().any():
        missing = workplaces[workplaces["_order"].isna()]["workplace_id"].tolist()
        raise RuntimeError(f"Unexpected workplace ids: {missing}")
    return workplaces.sort_values("_order").drop(columns=["_order"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_dashboard_data(workplace_id: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, float | str]]:
    preferences = pd.read_csv(PREFERENCE_CSV)
    rent_commute = pd.read_csv(RENT_COMMUTE_CSV)
    livability = pd.read_csv(LIVABILITY_CSV)
    locations = pd.read_csv(CANDIDATE_LOCATIONS_CSV)

    if workplace_id not in set(rent_commute["workplace_id"]):
        raise RuntimeError(f"Unknown workplace_id: {workplace_id}")
    rent_commute = rent_commute[rent_commute["workplace_id"] == workplace_id].copy()
    preferences = preferences[preferences["workplace_id"] == workplace_id].copy()
    if len(rent_commute) != 16:
        raise RuntimeError(f"Expected 16 evaluated candidates for {workplace_id}, found {len(rent_commute)}.")

    candidates = rent_commute.merge(
        locations[["candidate_name", "lat", "lon"]],
        on="candidate_name",
        how="left",
        suffixes=("", "_location"),
        validate="one_to_one",
    )
    candidates["lat"] = candidates["lat"].fillna(candidates["lat_location"])
    candidates["lon"] = candidates["lon"].fillna(candidates["lon_location"])
    candidates = candidates.drop(columns=[column for column in ["lat_location", "lon_location"] if column in candidates])
    candidates = candidates.merge(
        livability[["candidate_name", "equal_weight_livability_index", "total_poi_count"]],
        on="candidate_name",
        how="left",
        validate="one_to_one",
    )
    candidates["rent"] = candidates["official_median_rent"]
    candidates["livability_index"] = candidates["equal_weight_livability_index"]
    candidates["living_area"] = candidates["candidate_name"].map(living_area)

    recommendations = preferences.copy()
    recommendations = recommendations.merge(
        candidates[
            [
                "candidate_name",
                "lat",
                "lon",
                "living_area",
                "livability_index",
                "total_poi_count",
                "route_summary",
            ]
        ],
        on="candidate_name",
        how="left",
        validate="many_to_one",
        suffixes=("", "_from_candidates"),
    )
    recommendations["livability_index"] = recommendations["livability_index"].fillna(
        recommendations["livability_index_from_candidates"]
    )
    recommendations = recommendations.drop(columns=["livability_index_from_candidates"])

    top3 = recommendations[recommendations["rank"] <= 3].copy()

    _validate_dashboard_data(candidates, recommendations, top3)

    destination_rows = rent_commute[
        [
            "workplace_id",
            "workplace_name",
            "workplace_district",
            "workplace_lat",
            "workplace_lon",
        ]
    ].drop_duplicates()
    if len(destination_rows) != 1:
        raise RuntimeError(f"Expected one workplace row, found {len(destination_rows)}.")
    destination_row = destination_rows.iloc[0].to_dict()
    destination = {
        "workplace_id": destination_row["workplace_id"],
        "workplace_name": destination_row["workplace_name"],
        "workplace_district": destination_row["workplace_district"],
        "destination": destination_row["workplace_name"],
        "destination_lat": destination_row["workplace_lat"],
        "destination_lon": destination_row["workplace_lon"],
    }

    return candidates, recommendations, top3, destination


def _validate_dashboard_data(candidates: pd.DataFrame, recommendations: pd.DataFrame, top3: pd.DataFrame) -> None:
    if len(candidates) != 16:
        raise RuntimeError(f"Expected 16 evaluated candidates, found {len(candidates)}.")
    required_candidate_columns = [
        "candidate_name",
        "district",
        "rent",
        "commute_minutes",
        "transfer_count",
        "rent_saving_vs_neihu",
        "lat",
        "lon",
        "livability_index",
    ]
    missing_values = candidates[candidates[required_candidate_columns].isna().any(axis=1)]["candidate_name"].tolist()
    if missing_values:
        raise RuntimeError(f"Candidates have missing dashboard fields: {missing_values}.")

    for mode in MODE_ORDER:
        rows = top3[top3["preference_mode"] == mode]
        if len(rows) != 3:
            raise RuntimeError(f"Expected three Top 3 recommendations for {mode}, found {len(rows)}.")
        if sorted(rows["rank"].tolist()) != [1, 2, 3]:
            raise RuntimeError(f"{mode} ranks are not exactly 1, 2, 3.")

    life_quality_rows = recommendations[recommendations["preference_mode"] == "生活品質型"]
    if len(life_quality_rows) != 16:
        raise RuntimeError(f"Expected 16 生活品質型 rows for the full candidate table, found {len(life_quality_rows)}.")


@st.cache_data(show_spinner=False)
def load_boundaries() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    if not BOUNDARY_SHP.exists():
        raise FileNotFoundError(
            "Expected existing NLSC/MOI boundary data at "
            f"{BOUNDARY_SHP.relative_to(PROJECT_ROOT)}; the dashboard does not download new data."
        )
    towns = gpd.read_file(BOUNDARY_SHP, encoding="utf-8")
    if towns.crs is None:
        towns = towns.set_crs("EPSG:3824")
    towns = towns.to_crs("EPSG:4326")
    required = {"COUNTYNAME", "TOWNNAME", "geometry"}
    missing = required - set(towns.columns)
    if missing:
        raise RuntimeError(f"Boundary file is missing expected columns: {sorted(missing)}")
    towns = towns[towns["COUNTYNAME"].isin(["新北市", "臺北市"])].copy()
    cities = towns.dissolve(by="COUNTYNAME", as_index=False)
    return towns, cities


@st.cache_data(show_spinner=False)
def load_policy_lens_data() -> pd.DataFrame:
    policy = pd.read_csv(POLICY_LENS_CSV)
    livability = pd.read_csv(LIVABILITY_CSV)

    required_columns = {
        "candidate_name",
        "district",
        "official_median_rent",
        "official_contract_count",
        "commute_accessibility_minutes",
        "commute_accessibility_workplace_count",
        "livability_index",
        "policy_linked_record_count",
        "total_rental_record_count",
        "policy_linked_record_share",
        "lat",
        "lon",
        "policy_quadrant",
    }
    missing = required_columns - set(policy.columns)
    if missing:
        raise RuntimeError(f"Policy Lens v0 data is missing columns: {sorted(missing)}")
    if len(policy) != 16:
        raise RuntimeError(f"Expected 16 policy candidates, found {len(policy)}.")
    if policy["candidate_name"].nunique() != 16:
        raise RuntimeError("Policy Lens v0 data includes duplicated candidate_name values.")

    poi_columns = [
        "candidate_name",
        "food_count",
        "shopping_count",
        "recreation_count",
        "culture_count",
        "medical_count",
        "total_poi_count",
    ]
    available_poi_columns = [column for column in poi_columns if column in livability.columns]
    policy = policy.merge(
        livability[available_poi_columns],
        on="candidate_name",
        how="left",
        validate="one_to_one",
    )
    policy["living_area"] = policy["candidate_name"].map(living_area)

    required_no_missing = [
        "official_median_rent",
        "official_contract_count",
        "commute_accessibility_minutes",
        "commute_accessibility_workplace_count",
        "livability_index",
        "policy_linked_record_count",
        "total_rental_record_count",
        "policy_linked_record_share",
        "lat",
        "lon",
    ]
    missing_values = policy[policy[required_no_missing].isna().any(axis=1)]["candidate_name"].tolist()
    if missing_values:
        raise RuntimeError(f"Policy Lens v0 rows have missing required values: {missing_values}")
    return policy.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_career_policy_lens_phase7() -> tuple[pd.DataFrame, str]:
    missing_files = [
        path.relative_to(PROJECT_ROOT)
        for path in [CAREER_POLICY_LENS_PHASE7_CSV, CAREER_POLICY_LENS_PHASE7_MD]
        if not path.exists()
    ]
    if missing_files:
        raise FileNotFoundError(f"Missing Career Policy Lens Phase 7 files: {missing_files}")

    career_policy = pd.read_csv(CAREER_POLICY_LENS_PHASE7_CSV)
    career_policy_md = CAREER_POLICY_LENS_PHASE7_MD.read_text(encoding="utf-8")
    required_columns = {
        "target_domain",
        "target_occupation_name",
        "transition_span",
        "feasibility_level",
        "market_evidence_status",
        "high_relevance_job_count",
        "medium_relevance_job_count",
        "number_of_missing_skills",
        "missing_skills_preview",
        "potential_training_coverage_ratio",
        "matched_course_count",
        "total_training_hours",
        "estimated_direct_course_cost",
        "training_gap_status",
        "learning_burden",
        "ntpc_population_18_35",
        "ntpc_population_period",
        "ntpc_population_age_scope",
        "ntpc_population_age_harmonization",
        "mol_transition_intention_percent",
        "mol_transition_age_harmonization",
        "mol_training_participation_percent",
        "mol_training_age_harmonization",
        "mol_no_course_info_percent",
        "mol_no_course_info_denominator",
        "mol_fee_barrier_percent",
        "mol_fee_barrier_denominator",
    }
    missing = sorted(required_columns - set(career_policy.columns))
    if missing:
        raise RuntimeError(f"Career Policy Lens Phase 7 data is missing columns: {missing}")
    return career_policy.reset_index(drop=True), career_policy_md


@st.cache_data(show_spinner=False)
def load_career_evidence_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    missing_files = [
        path.relative_to(PROJECT_ROOT)
        for path in [
            CAREER_V35_CANDIDATES_CSV,
            CAREER_V4_TRAINING_CSV,
            CAREER_BEAUTY_PHASE5_CSV,
            CAREER_TRAINING_MAPPING_CSV,
            CAREER_TAIWANJOBS_RAW_CSV,
        ]
        if not path.exists()
    ]
    if missing_files:
        raise FileNotFoundError(f"Missing career evidence output files: {missing_files}")

    candidates_v35 = pd.read_csv(CAREER_V35_CANDIDATES_CSV)
    training_v4 = pd.read_csv(CAREER_V4_TRAINING_CSV)
    beauty_phase5 = pd.read_csv(CAREER_BEAUTY_PHASE5_CSV)
    course_mapping = pd.read_csv(CAREER_TRAINING_MAPPING_CSV)
    taiwanjobs_raw = pd.read_csv(CAREER_TAIWANJOBS_RAW_CSV, encoding="utf-8-sig")

    required_v35 = {
        "target_occupation_code",
        "target_occupation_name",
        "transition_span",
        "feasibility_level",
        "market_validation",
        "mapping_confidence",
        "manual_review_needed",
        "matched_job_count",
        "total_demand_persons",
        "salary_lower_median",
        "salary_upper_median",
        "salary_basis",
        "shared_top_skills",
        "missing_skills",
        "target_skill_gap",
        "transferable_skill_coverage",
    }
    required_v4 = {
        "target_occupation_code",
        "target_occupation_name",
        "training_coverage_ratio",
        "gap_skill_training_coverage_ratio",
        "number_of_missing_skills",
        "number_of_gap_skills",
        "number_of_trainable_skills_found",
        "total_training_hours",
        "estimated_direct_course_cost",
        "learning_burden_level",
        "partially_covered_skills",
        "missing_skills",
        "learning_plan_phase_1_foundational_skills",
        "learning_plan_phase_2_domain_technical_skills",
        "learning_plan_phase_3_portfolio_job_preparation",
        "scenario_6m_training_coverage_ratio",
        "scenario_6m_feasibility_estimate",
    }
    required_mapping = {
        "target_occupation_code",
        "skill_name",
        "skill_gap_status",
        "course_code",
        "course_name",
        "training_provider",
        "location",
        "training_hours",
        "fee_per_person",
        "mapping_score",
        "mapping_confidence",
        "manual_review_needed",
    }
    required_taiwanjobs = {
        "OCCU_DESC（職務名稱）",
        "CJOB_NAME1（職務大類別名稱）",
        "CJOB_NAME2（職務小類別名稱）",
        "JOB_PERSON（雇用人數）",
        "JOB_DETAIL（工作內容）",
        "CITYNAME（工作地點）",
        "SALARYCD（核薪方式）",
        "NT_L（薪資範圍下限）",
        "NT_U（薪資範圍上限）",
        "URL_QUERY（職缺資料URL）",
        "COMPNAME（公司名稱）",
    }
    required_beauty = {
        "target_occupation_code",
        "target_occupation_name",
        "target_domain_primary_signal",
        "transition_span",
        "feasibility_level",
        "skill_similarity",
        "transferable_skill_coverage",
        "target_skill_gap",
        "education_barrier",
        "credential_barrier",
        "taiwan_market_evidence",
        "taiwanjobs_high_relevance_job_count",
        "taiwanjobs_medium_relevance_job_count",
        "total_demand_persons_high",
        "salary_lower_median_high",
        "salary_upper_median_high",
        "training_availability",
        "training_course_count",
        "total_training_hours",
        "estimated_direct_course_cost",
        "learning_burden",
        "already_covered_skills",
        "partially_covered_skills",
        "missing_skills",
        "matched_training_courses",
        "high_relevance_job_examples",
        "medium_relevance_job_examples",
    }
    for label, frame, required in [
        ("v3.5 candidates", candidates_v35, required_v35),
        ("v4 training", training_v4, required_v4),
        ("Phase 5 beauty candidates", beauty_phase5, required_beauty),
        ("v4 course mapping", course_mapping, required_mapping),
        ("TaiwanJobs raw jobs", taiwanjobs_raw, required_taiwanjobs),
    ]:
        missing = sorted(required - set(frame.columns))
        if missing:
            raise RuntimeError(f"Career {label} is missing required columns: {missing}")

    return candidates_v35, training_v4, course_mapping, taiwanjobs_raw, beauty_phase5
