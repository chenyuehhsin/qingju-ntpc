# Housing Exploration Summary

Scope: independent suites only.

Sources:

- New Taipei rental transaction individual records: `data/raw/housing/ntpc_rental_transactions_2026-08-21.csv`
- MOI rent total quartiles PDF: `data/raw/housing/moi_rent_total_quartiles_2026-03.pdf`
- MOI rent unit-price quartiles PDF: `data/raw/housing/moi_rent_unit_price_quartiles_2026-03.pdf`

Transaction-derived period observed in cleaned records: 2025-02-11 to 2026-06-10.
Official benchmark statistic period: 2026-03.

## Q1. Lower / Higher Official Median Rents

Lowest New Taipei official median rents:

- 三芝區: 6,800 NTD
- 萬里區: 8,500 NTD
- 三峽區: 10,000 NTD
- 淡水區: 10,000 NTD
- 泰山區: 10,000 NTD

Highest New Taipei official median rents:

- 蘆洲區: 18,500 NTD
- 林口區: 18,000 NTD
- 五股區: 16,000 NTD
- 板橋區: 16,000 NTD
- 新莊區: 15,700 NTD

## Q2. Total Rent vs Unit Rent

Across the 20 extracted New Taipei districts, official median total rent and official median unit rent have Pearson correlation 0.71. Lower total rent often aligns with lower unit rent, but not always.

Notable example: 泰山區 has low official median total rent but high unit rent, which suggests smaller unit sizes may be part of the total-rent story.

## Q3. Neihu Baseline

Taipei Neihu official median rent baseline: 19,500 NTD; official median unit rent: 2,070 NTD/ping.

- 汐止區: 14,000 NTD, -5,500 NTD vs Neihu
- 中和區: 15,000 NTD, -4,500 NTD vs Neihu
- 永和區: 15,000 NTD, -4,500 NTD vs Neihu
- 新店區: 15,500 NTD, -4,000 NTD vs Neihu
- 板橋區: 16,000 NTD, -3,500 NTD vs Neihu

## Q4. Individual Records vs Official Benchmark

Largest rent-median differences. These are differences, not errors by themselves:

- 三重區: transaction median is 4,000 NTD higher than official; transaction sample=757, social housing share=61.7%
- 鶯歌區: transaction median is 3,000 NTD lower than official; transaction sample=34, social housing share=97.1%
- 八里區: transaction median is 2,000 NTD higher than official; transaction sample=59, social housing share=98.3%
- 新店區: transaction median is 2,000 NTD higher than official; transaction sample=433, social housing share=61.9%
- 三峽區: transaction median is 2,000 NTD higher than official; transaction sample=253, social housing share=90.5%

Possible explanation / hypothesis for larger differences:

- The official benchmark and individual records may use different effective periods.
- The individual-record sample has very high social housing / rental-management share in many districts.
- District-level samples differ in size.
- Unit size, building age, and floor composition may differ across sources even within independent suites.

## Q5. Readiness for Rent x Commute-Time Analysis

The housing side is usable for a first rent x commute-time exploration, with caution: official benchmark rows cover 20 New Taipei districts plus the Neihu baseline, while individual transaction rows are heavily shaped by social housing / rental-management cases.

Official unit rent and transaction unit price are not directly compared in this report because their units differ: MOI official unit rent is presented as NTD/ping, while the raw transaction CSV field is NTD/square meter.

Minimum next-step input table:

```text
district / candidate location
lat
lon
official_median_rent
official_median_unit_price_ping
commute_minutes_to_neihu
transfer_count
```

## Social Housing Structure

Cleaned independent-suite transaction rows: 7,032.
社宅 / 包租代管 share: 84.1%.

- 社宅 / 包租代管: 5,911
- 一般租賃: 692
- 其他 / unknown: 429