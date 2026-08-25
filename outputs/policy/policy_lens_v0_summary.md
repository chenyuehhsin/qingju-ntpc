# Policy Lens v0 Summary

Purpose: screen candidate New Taipei living areas that may warrant further housing-policy attention from a Youth Bureau lens.
This is a diagnostic view, not a formal policy priority ranking and not a policy prescription.

## Method

- Candidates: 16 existing MVP living-area nodes.
- Commute accessibility: median `commute_minutes` across 9 existing workplace presets.
- Rent threshold: overall candidate median = 15,000 NTD/month.
- Commute threshold: overall candidate median = 41.9 minutes.
- Livability: OSM 800m POI equal-weight index used as a life-function proxy.
- Policy-linked rental share: share of cleaned independent-suite rental registration sample with `social_housing_flag == 社宅 / 包租代管`.

## 1. 高租金 × 長通勤

- 蘆洲站（蘆洲區）：租金 18,500，可達性 47.7 min，生活機能 0.306，policy-linked share 98.1% (104/106)
- 林口站（林口區）：租金 18,000，可達性 52.2 min，生活機能 0.165，policy-linked share 69.3% (79/114)
- 五股區公所（五股區）：租金 16,000，可達性 54.5 min，生活機能 0.030，policy-linked share 99.2% (128/129)
- 新莊站（新莊區）：租金 15,700，可達性 42.2 min，生活機能 0.304，policy-linked share 89.2% (388/435)
- 大坪林站（新店區）：租金 15,500，可達性 45.7 min，生活機能 0.717，policy-linked share 61.9% (268/433)

These candidates combine above-median district rent benchmark and above-median median commute to existing workplace anchors.

## 2. 低租金 × 長通勤

- 淡水站（淡水區）：租金 10,000，可達性 66.7 min，生活機能 0.393，policy-linked share 87.8% (1166/1328)
- 三峽北大特區（三峽區）：租金 10,000，可達性 64.3 min，生活機能 0.552，policy-linked share 90.5% (229/253)
- 鶯歌車站（鶯歌區）：租金 14,500，可達性 49.4 min，生活機能 0.134，policy-linked share 97.1% (33/34)

These may look affordable on district rent benchmark but are less accessible under the current public-transit anchor set.

## 3. Better Rent × Transit Trade-Off

- 汐止車站（汐止區）：租金 14,000，可達性 33.4 min，生活機能 0.337，policy-linked share 94.4% (437/463)
- 樹林車站（樹林區）：租金 13,000，可達性 33.8 min，生活機能 0.627，policy-linked share 93.2% (109/117)
- 泰山站（泰山區）：租金 10,000，可達性 39.6 min，生活機能 0.212，policy-linked share 99.0% (100/101)
- 土城站（土城區）：租金 14,500，可達性 41.6 min，生活機能 0.180，policy-linked share 93.1% (284/305)

These fall in the lower-rent and shorter-commute quadrant under the v0 thresholds.

## 4. Livability Exceptions

High-pressure quadrant but relatively strong livability proxy:

- 大坪林站（新店區）：租金 15,500，可達性 45.7 min，生活機能 0.717，policy-linked share 61.9% (268/433)
- 蘆洲站（蘆洲區）：租金 18,500，可達性 47.7 min，生活機能 0.306，policy-linked share 98.1% (104/106)

Favorable rent/commute quadrant but weaker livability proxy:

- 土城站（土城區）：租金 14,500，可達性 41.6 min，生活機能 0.180，policy-linked share 93.1% (284/305)
- 泰山站（泰山區）：租金 10,000，可達性 39.6 min，生活機能 0.212，policy-linked share 99.0% (100/101)

This suggests POI-based life-function can complicate a simple rent/commute diagnosis.

## 5. Policy-Linked Rental Record Share

Highest shares in candidate districts:

- 五股區公所（五股區）：租金 16,000，可達性 54.5 min，生活機能 0.030，policy-linked share 99.2% (128/129)
- 泰山站（泰山區）：租金 10,000，可達性 39.6 min，生活機能 0.212，policy-linked share 99.0% (100/101)
- 蘆洲站（蘆洲區）：租金 18,500，可達性 47.7 min，生活機能 0.306，policy-linked share 98.1% (104/106)
- 鶯歌車站（鶯歌區）：租金 14,500，可達性 49.4 min，生活機能 0.134，policy-linked share 97.1% (33/34)
- 汐止車站（汐止區）：租金 14,000，可達性 33.4 min，生活機能 0.337，policy-linked share 94.4% (437/463)

Lowest shares in candidate districts:

- 三重站（三重區）：租金 15,000，可達性 36.5 min，生活機能 0.414，policy-linked share 61.7% (467/757)
- 大坪林站（新店區）：租金 15,500，可達性 45.7 min，生活機能 0.717，policy-linked share 61.9% (268/433)
- 林口站（林口區）：租金 18,000，可達性 52.2 min，生活機能 0.165，policy-linked share 69.3% (79/114)
- 景安站（中和區）：租金 15,000，可達性 37.9 min，生活機能 0.551，policy-linked share 79.0% (791/1001)
- 頂溪站（永和區）：租金 15,000，可達性 36.2 min，生活機能 0.465，policy-linked share 87.6% (275/314)

Important interpretation limit: this is only the share within the cleaned rental registration sample. It is not market share, not youth rental share, and not the true district social-housing or sublease-management supply rate.

Small sample districts to treat carefully:

- 鶯歌車站（鶯歌區）：租金 14,500，可達性 49.4 min，生活機能 0.134，policy-linked share 97.1% (33/34)

## 6. Hypotheses Only

- High rent and long commute may indicate housing-accessibility pressure, but this does not prove unmet youth demand.
- Low rent and long commute may indicate affordability/accessibility trade-off, but not necessarily poor welfare outcomes.
- Higher livability proxy reflects POI counts around one representative node, not complete neighborhood quality.
- Policy-linked rental share reflects observed rental-registration sample structure, not actual policy coverage.
- The data has no tenant age, so none of the rental records can be called youth rental cases.

## 7. Missing Data Before Social Housing / Subsidy Discussion

- Existing and planned social-housing units by location, unit type, and eligibility.
- Rental subsidy application, approval, waiting, and unmet-demand data by age group and district.
- Youth population, workplace distribution, income, and household formation data at finer geography.
- Real listing rents or transaction microdata closer to station-area buffers.
- Door-to-door commute estimates and off-peak/weekend accessibility.
- Land/public-asset availability and policy feasibility constraints.
