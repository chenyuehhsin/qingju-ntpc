from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

from common import MOI_RENT_TOTAL_PDF, MOI_UNIT_PRICE_PDF, OUTPUT_HOUSING, RENTAL_CSV, ensure_output_dirs


def inspect_csv(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        row_count = sum(1 for _ in reader)

    full = pd.read_csv(path, encoding="utf-8-sig", dtype=str)

    columns_of_interest = [
        "district",
        "rps01",
        "rps15_area",
        "rps22_amountsunitdollars",
        "rps23_amountsunitdollars",
        "rps29",
        "rps34",
        "rps07_yyymmddroc",
        "rps31",
    ]
    profiles = {}
    for col in columns_of_interest:
        profiles[col] = {
            "missing": int(full[col].isna().sum()),
            "unique_count": int(full[col].nunique(dropna=True)),
            "top_values": full[col].value_counts(dropna=False).head(20).astype(int).to_dict(),
        }

    return {
        "filename": path.name,
        "path": path.as_posix(),
        "format": "csv",
        "size_bytes": path.stat().st_size,
        "encoding": "utf-8-sig",
        "row_count": row_count,
        "column_count": len(header),
        "columns": header,
        "duplicate_rows": int(full.duplicated().sum()),
        "readable": True,
        "profiles": profiles,
    }


def inspect_pdf(path: Path) -> dict[str, object]:
    reader = PdfReader(str(path))
    return {
        "filename": path.name,
        "path": path.as_posix(),
        "format": "pdf",
        "size_bytes": path.stat().st_size,
        "page_count": len(reader.pages),
        "readable": True,
    }


def main() -> None:
    ensure_output_dirs()
    inspection = {
        "raw_files": [
            inspect_csv(RENTAL_CSV),
            inspect_pdf(MOI_RENT_TOTAL_PDF),
            inspect_pdf(MOI_UNIT_PRICE_PDF),
        ]
    }
    output = OUTPUT_HOUSING / "raw_data_inspection.json"
    output.write_text(json.dumps(inspection, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(inspection["raw_files"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
