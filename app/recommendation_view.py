from __future__ import annotations

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from components.cards import render_mode_intro, render_recommendation_cards
from components.map_view import build_recommendation_map
from data_loader import MODE_COLORS, minutes, money


def render_dashboard_view(
    mode: str,
    candidates: pd.DataFrame,
    recommendations: pd.DataFrame,
    top3: pd.DataFrame,
    destination: dict[str, float | str],
    towns,
    cities,
) -> None:
    mode_rows = top3[top3["preference_mode"] == mode].sort_values("rank").copy()

    left, right = st.columns([0.92, 2.35], gap="large")
    with left:
        render_mode_intro(mode)
        st.markdown("### Top 3 推薦")
        render_recommendation_cards(mode, mode_rows)
    with right:
        st.markdown("### 推薦生活圈地圖")
        map_obj = build_recommendation_map(mode, candidates, top3, destination, towns, cities)
        st_folium(map_obj, height=720, use_container_width=True, returned_objects=[])

    _render_mode_summary(mode, mode_rows)
    render_all_candidates_table(mode, candidates, recommendations)


def render_all_candidates_table(mode: str, candidates: pd.DataFrame, recommendations: pd.DataFrame) -> None:
    st.markdown("### 全部候選生活圈比較")
    display = build_all_candidates_table(mode, candidates, recommendations)

    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        height=420,
        column_config={
            "candidate_name": st.column_config.TextColumn("candidate_name", width="medium"),
            "district": st.column_config.TextColumn("district", width="small"),
            "official_median_rent": st.column_config.TextColumn("official_median_rent", width="medium"),
            "commute_minutes": st.column_config.TextColumn("commute_minutes", width="small"),
            "transfer_count": st.column_config.NumberColumn("transfer_count", width="small"),
            "rent_saving_vs_neihu": st.column_config.TextColumn("rent_saving_vs_neihu", width="medium"),
            "livability_index": st.column_config.TextColumn("livability_index", width="small"),
            "mode_rank": st.column_config.TextColumn(f"{mode} rank", width="small"),
            "preference_score": st.column_config.TextColumn("preference_score", width="small"),
            "preference_cost": st.column_config.TextColumn("preference_cost", width="small"),
        },
    )


def build_all_candidates_table(mode: str, candidates: pd.DataFrame, recommendations: pd.DataFrame) -> pd.DataFrame:
    mode_preferences = recommendations[
        [
            "preference_mode",
            "candidate_name",
            "rank",
            "preference_score",
            "preference_cost",
        ]
    ][recommendations["preference_mode"] == mode].copy()

    table = candidates[
        [
            "candidate_name",
            "district",
            "official_median_rent",
            "commute_minutes",
            "transfer_count",
            "rent_saving_vs_neihu",
            "livability_index",
        ]
    ].merge(
        mode_preferences.drop(columns=["preference_mode"]),
        on="candidate_name",
        how="left",
        validate="one_to_one",
    )
    table = table.sort_values(
        by=["rank", "commute_minutes", "official_median_rent"],
        ascending=[True, True, True],
        na_position="last",
    ).copy()
    table["mode_rank"] = table["rank"].map(_rank_label)
    table["preference_score"] = table["preference_score"].map(lambda value: "" if pd.isna(value) else f"{float(value):.3f}")
    table["preference_cost"] = table["preference_cost"].map(lambda value: "" if pd.isna(value) else f"{float(value):.3f}")

    display = table[
        [
            "candidate_name",
            "district",
            "official_median_rent",
            "commute_minutes",
            "transfer_count",
            "rent_saving_vs_neihu",
            "livability_index",
            "mode_rank",
            "preference_score",
            "preference_cost",
        ]
    ].copy()
    display["official_median_rent"] = display["official_median_rent"].map(lambda value: f"{money(value)} NTD")
    display["commute_minutes"] = display["commute_minutes"].map(minutes)
    display["rent_saving_vs_neihu"] = display["rent_saving_vs_neihu"].map(lambda value: f"{money(value)} NTD")
    display["livability_index"] = display["livability_index"].map(lambda value: f"{float(value):.3f}")
    return display


def _rank_label(value: float | int) -> str:
    if pd.isna(value):
        return ""
    rank = int(value)
    if rank <= 3:
        return f"Top {rank}"
    return f"#{rank}"


def _render_mode_summary(mode: str, mode_rows: pd.DataFrame) -> None:
    top1 = mode_rows.iloc[0]
    color = MODE_COLORS[mode]
    st.markdown(
        f"""
        <div class="qj-panel" style="border-left: 5px solid {color}; margin-top: 0.4rem;">
            <b>{mode} Top 1：</b>{top1['living_area']}，
            月租 {money(top1['rent'])} NTD，通勤 {minutes(top1['commute_minutes'])}，
            相較內湖每月省 {money(top1['rent_saving_vs_neihu'])} NTD。
        </div>
        """,
        unsafe_allow_html=True,
    )
