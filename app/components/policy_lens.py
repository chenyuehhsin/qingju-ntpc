from __future__ import annotations

import html
import os
import tempfile
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from branca.colormap import LinearColormap
from branca.element import MacroElement, Template

PROJECT_CACHE_DIR = Path(tempfile.gettempdir()) / "qingju_ntpc_cache"
os.environ.setdefault("XDG_CACHE_HOME", str(PROJECT_CACHE_DIR / "xdg"))
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_CACHE_DIR / "matplotlib"))

import matplotlib.font_manager as fm
from matplotlib import pyplot as plt
from streamlit_folium import st_folium

from data_loader import money


POLICY_VIEWS = {
    "租金": {
        "field": "official_median_rent",
        "title": "租金",
        "unit": "NTD/month",
        "caption": "MOI 行政區獨立套房官方租金 benchmark；不是即時房源價格或站點周邊租金。",
        "low_color": "#F8EBDD",
        "high_color": "#D97950",
        "higher_label": "租金越高",
    },
    "公共運輸可達性": {
        "field": "commute_accessibility_minutes",
        "title": "公共運輸可達性",
        "unit": "min",
        "caption": "現有 9 個 workplace presets 的公共運輸通勤時間中位數。時間越長 = 可達性越弱。",
        "low_color": "#E9F1F4",
        "high_color": "#557F9A",
        "higher_label": "時間越長，可達性越弱",
    },
    "生活機能": {
        "field": "livability_index",
        "title": "生活機能",
        "unit": "index",
        "caption": "OSM 800m POI proxy，值越高代表周邊生活機能 proxy 越高；不代表完整生活品質。",
        "low_color": "#EEF2EA",
        "high_color": "#5D9C7A",
        "higher_label": "生活機能 proxy 越高",
    },
    "政策型租賃樣本": {
        "field": "policy_linked_record_share",
        "title": "政策型租賃相關登錄樣本占比",
        "unit": "share",
        "caption": "此比例僅反映目前清理後租賃登錄樣本結構，不是市場占比、供給率或青年租屋占比。",
        "low_color": "#EFEAF4",
        "high_color": "#8F78AD",
        "higher_label": "樣本占比越高",
    },
}

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SMALL_SAMPLE_THRESHOLD = 50


