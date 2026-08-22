from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_HOUSING = PROJECT_ROOT / "data" / "raw" / "housing"
INTERIM_HOUSING = PROJECT_ROOT / "data" / "interim" / "housing"
PROCESSED_HOUSING = PROJECT_ROOT / "data" / "processed" / "housing"
OUTPUT_HOUSING = PROJECT_ROOT / "outputs" / "housing"

RENTAL_CSV = RAW_HOUSING / "ntpc_rental_transactions_2026-08-21.csv"
MOI_RENT_TOTAL_PDF = RAW_HOUSING / "moi_rent_total_quartiles_2026-03.pdf"
MOI_UNIT_PRICE_PDF = RAW_HOUSING / "moi_rent_unit_price_quartiles_2026-03.pdf"


def ensure_output_dirs() -> None:
    INTERIM_HOUSING.mkdir(parents=True, exist_ok=True)
    PROCESSED_HOUSING.mkdir(parents=True, exist_ok=True)
    OUTPUT_HOUSING.mkdir(parents=True, exist_ok=True)


def roc_yyyymmdd_to_iso(value: object) -> str:
    text = "" if value is None else str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) != 7:
        return ""
    year = int(digits[:3]) + 1911
    return f"{year:04d}-{digits[3:5]}-{digits[5:7]}"


def pct(value: float | int | None) -> str:
    if value is None:
        return ""
    return f"{value:.1%}"
