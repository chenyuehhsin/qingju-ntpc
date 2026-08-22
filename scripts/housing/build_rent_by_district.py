from __future__ import annotations

import pandas as pd

from common import INTERIM_HOUSING, PROCESSED_HOUSING, ensure_output_dirs


CLEAN_CSV = INTERIM_HOUSING / "ntpc_rental_independent_suite_clean.csv"
BENCHMARK_CSV = PROCESSED_HOUSING / "moi_independent_suite_rent_benchmark.csv"
OUTPUT_CSV = PROCESSED_HOUSING / "rent_by_district.csv"


def q1(series: pd.Series) -> float:
    return float(series.quantile(0.25))


def q3(series: pd.Series) -> float:
    return float(series.quantile(0.75))


def main() -> None:
    ensure_output_dirs()
    clean = pd.read_csv(CLEAN_CSV)
    benchmark = pd.read_csv(BENCHMARK_CSV)

    grouped = clean.groupby("district", dropna=False)
    transaction_stats = grouped.agg(
        transaction_record_count=("rent", "size"),
        transaction_rent_q1=("rent", q1),
        transaction_median_rent=("rent", "median"),
        transaction_rent_q3=("rent", q3),
        transaction_unit_price_q1=("unit_price", q1),
        transaction_median_unit_price=("unit_price", "median"),
        transaction_unit_price_q3=("unit_price", q3),
        social_housing_share=("social_housing_flag", lambda s: float((s == "社宅 / 包租代管").mean())),
    ).reset_index()
    transaction_stats.insert(0, "city", "新北市")

    non_social = clean[clean["social_housing_flag"] != "社宅 / 包租代管"]
    non_social_stats = (
        non_social.groupby("district", dropna=False)
        .agg(
            non_social_record_count=("rent", "size"),
            non_social_median_rent=("rent", "median"),
            non_social_median_unit_price=("unit_price", "median"),
        )
        .reset_index()
    )
    non_social_stats.insert(0, "city", "新北市")

    official = benchmark.rename(
        columns={
            "contract_count": "official_contract_count",
            "rent_q1": "official_rent_q1",
            "rent_median": "official_median_rent",
            "rent_q3": "official_rent_q3",
            "unit_price_q1": "official_unit_price_q1",
            "unit_price_median": "official_median_unit_price",
            "unit_price_q3": "official_unit_price_q3",
        }
    )

    keep_official_columns = [
        "city",
        "district",
        "official_contract_count",
        "official_rent_q1",
        "official_median_rent",
        "official_rent_q3",
        "official_unit_price_q1",
        "official_median_unit_price",
        "official_unit_price_q3",
        "contract_count_match_between_pdfs",
    ]
    result = official[keep_official_columns].merge(transaction_stats, on=["city", "district"], how="left")
    result = result.merge(non_social_stats, on=["city", "district"], how="left")

    result["rent_difference"] = result["transaction_median_rent"] - result["official_median_rent"]
    result["rent_difference_pct"] = result["rent_difference"] / result["official_median_rent"]
    ordered_columns = [
        "city",
        "district",
        "official_contract_count",
        "official_rent_q1",
        "official_median_rent",
        "official_rent_q3",
        "official_unit_price_q1",
        "official_median_unit_price",
        "official_unit_price_q3",
        "transaction_record_count",
        "transaction_rent_q1",
        "transaction_median_rent",
        "transaction_rent_q3",
        "transaction_unit_price_q1",
        "transaction_median_unit_price",
        "transaction_unit_price_q3",
        "social_housing_share",
        "non_social_record_count",
        "non_social_median_rent",
        "non_social_median_unit_price",
        "rent_difference",
        "rent_difference_pct",
        "contract_count_match_between_pdfs",
    ]
    result = result[ordered_columns].sort_values(["city", "district"])

    if result.duplicated(["city", "district"]).any():
        duplicates = result[result.duplicated(["city", "district"], keep=False)]
        raise RuntimeError("Duplicate city/district rows in rent_by_district:\n" + duplicates.to_string())

    result.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"Wrote {OUTPUT_CSV} rows={len(result)}")
    print(result[["city", "district", "official_median_rent", "transaction_median_rent", "social_housing_share"]].to_string(index=False))


if __name__ == "__main__":
    main()