def render_policy_lens(policy: pd.DataFrame, towns: gpd.GeoDataFrame, cities: gpd.GeoDataFrame) -> None:
    st.markdown(
        """
        <div class="qj-policy-header">
            <div class="qj-header-title">青聚新北｜青年居住 Policy Lens</div>
            <div class="qj-subtitle">從租金、交通可達性、生活機能與租賃資料結構觀察新北青年居住環境</div>
            <div class="qj-policy-alert">Policy v0 為政策篩選與探索工具，不代表正式政策優先順序。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, switch_col, _ = st.columns([0.55, 2.3, 0.55])
    with switch_col:
        selected_view = st.segmented_control(
            "Policy Lens 視角",
            options=list(POLICY_VIEWS.keys()),
            default=st.session_state.get("policy_view", "租金"),
            key="policy_view",
            label_visibility="collapsed",
        )
    if selected_view is None:
        selected_view = "租金"

    map_col, detail_col = st.columns([2.65, 1.0], gap="medium")
    with map_col:
        map_obj = build_policy_map(policy, towns, cities, selected_view)
        map_state = st_folium(
            map_obj,
            height=650,
            use_container_width=True,
            returned_objects=["last_object_clicked"],
            key=f"policy_map_{selected_view}",
        )
    clicked_candidate = _candidate_from_click(policy, map_state)
    if clicked_candidate:
        st.session_state.policy_selected_candidate = clicked_candidate
    if "policy_selected_candidate" not in st.session_state:
        st.session_state.policy_selected_candidate = str(policy.sort_values(POLICY_VIEWS[selected_view]["field"], ascending=False).iloc[0]["candidate_name"])
    selected_candidate = st.session_state.policy_selected_candidate

    with detail_col:
        render_view_explainer(selected_view)
        selected_candidate = st.selectbox(
            "生活圈摘要",
            policy["candidate_name"].tolist(),
            index=policy["candidate_name"].tolist().index(selected_candidate)
            if selected_candidate in policy["candidate_name"].tolist()
            else 0,
            format_func=lambda value: str(policy.loc[policy["candidate_name"] == value, "living_area"].iloc[0]),
        )
        st.session_state.policy_selected_candidate = selected_candidate
        row = policy[policy["candidate_name"] == selected_candidate].iloc[0]
        render_candidate_detail(row)

    st.markdown("## 租金 × 公共運輸可達性壓力篩選")
    st.markdown(
        '<div class="qj-section-note">X = commute accessibility minutes，Y = official median rent，顏色 = livability_index。象限線使用目前 16 個候選點的 median 動態計算。</div>',
        unsafe_allow_html=True,
    )
    fig = build_policy_scatter(policy)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    with st.expander("資料、方法與限制", expanded=False):
        render_policy_method_notes()


def build_policy_map(
    policy: pd.DataFrame,
    towns: gpd.GeoDataFrame,
    cities: gpd.GeoDataFrame,
    view: str,
) -> folium.Map:
    view_config = POLICY_VIEWS[view]
    values = policy[view_config["field"]]
    min_value = float(values.min())
    max_value = float(values.max())
    color_map = LinearColormap(
        colors=[view_config["low_color"], view_config["high_color"]],
        vmin=min_value,
        vmax=max_value,
    )

    map_obj = folium.Map(
        location=[25.04, 121.50],
        zoom_start=10,
        tiles="CartoDB positron",
        control_scale=True,
        prefer_canvas=True,
    )
    _fit_policy_bounds(map_obj, policy)
    _add_policy_boundaries(map_obj, towns, cities)

    for _, row in policy.iterrows():
        value = float(row[view_config["field"]])
        radius = _scaled_radius(value, min_value, max_value)
        color = color_map(value)
        if view == "生活機能":
            tooltip = _livability_tooltip(row)
        elif view == "政策型租賃樣本":
            tooltip = _policy_sample_tooltip(row)
        elif view == "公共運輸可達性":
            tooltip = (
                f"{row['living_area']}｜median {row['commute_accessibility_minutes']:.1f} min｜"
                f"{int(row['commute_accessibility_workplace_count'])} workplaces"
            )
        else:
            tooltip = (
                f"{row['living_area']}｜{money(row['official_median_rent'])} NTD/month｜"
                f"{int(row['official_contract_count'])} official contracts"
            )

        folium.CircleMarker(
            location=[float(row["lat"]), float(row["lon"])],
            radius=radius,
            color="#FFFFFF",
            weight=2.0,
            fill=True,
            fill_color=color,
            fill_opacity=0.90,
            opacity=0.95,
            tooltip=tooltip,
            popup=_policy_popup(row),
        ).add_to(map_obj)

    _add_city_label(map_obj, 25.095, 121.405, "新北市")
    _add_city_label(map_obj, 25.045, 121.555, "臺北市")
    _add_policy_legend(map_obj, view_config, min_value, max_value)
    return map_obj


def render_view_explainer(view: str) -> None:
    view_config = POLICY_VIEWS[view]
    st.html(
        f"""
        <div class="qj-policy-panel">
            <div class="qj-policy-eyebrow">目前視角</div>
            <div class="qj-policy-panel-title">{html.escape(view_config['title'])}</div>
            <div class="qj-policy-panel-copy">{html.escape(view_config['caption'])}</div>
            <div class="qj-policy-mini-note">{html.escape(view_config['higher_label'])}</div>
        </div>
        """
    )


def render_candidate_detail(row: pd.Series) -> None:
    share = float(row["policy_linked_record_share"])
    sample_warning = ""
    if int(row["total_rental_record_count"]) < SMALL_SAMPLE_THRESHOLD:
        sample_warning = '<div class="qj-policy-warning">小樣本，請謹慎解讀</div>'
    st.html(
        f"""
        <div class="qj-policy-detail">
            <div class="qj-policy-detail-title">{html.escape(str(row['living_area']))}</div>
            <div class="qj-policy-detail-subtitle">{html.escape(str(row['candidate_name']))}｜{html.escape(str(row['district']))}｜{html.escape(str(row['policy_quadrant']))}</div>
            <div class="qj-policy-metric-grid">
                <div><span>租金</span><b>{money(row['official_median_rent'])}</b><small>NTD/month</small></div>
                <div><span>公共運輸可達性</span><b>{float(row['commute_accessibility_minutes']):.1f}</b><small>min</small></div>
                <div><span>生活機能 proxy</span><b>{float(row['livability_index']):.3f}</b><small>OSM 800m</small></div>
                <div><span>政策型租賃相關登錄樣本</span><b>{share * 100:.1f}%</b><small>{int(row['policy_linked_record_count'])} / {int(row['total_rental_record_count'])}</small></div>
            </div>
            {sample_warning}
            <div class="qj-policy-description">{html.escape(_describe_candidate(row))}</div>
        </div>
        """
    )


def build_policy_scatter(policy: pd.DataFrame):
    _configure_matplotlib()
    rent_threshold = float(policy["official_median_rent"].median())
    commute_threshold = float(policy["commute_accessibility_minutes"].median())

    fig, ax = plt.subplots(figsize=(12.2, 6.6))
    scatter = ax.scatter(
        policy["commute_accessibility_minutes"],
        policy["official_median_rent"],
        c=policy["livability_index"],
        cmap="YlGnBu",
        s=120,
        edgecolor="white",
        linewidth=1.2,
        alpha=0.92,
    )
    ax.axhline(rent_threshold, color="#9AA7AA", linewidth=1.2, linestyle=(0, (5, 5)))
    ax.axvline(commute_threshold, color="#9AA7AA", linewidth=1.2, linestyle=(0, (5, 5)))

    label_candidates = set(
        policy.sort_values("official_median_rent", ascending=False).head(3)["candidate_name"].tolist()
        + policy.sort_values("commute_accessibility_minutes", ascending=False).head(3)["candidate_name"].tolist()
        + policy.sort_values("livability_index", ascending=False).head(2)["candidate_name"].tolist()
    )
    for _, row in policy[policy["candidate_name"].isin(label_candidates)].iterrows():
        ax.annotate(
            row["candidate_name"],
            (row["commute_accessibility_minutes"], row["official_median_rent"]),
            xytext=(7, 5),
            textcoords="offset points",
            fontsize=9,
            color="#243238",
        )

    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    ax.text(x_min + 1, y_max - 700, "較高租金 × 較短通勤", color="#58676D", fontsize=10, weight="bold")
    ax.text(commute_threshold + 1, y_max - 700, "較高租金 × 較長通勤", color="#58676D", fontsize=10, weight="bold")
    ax.text(x_min + 1, y_min + 700, "較低租金 × 較短通勤", color="#58676D", fontsize=10, weight="bold")
    ax.text(commute_threshold + 1, y_min + 700, "較低租金 × 較長通勤", color="#58676D", fontsize=10, weight="bold")

    ax.set_xlabel("Commute accessibility minutes（越右 = 公共運輸可達性越弱）")
    ax.set_ylabel("Official median rent（NTD/month）")
    ax.set_title("Policy v0 housing-accessibility pressure screening", loc="left", fontsize=15, weight="bold")
    ax.grid(True, color="#E5EBEC", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#B8C2C5")
    colorbar = fig.colorbar(scatter, ax=ax, shrink=0.86, pad=0.02)
    colorbar.set_label("livability_index")
    fig.tight_layout()
    return fig


def render_policy_method_notes() -> None:
    st.markdown(
        """
        <div class="qj-note">
        <b>資料與方法限制</b><br>
        租金是行政區尺度 MOI 獨立套房官方 benchmark，不是站點周邊即時房租。<br>
        commute 是候選生活圈代表節點到現有 workplace anchors 的公共運輸 proxy。<br>
        livability 是 OSM 800m POI proxy，不代表完整生活品質。<br>
        policy-linked share 是租賃登錄樣本結構，不是市場占比、政策住宅供給率或青年租屋占比。<br>
        租賃資料沒有承租人年齡，因此不可稱為青年租賃案件。<br>
        Policy Lens 是 screening tool，不是因果分析或正式政策排序。
        </div>
        """,
        unsafe_allow_html=True,
    )


def _fit_policy_bounds(map_obj: folium.Map, policy: pd.DataFrame) -> None:
    bounds = [
        [max(24.91, float(policy["lat"].min()) - 0.04), max(121.30, float(policy["lon"].min()) - 0.05)],
        [min(25.24, float(policy["lat"].max()) + 0.04), min(121.72, float(policy["lon"].max()) + 0.05)],
    ]
    map_obj.fit_bounds(bounds, padding=(12, 12))


def _add_policy_boundaries(map_obj: folium.Map, towns: gpd.GeoDataFrame, cities: gpd.GeoDataFrame) -> None:
    taipei_towns = towns[towns["COUNTYNAME"] == "臺北市"]
    ntpc_towns = towns[towns["COUNTYNAME"] == "新北市"]
    folium.GeoJson(
        taipei_towns,
        name="taipei context",
        style_function=lambda _: {
            "fillColor": "#F3F5F4",
            "color": "#D4DCDE",
            "weight": 0.7,
            "opacity": 0.55,
            "fillOpacity": 0.12,
        },
    ).add_to(map_obj)
    folium.GeoJson(
        ntpc_towns,
        name="ntpc district boundary",
        style_function=lambda _: {
            "fillColor": "#FFFFFF",
            "color": "#C8D2D4",
            "weight": 0.95,
            "opacity": 0.75,
            "fillOpacity": 0.07,
        },
        tooltip=folium.GeoJsonTooltip(fields=["TOWNNAME"], labels=False),
    ).add_to(map_obj)

    def city_style(feature: dict) -> dict:
        city = feature["properties"].get("COUNTYNAME")
        return {
            "fillColor": "#FFFFFF",
            "color": "#728D79" if city == "新北市" else "#7890A0",
            "weight": 3.0 if city == "新北市" else 2.0,
            "opacity": 0.92 if city == "新北市" else 0.58,
            "fillOpacity": 0.0,
        }

    folium.GeoJson(
        cities,
        name="city boundary",
        style_function=city_style,
        tooltip=folium.GeoJsonTooltip(fields=["COUNTYNAME"], labels=False),
    ).add_to(map_obj)


def _scaled_radius(value: float, min_value: float, max_value: float) -> float:
    if max_value == min_value:
        return 10.0
    return 6.0 + ((value - min_value) / (max_value - min_value)) * 11.0


def _policy_popup(row: pd.Series) -> folium.Popup:
    warning = ""
    if int(row["total_rental_record_count"]) < SMALL_SAMPLE_THRESHOLD:
        warning = '<div style="color:#A15C2F;font-weight:700;margin-top:5px;">小樣本，請謹慎解讀</div>'
    html_body = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-width:235px;">
      <div style="font-weight:850;font-size:16px;margin-bottom:2px;">{html.escape(str(row['living_area']))}</div>
      <div style="color:#65747A;margin-bottom:8px;">{html.escape(str(row['candidate_name']))}｜{html.escape(str(row['district']))}</div>
      <div>租金：<b>{money(row['official_median_rent'])} NTD/month</b></div>
      <div>公共運輸可達性：<b>{float(row['commute_accessibility_minutes']):.1f} min</b></div>
      <div>生活機能 proxy：<b>{float(row['livability_index']):.3f}</b></div>
      <div>政策型租賃相關登錄樣本：<b>{float(row['policy_linked_record_share']) * 100:.1f}%</b> ({int(row['policy_linked_record_count'])} / {int(row['total_rental_record_count'])})</div>
      <div style="color:#65747A;margin-top:6px;">{html.escape(str(row['policy_quadrant']))}</div>
      {warning}
    </div>
    """
    return folium.Popup(html_body, max_width=320)


def _livability_tooltip(row: pd.Series) -> str:
    pieces = [
        f"{row['living_area']}｜livability {float(row['livability_index']):.3f}",
    ]
    if "food_count" in row and not pd.isna(row["food_count"]):
        pieces.append(
            "餐飲 {food}｜採買 {shopping}｜休閒 {recreation}｜文娛 {culture}｜醫療 {medical}".format(
                food=int(row["food_count"]),
                shopping=int(row["shopping_count"]),
                recreation=int(row["recreation_count"]),
                culture=int(row["culture_count"]),
                medical=int(row["medical_count"]),
            )
        )
    return "｜".join(pieces)


def _policy_sample_tooltip(row: pd.Series) -> str:
    warning = "｜小樣本，請謹慎解讀" if int(row["total_rental_record_count"]) < SMALL_SAMPLE_THRESHOLD else ""
    return (
        f"{row['living_area']}｜{float(row['policy_linked_record_share']) * 100:.1f}%"
        f"（{int(row['policy_linked_record_count'])} / {int(row['total_rental_record_count'])}）{warning}"
    )


def _candidate_from_click(policy: pd.DataFrame, map_state: dict | None) -> str | None:
    if not map_state or not map_state.get("last_object_clicked"):
        return None
    clicked = map_state["last_object_clicked"]
    if clicked.get("lat") is None or clicked.get("lng") is None:
        return None
    lat = float(clicked["lat"])
    lon = float(clicked["lng"])
    distances = (policy["lat"] - lat).abs() + (policy["lon"] - lon).abs()
    closest_index = distances.idxmin()
    if float(distances.loc[closest_index]) > 0.01:
        return None
    return str(policy.loc[closest_index, "candidate_name"])


def _describe_candidate(row: pd.Series) -> str:
    rent = "較高租金" if "高租金" in row["policy_quadrant"] else "較低租金"
    commute = "較長通勤" if "長通勤" in row["policy_quadrant"] else "較短通勤"
    livability = float(row["livability_index"])
    if livability >= 0.6:
        livability_text = "生活機能 proxy 在候選中相對較高"
    elif livability >= 0.3:
        livability_text = "生活機能 proxy 屬中間程度"
    else:
        livability_text = "生活機能 proxy 相對較弱"
    return f"目前資料顯示此生活圈位於「{rent} × {commute}」象限；{livability_text}。此描述僅供政策篩選，不代表政策優先順序。"


def _add_city_label(map_obj: folium.Map, lat: float, lon: float, label: str) -> None:
    folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(
            html=(
                '<div style="font-size:16px;font-weight:850;color:#52646B;'
                'text-shadow:0 0 5px white,0 0 7px white;white-space:nowrap;">'
                f"{html.escape(label)}</div>"
            ),
            icon_size=(70, 24),
            icon_anchor=(35, 12),
        ),
    ).add_to(map_obj)


