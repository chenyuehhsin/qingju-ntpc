# Preference Recommendation Summary

範圍：第一版 MVP 推薦模式，只使用 Rent x Commute Pareto-efficient candidates。

Normalization：`official_median_rent` 與 `commute_minutes` 都在 Pareto frontier 內做 min-max normalization。兩者皆為越低越好。`preference_cost` 是 normalized rent 與 normalized commute 的加權和，cost 越低排名越前。

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

## Outputs

- Input: `data/processed/integration/rent_commute_candidates_expanded.csv`
- Recommendations: `data/processed/integration/preference_recommendations.csv`
