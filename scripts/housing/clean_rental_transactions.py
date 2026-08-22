from __future__ import annotations

import json

import pandas as pd

from common import INTERIM_HOUSING, OUTPUT_HOUSING, RENTAL_CSV, ensure_output_dirs, pct, roc_yyyymmdd_to_iso


OUTPUT_CSV = INTERIM_HOUSING / "ntpc_rental_independent_suite_clean.csv"
REPORT_MD = OUTPUT_HOUSING / "data_cleaning_report.md"


def classify_social_housing(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip()
    if not text:
        return "其他 / unknown"
    if "社會住宅" in text or "包租" in text:
        return "社宅 / 包租代管"
    if text.startswith("一般"):
        return "一般租賃"
    return "其他 / unknown"


def main() -> None:
    ensure_output_dirs()
    df = pd.read_csv(RENTAL_CSV, encoding="utf-8-sig", dtype=str)

    report: dict[str, object] = {
        "source_file": RENTAL_CSV.as_posix(),
        "encoding": "utf-8-sig",
        "original_rows": int(len(df)),
        "original_columns": int(len(df.columns)),
        "duplicate_rows": int(df.duplicated().sum()),
        "columns": list(df.columns),
        "missing_values": {col: int(df[col].isna().sum()) for col in df.columns},
        "unique_values": {
            "district": df["district"].value_counts(dropna=False).astype(int).to_dict(),
            "rps01": df["rps01"].value_counts(dropna=False).astype(int).to_dict(),
            "rps29": df["rps29"].value_counts(dropna=False).astype(int).to_dict(),
            "rps34": df["rps34"].value_counts(dropna=False).astype(int).to_dict(),
        },
    }

    candidates = df[df["rps29"] == "獨立套房"].copy()
    report["independent_suite_rows"] = int(len(candidates))

    candidates["rent"] = pd.to_numeric(candidates["rps22_amountsunitdollars"], errors="coerce")
    candidates["unit_price"] = pd.to_numeric(candidates["rps23_amountsunitdollars"], errors="coerce")
    candidates["area"] = pd.to_numeric(candidates["rps15_area"], errors="coerce")
    candidates["rental_date"] = candidates["rps07_yyymmddroc"].map(roc_yyyymmdd_to_iso)
    candidates["social_housing_flag"] = candidates["rps34"].map(classify_social_housing)

    quality_counts = {
        "missing_district": int(candidates["district"].isna().sum()),
        "missing_rent": int(candidates["rent"].isna().sum()),
        "rent_le_zero": int((candidates["rent"] <= 0).fillna(False).sum()),
        "missing_unit_price": int(candidates["unit_price"].isna().sum()),
        "unit_price_le_zero": int((candidates["unit_price"] <= 0).fillna(False).sum()),
        "missing_area": int(candidates["area"].isna().sum()),
        "area_le_zero": int((candidates["area"] <= 0).fillna(False).sum()),
        "blank_rental_date": int((candidates["rental_date"] == "").sum()),
    }
    report["quality_counts_before_exclusion"] = quality_counts

    exclusion_masks = {
        "missing_district": candidates["district"].isna(),
        "missing_or_nonpositive_rent": candidates["rent"].isna() | (candidates["rent"] <= 0),
        "missing_or_nonpositive_unit_price": candidates["unit_price"].isna() | (candidates["unit_price"] <= 0),
        "missing_or_nonpositive_area": candidates["area"].isna() | (candidates["area"] <= 0),
        "pure_parking_or_land_transaction": ~candidates["rps01"].isin(["租賃房屋", "租賃房屋+車位"]),
    }

    keep = pd.Series(True, index=candidates.index)
    exclusions = []
    for reason, mask in exclusion_masks.items():
        step_excluded = keep & mask
        exclusions.append({"reason": reason, "excluded_rows": int(step_excluded.sum())})
        keep &= ~mask

    clean = candidates[keep].copy()
    report["exclusion_steps"] = exclusions
    report["final_rows"] = int(len(clean))
    report["social_housing_counts_final"] = clean["social_housing_flag"].value_counts(dropna=False).astype(int).to_dict()
    report["social_housing_share_final"] = {
        key: float(value / len(clean)) for key, value in report["social_housing_counts_final"].items()
    }
    report["final_district_counts"] = clean["district"].value_counts().astype(int).to_dict()

    output_columns = [
        "district",
        "rps01",
        "rps28",
        "rps29",
        "rps34",
        "rent",
        "unit_price",
        "area",
        "rental_date",
        "social_housing_flag",
        "rps07_yyymmddroc",
        "rps31",
        "rps11",
        "rps12",
        "rps13",
        "rps16_quantity",
        "rps17_quantity",
        "rps18_quantity",
    ]
    clean = clean.rename(columns={"rps29": "rental_type"})
    output_columns = ["rental_type" if col == "rps29" else col for col in output_columns]
    clean[output_columns].to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

    lines = [
        "# Housing Data Cleaning Report",
        "",
        "Source: `data/raw/housing/ntpc_rental_transactions_2026-08-21.csv`",
        "",
        "Raw files were read only. No raw file contents were modified.",
        "",
        "## Raw CSV",
        "",
        f"- Encoding: `utf-8-sig`",
        f"- Original rows: {report['original_rows']:,}",
        f"- Columns: {report['original_columns']}",
        f"- Duplicate rows: {report['duplicate_rows']:,}",
        "",
        "## Key Columns",
        "",
        "- `rps22_amountsunitdollars`: total rent (`總價元` in repository schema)",
        "- `rps23_amountsunitdollars`: unit price per square meter (`單價元平方公尺` in repository schema)",
        "- `rps15_area`: building area in square meters (`建物移轉總面積平方公尺` in repository schema)",
        "- `rps07_yyymmddroc`: transaction date in ROC `YYYMMDD` format",
        "- `rps29`: rental type",
        "- `rps34`: rental management / social housing indicator",
        "",
        "## Rental Type Filter",
        "",
        f"- Independent suite rows (`rps29 == 獨立套房`): {report['independent_suite_rows']:,}",
        "",
        "## Quality Counts Before Exclusion",
        "",
    ]
    for key, value in quality_counts.items():
        lines.append(f"- {key}: {value:,}")

    lines += ["", "## Exclusion Steps", ""]
    for step in exclusions:
        lines.append(f"- {step['reason']}: {step['excluded_rows']:,}")

    lines += [
        "",
        f"Final retained rows: {report['final_rows']:,}",
        "",
        "## Social Housing / Rental Management",
        "",
    ]
    for key, value in report["social_housing_counts_final"].items():
        share = report["social_housing_share_final"][key]
        lines.append(f"- {key}: {value:,} ({pct(share)})")

    lines += [
        "",
        "Social housing / rental management rows are retained for analysis. They are not removed from the cleaned interim file.",
        "",
        "## Machine-Readable Cleaning Stats",
        "",
        "```json",
        json.dumps(report, ensure_ascii=False, indent=2),
        "```",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {OUTPUT_CSV} rows={len(clean)}")
    print(f"Wrote {REPORT_MD}")


if __name__ == "__main__":
    main()
