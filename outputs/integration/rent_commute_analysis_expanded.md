# Expanded Rent x Commute Analysis

Scope: 16 candidate living-area nodes joined to New Taipei official independent-suite rent benchmarks by district.

Neihu rent baseline: 19,500 NTD/month. This is a reference line only and is not included in Pareto calculations.

## Added Candidates

- 三峽北大特區 (三峽區): NWT_BUS_STATION / 臺北大學正門 [NWT3282]. TDX bus station at NTPU main gate, representing the dense Sanxia Beida residential area with many bus routes.; TDX bus routes at station=17
- 五股區公所 (五股區): NWT_BUS_STATION / 五股區公所(五股公有市場) [NWT74479]. TDX bus station at Wugu District Office / public market, representing the district center.; TDX bus routes at station=5
- 土城站 (土城區): TRTC / 土城 [TRTC-BL03]. MRT station named for and located in Tucheng, suitable as the district's transit anchor.
- 林口站 (林口區): TYMC / 林口站 [TYMC-A9]. Taoyuan Airport MRT A9 station and the main rail node for Linkou new town.
- 樹林車站 (樹林區): TRA / 樹林 [TRA-1040]. TRA station and main rail anchor for Shulin.
- 泰山站 (泰山區): TYMC / 泰山站 [TYMC-A5]. Taoyuan Airport MRT A5 station in Taishan, the clearest rail node for the district.
- 淡水站 (淡水區): TRTC / 淡水 [TRTC-R28]. Terminal MRT station and highest-recognition Tamsui transit node.
- 鶯歌車站 (鶯歌區): TRA / 鶯歌 [TRA-1070]. TRA station and main rail anchor for Yingge.

## Main Findings

- Lowest rent candidate: 淡水站 (淡水區), 10,000 NTD/month, 67.8 minutes.
- Shortest commute candidate: 板橋站 (板橋區), 43.2 minutes, 16,000 NTD/month.
- Pareto-efficient candidates: 板橋站 (16,000 NTD, 43.2 min), 汐止車站 (14,000 NTD, 47.2 min), 樹林車站 (13,000 NTD, 64.7 min), 淡水站 (10,000 NTD, 67.8 min).
- Original Banqiao remains on frontier: yes.
- Original Xizhi remains on frontier: yes.

## All Candidates

| candidate | district | rent_ntd | commute_min | transfers | pareto | dominated_by |
|---|---:|---:|---:|---:|---|---|
| 板橋站 | 板橋區 | 16,000 | 43.2 | 1 | yes |  |
| 汐止車站 | 汐止區 | 14,000 | 47.2 | 1 | yes |  |
| 大坪林站 | 新店區 | 15,500 | 50.8 | 1 | no | 汐止車站 |
| 三重站 | 三重區 | 15,000 | 51.7 | 1 | no | 汐止車站 |
| 頂溪站 | 永和區 | 15,000 | 51.7 | 1 | no | 汐止車站 |
| 土城站 | 土城區 | 14,500 | 53.6 | 1 | no | 汐止車站 |
| 蘆洲站 | 蘆洲區 | 18,500 | 53.8 | 1 | no | 板橋站; 汐止車站; 大坪林站; 三重站; 頂溪站; 土城站 |
| 新莊站 | 新莊區 | 15,700 | 61.3 | 1 | no | 汐止車站; 大坪林站; 三重站; 頂溪站; 土城站 |
| 景安站 | 中和區 | 15,000 | 63.8 | 1 | no | 汐止車站; 三重站; 頂溪站; 土城站 |
| 樹林車站 | 樹林區 | 13,000 | 64.7 | 1 | yes |  |
| 五股區公所 | 五股區 | 16,000 | 66.8 | 2 | no | 板橋站; 汐止車站; 大坪林站; 三重站; 頂溪站; 土城站; 新莊站; 景安站; 樹林車站 |
| 淡水站 | 淡水區 | 10,000 | 67.8 | 1 | yes |  |
| 泰山站 | 泰山區 | 10,000 | 68.6 | 1 | no | 淡水站 |
| 鶯歌車站 | 鶯歌區 | 14,500 | 71.7 | 1 | no | 汐止車站; 土城站; 樹林車站; 淡水站; 泰山站 |
| 林口站 | 林口區 | 18,000 | 74.5 | 1 | no | 板橋站; 汐止車站; 大坪林站; 三重站; 頂溪站; 土城站; 新莊站; 景安站; 樹林車站; 五股區公所; 淡水站; 泰山站; 鶯歌車站 |
| 三峽北大特區 | 三峽區 | 10,000 | 91.1 | 1 | no | 淡水站; 泰山站 |

## Dominated Candidates

- 大坪林站: dominated by 汐止車站.
- 三重站: dominated by 汐止車站.
- 頂溪站: dominated by 汐止車站.
- 土城站: dominated by 汐止車站.
- 蘆洲站: dominated by 板橋站; 汐止車站; 大坪林站; 三重站; 頂溪站; 土城站.
- 新莊站: dominated by 汐止車站; 大坪林站; 三重站; 頂溪站; 土城站.
- 景安站: dominated by 汐止車站; 三重站; 頂溪站; 土城站.
- 五股區公所: dominated by 板橋站; 汐止車站; 大坪林站; 三重站; 頂溪站; 土城站; 新莊站; 景安站; 樹林車站.
- 泰山站: dominated by 淡水站.
- 鶯歌車站: dominated by 汐止車站; 土城站; 樹林車站; 淡水站; 泰山站.
- 林口站: dominated by 板橋站; 汐止車站; 大坪林站; 三重站; 頂溪站; 土城站; 新莊站; 景安站; 樹林車站; 五股區公所; 淡水站; 泰山站; 鶯歌車站.
- 三峽北大特區: dominated by 淡水站; 泰山站.

## Interpretation

The expanded frontier is more stable and more informative than the first 8-point frontier. Banqiao remains the commute-minimizing point, Xizhi remains a low-rent and moderate-commute point, while Shulin and Tamsui extend the frontier toward lower rent with longer commutes.

This creates a usable preliminary trade-off for three product narratives: commute-oriented (Banqiao), balanced (Xizhi or Shulin depending on tolerance), and rent-saving (Tamsui). The categories should still be treated as exploratory because each district is represented by one node and only one workplace anchor.

## Inputs And Outputs

- Expanded candidate locations: `data/processed/transport/candidate_locations_expanded.csv`
- Expanded commute table: `data/processed/transport/commute_to_gangqian_expanded.csv`
- Input housing benchmark: `data/processed/housing/moi_independent_suite_rent_benchmark.csv`
- Integrated table: `data/processed/integration/rent_commute_candidates_expanded.csv`
- Scatter plot: `outputs/integration/02_rent_commute_scatter_expanded.png`
