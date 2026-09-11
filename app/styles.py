from __future__ import annotations

import streamlit as st


PAGE_THEMES = {
    "青年職涯探索": {
        "primary": "#198A63",
        "primary_ink": "#126B4D",
        "soft": "#EDF8F3",
        "border": "#BFE2D2",
        "ambient_a": "rgba(25, 138, 99, 0.16)",
        "ambient_b": "rgba(72, 169, 235, 0.14)",
        "ambient_c": "rgba(245, 139, 167, 0.09)",
    },
    "青年安居推薦": {
        "primary": "#42C98E",
        "primary_ink": "#187A59",
        "soft": "#ECFBF3",
        "border": "#C3EFD9",
        "ambient_a": "rgba(66, 201, 142, 0.17)",
        "ambient_b": "rgba(110, 167, 199, 0.14)",
        "ambient_c": "rgba(232, 160, 90, 0.08)",
    },
    "青年局 Policy Lens": {
        "primary": "#F6C64A",
        "primary_ink": "#9A7200",
        "soft": "#FFF8E4",
        "border": "#FFE6A6",
        "ambient_a": "rgba(246, 198, 74, 0.18)",
        "ambient_b": "rgba(66, 201, 142, 0.11)",
        "ambient_c": "rgba(110, 167, 199, 0.11)",
    },
}


