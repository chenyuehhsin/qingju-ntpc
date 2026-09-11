"""Compact, responsive presentation components for career exploration results."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from textwrap import dedent
from typing import Callable, Sequence

import streamlit as st


@dataclass(frozen=True)
class CareerPathViewModel:
    occupation_id: str
    title: str
    english_title: str
    reason: str
    badge: str
    transferable_skills: tuple[str, ...]
    missing_skill_count: str
    transition_distance: str
    skill_reuse: str
    learning_burden: str
    market_signal: str


def render_career_filters(
    *,
    source_options: Sequence[str],
    domain_options: Sequence[str],
    horizon_options: Sequence[str],
    source_label: Callable[[str], str],
    applied_source: str,
    applied_domain: str,
    applied_horizon: str,
) -> tuple[bool, str, str, str]:
    """Render draft filters; results only change after explicit submission."""
    defaults = {
        "career_source_background_draft": applied_source,
        "career_target_domain_draft": applied_domain,
        "career_learning_horizon_draft": applied_horizon,
    }
    for key, value in defaults.items():
        if st.session_state.get(key) not in {
            "career_source_background_draft": source_options,
            "career_target_domain_draft": domain_options,
            "career_learning_horizon_draft": horizon_options,
        }[key]:
            st.session_state[key] = value

    with st.container(border=True, key="career_filter_panel"):
        source_col, domain_col, horizon_col, action_col = st.columns(
            [1.05, 1.05, 0.9, 0.72], gap="medium", vertical_alignment="bottom"
        )
        with source_col:
            source = st.selectbox(
                "目前背景",
                source_options,
                format_func=source_label,
                key="career_source_background_draft",
            )
        with domain_col:
            domain = st.selectbox(
                "目標領域",
                domain_options,
                key="career_target_domain_draft",
            )
        with horizon_col:
            horizon = st.selectbox(
                "學習時間窗",
                horizon_options,
                key="career_learning_horizon_draft",
            )
        with action_col:
            submitted = st.button(
                "重新分析",
                key="career_reanalyze_button",
                type="primary",
                use_container_width=True,
                help="依目前選擇更新職涯方向",
            )

        _html(
            '<div class="qj-career-scenario" aria-label="目前探索情境">'
            '<span class="qj-career-scenario-label">目前探索情境</span>'
            f'<span>{escape(source_label(applied_source))}</span>'
            f'<span>{escape(applied_domain)}</span>'
            f'<span>{escape(applied_horizon)}</span>'
            "</div>"
        )
    return submitted, source, domain, horizon


def render_career_loading_skeleton():
    """Show a short-lived, accessible placeholder while local results are rebuilt."""
    placeholder = st.empty()
    placeholder.markdown(
        '<div class="qj-career-skeleton" role="status" aria-live="polite" aria-label="正在載入職涯方向">'
        '<span></span><span></span><span></span></div>',
        unsafe_allow_html=True,
    )
    return placeholder


def render_career_exploration_page(
    paths: Sequence[CareerPathViewModel],
    *,
    on_path: Callable[[str], None],
    on_evidence: Callable[[str], None],
    data_date: str,
    analysis_copy: dict[str, str],
) -> None:
    """Render result cards, comparison panel, and collapsed methodology."""
    if not paths:
        with st.container(border=True, key="career_empty_state"):
            st.markdown("#### 找不到符合目前條件的職涯方向")
            st.write("目前資料沒有可呈現的結果，請調整目標領域後重新分析。")
        return

    _render_career_result_summary(paths)

    result_col, comparison_col = st.columns(
        [2.05, 1],
        gap="large",
        vertical_alignment="top",
    )
    with result_col:
        for rank, path in enumerate(paths, start=1):
            render_career_path_card(path, rank=rank, on_path=on_path, on_evidence=on_evidence)
    with comparison_col:
        with st.container(key="career_comparison_anchor"):
            render_career_comparison_panel(paths)

    render_career_evidence_panel(data_date=data_date, analysis_copy=analysis_copy)


def _render_career_result_summary(paths: Sequence[CareerPathViewModel]) -> None:
    """Give the result set a useful visual overview without inventing scores."""
    near_count = sum(path.transition_distance.strip() == "近" for path in paths)
    verified_count = sum(
        path.market_signal.strip() not in {"", "待驗證", "市場訊號待驗證", "資料不足"}
        for path in paths
    )
    market_value = f"{verified_count} 條已載入" if verified_count else "皆待驗證"
    items = [
        ("探索結果", f"{len(paths)} 個方向", "依目前條件產生"),
        ("優先路徑", paths[0].title, paths[0].badge or "第一推薦"),
        ("近距離銜接", f"{near_count} 個方向", "依能力銜接判斷"),
        ("市場證據", market_value, "與職能推薦分開呈現"),
    ]
    markup = "".join(
        '<div class="qj-result-summary-item">'
        f'<span>{escape(label)}</span><b>{escape(value)}</b><small>{escape(note)}</small>'
        "</div>"
        for label, value, note in items
    )
    _html(
        '<section class="qj-result-summary qj-career-result-summary" '
        'aria-label="本次職涯探索摘要">'
        f"{markup}</section>"
    )


def render_career_path_card(
    path: CareerPathViewModel,
    *,
    rank: int,
    on_path: Callable[[str], None],
    on_evidence: Callable[[str], None],
) -> None:
    emphasis = " qj-career-result-card-primary" if rank == 1 else ""
    with st.container(border=True, key=f"career_result_card_{rank}"):
        _html(
            f'<article class="qj-career-result-card{emphasis}" aria-labelledby="career-title-{rank}">'
            '<div class="qj-career-result-copy">'
            '<div class="qj-career-rank-row">'
            f'<span class="qj-career-rank" aria-label="推薦順序第 {rank} 名">{rank}</span>'
            f'<span class="qj-career-path-badge">{escape(path.badge)}</span>'
            "</div>"
            f'<h3 id="career-title-{rank}">{escape(path.title)}</h3>'
            f'<div class="qj-career-english">{escape(path.english_title or "英文名稱資料不足")}</div>'
            f'<p>{escape(path.reason or "推薦理由資料不足")}</p>'
            '<div class="qj-career-skill-heading">'
            '<span>可沿用技能</span>'
            f'<b>需補 {escape(path.missing_skill_count or "資料不足")}</b>'
            '</div>'
            f'{_skill_chips(path.transferable_skills)}'
            "</div>"
            f'{render_career_path_metrics(path)}'
            "</article>"
        )
        route_col, evidence_col = st.columns(2, gap="small")
        with route_col:
            if st.button(
                "查看轉職路徑",
                key=f"career_path_button_{rank}",
                type="primary",
                use_container_width=True,
                help=f"查看{path.title}的能力轉移、技能缺口與學習建議",
            ):
                on_path(path.occupation_id)
        with evidence_col:
            if st.button(
                "查看證據",
                key=f"career_evidence_button_{rank}",
                use_container_width=True,
                help=f"查看{path.title}的推薦與市場資料依據",
            ):
                on_evidence(path.occupation_id)


def render_career_path_metrics(path: CareerPathViewModel) -> str:
    items = [
        ("transition_distance", "轉職距離", path.transition_distance),
        ("skill_reuse", "能力沿用", path.skill_reuse),
        ("learning_burden", "學習負擔", path.learning_burden),
        ("market_signal", "市場訊號", path.market_signal),
    ]
    metrics = "".join(
        '<div class="qj-career-result-metric">'
        '<div class="qj-career-metric-heading">'
        f'{_metric_icon(attribute)}<span>{escape(label)}</span>'
        '</div>'
        f'<b>{escape(value or "資料不足")}</b>'
        f'{_metric_dots(value, attribute)}'
        "</div>"
        for attribute, label, value in items
    )
    return f'<div class="qj-career-result-metrics">{metrics}</div>'


def _metric_icon(attribute: str) -> str:
    """Return small, consistent inline icons without relying on emoji fonts."""
    paths = {
        "transition_distance": '<path d="M4 8h12m-3-3 3 3-3 3M16 16H4m3-3-3 3 3 3"/>',
        "skill_reuse": '<circle cx="10" cy="6" r="3"/><path d="M4.5 18c.5-4 2.3-6 5.5-6s5 2 5.5 6"/>',
        "learning_burden": '<path d="M3 5.5c3-1 5-.4 7 1.5 2-1.9 4-2.5 7-1.5V17c-3-1-5-.4-7 1.5C8 16.6 6 16 3 17Z"/><path d="M10 7v11"/>',
        "market_signal": '<path d="M4 17V9m6 8V4m6 13v-6"/>',
    }
    path = paths.get(attribute, '<circle cx="10" cy="10" r="6"/>')
    return (
        '<svg class="qj-career-metric-icon" viewBox="0 0 20 20" '
        'aria-hidden="true" focusable="false">'
        f'{path}</svg>'
    )


def _metric_dots(value: str, attribute: str) -> str:
    normalized = (value or "").strip()
    levels = {
        "transition_distance": {"近": 3, "中": 2, "遠": 1},
        "skill_reuse": {"低": 1, "中低": 1, "中": 2, "中高": 2, "高": 3},
        # The dots communicate ease of preparation: lower burden is more favourable.
        "learning_burden": {"低": 3, "中低": 3, "中": 2, "中高": 1, "高": 1},
        "market_signal": {
            "已有公開職缺訊號": 3,
            "公開職缺訊號有限": 2,
            "市場訊號待驗證": 1,
            "待驗證": 1,
        },
    }
    count = levels.get(attribute, {}).get(normalized, 0)
    dots = "".join(
        f'<i class="{"is-active" if index <= count else ""}" aria-hidden="true"></i>'
        for index in range(1, 5)
    )
    accessible_value = normalized or "資料不足"
    return (
        f'<span class="qj-career-metric-dots" role="img" '
        f'aria-label="{escape(accessible_value)}，程度 {count}／4">{dots}</span>'
    )


def render_career_comparison_panel(paths: Sequence[CareerPathViewModel]) -> None:
    headers = "".join(
        f'<th scope="col"><span>{index}</span>{escape(path.title)}</th>'
        for index, path in enumerate(paths, start=1)
    )
    rows = "".join(
        _comparison_row(label, [getattr(path, attribute) for path in paths], attribute)
        for label, attribute in [
            ("能力沿用", "skill_reuse"),
            ("學習負擔", "learning_burden"),
            ("轉職距離", "transition_distance"),
        ]
    )
    _html(
        '<aside class="qj-career-comparison" aria-label="三個職涯方向比較">'
        '<div class="qj-career-comparison-title">路徑比較</div>'
        '<div class="qj-career-comparison-subtitle">快速比較三個方向的重點指標。</div>'
        '<div class="qj-career-table-scroll" tabindex="0" aria-label="可水平捲動的職涯比較表">'
        '<table><thead><tr><th scope="col">評估面向</th>'
        f"{headers}</tr></thead><tbody>{rows}</tbody></table></div>"
        '<div class="qj-career-howto"><b>怎麼看這些結果？</b>'
        '<p>排序反映能力銜接程度與學習成本；市場資料將在證據頁另外呈現。</p></div>'
        '<div class="qj-career-limit">本結果提供職涯探索方向，不代表錄取機率、薪資或就業保證。</div>'
        "</aside>"
    )


def render_career_evidence_panel(*, data_date: str, analysis_copy: dict[str, str]) -> None:
    with st.expander("分析依據", expanded=False):
        cols = st.columns(3, gap="medium")
        for col, title, key in zip(
            cols,
            ["職能銜接", "學習成本", "公開職缺訊號"],
            ["skill", "learning", "market"],
        ):
            with col:
                st.markdown(f"**{title}**")
                st.write(analysis_copy.get(key) or "資料不足")
        st.caption(f"資料更新日期：{data_date or '資料不足'}")
        st.caption(analysis_copy.get("limitations") or "資料限制：資料不足")


def _comparison_row(label: str, values: Sequence[str], attribute: str) -> str:
    cells = "".join(f'<td>{_qualitative_scale(value, attribute)}</td>' for value in values)
    return f'<tr><th scope="row">{escape(label)}</th>{cells}</tr>'


def _qualitative_scale(value: str, attribute: str) -> str:
    normalized = value.strip()
    levels = {
        "skill_reuse": {"低": 1, "中低": 1, "中": 2, "中高": 2, "高": 3},
        "learning_burden": {"低": 1, "中低": 1, "中": 2, "中高": 2, "高": 3},
        "transition_distance": {"近": 1, "中": 2, "遠": 3},
    }
    count = levels.get(attribute, {}).get(normalized, 0)
    dots = "".join(
        f'<i class="{"is-active" if index <= count else ""}" aria-hidden="true"></i>'
        for index in range(1, 4)
    )
    label = normalized or "資料不足"
    return f'<span class="qj-career-scale"><span>{escape(label)}</span><span>{dots}</span></span>'


def _skill_chips(skills: Sequence[str]) -> str:
    visible = [skill for skill in skills if skill][:3]
    if not visible:
        return '<div class="qj-career-skill-list"><span class="qj-career-skill-empty">可沿用技能資料不足</span></div>'
    chips = "".join(f"<span>{escape(skill)}</span>" for skill in visible)
    remainder = len([skill for skill in skills if skill]) - len(visible)
    more = f'<span aria-label="另有 {remainder} 項技能">＋{remainder}</span>' if remainder > 0 else ""
    return f'<div class="qj-career-skill-list" aria-label="可沿用技能">{chips}{more}</div>'


def _html(markup: str) -> None:
    st.markdown(dedent(markup).strip(), unsafe_allow_html=True)
