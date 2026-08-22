# MOI Benchmark Extraction Validation

Source files:

- `/Users/yuehchen/Desktop/DSLab/1-Hackathon/qingju-ntpc/data/raw/housing/moi_rent_total_quartiles_2026-03.pdf`
- `/Users/yuehchen/Desktop/DSLab/1-Hackathon/qingju-ntpc/data/raw/housing/moi_rent_unit_price_quartiles_2026-03.pdf`

Extracted total-rent independent-suite rows across all cities: 133
Extracted unit-price independent-suite rows across all cities: 134
Processed benchmark rows retained: 21
New Taipei rows retained: 20
Taipei Neihu baseline retained: 1

Contract count match between total-rent PDF and unit-price PDF:

contract_count_match_between_pdfs
True    21

Rows with contract-count mismatch should be manually checked before using the benchmark as final evidence.