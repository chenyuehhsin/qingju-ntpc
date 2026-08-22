# Livability POI Exploration

範圍：16 個候選生活圈，每個生活圈以代表交通節點周邊 800m 半徑計算。

這是 MVP 階段的生活機能 proxy，用來觀察青年租屋時可能感受到的便利與休閒機能。它不應被解讀為完整或客觀的生活品質分數。

## 資料來源與 Query Definition

- Source: OpenStreetMap via Overpass API.
- Endpoint(s): `https://overpass-api.de/api/interpreter; https://overpass.kumi.systems/api/interpreter`
- Download date: 2026-08-22.
- Cache directory: `data/raw/livability/osm_overpass_800m_2026-08-22`
- Radius: 800m around each candidate node.

POI 類別定義：

- 餐飲: `amenity=restaurant|cafe`
- 日常採買: `shop=convenience|supermarket`
- 休閒: `leisure=park|sports_centre|pitch|fitness_centre|stadium`
- 文娛: `amenity=cinema|library|arts_centre|theatre`, `tourism=museum|gallery`
- 基本醫療: `amenity=clinic|hospital|pharmacy`

## 主要數量

| candidate | food | shopping | recreation | culture | medical | total | equal_weight_index |
|---|---:|---:|---:|---:|---:|---:|---:|
| 板橋站 | 193 | 57 | 59 | 10 | 19 | 338 | 0.802 |
| 大坪林站 | 256 | 49 | 34 | 4 | 48 | 391 | 0.717 |
| 樹林車站 | 198 | 42 | 23 | 9 | 33 | 305 | 0.627 |
| 三峽北大特區 | 157 | 39 | 52 | 6 | 11 | 265 | 0.552 |
| 景安站 | 137 | 62 | 23 | 3 | 36 | 261 | 0.551 |
| 頂溪站 | 132 | 54 | 27 | 4 | 16 | 233 | 0.465 |
| 三重站 | 82 | 48 | 30 | 5 | 12 | 177 | 0.414 |
| 淡水站 | 218 | 31 | 25 | 3 | 11 | 288 | 0.393 |
| 汐止車站 | 67 | 41 | 22 | 5 | 12 | 147 | 0.337 |
| 蘆洲站 | 104 | 36 | 33 | 2 | 5 | 180 | 0.306 |
| 新莊站 | 63 | 27 | 30 | 3 | 20 | 143 | 0.304 |
| 泰山站 | 60 | 18 | 26 | 3 | 12 | 119 | 0.212 |
| 土城站 | 37 | 17 | 21 | 3 | 15 | 93 | 0.180 |
| 林口站 | 93 | 24 | 19 | 1 | 5 | 142 | 0.165 |
| 鶯歌車站 | 22 | 14 | 14 | 5 | 8 | 63 | 0.134 |
| 五股區公所 | 47 | 16 | 13 | 0 | 1 | 77 | 0.030 |

## 初步觀察

equal-weight livability proxy 最高的生活圈：

- 板橋站: index 0.802, total POI 338.
- 大坪林站: index 0.717, total POI 391.
- 樹林車站: index 0.627, total POI 305.
- 三峽北大特區: index 0.552, total POI 265.
- 景安站: index 0.551, total POI 261.

raw total POI count 最高的生活圈：

- 大坪林站: 391 POIs.
- 板橋站: 338 POIs.
- 樹林車站: 305 POIs.
- 淡水站: 288 POIs.
- 三峽北大特區: 265 POIs.

各類別最高：

- 餐飲: 大坪林站 (256)
- 日常採買: 景安站 (62)
- 休閒: 板橋站 (59)
- 文娛: 板橋站 (10)
- 基本醫療: 大坪林站 (48)

## 資料限制

- OSM 完整度會受地區與 mapper 活躍度影響；較低數量可能反映未完整標圖，不一定代表實際機能不足。
- POI count 將所有點等權計算，未衡量品質、容量、營業時間、價格、步行安全、擁擠程度。
- 800m 是以代表節點為中心的簡單圓形範圍，不是實際步行路網可達範圍。
- 部分設施可能使用本 MVP query 未涵蓋的 OSM tag，因此會漏算。
- equal-weight index 只作探索用途，不應呈現為客觀生活品質分數。

## Outputs

- Processed table: `data/processed/livability/livability_by_candidate.csv`
- Comparison chart: `outputs/livability/01_livability_poi_comparison.png`
- Query definition: `outputs/livability/osm_overpass_query_definition.json`
