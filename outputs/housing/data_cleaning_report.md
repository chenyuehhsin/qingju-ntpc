# Housing Data Cleaning Report

Source: `data/raw/housing/ntpc_rental_transactions_2026-08-21.csv`

Raw files were read only. No raw file contents were modified.

## Raw CSV

- Encoding: `utf-8-sig`
- Original rows: 45,932
- Columns: 35
- Duplicate rows: 0

## Key Columns

- `rps22_amountsunitdollars`: total rent (`總價元` in repository schema)
- `rps23_amountsunitdollars`: unit price per square meter (`單價元平方公尺` in repository schema)
- `rps15_area`: building area in square meters (`建物移轉總面積平方公尺` in repository schema)
- `rps07_yyymmddroc`: transaction date in ROC `YYYMMDD` format
- `rps29`: rental type
- `rps34`: rental management / social housing indicator

## Rental Type Filter

- Independent suite rows (`rps29 == 獨立套房`): 7,032

## Quality Counts Before Exclusion

- missing_district: 0
- missing_rent: 0
- rent_le_zero: 0
- missing_unit_price: 0
- unit_price_le_zero: 0
- missing_area: 0
- area_le_zero: 0
- blank_rental_date: 0

## Exclusion Steps

- missing_district: 0
- missing_or_nonpositive_rent: 0
- missing_or_nonpositive_unit_price: 0
- missing_or_nonpositive_area: 0
- pure_parking_or_land_transaction: 0

Final retained rows: 7,032

## Social Housing / Rental Management

- 社宅 / 包租代管: 5,911 (84.1%)
- 一般租賃: 692 (9.8%)
- 其他 / unknown: 429 (6.1%)

Social housing / rental management rows are retained for analysis. They are not removed from the cleaned interim file.

## Machine-Readable Cleaning Stats

```json
{
  "source_file": "/Users/yuehchen/Desktop/DSLab/1-Hackathon/qingju-ntpc/data/raw/housing/ntpc_rental_transactions_2026-08-21.csv",
  "encoding": "utf-8-sig",
  "original_rows": 45932,
  "original_columns": 35,
  "duplicate_rows": 0,
  "columns": [
    "district",
    "rps01",
    "rps02",
    "rps03_area",
    "rps04",
    "rps05",
    "rps06",
    "rps07_yyymmddroc",
    "rps08",
    "rps09",
    "rps10_quantity",
    "rps11",
    "rps12",
    "rps13",
    "rps14_yyymmddroc",
    "rps15_area",
    "rps16_quantity",
    "rps17_quantity",
    "rps18_quantity",
    "rps19",
    "rps20",
    "rps21",
    "rps22_amountsunitdollars",
    "rps23_amountsunitdollars",
    "rps24",
    "rps25_area",
    "rps26_amountsunitdollars",
    "rps27",
    "rps28",
    "rps29",
    "rps30",
    "rps31",
    "rps32",
    "rps33",
    "rps34"
  ],
  "missing_values": {
    "district": 0,
    "rps01": 0,
    "rps02": 0,
    "rps03_area": 0,
    "rps04": 45290,
    "rps05": 45903,
    "rps06": 45903,
    "rps07_yyymmddroc": 0,
    "rps08": 0,
    "rps09": 135,
    "rps10_quantity": 122,
    "rps11": 0,
    "rps12": 139,
    "rps13": 124,
    "rps14_yyymmddroc": 2112,
    "rps15_area": 0,
    "rps16_quantity": 0,
    "rps17_quantity": 0,
    "rps18_quantity": 0,
    "rps19": 0,
    "rps20": 0,
    "rps21": 0,
    "rps22_amountsunitdollars": 0,
    "rps23_amountsunitdollars": 263,
    "rps24": 41146,
    "rps25_area": 0,
    "rps26_amountsunitdollars": 0,
    "rps27": 9404,
    "rps28": 0,
    "rps29": 2304,
    "rps30": 137,
    "rps31": 0,
    "rps32": 137,
    "rps33": 2320,
    "rps34": 8094
  },
  "unique_values": {
    "district": {
      "淡水區": 6100,
      "板橋區": 5163,
      "中和區": 4949,
      "三重區": 4630,
      "新莊區": 3856,
      "新店區": 2846,
      "汐止區": 2733,
      "土城區": 2289,
      "永和區": 2154,
      "五股區": 2036,
      "三峽區": 1647,
      "蘆洲區": 1647,
      "林口區": 1209,
      "樹林區": 1167,
      "鶯歌區": 1009,
      "泰山區": 986,
      "八里區": 701,
      "三芝區": 446,
      "瑞芳區": 105,
      "萬里區": 104,
      "深坑區": 92,
      "金山區": 54,
      "貢寮區": 2,
      "石門區": 2,
      "石碇區": 2,
      "烏來區": 2,
      "雙溪區": 1
    },
    "rps01": {
      "租賃房屋": 41105,
      "租賃房屋+車位": 4690,
      "車位": 96,
      "土地": 41
    },
    "rps29": {
      "整棟(戶)出租": 32156,
      "獨立套房": 7032,
      "分租套房": 3470,
      "NaN": 2304,
      "分租雅房": 844,
      "分層出租": 126
    },
    "rps34": {
      "社會住宅代管": 19069,
      "社會住宅包租轉租": 12735,
      "NaN": 8094,
      "一般轉租": 4166,
      "一般代管": 1765,
      "一般包租": 103
    }
  },
  "independent_suite_rows": 7032,
  "quality_counts_before_exclusion": {
    "missing_district": 0,
    "missing_rent": 0,
    "rent_le_zero": 0,
    "missing_unit_price": 0,
    "unit_price_le_zero": 0,
    "missing_area": 0,
    "area_le_zero": 0,
    "blank_rental_date": 0
  },
  "exclusion_steps": [
    {
      "reason": "missing_district",
      "excluded_rows": 0
    },
    {
      "reason": "missing_or_nonpositive_rent",
      "excluded_rows": 0
    },
    {
      "reason": "missing_or_nonpositive_unit_price",
      "excluded_rows": 0
    },
    {
      "reason": "missing_or_nonpositive_area",
      "excluded_rows": 0
    },
    {
      "reason": "pure_parking_or_land_transaction",
      "excluded_rows": 0
    }
  ],
  "final_rows": 7032,
  "social_housing_counts_final": {
    "社宅 / 包租代管": 5911,
    "一般租賃": 692,
    "其他 / unknown": 429
  },
  "social_housing_share_final": {
    "社宅 / 包租代管": 0.8405858930602957,
    "一般租賃": 0.09840728100113766,
    "其他 / unknown": 0.06100682593856655
  },
  "final_district_counts": {
    "淡水區": 1328,
    "中和區": 1001,
    "板橋區": 786,
    "三重區": 757,
    "汐止區": 463,
    "新莊區": 435,
    "新店區": 433,
    "永和區": 314,
    "土城區": 305,
    "三峽區": 253,
    "三芝區": 204,
    "五股區": 129,
    "樹林區": 117,
    "林口區": 114,
    "蘆洲區": 106,
    "泰山區": 101,
    "萬里區": 60,
    "八里區": 59,
    "鶯歌區": 34,
    "深坑區": 18,
    "金山區": 12,
    "烏來區": 2,
    "瑞芳區": 1
  }
}
```