def apply_styles(page: str = "青年安居推薦") -> None:
    """Apply the shared UI system and the accent theme for the active product page."""
    theme = PAGE_THEMES.get(page, PAGE_THEMES["青年安居推薦"])
    st.markdown(
        """
        <style>
        :root {
            --qj-bg: #F8FCFF;
            --qj-text: #17324D;
            --qj-muted: #64748B;
            --qj-line: #DDEAF2;
        }
        .stApp {
            background: var(--qj-bg);
            color: var(--qj-text);
        }
        .stApp [data-testid="stAppViewContainer"] .main .block-container,
        .block-container {
            max-width: none;
            width: 100%;
            padding-top: 3.05rem;
            padding-bottom: 2.5rem;
            padding-left: clamp(0.25rem, 0.45vw, 0.55rem);
            padding-right: clamp(0.25rem, 0.45vw, 0.55rem);
        }
        h1, h2, h3 {
            color: var(--qj-text);
            letter-spacing: 0;
        }
        .qj-header-title {
            color: var(--qj-text);
            font-size: clamp(2rem, 2.7vw, 3rem);
            font-weight: 900;
            line-height: 1.08;
            letter-spacing: 0;
            margin-top: 0.85rem;
        }
        .qj-subtitle {
            color: var(--qj-muted);
            font-size: 1.08rem;
            margin-top: 0.25rem;
            margin-bottom: 0.45rem;
        }
        div[data-testid="stSelectbox"] label {
            color: #65747a;
            font-size: 0.84rem;
            font-weight: 760;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            background: #ffffff;
            border-color: #d9e0e2;
            border-radius: 10px;
            min-height: 2.45rem;
            box-shadow: 0 1px 2px rgba(36, 50, 56, 0.035);
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] span {
            color: var(--qj-text);
            font-weight: 720;
        }
        div[data-testid="stSelectbox"] {
            margin-top: 0.10rem;
        }
        div[data-testid="stTextInput"] label,
        div[data-testid="stFormSubmitButton"] label,
        div[data-testid="stButton"] label {
            color: #65747a;
            font-size: 0.84rem;
            font-weight: 760;
        }
        div[data-testid="stTextInput"] input {
            background: #ffffff;
            border-color: #d9e0e2;
            border-radius: 10px;
            min-height: 2.45rem;
            box-shadow: 0 1px 2px rgba(36, 50, 56, 0.035);
        }
        div[data-testid="stFormSubmitButton"],
        div[data-testid="stButton"] {
            margin-top: 1.72rem;
        }
        div[data-testid="stFormSubmitButton"] button,
        div[data-testid="stButton"] button {
            min-height: 2.45rem;
            border-radius: 10px;
            font-weight: 820;
        }
        .qj-panel {
            background: #ffffff;
            border: 1px solid var(--qj-line);
            border-radius: 12px;
            padding: 0.88rem;
            box-shadow: 0 1px 2px rgba(36, 50, 56, 0.04);
        }
        .qj-card {
            background: #ffffff;
            border: 1px solid var(--qj-line);
            border-radius: 12px;
            padding: 0.82rem;
            margin-bottom: 0.66rem;
        }
        .qj-top1-card {
            background: #ffffff;
            border: 1.5px solid var(--qj-line);
            border-radius: 14px;
            padding: 1.08rem;
            margin-bottom: 0.72rem;
            box-shadow: 0 4px 14px rgba(36, 50, 56, 0.06);
        }
        .qj-top1-rank {
            color: #ffffff;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            font-weight: 900;
            font-size: 1.02rem;
            line-height: 1;
            padding: 0.46rem 0.70rem;
            margin-bottom: 0.58rem;
        }
        .qj-top1-title {
            color: var(--qj-text);
            font-size: 1.68rem;
            font-weight: 900;
            line-height: 1.12;
            margin-bottom: 0.15rem;
        }
        .qj-top1-metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
            margin: 0.72rem 0;
        }
        .qj-top1-metrics div {
            background: #f8faf9;
            border: 1px solid #edf1f2;
            border-radius: 10px;
            padding: 0.55rem;
        }
        .qj-top1-metrics span {
            color: #718086;
            display: block;
            font-size: 0.82rem;
        }
        .qj-top1-metrics b {
            color: var(--qj-text);
            display: block;
            font-size: 1.12rem;
            margin-top: 0.1rem;
        }
        .qj-top1-reason {
            color: #58676d;
            font-size: 0.96rem;
            line-height: 1.45;
        }
        .qj-compact-card {
            background: #ffffff;
            border: 1px solid var(--qj-line);
            border-radius: 12px;
            padding: 0.75rem 0.82rem;
            margin-bottom: 0.55rem;
            display: flex;
            gap: 0.72rem;
            align-items: flex-start;
        }
        .qj-compact-rank {
            font-size: 1.18rem;
            font-weight: 900;
            min-width: 2.0rem;
        }
        .qj-compact-body {
            min-width: 0;
        }
        .qj-compact-title {
            color: var(--qj-text);
            font-size: 1.16rem;
            font-weight: 850;
            line-height: 1.25;
        }
        .qj-compact-meta {
            color: #4f5f65;
            font-size: 0.92rem;
            line-height: 1.35;
            margin-top: 0.18rem;
        }
        .qj-compact-reason {
            color: #6b797f;
            font-size: 0.86rem;
            line-height: 1.35;
            margin-top: 0.25rem;
        }
        .qj-card-top {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 0.75rem;
        }
        .qj-rank {
            font-weight: 800;
            font-size: 0.92rem;
        }
        .qj-card-title {
            font-size: 1.18rem;
            font-weight: 800;
            margin-top: 0.12rem;
        }
        .qj-card-title-sub {
            color: #6b797f;
            font-size: 0.82rem;
            font-weight: 720;
            line-height: 1.25;
            margin-top: 0.14rem;
        }
        .qj-station {
            color: var(--qj-muted);
            font-size: 0.84rem;
            margin-bottom: 0.52rem;
        }
        .qj-metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.42rem;
            margin: 0.50rem 0;
        }
        .qj-metric {
            background: #f8faf9;
            border: 1px solid #edf1f2;
            border-radius: 10px;
            padding: 0.48rem;
        }
        .qj-metric-label {
            color: #718086;
            font-size: 0.72rem;
        }
        .qj-metric-value {
            color: var(--qj-text);
            font-weight: 800;
            font-size: 0.94rem;
        }
        .qj-reason {
            color: #58676d;
            font-size: 0.84rem;
            line-height: 1.45;
            margin-top: 0.25rem;
        }
        div[data-testid="stVerticalBlock"] {
            gap: 0.72rem;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 0.72rem;
        }
        .qj-note {
            color: #69777d;
            font-size: 0.78rem;
            line-height: 1.6;
        }
        .qj-summary-strip {
            background: #ffffff;
            border: 1px solid var(--qj-line);
            border-left: 5px solid #78B995;
            border-radius: 12px;
            padding: 0.95rem 1rem;
            color: #334249;
            font-size: 0.98rem;
            line-height: 1.55;
            margin-top: 0.55rem;
            box-shadow: 0 1px 2px rgba(36, 50, 56, 0.04);
        }
        .qj-audience-strip {
            align-items: center;
            color: #65747a;
            display: flex;
            flex-wrap: wrap;
            gap: 0.48rem;
            justify-content: center;
            margin: 0.2rem 0 0.85rem 0;
        }
        .qj-audience-strip span {
            border: 1px solid #dbe6df;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 820;
            line-height: 1;
            padding: 0.38rem 0.66rem;
        }
        .qj-audience-youth {
            background: #eef7f1;
            color: #315f45;
        }
        .qj-audience-policy {
            background: #f8faf9;
            color: #69777d;
        }
        .qj-section-note {
            color: #65747a;
            font-size: 0.92rem;
            margin-top: -0.35rem;
            margin-bottom: 0.55rem;
        }
        .qj-map-provenance {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.45rem 0.85rem;
            margin: 0.15rem 0 0.7rem;
            padding: 0.62rem 0.78rem;
            color: #315f45;
            background: #eef7f1;
            border: 1px solid #cfe2d5;
            border-left: 4px solid #4f9e8d;
            border-radius: 7px;
            font-size: 0.92rem;
        }
        .qj-map-provenance b {
            color: #243238;
        }
        .qj-map-provenance span {
            font-weight: 760;
        }
        .qj-mode-heading {
            font-size: clamp(2.1rem, 3vw, 3.25rem);
            font-weight: 920;
            line-height: 1.05;
            margin: 0.85rem 0 0.3rem 0;
            letter-spacing: 0;
        }
        .qj-mode-hero {
            text-align: center;
            margin: 0 0 0.18rem -50rem;
        }
        .qj-mode-hero-empty {
            min-height: 4.3rem;
        }
        .qj-mode-subtitle {
            color: #65747a;
            font-size: 1.02rem;
            line-height: 1.45;
            margin-top: -0.05rem;
        }
        .qj-overview-card {
            border: 1.3px solid var(--qj-line);
            border-radius: 13px;
            padding: 0.95rem;
            min-height: 174px;
            box-shadow: 0 1px 2px rgba(36, 50, 56, 0.035);
        }
        .qj-overview-mode {
            font-size: 0.88rem;
            font-weight: 850;
            display: flex;
            align-items: center;
            gap: 0.45rem;
            margin-bottom: 0.45rem;
        }
        .qj-dot {
            display: inline-block;
            width: 0.76rem;
            height: 0.76rem;
            border-radius: 50%;
            flex: 0 0 auto;
        }
        .qj-overview-title {
            color: var(--qj-text);
            font-size: 1.22rem;
            font-weight: 850;
            margin-bottom: 0.55rem;
        }
        .qj-overview-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.55rem;
            margin-bottom: 0.45rem;
        }
        .qj-overview-grid span {
            color: #718086;
            display: block;
            font-size: 0.72rem;
        }
        .qj-overview-grid b {
            color: var(--qj-text);
            display: block;
            font-size: 0.98rem;
        }
        .qj-overview-livability {
            color: #66757b;
            font-size: 0.82rem;
            font-weight: 750;
            margin-bottom: 0.42rem;
        }
        .qj-overview-copy {
            color: #5f6f75;
            font-size: 0.78rem;
            line-height: 1.35;
        }
        .qj-comparison-bar {
            background: #ffffff;
            border: 1px solid var(--qj-line);
            border-radius: 12px;
            padding: 0.9rem 1rem;
            margin-top: 0.35rem;
        }
        .qj-comparison-title {
            color: var(--qj-text);
            font-size: 0.95rem;
            font-weight: 850;
            margin: 0.6rem 0 0.15rem 0;
        }
        .qj-comparison-card {
            background: #ffffff;
            border: 1px solid var(--qj-line);
            border-radius: 11px;
            padding: 0.72rem 0.82rem;
            min-height: 104px;
        }
        .qj-comparison-mode {
            color: #334249;
            font-size: 0.86rem;
            display: flex;
            align-items: center;
            gap: 0.45rem;
            margin-bottom: 0.42rem;
        }
        .qj-comparison-main {
            color: var(--qj-text);
            font-size: 1.05rem;
            font-weight: 850;
            line-height: 1.25;
            margin-bottom: 0.25rem;
        }
        .qj-comparison-meta {
            color: #334249;
            font-size: 0.86rem;
            line-height: 1.35;
        }
        .qj-comparison-livability {
            color: #66757b;
            font-size: 0.78rem;
            font-weight: 750;
            min-height: 1.05rem;
            margin-top: 0.2rem;
        }
        .qj-life-detail-card {
            background: #ffffff;
            border: 1px solid var(--qj-line);
            border-left: 5px solid #78B995;
            border-radius: 12px;
            box-shadow: 0 1px 2px rgba(36, 50, 56, 0.04);
            padding: 0.95rem;
        }
        .qj-life-detail-eyebrow {
            color: #65747a;
            font-size: 0.78rem;
            font-weight: 850;
            margin-bottom: 0.18rem;
        }
        .qj-life-detail-title {
            color: var(--qj-text);
            font-size: 1.48rem;
            font-weight: 920;
            line-height: 1.14;
            margin-bottom: 0.15rem;
        }
        .qj-life-metric-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.48rem;
            margin-top: 0.72rem;
        }
        .qj-life-metric-grid div {
            background: #f8faf9;
            border: 1px solid #edf1f2;
            border-radius: 10px;
            padding: 0.52rem;
        }
        .qj-life-metric-grid span,
        .qj-life-metric-grid small {
            display: block;
            color: #718086;
            font-size: 0.72rem;
            line-height: 1.24;
        }
        .qj-life-metric-grid b {
            color: var(--qj-text);
            display: block;
            font-size: 1.02rem;
            font-weight: 900;
            line-height: 1.16;
            margin-top: 0.08rem;
        }
        .qj-life-summary {
            color: #334249;
            font-size: 0.94rem;
            font-weight: 780;
            line-height: 1.48;
            margin-top: 0.78rem;
        }
        .qj-life-poi-note {
            color: #69777d;
            font-size: 0.78rem;
            line-height: 1.42;
            margin-top: 0.58rem;
        }
        div[data-testid="stRadio"] label {
            font-weight: 760;
            cursor: pointer;
        }
        div[data-testid="stRadio"] {
            text-align: center;
            margin-top: 2rem;
            margin-bottom: 0.01rem;
            padding-right: 0;
            transform: translateX(-25rem);
        }
        div[data-testid="stRadio"] > div {
            gap: 0.55rem;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] {
            background: rgba(255, 255, 255, 0.70);
            border: 1px solid #dde5e6;
            border-radius: 16px;
            padding: 0.36rem;
            display: inline-flex;
            flex-wrap: nowrap;
            gap: 0.45rem;
            margin-left: auto;
            margin-right: auto;
            max-width: 100%;
            overflow-x: auto;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label {
            background: #ffffff;
            border: 1px solid #d7e0e2;
            border-radius: 999px;
            padding: 0.62rem 0.92rem;
            min-width: 7.6rem;
            justify-content: center;
            box-shadow: 0 1px 2px rgba(36, 50, 56, 0.04);
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
            background: #E3F3EC;
            border-color: #78B995;
            color: #243238;
            box-shadow: 0 4px 12px rgba(120, 185, 149, 0.18);
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {
            color: #243238;
            font-weight: 850;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label p {
            font-size: 0.94rem;
        }
        iframe {
            border-radius: 12px;
        }
        div[data-testid="stSegmentedControl"] {
            margin-bottom: 0.45rem;
        }
        div[data-testid="stSegmentedControl"] button {
            border-radius: 999px;
            border-color: #d8e1e3;
            background: rgba(255, 255, 255, 0.86);
            color: #243238;
            font-weight: 820;
            min-height: 2.35rem;
            box-shadow: 0 1px 2px rgba(36, 50, 56, 0.035);
        }
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
            background: #EAF4FA;
            border-color: #6EA7C7;
            color: #243238;
            box-shadow: 0 3px 10px rgba(36, 50, 56, 0.08);
        }
        .qj-policy-header {
            margin-top: 0.35rem;
            margin-bottom: 0.75rem;
        }
        .qj-policy-section-head {
            margin: 0.55rem 0 1rem 0;
        }
        .qj-policy-section-title {
            color: #243238;
            font-size: 1.42rem;
            font-weight: 920;
            line-height: 1.15;
        }
        .qj-policy-section-copy {
            color: #5e6d73;
            font-size: 0.98rem;
            line-height: 1.5;
            margin-top: 0.32rem;
        }
        .qj-policy-alert {
            display: inline-flex;
            align-items: center;
            background: #fff7e8;
            border: 1px solid #ead5ae;
            border-radius: 999px;
            color: #6c5632;
            font-size: 0.92rem;
            font-weight: 760;
            padding: 0.45rem 0.78rem;
            margin-top: 0.7rem;
        }
        .qj-policy-capabilities {
            display: flex;
            flex-wrap: wrap;
            gap: 0.42rem;
            margin-top: 0.7rem;
        }
        .qj-policy-capabilities span {
            align-items: center;
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid #F0D88D;
            border-radius: 999px;
            color: #6D5718;
            display: inline-flex;
            font-size: 0.78rem;
            font-weight: 780;
            gap: 0.35rem;
            padding: 0.3rem 0.58rem;
        }
        .qj-policy-capabilities span::before {
            background: #E5B72D;
            border-radius: 999px;
            content: "";
            height: 0.42rem;
            width: 0.42rem;
        }
        .qj-policy-view-switch {
            display: flex;
            justify-content: center;
            margin: 0.2rem 0 0.75rem 0;
        }
        .qj-policy-view-switch div[data-testid="stSegmentedControl"] {
            text-align: center;
        }
        .qj-policy-view-switch div[data-testid="stSegmentedControl"] button {
            min-width: 9.2rem;
        }
        .qj-policy-panel,
        .qj-policy-detail {
            background: #ffffff;
            border: 1px solid var(--qj-line);
            border-radius: 14px;
            padding: 1rem;
            box-shadow: 0 1px 3px rgba(36, 50, 56, 0.045);
            margin-bottom: 0.75rem;
        }
        .qj-policy-eyebrow {
            color: #65747a;
            font-size: 0.78rem;
            font-weight: 850;
            margin-bottom: 0.18rem;
        }
        .qj-policy-panel-title {
            color: #243238;
            font-size: 1.36rem;
            font-weight: 900;
            line-height: 1.18;
        }
        .qj-policy-panel-copy {
            color: #5e6d73;
            font-size: 0.94rem;
            line-height: 1.5;
            margin-top: 0.42rem;
        }
        .qj-policy-mini-note {
            display: inline-flex;
            background: #eef5f5;
            border-radius: 999px;
            color: #52646b;
            font-size: 0.82rem;
            font-weight: 760;
            padding: 0.32rem 0.56rem;
            margin-top: 0.68rem;
        }
        .qj-policy-detail-title {
            color: #243238;
            font-size: 1.52rem;
            font-weight: 920;
            line-height: 1.12;
        }
        .qj-policy-detail-subtitle {
            color: #65747a;
            font-size: 0.9rem;
            margin-top: 0.2rem;
            margin-bottom: 0.72rem;
        }
        .qj-policy-metric-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.56rem;
        }
        .qj-policy-metric-grid div {
            background: #f8faf9;
            border: 1px solid #edf1f2;
            border-radius: 11px;
            padding: 0.62rem;
        }
        .qj-policy-metric-grid span,
        .qj-policy-metric-grid small {
            display: block;
            color: #718086;
            font-size: 0.76rem;
            line-height: 1.25;
        }
        .qj-policy-metric-grid b {
            display: block;
            color: #243238;
            font-size: 1.1rem;
            font-weight: 900;
            margin-top: 0.08rem;
        }
        .qj-policy-warning {
            background: #fff7e8;
            border: 1px solid #ead5ae;
            border-radius: 10px;
            color: #8a5e22;
            font-weight: 820;
            font-size: 0.88rem;
            padding: 0.48rem 0.6rem;
            margin-top: 0.7rem;
        }
        .qj-policy-description {
            color: #58676d;
            font-size: 0.94rem;
            line-height: 1.55;
            margin-top: 0.82rem;
        }
        .qj-career-policy-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.72rem;
            margin: 0.4rem 0 0.85rem 0;
        }
        .qj-career-policy-card {
            background: #ffffff;
            border: 1px solid var(--qj-line);
            border-left: 5px solid #78B995;
            border-radius: 12px;
            padding: 0.7rem 0.78rem;
            box-shadow: 0 1px 2px rgba(36, 50, 56, 0.04);
            min-height: 96px;
        }
        .qj-career-policy-card span,
        .qj-career-policy-card small {
            display: block;
            color: #65747a;
            font-size: 0.82rem;
            line-height: 1.32;
        }
        .qj-career-policy-card b {
            display: block;
            color: #243238;
            font-size: 1.45rem;
            font-weight: 920;
            line-height: 1.05;
            margin: 0.24rem 0;
        }
        .qj-policy-insight-card,
        .qj-policy-analysis-card,
        .qj-policy-compact-metric {
            background: #ffffff;
            border: 1px solid #F3D98B;
            border-radius: 16px;
            box-shadow: 0 2px 8px rgba(23, 50, 77, 0.045);
        }
        .qj-policy-insight-card {
            min-height: 96px;
            padding: 0.64rem 0.74rem;
            margin-bottom: 0.5rem;
        }
        .qj-policy-evidence-badge {
            display: inline-flex;
            background: #FFF4C7;
            border: 1px solid #F3D98B;
            border-radius: 999px;
            color: #17324D;
            font-size: 0.7rem;
            font-weight: 800;
            padding: 0.18rem 0.42rem;
        }
        .qj-policy-matrix-wrap {
            max-width: 100%;
            overflow-x: auto;
            margin: 0.3rem 0 0.65rem;
        }
        .qj-policy-compact-matrix {
            width: 100%;
            min-width: 620px;
            border-collapse: separate;
            border-spacing: 0;
            color: #52646B;
            font-size: 0.76rem;
            line-height: 1.35;
            table-layout: fixed;
        }
        .qj-policy-compact-matrix th,
        .qj-policy-compact-matrix td {
            overflow-wrap: anywhere;
            text-align: left;
            vertical-align: top;
        }
        .qj-policy-compact-matrix th {
            background: #FFF8E4;
            border-bottom: 1px solid #F3D98B;
            color: #775B12;
            font-size: 0.72rem;
            font-weight: 850;
            padding: 0.42rem 0.5rem;
        }
        .qj-policy-compact-matrix th:first-child {
            border-left: 3px solid #F3D98B;
            border-radius: 8px 0 0 0;
            width: 18%;
        }
        .qj-policy-compact-matrix th:nth-child(2) { width: 37%; }
        .qj-policy-compact-matrix th:nth-child(3) { width: 27%; }
        .qj-policy-compact-matrix th:last-child {
            border-radius: 0 8px 0 0;
            width: 18%;
        }
        .qj-policy-compact-matrix td {
            background: #ffffff;
            border-bottom: 1px solid #F5E9C3;
            padding: 0.46rem 0.5rem;
        }
        .qj-policy-compact-matrix td:first-child {
            border-left: 3px solid #FFF0BF;
            color: #17324D;
            font-weight: 800;
        }
        .qj-policy-insight-title,
        .qj-policy-analysis-title {
            color: #17324D;
            font-size: 0.94rem;
            font-weight: 850;
            line-height: 1.35;
        }
        .qj-policy-insight-title {
            margin-top: 0.35rem;
        }
        .qj-policy-analysis-title {
            margin-top: 0.48rem;
        }
        .qj-policy-insight-copy,
        .qj-policy-analysis-copy {
            color: #52646B;
            font-size: 0.82rem;
        }
        .qj-policy-insight-copy {
            line-height: 1.35;
            margin-top: 0.18rem;
        }
        .qj-policy-analysis-copy {
            line-height: 1.48;
            margin-top: 0.28rem;
        }
        .qj-policy-analysis-card {
            padding: 0.82rem 0.9rem;
            margin-bottom: 0.68rem;
        }
        .qj-policy-compact-metric {
            min-height: 104px;
            padding: 0.7rem 0.75rem;
        }
        .qj-policy-compact-metric span,
        .qj-policy-compact-metric small {
            display: block;
            color: #64748B;
            font-size: 0.73rem;
            line-height: 1.3;
        }
        .qj-policy-compact-metric b {
            display: block;
            color: #17324D;
            font-size: 1.05rem;
            font-weight: 900;
            line-height: 1.15;
            margin: 0.24rem 0;
            overflow-wrap: anywhere;
        }
        .qj-policy-detail-summary {
            display: flex;
            flex-wrap: wrap;
            gap: 0.42rem;
        }
        .qj-policy-detail-summary span {
            background: #FFF8E4;
            border: 1px solid #F3D98B;
            border-radius: 999px;
            color: #17324D;
            font-size: 0.78rem;
            font-weight: 720;
            padding: 0.26rem 0.5rem;
        }
        [class*="st-key-policy_career_path_"] {
            background: #ffffff;
            border-color: #F3D98B !important;
            border-radius: 16px;
            box-shadow: 0 2px 8px rgba(23, 50, 77, 0.045);
        }
        [class*="st-key-policy_career_path_"] div[data-testid="stButton"] {
            margin-top: 0.5rem;
        }
        [class*="st-key-policy_career_path_"] div[data-testid="stButton"] button {
            min-height: 2.15rem;
            padding: 0.38rem 0.72rem;
            font-size: 0.86rem;
        }
        .qj-career-header {
            margin-top: 0.3rem;
            margin-bottom: 0.7rem;
        }
        .qj-career-preset,
        .qj-career-empty,
        .qj-career-card {
            background: #ffffff;
            border: 1px solid var(--qj-line);
            border-radius: 12px;
            box-shadow: 0 1px 2px rgba(36, 50, 56, 0.04);
        }
        .qj-career-preset {
            border-left: 5px solid #78B995;
            padding: 0.88rem 1rem;
            min-height: 86px;
        }
        .qj-career-preset-value {
            color: #243238;
            font-size: 1.18rem;
            font-weight: 900;
            line-height: 1.18;
            margin-top: 0.18rem;
        }
        .qj-career-empty {
            color: #65747a;
            font-size: 0.98rem;
            line-height: 1.55;
            padding: 1rem;
            margin-top: 0.85rem;
        }
        .qj-career-card {
            border-top: 5px solid #78B995;
            padding: 0.95rem;
            min-height: 330px;
        }
        .qj-career-card-high-reuse {
            border-top-color: #5da87d;
        }
        .qj-career-card-partial-reuse {
            border-top-color: #78B995;
        }
        .qj-career-card-major-reskilling {
            border-top-color: #d39b43;
        }
        .qj-career-intro {
            color: #46575d;
            font-size: 0.92rem;
            line-height: 1.55;
            margin-top: 0.66rem;
            min-height: 86px;
        }
        .qj-career-badge {
            display: inline-flex;
            align-items: center;
            background: #fff7e8;
            border: 1px solid #ead5ae;
            border-radius: 999px;
            color: #7a5a24;
            font-size: 0.78rem;
            font-weight: 850;
            padding: 0.24rem 0.52rem;
            margin: 0.45rem 0 0.2rem 0;
        }
        .qj-career-card-grid,
        .qj-career-profile-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.48rem;
            margin-top: 0.7rem;
        }
        .qj-career-card-grid .qj-metric,
        .qj-career-profile-grid .qj-metric {
            min-height: 68px;
        }
        .qj-career-card-grid {
            grid-template-columns: 1fr;
        }
        .qj-transition-map {
            background: #ffffff;
            border: 1px solid var(--qj-line);
            border-radius: 12px;
            box-shadow: 0 1px 2px rgba(36, 50, 56, 0.04);
            margin: 0.8rem 0 0.9rem 0;
            padding: 0.95rem;
        }
        .qj-transition-map-head {
            align-items: center;
            border-bottom: 1px solid #edf1f2;
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            padding-bottom: 0.68rem;
        }
        .qj-transition-source,
        .qj-transition-target {
            color: #243238;
            font-size: 0.92rem;
            font-weight: 850;
            white-space: nowrap;
        }
        .qj-transition-target {
            color: #315f45;
            text-align: right;
        }
        .qj-transition-lanes {
            display: grid;
            gap: 0.62rem;
            margin-top: 0.8rem;
        }
        .qj-transition-lane {
            align-items: stretch;
            display: grid;
            grid-template-columns: 96px 52px minmax(0, 1fr);
            gap: 0.55rem;
        }
        .qj-transition-origin {
            align-items: center;
            background: #eef7f1;
            border: 1px solid #d7eadf;
            border-radius: 10px;
            color: #315f45;
            display: flex;
            font-size: 0.9rem;
            font-weight: 900;
            justify-content: center;
            min-height: 104px;
            padding: 0.55rem;
            text-align: center;
        }
        .qj-transition-arrow {
            align-self: center;
            background: linear-gradient(90deg, #78B995, #b9cf88);
            border-radius: 999px;
            height: 4px;
            position: relative;
        }
        .qj-transition-arrow::after {
            border-bottom: 6px solid transparent;
            border-left: 8px solid #b9cf88;
            border-top: 6px solid transparent;
            content: "";
            position: absolute;
            right: -2px;
            top: 50%;
            transform: translateY(-50%);
        }
        .qj-transition-arrow-long {
            background: linear-gradient(90deg, #78B995, #d39b43);
        }
        .qj-transition-arrow-long::after {
            border-left-color: #d39b43;
        }
        .qj-transition-node {
            background: #fbfdfb;
            border: 1px solid #dceae1;
            border-top: 4px solid #78B995;
            border-radius: 10px;
            min-height: 104px;
            min-width: 0;
            padding: 0.68rem;
        }
        .qj-transition-node-title {
            color: #243238;
            font-size: 1rem;
            font-weight: 900;
            line-height: 1.2;
            word-break: keep-all;
        }
        .qj-transition-node-intro {
            color: #58676d;
            font-size: 0.84rem;
            line-height: 1.45;
            margin-top: 0.28rem;
            word-break: normal;
        }
        .qj-transition-node-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.32rem;
            margin-top: 0.48rem;
        }
        .qj-transition-node-meta span {
            background: #ffffff;
            border: 1px solid #edf1f2;
            border-radius: 999px;
            color: #4c6066;
            font-size: 0.72rem;
            font-weight: 820;
            line-height: 1;
            padding: 0.28rem 0.48rem;
        }
        .qj-career-detail-block {
            border-bottom: 1px solid #edf1f2;
            padding-bottom: 0.72rem;
            margin-bottom: 0.72rem;
        }
        .qj-path-conclusion {
            background: #eef7f1;
            border: 1px solid #d7eadf;
            border-radius: 10px;
            color: #315f45;
            font-size: 0.98rem;
            font-weight: 850;
            line-height: 1.45;
            margin-bottom: 0.82rem;
            padding: 0.72rem 0.78rem;
        }
        .qj-career-detail-block:last-child {
            border-bottom: 0;
            padding-bottom: 0;
            margin-bottom: 0;
        }
        .qj-career-detail-text {
            color: #334249;
            font-size: 0.92rem;
            line-height: 1.5;
            margin-top: 0.18rem;
        }
        .qj-skill-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.38rem;
            margin-top: 0.35rem;
        }
        .qj-skill-chip,
        .qj-skill-more {
            display: inline-flex;
            align-items: center;
            background: #eef7f1;
            border: 1px solid #d7eadf;
            border-radius: 999px;
            color: #315f45;
            font-size: 0.82rem;
            font-weight: 800;
            line-height: 1.2;
            padding: 0.28rem 0.56rem;
        }
        .qj-skill-more {
            background: #f8faf9;
            border-color: #edf1f2;
            color: #69777d;
        }
        .qj-job-card {
            background: #ffffff;
            border: 1px solid #dfe9e3;
            border-left: 5px solid #78B995;
            border-radius: 10px;
            box-shadow: 0 1px 2px rgba(36, 50, 56, 0.035);
            margin-top: 0.62rem;
            padding: 0.72rem 0.78rem;
        }
        .qj-job-title {
            color: #243238;
            font-size: 0.98rem;
            font-weight: 900;
            line-height: 1.28;
        }
        .qj-job-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.36rem;
            margin-top: 0.44rem;
        }
        .qj-job-meta span {
            background: #f8faf9;
            border: 1px solid #edf1f2;
            border-radius: 999px;
            color: #52646a;
            font-size: 0.76rem;
            font-weight: 780;
            line-height: 1.15;
            padding: 0.28rem 0.48rem;
        }
        .qj-job-summary {
            color: #46575d;
            font-size: 0.86rem;
            line-height: 1.5;
            margin-top: 0.5rem;
        }
        .qj-job-source {
            font-size: 0.78rem;
            font-weight: 820;
            margin-top: 0.5rem;
        }
        .qj-job-source a {
            color: #315f45;
            text-decoration: none;
        }
        .qj-job-review {
            background: #fff7e8;
            border: 1px solid #ead5ae;
            border-radius: 999px;
            color: #7a5a24;
            display: inline-flex;
            font-size: 0.74rem;
            font-weight: 850;
            line-height: 1;
            margin-top: 0.38rem;
            padding: 0.28rem 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # Keep page colour distinct without coupling presentation to any data or view logic.
    st.markdown(
        f"""
        <style>
        .stApp {{
            --qj-bg: #F8FCFF;
            --qj-surface: #ffffff;
            --qj-text: #17324D;
            --qj-muted: #64748B;
            --qj-line: #DDEAF2;
            --qj-primary: {theme['primary']};
            --qj-primary-ink: {theme['primary_ink']};
            --qj-primary-soft: {theme['soft']};
            --qj-primary-border: {theme['border']};
            --qj-accent-pink: #F58BA7;
            --qj-accent-pink-soft: #FFF0F4;
            --qj-accent-pink-ink: #9E3F59;
            --qj-radius-card: 12px;
            --qj-radius-control: 10px;
            --qj-shadow: 0 1px 4px rgba(23, 50, 77, 0.045);
            background:
                radial-gradient(ellipse 54rem 36rem at -6% -8%, {theme['ambient_a']} 0%, transparent 72%),
                radial-gradient(ellipse 52rem 34rem at 106% 10%, {theme['ambient_b']} 0%, transparent 70%),
                radial-gradient(ellipse 60rem 32rem at 52% 108%, {theme['ambient_c']} 0%, transparent 72%),
                linear-gradient(180deg, #F7FCFF 0%, #FCFEFF 44%, #F7FAFC 100%),
                var(--qj-bg);
            background-attachment: fixed;
        }}
        .stApp [data-testid="stAppViewContainer"],
        .stApp section[data-testid="stMain"] {{
            background: transparent;
        }}
        .stApp [data-testid="stAppViewContainer"] .main .block-container,
        .block-container {{ 
            width: calc(100vw - 12px) !important;
            max-width: none !important;
            margin-left: 6px !important;
            margin-right: 6px !important;
            padding-left: 6px !important;
            padding-right: 6px !important;
            padding-inline: 6px !important;
        }}
        h1, h2, h3 {{
            color: var(--qj-text);
            letter-spacing: -0.018em;
        }}
        h2 {{ margin-top: 1.8rem; }}
        h3 {{ margin-top: 1.25rem; }}
        .qj-header-title {{
            color: var(--qj-text);
            font-size: clamp(2rem, 3vw, 3.15rem);
            letter-spacing: -0.035em;
            margin-top: 0.35rem;
        }}
        .qj-subtitle {{ max-width: 48rem; line-height: 1.55; }}

        /* Global top navigation: a light website header, not a dashboard card. */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.qj-top-nav-brand) {{
            background: rgba(255, 255, 255, 0.94);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 0 !important;
            border-bottom: 1px solid #DDEAF2 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            margin: 0 0 0.5rem !important;
            padding: 0 0.15rem !important;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.qj-top-nav-brand) > div {{
            padding: 0 !important;
        }}
        .qj-top-nav-brand {{
            align-items: center;
            display: flex;
            flex-direction: row;
            gap: 0.62rem;
            justify-content: flex-start;
            min-height: 52px;
            padding-left: 0.45rem;
            text-align: left;
        }}
        .qj-brand-mark {{
            background:
                radial-gradient(circle at 68% 28%, #7DE2B1 0 18%, transparent 19%),
                linear-gradient(145deg, var(--qj-primary) 0 48%, var(--qj-primary-ink) 49% 100%);
            border-radius: 55% 45% 60% 40%;
            box-shadow: 0 4px 12px rgba(23, 50, 77, 0.12);
            display: block;
            flex: 0 0 auto;
            height: 1.7rem;
            position: relative;
            transform: rotate(-10deg);
            width: 1.7rem;
        }}
        .qj-brand-mark::after {{
            background: rgba(255, 255, 255, 0.92);
            border-radius: 999px;
            content: "";
            height: 0.28rem;
            left: 0.42rem;
            position: absolute;
            top: 0.72rem;
            transform: rotate(42deg);
            width: 0.92rem;
        }}
        .qj-top-nav-title {{
            color: var(--qj-text);
            font-size: clamp(1rem, 1.25vw, 1.28rem);
            font-weight: 900;
            letter-spacing: -0.025em;
            line-height: 1.1;
            white-space: nowrap;
        }}
        .qj-top-nav-subtitle {{
            color: var(--qj-muted);
            font-size: 0.72rem;
            font-weight: 720;
            margin-top: 0.18rem;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.qj-top-nav-brand) [data-testid="stHorizontalBlock"]:has(button) {{
            display: flex;
            justify-content: flex-end;
            align-items: center;
            min-height: 52px;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.qj-top-nav-brand) button {{
            min-height: 2.15rem;
            padding: 0.35rem 0.5rem;
            background: transparent !important;
            border: 0 !important;
            border-radius: 6px !important;
            box-shadow: none !important;
            color: var(--qj-muted) !important;
            font-size: 0.88rem;
            font-weight: 780;
            white-space: nowrap;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.qj-top-nav-brand) button:hover {{
            color: var(--qj-text) !important;
            background: rgba(23, 50, 77, 0.04) !important;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.qj-top-nav-brand) button[data-testid="stBaseButton-primary"] {{
            color: var(--qj-text) !important;
            background: var(--qj-primary-soft) !important;
            border-bottom: 2px solid var(--qj-primary) !important;
        }}

        /* Each supplied illustration is a complete banner, with no text overlaid. */
        .qj-page-hero {{
            width: 100%;
            height: 138px;
            margin: 0 0 0.85rem;
            overflow: hidden;
            border: 1px solid #E1EDF2;
            border-radius: 10px;
            box-shadow: 0 8px 28px rgba(23, 50, 77, 0.08);
            position: relative;
        }}
        .qj-page-hero::after {{
            border: 1px solid rgba(255, 255, 255, 0.68);
            border-radius: 9px;
            content: "";
            inset: 5px;
            pointer-events: none;
            position: absolute;
        }}
        .qj-page-hero img {{
            display: block;
            width: 100% !important;
            height: 100% !important;
            object-fit: cover;
            object-position: center;
            border-radius: 10px;
        }}
        /* Career/housing illustrations are presented as cropped page banners. */
        .qj-page-hero.qj-page-hero-original {{
            background: #eef7f8;
            height: clamp(125px, 10vw, 155px);
        }}
        .qj-page-hero.qj-page-hero-original img {{
            height: 100% !important;
            max-height: none;
            object-fit: cover;
            object-position: center 18%;
            width: 100% !important;
        }}
        .qj-page-hero.qj-page-hero-housing {{
            height: clamp(125px, 10vw, 155px);
        }}
        .qj-page-hero-fallback {{
            background:
                radial-gradient(circle at 82% 22%, rgba(255, 255, 255, 0.72), transparent 28%),
                linear-gradient(112deg, var(--qj-primary-soft), rgba(255, 255, 255, 0.9));
        }}
        .qj-visually-hidden {{
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }}
        .qj-career-header,
        .qj-policy-header,
        .qj-housing-page-intro {{
            margin: 0 0 0.7rem;
        }}
        .qj-page-intro {{
            max-width: 48rem;
            color: var(--qj-muted);
            font-size: 0.98rem;
            line-height: 1.5;
        }}
        .qj-column-heading {{
            min-height: 44px;
            display: flex;
            align-items: flex-end;
            margin: 0 0 12px 0;
            padding: 0;
        }}
        .qj-column-heading h2,
        .qj-column-heading h3 {{
            margin: 0;
            padding: 0;
            line-height: 1.15;
        }}
        @media (max-width: 1440px) {{
            .qj-page-hero {{ height: 132px; }}
        }}

        /* Navigation, selectors, and actions share the same quiet, rounded treatment. */
        div[data-testid="stSegmentedControl"] {{ margin-bottom: 0.9rem; }}
        div[data-testid="stSegmentedControl"] button {{
            border-color: var(--qj-line);
            border-radius: 999px;
            min-height: 2.5rem;
            padding-inline: 0.95rem;
            transition: background 150ms ease, border-color 150ms ease, box-shadow 150ms ease;
        }}
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] {{
            background: var(--qj-primary-soft) !important;
            border-color: var(--qj-primary) !important;
            color: var(--qj-text) !important;
            box-shadow: 0 3px 10px rgba(23, 50, 77, 0.07);
        }}
        div[data-testid="stSegmentedControl"] button[data-checked="true"] {{
            background: var(--qj-primary-soft) !important;
            border-color: var(--qj-primary) !important;
            color: var(--qj-text) !important;
            box-shadow: 0 3px 10px rgba(23, 50, 77, 0.07);
        }}
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        div[data-testid="stTextInput"] input {{
            border-color: var(--qj-line);
            border-radius: var(--qj-radius-control);
            box-shadow: 0 1px 2px rgba(37, 61, 72, 0.035);
        }}
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within,
        div[data-testid="stTextInput"] input:focus {{
            border-color: var(--qj-primary);
            box-shadow: 0 0 0 3px var(--qj-primary-soft);
        }}
        div[data-testid="stButton"] button,
        div[data-testid="stFormSubmitButton"] button {{
            background: var(--qj-primary);
            border-color: var(--qj-primary);
            border-radius: var(--qj-radius-control);
            color: #ffffff;
            box-shadow: 0 4px 10px rgba(37, 61, 72, 0.10);
        }}
        div[data-testid="stButton"] button:hover,
        div[data-testid="stFormSubmitButton"] button:hover {{
            background: var(--qj-primary);
            border-color: var(--qj-primary);
            filter: brightness(0.94);
        }}
        div[data-testid="stButton"] button:focus-visible,
        div[data-testid="stFormSubmitButton"] button:focus-visible {{
            box-shadow: 0 0 0 3px var(--qj-primary-soft);
        }}
        .st-key-career_explore_button button,
        [class*="st-key-career_evidence_button_"] button {{
            background: #EAF6FF !important;
            border-color: #BDE7FF !important;
            color: #257FBE !important;
            box-shadow: none !important;
        }}
        .st-key-career_explore_button button:hover,
        [class*="st-key-career_evidence_button_"] button:hover {{
            background: #D7F0FF !important;
            border-color: #93D6FF !important;
            filter: none;
        }}
        .st-key-career_explore_button button:focus-visible,
        [class*="st-key-career_evidence_button_"] button:focus-visible {{
            box-shadow: 0 0 0 3px rgba(59, 167, 245, 0.22) !important;
        }}
        div[data-testid="stRadio"] {{
            margin-top: 0.7rem;
            transform: none;
            text-align: left;
        }}
        div[data-testid="stRadio"] div[role="radiogroup"] {{
            background: rgba(255, 255, 255, 0.78);
            border-color: var(--qj-line);
            border-radius: 16px;
        }}
        div[data-testid="stRadio"] div[role="radiogroup"] label {{
            border-color: var(--qj-line);
            border-radius: 999px;
        }}
        div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {{
            background: var(--qj-primary-soft);
            border-color: var(--qj-primary);
            box-shadow: 0 3px 10px rgba(23, 50, 77, 0.07);
        }}

        /* Shared surface system: cards, metrics, badges, and low-priority evidence notes. */
        .qj-panel, .qj-card, .qj-top1-card, .qj-compact-card,
        .qj-overview-card, .qj-comparison-bar, .qj-comparison-card,
        .qj-life-detail-card, .qj-policy-panel, .qj-policy-detail,
        .qj-career-preset, .qj-career-empty, .qj-career-card,
        .qj-career-policy-card, .qj-transition-map, .qj-transition-node,
        .qj-job-card {{
            background: var(--qj-surface);
            border-color: var(--qj-line);
            border-radius: var(--qj-radius-card);
            box-shadow: var(--qj-shadow);
        }}
        .qj-overview-card {{
            background: var(--qj-surface) !important;
            border-color: var(--qj-line) !important;
        }}
        .qj-panel, .qj-policy-panel, .qj-policy-detail, .qj-transition-map {{
            padding: clamp(0.95rem, 1.8vw, 1.2rem);
        }}
        .qj-metric, .qj-top1-metrics div, .qj-life-metric-grid div,
        .qj-policy-metric-grid div {{
            background: var(--qj-primary-soft);
            border-color: var(--qj-primary-border);
            border-radius: 12px;
        }}
        .qj-summary-strip, .qj-life-detail-card, .qj-career-preset,
        .qj-career-card, .qj-job-card {{ border-left-color: var(--qj-primary); }}
        .qj-career-card, .qj-transition-node {{ border-top-color: var(--qj-primary); }}
        .qj-career-card-high-reuse {{ border-top-color: var(--qj-primary-ink); }}
        .qj-career-card-partial-reuse {{ border-top-color: var(--qj-primary); }}
        .qj-career-card-major-reskilling, .qj-career-policy-card {{ border-top-color: var(--qj-primary); border-left-color: var(--qj-primary); }}
        .qj-career-card-data-scientists {{
            border-color: #B99A58;
            border-top-color: #B99A58;
            border-left-color: #B99A58;
        }}
        .st-key-housing_mode_card_0,
        .st-key-housing_mode_card_0 [data-testid="stVerticalBlockBorderWrapper"] {{ border-color: #78B995 !important; }}
        .st-key-housing_mode_card_1,
        .st-key-housing_mode_card_1 [data-testid="stVerticalBlockBorderWrapper"] {{ border-color: #6EA7C7 !important; }}
        .st-key-housing_mode_card_2,
        .st-key-housing_mode_card_2 [data-testid="stVerticalBlockBorderWrapper"] {{ border-color: #E8A05A !important; }}
        .st-key-housing_mode_card_3,
        .st-key-housing_mode_card_3 [data-testid="stVerticalBlockBorderWrapper"] {{ border-color: #A98BC8 !important; }}
        .qj-transition-origin, .qj-path-conclusion, .qj-skill-chip {{
            background: var(--qj-primary-soft);
            border-color: var(--qj-primary-border);
            color: var(--qj-text);
        }}
        .qj-transition-target, .qj-job-source a {{ color: var(--qj-primary-ink); }}
        .qj-transition-arrow {{ background: linear-gradient(90deg, var(--qj-primary), var(--qj-primary-border)); }}
        .qj-transition-arrow::after {{ border-left-color: var(--qj-primary-border); }}
        .qj-career-badge, .qj-job-review {{
            background: var(--qj-accent-pink-soft);
            border-color: var(--qj-accent-pink);
            color: var(--qj-accent-pink-ink);
        }}
        .qj-note, .qj-section-note, .qj-geocode-note {{
            color: var(--qj-muted);
            font-size: 0.78rem;
            line-height: 1.55;
        }}
        .qj-map-provenance {{
            background: var(--qj-primary-soft);
            border-color: var(--qj-primary-border);
            border-left-color: var(--qj-primary);
            border-radius: var(--qj-radius-control);
            color: var(--qj-primary-ink);
            font-size: 0.82rem;
        }}
        div[data-testid="stExpander"] {{
            border: 1px solid var(--qj-line);
            border-radius: var(--qj-radius-control);
            background: rgba(255, 255, 255, 0.68);
        }}
        div[data-testid="stExpander"] summary {{
            color: var(--qj-muted);
            font-size: 0.88rem;
            font-weight: 720;
        }}
        .stTabs [data-baseweb="tab"] {{
            color: var(--qj-muted);
        }}
        .stTabs [data-baseweb="tab"][aria-selected="true"] {{
            color: var(--qj-text) !important;
            border-bottom-color: var(--qj-primary) !important;
        }}
        .stTabs [data-baseweb="tab-highlight"] {{
            background-color: var(--qj-primary) !important;
        }}
        div[data-testid="stMetric"] {{
            background: var(--qj-surface);
            border: 1px solid var(--qj-line);
            border-radius: var(--qj-radius-card);
            box-shadow: var(--qj-shadow);
            padding: 0.8rem 0.9rem;
        }}
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {{ color: var(--qj-primary); }}
        .qj-policy-alert, .qj-policy-warning {{
            background: var(--qj-primary-soft);
            border-color: var(--qj-primary-border);
            color: var(--qj-text);
        }}
        iframe {{ border-radius: var(--qj-radius-card); }}

        /* Housing Phase 2A: a calmer, clearer entry flow and recommendation overview. */
        .qj-housing-page-intro {{
            margin: 0 0 0.7rem;
        }}
        .qj-housing-eyebrow,
        .qj-section-eyebrow,
        .qj-housing-view-eyebrow {{
            color: var(--qj-primary-ink);
            font-size: 0.74rem;
            font-weight: 850;
            letter-spacing: 0.075em;
            text-transform: uppercase;
        }}
        .qj-housing-page-intro .qj-header-title {{
            color: #245542;
            font-size: clamp(2.15rem, 3.35vw, 3.4rem);
            font-weight: 880;
            line-height: 1.05;
            margin: 0.3rem 0 0.45rem;
        }}
        .qj-housing-page-intro .qj-subtitle {{
            color: #5d7469;
            font-size: 1.02rem;
            margin: 0;
        }}
        .qj-housing-workflow-title {{
            color: var(--qj-text);
            font-size: 1.1rem;
            font-weight: 850;
            margin: 0.1rem 0 0.16rem;
        }}
        .qj-housing-workflow-copy {{
            color: var(--qj-muted);
            font-size: 0.84rem;
            line-height: 1.5;
            margin-bottom: 0.15rem;
        }}
        .qj-housing-setting-note {{
            color: #61766c;
            font-size: 0.76rem;
            line-height: 1.45;
            margin: 0.08rem 0 0.18rem;
        }}
        .qj-housing-setting-note span {{
            color: var(--qj-muted);
        }}
        .qj-geocode-note {{
            align-items: baseline;
            background: var(--qj-primary-soft);
            border: 1px solid var(--qj-primary-border);
            border-radius: var(--qj-radius-control);
            color: #365e4d;
            display: flex;
            flex-wrap: wrap;
            gap: 0.2rem 0.48rem;
            margin-top: 0.15rem;
            padding: 0.52rem 0.68rem;
        }}
        .qj-geocode-detail {{
            color: var(--qj-muted);
            font-size: 0.72rem;
        }}
        .qj-housing-view-switch {{
            background: rgba(255, 255, 255, 0.84);
            border: 1px solid var(--qj-line);
            border-radius: var(--qj-radius-card);
            box-shadow: var(--qj-shadow);
            margin: 0.25rem 0 0.1rem;
            padding: 1rem 1.05rem;
        }}
        .qj-housing-view-title {{
            color: #245542;
            font-size: clamp(1.45rem, 2.05vw, 2.05rem);
            font-weight: 880;
            line-height: 1.15;
            margin: 0.28rem 0 0.22rem;
        }}
        .qj-housing-view-copy {{
            color: var(--qj-muted);
            font-size: 0.86rem;
            line-height: 1.5;
        }}
        .qj-overview-section-head {{
            margin: 2.25rem 0 0.3rem;
        }}
        .qj-section-title {{
            color: var(--qj-text);
            font-size: clamp(1.45rem, 2.1vw, 1.85rem);
            font-weight: 880;
            letter-spacing: -0.022em;
            line-height: 1.18;
            margin-top: 0.22rem;
        }}
        .qj-section-copy {{
            color: var(--qj-muted);
            font-size: 0.88rem;
            line-height: 1.55;
            margin-top: 0.32rem;
        }}
        .qj-overview-card {{
            background: #ffffff !important;
            border: 1px solid var(--qj-line) !important;
            border-top: 4px solid var(--qj-mode-color) !important;
            box-shadow: 0 5px 16px rgba(23, 50, 77, 0.055);
            min-height: 236px;
            padding: 1.05rem;
        }}
        .qj-overview-card-top {{
            align-items: center;
            display: flex;
            justify-content: space-between;
            gap: 0.5rem;
        }}
        .qj-overview-mode {{
            color: var(--qj-mode-color);
            font-size: 0.84rem;
            margin: 0;
        }}
        .qj-overview-mode .qj-dot {{
            background: var(--qj-mode-color);
            height: 0.62rem;
            width: 0.62rem;
        }}
        .qj-overview-rank {{
            background: var(--qj-mode-soft);
            border-radius: 999px;
            color: var(--qj-mode-color);
            font-size: 0.7rem;
            font-weight: 850;
            line-height: 1;
            padding: 0.3rem 0.48rem;
        }}
        .qj-overview-title {{
            font-size: 1.28rem;
            line-height: 1.2;
            margin: 0.68rem 0 0.14rem;
        }}
        .qj-overview-location {{
            color: var(--qj-muted);
            font-size: 0.75rem;
            line-height: 1.35;
            min-height: 1.05rem;
        }}
        .qj-overview-grid {{
            align-items: stretch;
            border-top: 1px solid #edf2ef;
            gap: 0;
            margin: 0.78rem 0 0.7rem;
            padding-top: 0.7rem;
        }}
        .qj-overview-grid > div {{
            min-width: 0;
        }}
        .qj-overview-grid > div + div {{
            border-left: 1px solid #e8efeb;
            padding-left: 0.65rem;
        }}
        .qj-overview-grid span {{
            font-size: 0.7rem;
        }}
        .qj-overview-grid b {{
            font-size: 1rem;
            line-height: 1.25;
            margin-top: 0.1rem;
        }}
        .qj-overview-primary-metric b {{
            color: #245542;
            font-size: 1.22rem;
        }}
        .qj-overview-grid small {{
            color: var(--qj-muted);
            font-size: 0.65rem;
            font-weight: 720;
            margin-left: 0.14rem;
        }}
        .qj-overview-copy {{
            border-top: 1px solid #f0f4f2;
            color: #5b6d64;
            font-size: 0.76rem;
            line-height: 1.48;
            padding-top: 0.55rem;
        }}
        .qj-overview-copy span {{
            color: var(--qj-muted);
            display: block;
            font-size: 0.67rem;
            font-weight: 820;
            letter-spacing: 0.045em;
            margin-bottom: 0.08rem;
            text-transform: uppercase;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.qj-overview-map-head) {{
            background: rgba(255, 255, 255, 0.9);
            border-color: var(--qj-line);
            border-radius: var(--qj-radius-card);
            box-shadow: var(--qj-shadow);
            margin-top: 1.55rem;
            padding: 0.25rem;
        }}
        .qj-overview-map-head {{
            padding: 0.2rem 0 0.35rem;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.qj-overview-map-head) div[data-testid="stSegmentedControl"] {{
            margin: 0.5rem 0 0;
        }}
        .qj-map-provenance {{
            font-size: 0.76rem;
            margin: 0.35rem 0 0.72rem;
            padding: 0.56rem 0.7rem;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.qj-overview-map-head) iframe {{
            border: 1px solid var(--qj-line);
        }}
        @media (max-width: 720px) {{
            .stApp [data-testid="stAppViewContainer"] .main .block-container,
            .block-container {{
                margin: 0 !important;
                padding: 1.05rem 0.65rem 2rem !important;
                width: 100% !important;
            }}
            .qj-header-title {{ font-size: 2rem; }}
            .qj-page-hero {{
                height: 112px;
                margin-bottom: 0.8rem;
                border-radius: 9px;
            }}
            .qj-page-hero img {{ border-radius: 9px; }}
            .qj-housing-view-switch {{ margin-top: 0.9rem; }}
            .qj-overview-card {{ min-height: auto; }}
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.qj-top-nav-brand) [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; }}
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.qj-top-nav-brand) [data-testid="column"] {{ min-width: 100% !important; }}
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.qj-top-nav-brand) [data-testid="stHorizontalBlock"]:has(button) {{ justify-content: flex-start; min-height: auto; padding-bottom: 0.55rem; }}
            div[data-testid="stSegmentedControl"] button {{ padding-inline: 0.7rem; }}
            .qj-career-policy-grid {{ grid-template-columns: 1fr 1fr; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        """
        <style>
        /* Career exploration result page */
        .qj-career-header {
            margin: 0 auto 1rem;
        }
        .qj-career-title-row {
            align-items: center;
            display: flex;
            gap: 2rem;
            justify-content: space-between;
        }
        .qj-career-title-row h1 {
            color: #17324D;
            font-size: clamp(1.75rem, 2.4vw, 2.5rem);
            line-height: 1.15;
            margin: 0 0 0.3rem;
        }
        .qj-career-steps {
            align-items: center;
            display: flex;
            flex: 0 0 auto;
            gap: 0.75rem;
            list-style: none;
            margin: 0;
            padding: 0;
        }
        .qj-career-steps li {
            align-items: center;
            color: #718096;
            display: flex;
            font-size: 0.84rem;
            font-weight: 750;
            gap: 0.38rem;
            white-space: nowrap;
        }
        .qj-career-steps li:not(:last-child)::after {
            background: #CBD5E1;
            content: "";
            height: 1px;
            margin-left: 0.38rem;
            width: 1.2rem;
        }
        .qj-career-steps span,
        .qj-career-comparison th span {
            align-items: center;
            background: #E9EEF2;
            border-radius: 999px;
            display: inline-flex;
            height: 1.7rem;
            justify-content: center;
            min-width: 1.7rem;
        }
        .qj-career-steps li.is-active {
            color: #126B4D;
        }
        .qj-career-steps li.is-active span {
            background: #198A63;
            color: #FFFFFF;
        }
        .st-key-career_filter_panel > div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF;
            border: 1px solid #DCE7E2;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(23, 50, 77, 0.05);
            padding: 0.9rem 1rem 0.75rem;
        }
        .st-key-career_filter_panel div[data-testid="stButton"] button,
        .st-key-career_reanalyze_button button {
            min-height: 2.55rem;
        }
        .qj-career-scenario {
            align-items: center;
            border-top: 1px solid #E7EEEB;
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.65rem;
            padding-top: 0.65rem;
        }
        .qj-career-scenario-label {
            background: transparent !important;
            border: 0 !important;
            color: #64748B !important;
            font-weight: 750 !important;
            padding-left: 0 !important;
        }
        .qj-career-scenario span {
            background: #FFF0F1;
            border: 1px solid #F5CFD3;
            border-radius: 999px;
            color: #9B3F4A;
            font-size: 0.78rem;
            font-weight: 700;
            padding: 0.25rem 0.55rem;
        }
        .qj-career-data-scope {
            margin: 0.25rem 0 0.75rem;
        }
        .qj-result-summary {
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            background: rgba(255, 255, 255, 0.86);
            border: 1px solid #DCE7E2;
            border-radius: 12px;
            box-shadow: 0 5px 18px rgba(23, 50, 77, 0.055);
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            margin: 0.1rem 0 0.8rem;
            overflow: hidden;
        }
        .qj-result-summary-item {
            min-width: 0;
            padding: 0.62rem 0.78rem 0.66rem;
            position: relative;
        }
        .qj-result-summary-item + .qj-result-summary-item {
            border-left: 1px solid #E6EEEA;
        }
        .qj-result-summary-item::before {
            background: var(--qj-primary);
            border-radius: 999px;
            content: "";
            height: 3px;
            left: 0.78rem;
            position: absolute;
            top: 0;
            width: 1.6rem;
        }
        .qj-result-summary-item span,
        .qj-result-summary-item small {
            color: #718096;
            display: block;
            font-size: 0.68rem;
            line-height: 1.3;
        }
        .qj-result-summary-item b {
            color: #17324D;
            display: block;
            font-size: 0.9rem;
            font-weight: 850;
            line-height: 1.25;
            margin: 0.16rem 0 0.12rem;
            overflow-wrap: anywhere;
        }
        .qj-career-result-summary .qj-result-summary-item:nth-child(2)::before {
            background: #F58BA7;
        }
        .qj-career-result-summary .qj-result-summary-item:nth-child(3)::before {
            background: #6EA7C7;
        }
        .qj-career-result-summary .qj-result-summary-item:nth-child(4)::before {
            background: #E8A05A;
        }
        [class*="st-key-career_result_card_"] > div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF;
            border: 1px solid #DCE7E2;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(23, 50, 77, 0.045);
            margin-bottom: 0.7rem;
            padding: 0.85rem 0.95rem 0.8rem;
            transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
        }
        [class*="st-key-career_result_card_"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: #A8D2BF;
            box-shadow: 0 8px 24px rgba(23, 50, 77, 0.085);
            transform: translateY(-1px);
        }
        .st-key-career_result_card_1 > div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #198A63;
            box-shadow: 0 3px 13px rgba(25, 138, 99, 0.11);
        }
        .qj-career-result-card {
            align-items: stretch;
            display: grid;
            gap: 0.9rem;
            grid-template-columns: minmax(0, 1.05fr) minmax(410px, 1.15fr);
        }
        .qj-career-result-copy {
            min-width: 0;
        }
        .qj-career-rank-row {
            align-items: center;
            display: flex;
            gap: 0.5rem;
            margin-bottom: 0.3rem;
        }
        .qj-career-rank {
            align-items: center;
            background: #E3EEE9;
            border-radius: 999px;
            color: #17324D;
            display: inline-flex;
            font-size: 0.82rem;
            font-weight: 850;
            height: 1.65rem;
            justify-content: center;
            width: 1.65rem;
        }
        .qj-career-result-card-primary .qj-career-rank {
            background: #198A63;
            color: #FFFFFF;
        }
        .qj-career-path-badge {
            background: #FFF0F1;
            border: 1px solid #F5CFD3;
            border-radius: 999px;
            color: #9B3F4A;
            display: inline-flex;
            font-size: 0.74rem;
            font-weight: 800;
            padding: 0.22rem 0.52rem;
        }
        .qj-career-result-card h3 {
            font-size: 1.15rem;
            line-height: 1.25;
            margin: 0;
            overflow-wrap: anywhere;
        }
        .qj-career-english {
            color: #64748B;
            font-size: 0.76rem;
            line-height: 1.35;
            margin-top: 0.12rem;
            overflow-wrap: anywhere;
        }
        .qj-career-result-card p {
            color: #465A67;
            font-size: 0.84rem;
            line-height: 1.45;
            margin: 0.42rem 0 0.48rem;
        }
        .qj-career-skill-heading {
            align-items: center;
            color: #64748B;
            display: flex;
            font-size: 0.72rem;
            justify-content: space-between;
            margin-bottom: 0.26rem;
        }
        .qj-career-skill-heading b {
            color: #465A67;
        }
        .qj-career-skill-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.3rem;
        }
        .qj-career-skill-list span {
            background: #EDF8F3;
            border: 1px solid #CBE6D9;
            border-radius: 6px;
            color: #126B4D;
            font-size: 0.71rem;
            font-weight: 700;
            padding: 0.23rem 0.45rem;
        }
        .qj-career-skill-list .qj-career-skill-empty {
            background: #F7F9FA;
            border-color: #E3E8EB;
            color: #64748B;
        }
        .qj-career-result-metrics {
            align-self: stretch;
            border-left: 1px solid #E4ECE8;
            display: grid;
            gap: 0;
            grid-template-columns: repeat(4, minmax(82px, 1fr));
            padding-left: 0.9rem;
        }
        .qj-career-result-metric {
            align-items: center;
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 3.45rem;
            padding: 0.35rem;
            text-align: center;
        }
        .qj-career-result-metric:not(:last-child) {
            border-right: 1px solid #EDF1EF;
        }
        .qj-career-result-metric span {
            color: #718096;
            font-size: 0.82rem;
            font-weight: 700;
        }
        .qj-career-metric-heading {
            align-items: center;
            display: flex;
            gap: 0.28rem;
            justify-content: center;
        }
        .qj-career-metric-icon {
            fill: none;
            height: 1.18rem;
            stroke: #126B4D;
            stroke-linecap: round;
            stroke-linejoin: round;
            stroke-width: 1.65;
            width: 1.18rem;
        }
        .qj-career-result-metric b {
            color: #17324D;
            font-size: 1.05rem;
            line-height: 1.3;
            margin-top: 0.18rem;
        }
        .qj-career-metric-dots {
            align-items: center;
            display: flex;
            gap: 0.2rem;
            margin-top: 0.28rem;
        }
        .qj-career-metric-dots i {
            background: #DCE4E7;
            border-radius: 999px;
            display: block;
            height: 0.47rem;
            width: 0.47rem;
        }
        .qj-career-metric-dots i.is-active {
            background: #198A63;
        }
        [class*="st-key-career_result_card_"] [data-testid="stButton"] button {
            min-height: 2.2rem;
            padding: 0.38rem 0.65rem;
        }
        [class*="st-key-career_evidence_button_"] button {
            background: #FFFFFF !important;
            border-color: #198A63 !important;
            color: #126B4D !important;
            box-shadow: none !important;
        }
        [class*="st-key-career_evidence_button_"] button:hover {
            background: #EDF8F3 !important;
            border-color: #126B4D !important;
        }
        .qj-career-comparison {
            background: #FFFFFF;
            border: 1px solid #DCE7E2;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(23, 50, 77, 0.05);
            padding: 1rem;
            position: static;
            top: auto;
        }
        div[data-testid="stHorizontalBlock"]:has(.st-key-career_comparison_anchor) {
            align-items: flex-start !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.st-key-career_comparison_anchor) > div[data-testid="column"] {
            align-self: flex-start !important;
        }
        .st-key-career_comparison_anchor {
            margin-top: 0 !important;
        }
        .qj-career-comparison-title {
            color: #17324D;
            font-size: 1.2rem;
            font-weight: 850;
        }
        .qj-career-comparison-subtitle {
            color: #64748B;
            font-size: 0.78rem;
            margin: 0.18rem 0 0.7rem;
        }
        .qj-career-table-scroll {
            border: 1px solid #E3EAE7;
            border-radius: 9px;
            overflow-x: auto;
        }
        .qj-career-table-scroll:focus-visible {
            box-shadow: 0 0 0 3px #EDF8F3;
            outline: 2px solid #198A63;
        }
        .qj-career-comparison table {
            border-collapse: collapse;
            font-size: 0.72rem;
            table-layout: fixed;
            min-width: 420px;
            width: 100%;
        }
        .qj-career-comparison th,
        .qj-career-comparison td {
            border-bottom: 1px solid #E9EFEC;
            border-right: 1px solid #E9EFEC;
            padding: 0.55rem 0.42rem;
            text-align: center;
            vertical-align: middle;
        }
        .qj-career-comparison th:last-child,
        .qj-career-comparison td:last-child {
            border-right: 0;
        }
        .qj-career-comparison thead th {
            background: #F5F8F7;
            color: #354B5B;
            font-weight: 800;
            height: 5.25rem;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }
        .qj-career-comparison th:first-child {
            width: 28%;
        }
        .qj-career-comparison thead th:not(:first-child) {
            width: 24%;
        }
        .qj-career-comparison tbody th,
        .qj-career-comparison tbody td {
            height: 4.5rem;
        }
        .qj-career-comparison tbody th {
            color: #354B5B;
            line-height: 1.35;
            text-align: left;
        }
        .qj-career-comparison th span {
            display: flex;
            height: 1.35rem;
            margin: 0 auto 0.22rem;
            min-width: 1.35rem;
            width: 1.35rem;
        }
        .qj-career-scale {
            align-items: center;
            display: flex;
            flex-direction: column;
            gap: 0.3rem;
            height: 100%;
            justify-content: center;
            line-height: 1.2;
        }
        .qj-career-scale > span:last-child {
            display: flex;
            gap: 0.18rem;
        }
        .qj-career-scale i {
            background: #DCE4E7;
            border-radius: 999px;
            display: block;
            height: 0.42rem;
            width: 0.42rem;
        }
        .qj-career-scale i.is-active {
            background: #198A63;
        }
        .qj-career-howto {
            background: #FFF9ED;
            border: 1px solid #F1DDAF;
            border-radius: 10px;
            color: #5C4A22;
            margin-top: 0.75rem;
            padding: 0.7rem 0.78rem;
        }
        .qj-career-howto b {
            color: #4A3B1C;
            font-size: 0.85rem;
        }
        .qj-career-howto p,
        .qj-career-limit {
            font-size: 0.74rem;
            line-height: 1.45;
            margin: 0.22rem 0 0;
        }
        .qj-career-limit {
            color: #64748B;
            padding: 0.65rem 0.1rem 0;
        }
        .qj-career-next-actions {
            background: #FFFFFF;
            border: 1px solid #DCE7E2;
            border-radius: 12px;
            color: #354B5B;
            line-height: 1.55;
            margin: 0;
            padding: 0.8rem 1rem 0.8rem 2rem;
        }
        .qj-career-skeleton {
            display: grid;
            gap: 0.7rem;
            margin: 0.7rem 0;
        }
        .qj-career-skeleton span {
            animation: qj-career-pulse 1.15s ease-in-out infinite alternate;
            background: #E8EFEC;
            border-radius: 12px;
            display: block;
            height: 7.5rem;
        }
        @keyframes qj-career-pulse {
            from { opacity: 0.55; }
            to { opacity: 1; }
        }
        @media (prefers-reduced-motion: reduce) {
            .qj-career-skeleton span { animation: none; }
        }
        @media (max-width: 1100px) {
            .qj-career-title-row {
                align-items: flex-start;
                flex-direction: column;
                gap: 0.8rem;
            }
            .qj-career-result-card {
                grid-template-columns: 1fr;
            }
            .qj-career-result-metrics {
                border-left: 0;
                border-top: 1px solid #E4ECE8;
                padding-left: 0;
                padding-top: 0.4rem;
            }
            .qj-career-comparison {
                position: static;
            }
        }
        @media (max-width: 900px) {
            div[data-testid="stHorizontalBlock"]:has(.qj-career-comparison) {
                flex-wrap: wrap;
            }
            div[data-testid="stHorizontalBlock"]:has(.qj-career-comparison) > div[data-testid="column"] {
                flex: 1 1 100% !important;
                min-width: 100% !important;
                width: 100% !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.st-key-career_reanalyze_button) {
                flex-wrap: wrap;
            }
            div[data-testid="stHorizontalBlock"]:has(.st-key-career_reanalyze_button) > div[data-testid="column"] {
                flex: 1 1 42% !important;
                min-width: 15rem !important;
            }
        }
        @media (max-width: 720px) {
            .qj-career-steps {
                align-items: flex-start;
                flex-direction: column;
                gap: 0.4rem;
            }
            .qj-career-steps li::after {
                display: none;
            }
            .qj-career-result-metrics {
                grid-template-columns: 1fr 1fr;
            }
            .qj-career-result-metric:nth-child(2) {
                border-right: 0;
            }
            .qj-career-result-metric:nth-child(-n+2) {
                border-bottom: 1px solid #EDF1EF;
            }
            div[data-testid="stHorizontalBlock"]:has(.st-key-career_reanalyze_button) > div[data-testid="column"] {
                flex-basis: 100% !important;
                min-width: 100% !important;
            }
            .qj-career-scenario {
                align-items: flex-start;
                flex-direction: column;
            }
        }

        /* Housing recommendation result page */
        .qj-housing-results-title {
            margin: 0.1rem 0 0.7rem;
        }
        .qj-housing-results-title h1 {
            color: #17324D;
            font-size: clamp(1.75rem, 2.2vw, 2.35rem);
            line-height: 1.15;
            margin: 0 0 0.28rem;
        }
        .qj-housing-results-title p {
            color: #64748B;
            margin: 0;
        }
        .st-key-housing_condition_summary > div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF;
            border: 1px solid #DCE7E2;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(23, 50, 77, 0.045);
            padding: 0.75rem 0.9rem;
        }
        .qj-housing-condition-list {
            align-items: center;
            display: grid;
            gap: 0;
            grid-template-columns: 1.3fr 1fr 0.78fr 0.9fr;
        }
        .qj-housing-condition-list > div {
            border-right: 1px solid #E5ECE9;
            min-width: 0;
            padding: 0.15rem 0.85rem;
        }
        .qj-housing-condition-list > div:last-child {
            border-right: 0;
        }
        .qj-housing-condition-item {
            align-items: center;
            display: flex;
            gap: 0.62rem;
        }
        .qj-housing-condition-item svg {
            fill: none;
            flex: 0 0 auto;
            height: 1.45rem;
            stroke: #17324D;
            stroke-linecap: round;
            stroke-linejoin: round;
            stroke-width: 1.8;
            width: 1.45rem;
        }
        .qj-housing-condition-item p {
            margin: 0;
            min-width: 0;
        }
        .qj-housing-condition-list span {
            color: #718096;
            display: block;
            font-size: 0.72rem;
            margin-bottom: 0.16rem;
        }
        .qj-housing-condition-list b {
            color: #17324D;
            display: flex;
            flex-wrap: wrap;
            font-size: 0.9rem;
            font-weight: 800;
            gap: 0.32rem;
            overflow-wrap: anywhere;
        }
        .qj-housing-condition-list i {
            background: #EDF8F3;
            border: 1px solid #CBE6D9;
            border-radius: 999px;
            color: #126B4D;
            font-size: 0.75rem;
            font-style: normal;
            padding: 0.2rem 0.48rem;
        }
        .qj-housing-condition-editor-title {
            border-top: 1px solid #E5ECE9;
            color: #354B5B;
            font-size: 0.9rem;
            font-weight: 800;
            margin-top: 0.55rem;
            padding-top: 0.7rem;
        }
        .qj-housing-fixed-condition {
            min-height: 2.5rem;
            padding-bottom: 0.22rem;
        }
        .qj-housing-fixed-condition > span {
            color: #52646B;
            display: block;
            font-size: 0.8rem;
            margin-bottom: 0.36rem;
        }
        .qj-housing-fixed-condition b {
            display: flex;
            flex-wrap: wrap;
            gap: 0.3rem;
        }
        .qj-housing-fixed-condition i {
            background: #EDF8F3;
            border: 1px solid #CBE6D9;
            border-radius: 999px;
            color: #126B4D;
            font-size: 0.72rem;
            font-style: normal;
            padding: 0.2rem 0.45rem;
        }
        [class*="st-key-housing_result_card_"] > div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF;
            border: 1px solid #DCE7E2;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(23, 50, 77, 0.04);
            box-sizing: border-box;
            height: 276px;
            padding: 0.75rem;
            transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
        }
        [class*="st-key-housing_result_card_"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            box-shadow: 0 8px 24px rgba(23, 50, 77, 0.08);
            transform: translateY(-1px);
        }
        .st-key-housing_result_card_saving > div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #78B995;
        }
        .st-key-housing_result_card_balanced > div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #6EA7C7;
        }
        .st-key-housing_result_card_commute > div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #E8A05A;
        }
        .st-key-housing_result_card_lifestyle > div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #D97972;
        }
        [class*="st-key-housing_result_card_"] > div[data-testid="stVerticalBlockBorderWrapper"]:has(.is-selected) {
            box-shadow: 0 0 0 2px rgba(66, 201, 142, 0.11), 0 3px 12px rgba(23, 50, 77, 0.06);
        }
        .qj-housing-mode-card {
            min-height: 187px;
        }
        .qj-housing-card-head {
            align-items: center;
            display: flex;
            gap: 0.45rem;
            justify-content: space-between;
        }
        .qj-housing-mode-label {
            align-items: center;
            display: flex;
            font-size: 1.5rem;
            font-weight: 850;
            gap: 0.34rem;
        }
        .qj-housing-mode-card--saving .qj-housing-mode-label,
        .qj-housing-mode-card--saving .qj-housing-card-metrics b {
            color: #4D936C;
        }
        .qj-housing-mode-card--balanced .qj-housing-mode-label,
        .qj-housing-mode-card--balanced .qj-housing-card-metrics b {
            color: #397FA8;
        }
        .qj-housing-mode-card--commute .qj-housing-mode-label,
        .qj-housing-mode-card--commute .qj-housing-card-metrics b {
            color: #B66D15;
        }
        .qj-housing-mode-card--lifestyle .qj-housing-mode-label,
        .qj-housing-mode-card--lifestyle .qj-housing-card-metrics b {
            color: #C2534D;
        }
        .qj-housing-mode-label svg {
            border-radius: 999px;
            box-sizing: content-box;
            fill: none;
            height: 1.5rem;
            padding: 0.48rem;
            stroke: currentColor;
            stroke-linecap: round;
            stroke-linejoin: round;
            stroke-width: 1.6;
            width: 1.5rem;
        }
        .qj-housing-mode-card--saving .qj-housing-mode-label svg {
            background: #EAF6EF;
        }
        .qj-housing-mode-card--balanced .qj-housing-mode-label svg {
            background: #EAF4FA;
        }
        .qj-housing-mode-card--commute .qj-housing-mode-label svg {
            background: #FFF1E3;
        }
        .qj-housing-mode-card--lifestyle .qj-housing-mode-label svg {
            background: #FFF0EE;
        }
        .qj-housing-selected-badge {
            background: #EAF6EF;
            border: 1px solid #78B995;
            border-radius: 999px;
            color: #28784F;
            font-size: 0.68rem;
            font-weight: 800;
            padding: 0.18rem 0.42rem;
            white-space: nowrap;
        }
        .qj-housing-mode-card h3 {
            color: #17324D;
            font-size: 1.1rem;
            line-height: 1.25;
            margin: 0.48rem 0 0.28rem;
            min-height: 1.4rem;
            overflow-wrap: anywhere;
        }
        .qj-housing-mode-card p,
        .qj-housing-card-empty {
            color: #64748B;
            font-size: 0.75rem;
            line-height: 1.4;
            margin: 0 0 0.6rem;
            min-height: 3.15rem;
        }
        .qj-housing-card-metrics {
            border: 1px solid #E6ECE9;
            border-radius: 9px;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            overflow: hidden;
        }
        .qj-housing-card-metrics > div {
            min-width: 0;
            padding: 0.48rem 0.38rem;
            text-align: center;
        }
        .qj-housing-card-metrics > div + div {
            border-left: 1px solid #E6ECE9;
        }
        .qj-housing-card-metrics span {
            color: #718096;
            display: block;
            font-size: 0.65rem;
        }
        .qj-housing-card-metrics b {
            display: block;
            font-size: 0.78rem;
            line-height: 1.25;
            margin-top: 0.15rem;
            overflow-wrap: anywhere;
        }
        [class*="st-key-housing_result_card_"] button {
            background: #FFFFFF !important;
            border-color: currentColor !important;
            min-height: 2.05rem;
        }
        .st-key-housing_result_card_saving button {
            color: #4D936C !important;
        }
        .st-key-housing_result_card_balanced button {
            color: #397FA8 !important;
        }
        .st-key-housing_result_card_commute button {
            color: #B66D15 !important;
        }
        .st-key-housing_result_card_lifestyle button {
            color: #C2534D !important;
        }
        [class*="st-key-housing_result_card_"] button:hover:not(:disabled) {
            background: #F8FBFA !important;
        }
        .qj-housing-plan-summary {
            background: #F7FAF8;
            border: 1px solid #DCE7E2;
            border-radius: 10px;
            margin-top: 0.5rem;
            padding: 0.68rem 0.78rem;
        }
        .qj-housing-plan-summary span {
            color: #718096;
            display: block;
            font-size: 0.7rem;
        }
        .qj-housing-plan-summary b {
            color: #17324D;
        }
        .qj-housing-plan-summary p {
            color: #52646B;
            font-size: 0.76rem;
            line-height: 1.4;
            margin: 0.35rem 0 0;
        }
        .qj-housing-data-limit {
            color: #64748B;
            font-size: 0.76rem;
            margin-top: 0.8rem;
            text-align: center;
        }
        @media (max-width: 1100px) {
            .qj-result-summary {
                grid-template-columns: 1fr 1fr;
            }
            .qj-result-summary-item:nth-child(3) {
                border-left: 0;
                border-top: 1px solid #E6EEEA;
            }
            .qj-result-summary-item:nth-child(4) {
                border-top: 1px solid #E6EEEA;
            }
            div[data-testid="stHorizontalBlock"]:has(.qj-housing-plan-summary) {
                flex-wrap: wrap;
            }
            div[data-testid="stHorizontalBlock"]:has(.qj-housing-plan-summary) > div[data-testid="column"] {
                flex: 1 1 100% !important;
                min-width: 100% !important;
                width: 100% !important;
            }
        }
        @media (max-width: 720px) {
            .qj-page-hero.qj-page-hero-housing {
                height: 120px;
            }
            .qj-housing-condition-list {
                grid-template-columns: 1fr;
            }
            .qj-result-summary {
                grid-template-columns: 1fr;
            }
            .qj-result-summary-item + .qj-result-summary-item {
                border-left: 0;
                border-top: 1px solid #E6EEEA;
            }
            .qj-result-summary-item {
                padding-block: 0.72rem;
            }
            .qj-housing-condition-list > div {
                border-bottom: 1px solid #E5ECE9;
                border-right: 0;
                padding: 0.48rem 0;
            }
            .qj-housing-condition-list > div:last-child {
                border-bottom: 0;
                padding-bottom: 0;
            }
            div[data-testid="stHorizontalBlock"]:has(.qj-housing-mode-card) {
                flex-wrap: wrap;
            }
            div[data-testid="stHorizontalBlock"]:has(.qj-housing-mode-card) > div[data-testid="column"] {
                flex: 1 1 100% !important;
                min-width: 100% !important;
                width: 100% !important;
            }
            [class*="st-key-housing_result_card_"] > div[data-testid="stVerticalBlockBorderWrapper"] {
                height: auto;
                min-height: auto;
            }
            .qj-housing-mode-card {
                min-height: auto;
            }
        }
        @media (prefers-reduced-motion: reduce) {
            [class*="st-key-career_result_card_"] > div[data-testid="stVerticalBlockBorderWrapper"],
            [class*="st-key-housing_result_card_"] > div[data-testid="stVerticalBlockBorderWrapper"] {
                transition: none;
            }
            [class*="st-key-career_result_card_"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover,
            [class*="st-key-housing_result_card_"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
                transform: none;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_selected_radio_style() -> None:
    """Keep Housing mode navigation within the Housing page theme."""
    st.markdown(
        """
        <style>
        div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
            background: var(--qj-primary-soft);
            border-color: var(--qj-primary);
            color: var(--qj-text);
            box-shadow: 0 3px 10px rgba(23, 50, 77, 0.07);
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {
            color: var(--qj-text);
            font-weight: 850;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
