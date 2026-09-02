from __future__ import annotations

import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_CSV = PROCESSED_DIR / "youth_employment_map.csv"


def find_files(root: Path, suffixes: Iterable[str]) -> list[Path]:
    if not root.exists():
        return []
    suffix_set = {suffix.lower() for suffix in suffixes}
    return sorted(path for path in root.rglob("*") if path.suffix.lower() in suffix_set)


def read_csv(path: Path) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "cp950", "big5"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    return pd.read_csv(path)


def read_processed(path: Path = PROCESSED_CSV) -> pd.DataFrame:
    return pd.read_csv(path)


def read_xml_rows(path: Path, row_tag: str = "ROW") -> tuple[pd.DataFrame, dict[str, str | None]]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return read_loose_cdata_xml_rows(path), {"parser": "loose_cdata"}
    records: list[dict[str, str | None]] = []
    metadata = {
        child.tag: child.text
        for child in root
        if child.tag != row_tag and len(list(child)) == 0
    }

    rows = root.findall(row_tag)
    if not rows:
        child_tags = [child.tag for child in root if len(list(child)) > 0]
        if child_tags:
            row_tag = child_tags[0]
            rows = root.findall(row_tag)

    for row in rows:
        records.append({child.tag: child.text for child in row})

    return pd.DataFrame(records), metadata


def read_loose_cdata_xml_rows(path: Path) -> pd.DataFrame:
    text = path.read_text(encoding="utf-8", errors="replace")
    records: list[dict[str, str]] = []
    for block in re.findall(r"<Data>(.*?)</Data>", text, flags=re.DOTALL):
        record: dict[str, str] = {}
        for tag, value in re.findall(r"<([^<>/]+)><!\[CDATA\[(.*?)\]\]></\1>", block, flags=re.DOTALL):
            record[tag] = value.strip()
        if record:
            records.append(record)
    return pd.DataFrame(records)


def read_json_rows(path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict) and isinstance(payload.get("responseData"), list):
        metadata = {key: value for key, value in payload.items() if key != "responseData"}
        return pd.DataFrame(payload["responseData"]), metadata

    if isinstance(payload, list):
        return pd.DataFrame(payload), {}

    return pd.DataFrame(), {"unrecognized_json_shape": True}


def find_geojson(root: Path = PROJECT_ROOT) -> list[Path]:
    return find_files(root, [".geojson", ".json"])


def load_geojson(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
