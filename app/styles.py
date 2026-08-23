from __future__ import annotations

import streamlit as st


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --qj-bg: #f7f6f1;
            --qj-text: #243238;
            --qj-muted: #65747a;
            --qj-line: #dde5e6;
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
        .qj-control-row + div[data-testid="stHorizontalBlock"] {
            max-width: 680px;
            margin-left: 0;
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
        .qj-section-note {
            color: #65747a;
            font-size: 0.92rem;
            margin-top: -0.35rem;
            margin-bottom: 0.55rem;
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
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_selected_radio_style(color: str, soft_color: str) -> None:
    st.markdown(
        f"""
        <style>
        div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {{
            background: {soft_color};
            border-color: {color};
            color: #243238;
            box-shadow: 0 4px 12px rgba(36, 50, 56, 0.10);
        }}
        div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {{
            color: #243238;
            font-weight: 850;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