def _add_policy_legend(map_obj: folium.Map, view_config: dict[str, str], min_value: float, max_value: float) -> None:
    if view_config["unit"] == "share":
        min_label = f"{min_value * 100:.1f}%"
        max_label = f"{max_value * 100:.1f}%"
    elif view_config["unit"] == "NTD/month":
        min_label = f"{money(min_value)}"
        max_label = f"{money(max_value)}"
    elif view_config["unit"] == "min":
        min_label = f"{min_value:.1f}"
        max_label = f"{max_value:.1f}"
    else:
        min_label = f"{min_value:.3f}"
        max_label = f"{max_value:.3f}"
    template = Template(
        f"""
        {{% macro html(this, kwargs) %}}
        <div style="
            position: fixed;
            right: 24px;
            bottom: 28px;
            z-index: 9999;
            background: rgba(255,255,255,0.94);
            border: 1px solid #D6DDE0;
            border-radius: 10px;
            padding: 10px 12px;
            color: #243238;
            font-size: 13px;
            box-shadow: 0 1px 4px rgba(36,50,56,0.10);
            min-width: 190px;
        ">
          <div style="font-weight:850;margin-bottom:7px;">{html.escape(view_config['title'])}</div>
          <div style="height:10px;border-radius:999px;background:linear-gradient(90deg,{view_config['low_color']},{view_config['high_color']});margin-bottom:5px;"></div>
          <div style="display:flex;justify-content:space-between;color:#65747A;font-size:12px;"><span>{min_label}</span><span>{max_label}</span></div>
          <div style="margin-top:7px;color:#65747A;">{html.escape(view_config['higher_label'])}</div>
          <div style="margin-top:6px;"><span style="display:inline-block;width:18px;border-top:3px solid #728D79;margin-right:6px;"></span>新北市外框</div>
        </div>
        {{% endmacro %}}
        """
    )
    macro = MacroElement()
    macro._template = template
    map_obj.get_root().add_child(macro)


def _configure_matplotlib() -> None:
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
    plt.rcParams["figure.dpi"] = 150
