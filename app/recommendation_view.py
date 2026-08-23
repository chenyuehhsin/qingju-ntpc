from __future__ import annotations

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from components.cards import render_recommendation_cards
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

    left, right = st.columns([0.92, 2.78], gap="medium")
    with left:
        st.markdown("### Top 3 推薦")
        render_recommendation_cards(mode, mode_rows)
    with right:
        st.markdown("### 推薦生活圈地圖")
        map_obj = build_recommendation_map(mode, candidates, top3, destination, towns, cities)
        st_folium(map_obj, height=720, use_container_width=True, returned_objects=[])

    _render_mode_summary(mode, mode_rows, str(destination["destination"]))
    with st.expander("查看全部 16 個候選生活圈", expanded=False):
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


def _render_mode_summary(mode: str, mode_rows: pd.DataFrame, workplace_name: str) -> None:
    top1 = mode_rows.iloc[0]
    color = MODE_COLORS[mode]
    st.markdown(
        f"""
        <div class="qj-summary-strip" style="border-left-color: {color};">
            <b>{mode} Top 1：</b>{top1['living_area']}，月租約 {money(top1['rent'])} 元，
            到{workplace_name}約 {minutes(top1['commute_minutes'])}，
            相較內湖租金 benchmark 每月約省 {money(top1['rent_saving_vs_neihu'])} 元。
        </div>
        """,
        unsafe_allow_html=True,
    )
