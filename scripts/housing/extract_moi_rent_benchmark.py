from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pdfplumber

from common import MOI_RENT_TOTAL_PDF, MOI_UNIT_PRICE_PDF, OUTPUT_HOUSING, PROCESSED_HOUSING, ensure_output_dirs


OUTPUT_CSV = PROCESSED_HOUSING / "moi_independent_suite_rent_benchmark.csv"
VALIDATION_CSV = OUTPUT_HOUSING / "moi_benchmark_extraction_validation.csv"
VALIDATION_MD = OUTPUT_HOUSING / "moi_benchmark_extraction_validation.md"


@dataclass
class Row:
    page: int
    top: float
    text: str
    seq: str
    city: str
    district: str
    rental_type: str
    building_age_type: str
    floor_type: str
    contract_count: str
    q1: str
    median: str
    q3: str


TOTAL_COLUMN_RANGES = {
    "seq": (30, 55),
    "city": (55, 110),
    "district": (110, 165),
    "rental_type": (165, 235),
    "building_age_type": (235, 290),
    "floor_type": (290, 345),
    "contract_count": (345, 405),
    "q1": (405, 460),
    "median": (460, 520),
    "q3": (520, 590),
}

UNIT_COLUMN_RANGES = {
    "seq": (45, 85),
    "city": (85, 130),
    "district": (130, 180),
    "rental_type": (180, 235),
    "building_age_type": (235, 290),
    "floor_type": (290, 345),
    "contract_count": (345, 395),
    "q1": (395, 445),
    "median": (445, 495),
    "q3": (495, 550),
}


def group_words_into_rows(words: list[dict[str, object]], tolerance: float = 3.0) -> list[list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    for word in sorted(words, key=lambda item: (float(item["top"]), float(item["x0"]))):
        top = float(word["top"])
        if not rows or abs(float(rows[-1]["top"]) - top) > tolerance:
            rows.append({"top": top, "words": [word]})
        else:
            rows[-1]["words"].append(word)
            count = len(rows[-1]["words"])
            rows[-1]["top"] = (float(rows[-1]["top"]) * (count - 1) + top) / count
    return [row["words"] for row in rows]


def cell(words: list[dict[str, object]], left: float, right: float, numeric: bool = False) -> str:
    selected = sorted(
        [word for word in words if left <= float(word["x0"]) < right],
        key=lambda item: float(item["x0"]),
    )
    text = "".join(str(word["text"]) for word in selected).strip()
    if numeric:
        text = text.replace(",", "").replace("，", "").replace(" ", "")
    return text


def parse_int(value: str) -> int | None:
    if not value or not re.fullmatch(r"\d+", value):
        return None
    return int(value)


def row_from_words(page: int, words: list[dict[str, object]], ranges: dict[str, tuple[int, int]]) -> Row:
    text = " ".join(str(word["text"]) for word in sorted(words, key=lambda item: float(item["x0"])))
    top = sum(float(word["top"]) for word in words) / len(words)
    return Row(
        page=page,
        top=top,
        text=text,
        seq=cell(words, *ranges["seq"]),
        city=cell(words, *ranges["city"]),
        district=cell(words, *ranges["district"]),
        rental_type=cell(words, *ranges["rental_type"]),
        building_age_type=cell(words, *ranges["building_age_type"]),
        floor_type=cell(words, *ranges["floor_type"]),
        contract_count=cell(words, *ranges["contract_count"], numeric=True),
        q1=cell(words, *ranges["q1"], numeric=True),
        median=cell(words, *ranges["median"], numeric=True),
        q3=cell(words, *ranges["q3"], numeric=True),
    )


def extract_rows(path: Path, ranges: dict[str, tuple[int, int]]) -> list[Row]:
    rows: list[Row] = []
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False)
            for row_words in group_words_into_rows(words):
                row = row_from_words(page_number, row_words, ranges)
                if any(token in row.text for token in ["表一", "表三", "序號", "縣市", "行政區", "分位"]):
                    continue
                rows.append(row)
    return rows


def nearest_district_label(target: Row, district_labels: list[Row]) -> tuple[str, str, float]:
    candidates = [row for row in district_labels if row.page == target.page]
    if not candidates:
        return "", "", 9999.0
    nearest = min(candidates, key=lambda row: abs(row.top - target.top))
    return nearest.city, nearest.district, abs(nearest.top - target.top)


