"""新北市行政區名稱標準化。"""

from __future__ import annotations

import re
from typing import Any


NEW_TAIPEI_DISTRICTS = (
    "板橋區", "三重區", "中和區", "永和區", "新莊區", "新店區", "樹林區",
    "鶯歌區", "三峽區", "淡水區", "汐止區", "瑞芳區", "土城區", "蘆洲區",
    "五股區", "泰山區", "林口區", "深坑區", "石碇區", "坪林區", "三芝區",
    "石門區", "八里區", "平溪區", "雙溪區", "貢寮區", "金山區", "萬里區", "烏來區",
)

_DISTRICT_SET = set(NEW_TAIPEI_DISTRICTS)
_ALIASES = {district.removesuffix("區"): district for district in NEW_TAIPEI_DISTRICTS}
_ALIASES.update({district: district for district in NEW_TAIPEI_DISTRICTS})


def normalize_district(value: Any) -> str | None:
    """以明確別名比對統一為「○○區」；非新北 29 區回傳 None。"""
    if value is None:
        return None
    text = re.sub(r"\s+", "", str(value)).replace("臺", "台")
    if not text or text.lower() == "nan":
        return None
    for prefix in ("新北市", "台北縣"):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    return _ALIASES.get(text)


def is_new_taipei_district(value: Any) -> bool:
    return normalize_district(value) in _DISTRICT_SET
