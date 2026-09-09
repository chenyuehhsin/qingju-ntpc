# Preference Recommendation Summary

範圍：第一版 MVP 推薦模式。省租型、平衡型、通勤型維持只使用 Rent x Commute Pareto-efficient candidates；生活品質型重新評估全部 16 個候選生活圈。

Normalization：省租型、平衡型、通勤型的 `official_median_rent` 與 `commute_minutes` 都在 Pareto frontier 內做 min-max normalization。生活品質型則在 16 個候選點內 normalize rent、commute、livability。cost 越低排名越前。

這些權重只是 MVP 的使用者偏好設定，不是客觀最佳權重。

Pareto candidates 即使沒有成為 Top 1，也會保留在推薦池中。例如樹林車站仍保留，因為它在 rent x commute 下仍是 Pareto-efficient。

## 省租型

Top 1: 淡水站 (淡水區), cost=0.300, rent=10,000 NTD, commute=67.8 min.

Top 3:

- #1 淡水站: cost=0.300, rent=10,000 NTD, commute=67.8 min
- #2 汐止車站: cost=0.515, rent=14,000 NTD, commute=47.2 min
- #3 樹林車站: cost=0.612, rent=13,000 NTD, commute=64.7 min

排序原因：租金權重最高，因此淡水站因 normalized rent 最低而排名第一，即使它在 Top 3 中通勤時間最長。 使用權重：rent=0.7, commute=0.3。

## 平衡型

Top 1: 汐止車站 (汐止區), cost=0.415, rent=14,000 NTD, commute=47.2 min.

Top 3:

- #1 汐止車站: cost=0.415, rent=14,000 NTD, commute=47.2 min
- #2 板橋站: cost=0.500, rent=16,000 NTD, commute=43.2 min
- #3 淡水站: cost=0.500, rent=10,000 NTD, commute=67.8 min

排序原因：租金與通勤權重相同，因此汐止車站以低於 frontier 中段的租金，加上接近板橋的通勤時間取得第一。 使用權重：rent=0.5, commute=0.5。

## 通勤型

Top 1: 板橋站 (板橋區), cost=0.300, rent=16,000 NTD, commute=43.2 min.

Top 3:

- #1 板橋站: cost=0.300, rent=16,000 NTD, commute=43.2 min
- #2 汐止車站: cost=0.314, rent=14,000 NTD, commute=47.2 min
- #3 淡水站: cost=0.700, rent=10,000 NTD, commute=67.8 min

排序原因：通勤權重最高，因此板橋站因 frontier 中最短通勤時間而排名第一。 使用權重：rent=0.3, commute=0.7。

## Pareto Pool Used

| candidate | district | normalized_rent | normalized_commute |
|---|---|---:|---:|
| 板橋站 | 板橋區 | 1.000 | 0.000 |
| 汐止車站 | 汐止區 | 0.667 | 0.163 |
| 樹林車站 | 樹林區 | 0.500 | 0.874 |
| 淡水站 | 淡水區 | 0.000 | 1.000 |

## 生活品質型

生活品質型會重新評估全部 16 個候選生活圈，不沿用 Rent x Commute 的 2D Pareto filter。

MVP preference weights: livability=0.6, rent=0.2, commute=0.2。這是生活品質型的 MVP 使用者偏好設定，不是客觀最佳權重。

`livability_index` 是以 OpenStreetMap POI 生活機能作為生活品質 proxy，不是客觀完整生活品質指標。

Scoring: rent 與 commute 為越低越好，livability 為越高越好；`preference_cost = 0.2 * normalized_rent + 0.2 * normalized_commute + 0.6 * (1 - normalized_livability)`，cost 越低排名越前。

Top 3:

- #1 板橋站: cost=0.141, score=0.859, rent=16,000 NTD, commute=43.2 min, livability_index=0.802
- #2 大坪林站: cost=0.227, score=0.773, rent=15,500 NTD, commute=50.8 min, livability_index=0.717
- #3 樹林車站: cost=0.296, score=0.704, rent=13,000 NTD, commute=64.7 min, livability_index=0.627