def is_numeric_row(row: Row) -> bool:
    return all(parse_int(value) is not None for value in [row.contract_count, row.q1, row.median, row.q3])


def is_overall_row(row: Row) -> bool:
    return row.building_age_type == "不分類" and row.floor_type == "不分類"


def is_non_specific_numeric_label_row(row: Row) -> bool:
    age = row.building_age_type
    floor = row.floor_type
    text = row.text
    specific_age = any(token in age for token in ["0-5年", "6-30年", "30年以上"])
    specific_floor = any(token in floor for token in ["5樓以下", "6樓以上"])
    return is_numeric_row(row) and (not specific_age) and (not specific_floor) and "不分類" in text


def extract_independent_suite(path: Path, value_prefix: str) -> pd.DataFrame:
    ranges = UNIT_COLUMN_RANGES if value_prefix == "unit_price" else TOTAL_COLUMN_RANGES
    rows = extract_rows(path, ranges)
    row_indices = {id(row): index for index, row in enumerate(rows)}
    district_labels = [
        row
        for row in rows
        if row.city and row.district and row.city not in ["縣市"] and row.district not in ["行政區"]
    ]
    district_label_items = [(row_indices[id(row)], row) for row in district_labels]
    numeric_rows = [row for row in rows if is_numeric_row(row)]

    records: list[dict[str, object]] = []
    used_keys: set[tuple[int, float]] = set()
    for label in rows:
        if label.rental_type != "獨立套房":
            continue

        # In these PDFs, the rental-type label is vertically centered across
        # the group. The true "不分類 / 不分類" overall row is usually above the
        # visible "獨立套房" label, while the same line can contain a subgroup.
        label_index = row_indices[id(label)]
        previous_rental_label_indices = [
            row_indices[id(row)]
            for row in rows
            if row_indices[id(row)] < label_index and row.rental_type
        ]
        last_rental_label_index = max(previous_rental_label_indices) if previous_rental_label_indices else -1

        previous_candidates = [
            row
            for row in numeric_rows
            if row.page == label.page
            and row_indices[id(row)] > last_rental_label_index
            and row.top < label.top
            and label.top - row.top <= 95
            and is_overall_row(row)
        ]
        if previous_candidates:
            target = max(previous_candidates, key=lambda row: row.top)
        elif is_non_specific_numeric_label_row(label):
            target = label
        else:
            continue

        key = (target.page, round(target.top, 3))
        if key in used_keys:
            continue
        used_keys.add(key)

        # District labels are vertically centered too. Use row-order distance,
        # with a special case for page starts: page-leading rows usually continue
        # the previous district unless the next district label is only a few rows
        # away from the rental-type label.
        same_page_items = [(index, row) for index, row in district_label_items if row.page == label.page]
        previous_items = [(index, row) for index, row in district_label_items if index < label_index]
        next_items = [(index, row) for index, row in district_label_items if index > label_index]
        previous_item = max(previous_items, key=lambda item: item[0]) if previous_items else None
        next_item = min(next_items, key=lambda item: item[0]) if next_items else None

        if same_page_items and label_index < min(index for index, _row in same_page_items):
            if next_item and next_item[0] - label_index <= 3:
                chosen_index, chosen_row = next_item
            elif previous_item:
                chosen_index, chosen_row = previous_item
            else:
                chosen_index, chosen_row = next_item
        elif same_page_items:
            chosen_index, chosen_row = min(same_page_items, key=lambda item: abs(item[0] - label_index))
        elif previous_item:
            chosen_index, chosen_row = previous_item
        else:
            chosen_index, chosen_row = next_item

        city, district = chosen_row.city, chosen_row.district
        district_distance = abs(chosen_index - label_index)

        records.append(
            {
                "city": city,
                "district": district,
                "rental_type": "獨立套房",
                "building_age_type": "不分類",
                "floor_type": "不分類",
                "contract_count": int(target.contract_count),
                f"{value_prefix}_q1": int(target.q1),
                f"{value_prefix}_median": int(target.median),
                f"{value_prefix}_q3": int(target.q3),
                "source_pdf": path.name,
                "source_page": target.page,
                "source_top": round(target.top, 2),
                "district_label_distance": round(district_distance, 2),
                "extracted_text": target.text,
            }
        )

    df = pd.DataFrame(records)
    if df.empty:
        raise RuntimeError(f"No independent suite benchmark rows extracted from {path}")
    return df


