# Unit Price Validation

## Finding

Official unit price and transaction unit price are not directly comparable as currently stored.

## MOI Table 3

- Source file: `data/raw/housing/moi_rent_unit_price_quartiles_2026-03.pdf`
- Topic: district-level rent unit-price quartiles.
- Unit confirmed from the Ministry of the Interior real-price rental query display: `元/坪`.
- Area denominator: total rental area in ping as presented by the MOI real-price rental service.

## Transaction CSV

- Source file: `data/raw/housing/ntpc_rental_transactions_2026-08-21.csv`
- Repository schema maps `rps23_amountsunitdollars` to `單價元平方公尺`.
- Repository schema maps `rps15_area` to `建物移轉總面積平方公尺`.
- In the cleaned independent-suite records, `round(rent / area)` matches `unit_price` for 98.9% of rows.
- Median transaction unit price: 332 NTD/square meter.
- Median transaction area denominator: 42.78 square meters.

## Comparability Decision

Do not directly subtract or percentage-compare `official_median_unit_price` and `transaction_median_unit_price`.

Reason:

- `official_median_unit_price` is stored from MOI Table 3 in NTD/ping.
- `transaction_median_unit_price` is calculated from the raw CSV field in NTD/square meter.
- A direct difference would mix units and overstate the discrepancy by roughly the ping-to-square-meter conversion factor.

Future work can create explicit converted fields, for example `official_median_unit_price_sqm = official_median_unit_price / 3.305785`, if the team confirms the same area basis is appropriate.