排序原因：板橋站的 livability proxy 最高且通勤最短，因此在生活品質型拿到第一；大坪林站雖然在 Rent x Commute 中被汐止車站 dominated，但 POI 生活機能非常高，因此升到第二；樹林車站則同時有較高 livability proxy 與較低租金，排名第三。

加入 livability 後重新具有競爭力的 Rent x Commute dominated candidates:

- 大坪林站: 生活品質型 rank #2, livability_index=0.717, 原 dominated_by=汐止車站
- 三峽北大特區: 生活品質型 rank #4, livability_index=0.552, 原 dominated_by=淡水站; 泰山站
- 景安站: 生活品質型 rank #5, livability_index=0.551, 原 dominated_by=汐止車站; 三重站; 頂溪站; 土城站
- 頂溪站: 生活品質型 rank #6, livability_index=0.465, 原 dominated_by=汐止車站

## Livability Sanity Check

- POI radius values: [800] meters; all candidates use 800m.
- Raw cache files checked for duplicate category matches: 16.
- Multi-category duplicate element count: 0.

POI query/tag definition:

- 餐飲 (food): amenity=cafe|restaurant
- 日常採買 (shopping): shop=convenience|supermarket
- 休閒 (recreation): leisure=fitness_centre|park|pitch|sports_centre|stadium
- 文娛 (culture): amenity=arts_centre|cinema|library|theatre, tourism=gallery|museum
- 基本醫療 (medical): amenity=clinic|hospital|pharmacy

Sample classification audits:

- 板橋站: elements=338, food=193, shopping=57, recreation=59, culture=10, medical=19, multi-category duplicates=0
- 大坪林站: elements=391, food=256, shopping=49, recreation=34, culture=4, medical=48, multi-category duplicates=0
- 五股區公所: elements=77, food=47, shopping=16, recreation=13, culture=0, medical=1, multi-category duplicates=0

## 生活品質型全 16 排名

| rank | candidate | rent | commute | livability_index | cost | score | rent_commute_pareto |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | 板橋站 | 16,000 | 43.2 | 0.802 | 0.141 | 0.859 | yes |
| 2 | 大坪林站 | 15,500 | 50.8 | 0.717 | 0.227 | 0.773 | no |
| 3 | 樹林車站 | 13,000 | 64.7 | 0.627 | 0.296 | 0.704 | yes |
| 4 | 三峽北大特區 | 10,000 | 91.1 | 0.552 | 0.394 | 0.606 | no |
| 5 | 景安站 | 15,000 | 63.8 | 0.551 | 0.399 | 0.601 | no |
| 6 | 頂溪站 | 15,000 | 51.7 | 0.465 | 0.415 | 0.585 | no |
| 7 | 淡水站 | 10,000 | 67.8 | 0.393 | 0.420 | 0.580 | yes |
| 8 | 三重站 | 15,000 | 51.7 | 0.414 | 0.455 | 0.545 | no |
| 9 | 汐止車站 | 14,000 | 47.2 | 0.337 | 0.472 | 0.528 | yes |
| 10 | 泰山站 | 10,000 | 68.6 | 0.212 | 0.564 | 0.436 | no |
| 11 | 新莊站 | 15,700 | 61.3 | 0.304 | 0.597 | 0.403 | no |
| 12 | 蘆洲站 | 18,500 | 53.8 | 0.306 | 0.630 | 0.370 | no |
| 13 | 土城站 | 14,500 | 53.6 | 0.180 | 0.633 | 0.367 | no |
| 14 | 鶯歌車站 | 14,500 | 71.7 | 0.134 | 0.744 | 0.256 | no |
| 15 | 林口站 | 18,000 | 74.5 | 0.165 | 0.813 | 0.187 | no |
| 16 | 五股區公所 | 16,000 | 66.8 | 0.030 | 0.840 | 0.160 | no |

## Outputs

- Input: `data/processed/integration/rent_commute_candidates_expanded.csv`
- Livability input: `data/processed/livability/livability_by_candidate.csv`
- Recommendations: `data/processed/integration/preference_recommendations.csv`