def main() -> None:
    ensure_output_dirs()
    total = extract_independent_suite(MOI_RENT_TOTAL_PDF, "rent")
    unit = extract_independent_suite(MOI_UNIT_PRICE_PDF, "unit_price")

    desired_total = total[(total["city"] == "新北市") | ((total["city"] == "臺北市") & (total["district"] == "內湖區"))].copy()
    desired_unit = unit[(unit["city"] == "新北市") | ((unit["city"] == "臺北市") & (unit["district"] == "內湖區"))].copy()

    validation = pd.concat(
        [
            total.assign(table="rent_total"),
            unit.assign(table="unit_price"),
        ],
        ignore_index=True,
    )
    validation.to_csv(VALIDATION_CSV, index=False, encoding="utf-8")

    merged = desired_total.merge(
        desired_unit,
        on=["city", "district", "rental_type", "building_age_type", "floor_type"],
        how="outer",
        suffixes=("_total_pdf", "_unit_pdf"),
        indicator=True,
    )

    duplicate_keys = merged.duplicated(["city", "district"], keep=False)
    if duplicate_keys.any():
        raise RuntimeError("Duplicate city/district rows in MOI benchmark extraction:\n" + merged[duplicate_keys].to_string())

    if not ((merged["city"] == "臺北市") & (merged["district"] == "內湖區")).any():
        raise RuntimeError("Taipei Neihu baseline was not extracted from MOI benchmark PDFs.")

    if not (merged["_merge"] == "both").all():
        missing = merged[merged["_merge"] != "both"]
        raise RuntimeError("Rent total and unit price PDFs did not align for all desired rows:\n" + missing.to_string())

    merged["contract_count_match"] = merged["contract_count_total_pdf"] == merged["contract_count_unit_pdf"]
    output = pd.DataFrame(
        {
            "city": merged["city"],
            "district": merged["district"],
            "contract_count": merged["contract_count_total_pdf"].astype(int),
            "rent_q1": merged["rent_q1"].astype(int),
            "rent_median": merged["rent_median"].astype(int),
            "rent_q3": merged["rent_q3"].astype(int),
            "unit_price_q1": merged["unit_price_q1"].astype(int),
            "unit_price_median": merged["unit_price_median"].astype(int),
            "unit_price_q3": merged["unit_price_q3"].astype(int),
            "contract_count_match_between_pdfs": merged["contract_count_match"],
            "rent_total_pdf_page": merged["source_page_total_pdf"],
            "unit_price_pdf_page": merged["source_page_unit_pdf"],
        }
    ).sort_values(["city", "district"])

    output.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

    lines = [
        "# MOI Benchmark Extraction Validation",
        "",
        "Source files:",
        "",
        f"- `{MOI_RENT_TOTAL_PDF.as_posix()}`",
        f"- `{MOI_UNIT_PRICE_PDF.as_posix()}`",
        "",
        f"Extracted total-rent independent-suite rows across all cities: {len(total):,}",
        f"Extracted unit-price independent-suite rows across all cities: {len(unit):,}",
        f"Processed benchmark rows retained: {len(output):,}",
        f"New Taipei rows retained: {int((output['city'] == '新北市').sum()):,}",
        f"Taipei Neihu baseline retained: {int(((output['city'] == '臺北市') & (output['district'] == '內湖區')).sum()):,}",
        "",
        "Contract count match between total-rent PDF and unit-price PDF:",
        "",
        output["contract_count_match_between_pdfs"].value_counts(dropna=False).to_string(),
        "",
        "Rows with contract-count mismatch should be manually checked before using the benchmark as final evidence.",
    ]
    VALIDATION_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {OUTPUT_CSV} rows={len(output)}")
    print(f"Wrote {VALIDATION_CSV} rows={len(validation)}")
    print(f"Wrote {VALIDATION_MD}")
    print(output[["city", "district", "contract_count", "rent_median", "unit_price_median", "contract_count_match_between_pdfs"]].to_string(index=False))


if __name__ == "__main__":
    main()
