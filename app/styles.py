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
        .block-container {
            max-width: min(1840px, calc(100vw - 18px));
            padding-top: 1.1rem;
            padding-bottom: 2.5rem;
            padding-left: clamp(0.45rem, 1vw, 0.9rem);
            padding-right: clamp(0.45rem, 1vw, 0.9rem);
        }
        h1, h2, h3 {
            color: var(--qj-text);
            letter-spacing: 0;
        }
        .qj-subtitle {
            color: var(--qj-muted);
            font-size: 1.08rem;
            margin-top: -0.45rem;
            margin-bottom: 0.85rem;
        }
        .qj-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.65rem;
            margin: 0.45rem 0 0.85rem 0;
        }
        .qj-chip {
            background: #ffffff;
            border: 1px solid #d9e0e2;
            border-radius: 10px;
            padding: 0.60rem 0.86rem;
            min-width: 132px;
        }
        .qj-chip-label {
            color: #7a878b;
            font-size: 0.75rem;
            line-height: 1;
        }
        .qj-chip-value {
            color: var(--qj-text);
            font-weight: 700;
            font-size: 1rem;
            line-height: 1.35;
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
            gap: 1.0rem;
        }
        .qj-note {
            color: #69777d;
            font-size: 0.78rem;
            line-height: 1.6;
        }
        .qj-section-note {
            color: #65747a;
            font-size: 0.92rem;
            margin-top: -0.35rem;
            margin-bottom: 0.55rem;
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
        div[data-testid="stRadio"] > div {
            gap: 0.55rem;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] {
            background: rgba(255, 255, 255, 0.70);
            border: 1px solid #dde5e6;
            border-radius: 16px;
            padding: 0.36rem;
            display: inline-flex;
            flex-wrap: wrap;
            gap: 0.45rem;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label {
            background: #ffffff;
            border: 1px solid #d7e0e2;
            border-radius: 999px;
            padding: 0.62rem 1.05rem;
            min-width: 9.5rem;
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
            font-size: 0.98rem;
        }
        iframe {
            border-radius: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
