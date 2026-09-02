from __future__ import annotations

import math
from typing import Any

import pandas as pd


TREND_CONFIG: dict[str, float] = {
    "stable_threshold_pct": 5.0,
}

FORECAST_READINESS_RULES: list[tuple[int, str, str]] = [
    (12, "seasonal_candidate", "較適合評估季節性分析"),
    (6, "experimental_forecasting_possible", "可進行實驗性預測準備"),
    (3, "trend_only", "可做初步趨勢"),
    (0, "insufficient", "尚不足"),
]


def percent_change(current: object, previous: object) -> float | None:
    current_value = pd.to_numeric(pd.Series([current]), errors="coerce").iloc[0]
    previous_value = pd.to_numeric(pd.Series([previous]), errors="coerce").iloc[0]
    if pd.isna(current_value) or pd.isna(previous_value) or float(previous_value) == 0:
        return None
    return float((float(current_value) - float(previous_value)) / float(previous_value) * 100)


def absolute_change(current: object, previous: object) -> float | None:
    current_value = pd.to_numeric(pd.Series([current]), errors="coerce").iloc[0]
    previous_value = pd.to_numeric(pd.Series([previous]), errors="coerce").iloc[0]
    if pd.isna(current_value) or pd.isna(previous_value):
        return None
    return float(current_value) - float(previous_value)


def trend_label(percent: object, threshold: float | None = None) -> str | None:
    threshold = TREND_CONFIG["stable_threshold_pct"] if threshold is None else threshold
    value = pd.to_numeric(pd.Series([percent]), errors="coerce").iloc[0]
    if pd.isna(value):
        return None
    if float(value) > threshold:
        return "上升"
    if float(value) < -threshold:
        return "下降"
    return "持平"


def demand_growth_signal(openings_pct: object, postings_pct: object = None, company_pct: object = None) -> str | None:
    values = [
        pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        for value in [openings_pct, postings_pct, company_pct]
    ]
    clean = [float(value) for value in values if not pd.isna(value)]
    if not clean:
        return None
    score = sum(clean) / len(clean)
    label = trend_label(score)
    if label == "上升":
        return "需求增加"
    if label == "下降":
        return "需求下降"
    return "相對穩定"


def forecast_readiness(period_count: int) -> dict[str, Any]:
    for minimum, key, label in FORECAST_READINESS_RULES:
        if period_count >= minimum:
            return {
                "period_count": int(period_count),
                "level": key,
                "label": label,
                "note": "此分類只代表資料量準備度，不是預測品質保證。",
            }
    raise AssertionError("unreachable")


def clean_json_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        if value.is_integer():
            return int(value)
    if hasattr(value, "item") and callable(value.item):
        return clean_json_value(value.item())
    if isinstance(value, dict):
        return {key: clean_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_json_value(item) for item in value]
    return value
