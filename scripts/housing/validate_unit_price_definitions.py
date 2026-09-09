from __future__ import annotations

import pandas as pd

from common import INTERIM_HOUSING, OUTPUT_HOUSING, ensure_output_dirs


CLEAN_CSV = INTERIM_HOUSING / "ntpc_rental_independent_suite_clean.csv"
REPORT_MD = OUTPUT_HOUSING / "unit_price_validation.md"


def main() -> None:
    ensure_output_dirs()
    clean = pd.read_csv(CLEAN_CSV)
    calculated = (clean["rent"] / clean["area"]).round(0)
    exact_match_share = float((calculated == clean["unit_price"]).mean())
    median_transaction_unit_price = float(clean["unit_price"].median())
    median_transaction_area_sqm = float(clean["area"].median())

    lines = [
        "# Unit Price Validation",
        "",
        "## Finding",
        "",
        "Official unit price and transaction unit price are not directly comparable as currently stored.",
        "",
        "## MOI Table 3",
        "",
        "- Source file: `data/raw/housing/moi_rent_unit_price_quartiles_2026-03.pdf`",
        "- Topic: district-level rent unit-price quartiles.",
        "- Unit confirmed from the Ministry of the Interior real-price rental query display: `元/坪`.",
        "- Area denominator: total rental area in ping as presented by the MOI real-price rental service.",
        "",
        "## Transaction CSV",
        "",
        "- Source file: `data/raw/housing/ntpc_rental_transactions_2026-08-21.csv`",
        "- Repository schema maps `rps23_amountsunitdollars` to `單價元平方公尺`.",
        "- Repository schema maps `rps15_area` to `建物移轉總面積平方公尺`.",
        f"- In the cleaned independent-suite records, `round(rent / area)` matches `unit_price` for {exact_match_share:.1%} of rows.",
        f"- Median transaction unit price: {median_transaction_unit_price:,.0f} NTD/square meter.",
        f"- Median transaction area denominator: {median_transaction_area_sqm:,.2f} square meters.",
        "",
        "## Comparability Decision",
        "",
        "Do not directly subtract or percentage-compare `official_median_unit_price` and `transaction_median_unit_price`.",
        "",
        "Reason:",
        "",
        "- `official_median_unit_price` is stored from MOI Table 3 in NTD/ping.",
        "- `transaction_median_unit_price` is calculated from the raw CSV field in NTD/square meter.",
        "- A direct difference would mix units and overstate the discrepancy by roughly the ping-to-square-meter conversion factor.",
        "",
        "Future work can create explicit converted fields, for example `official_median_unit_price_sqm = official_median_unit_price / 3.305785`, if the team confirms the same area basis is appropriate.",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT_MD}")


if __name__ == "__main__":
    main()
