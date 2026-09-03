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
            padding: 0.86rem 0.9rem;
            box-shadow: 0 1px 2px rgba(36, 50, 56, 0.04);
            min-height: 112px;
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
            font-size: 1.6rem;
            font-weight: 920;
            line-height: 1.05;
            margin: 0.24rem 0;
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
