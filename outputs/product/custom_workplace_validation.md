# Custom Workplace Validation

Scenario: public transit, weekday 08:00 Asia/Taipei, candidate node to user-input workplace coordinates.

Geocoding source: OpenStreetMap Nominatim

| test address | geocoding | lat | lon | 省租型 Top 1 | 平衡型 Top 1 | 通勤型 Top 1 | 生活品質型 Top 1 | route failures |
|---|---|---:|---:|---|---|---|---|---|
| 台北市內湖區瑞光路 | success | 25.069779 | 121.583278 | 淡水站 | 汐止車站 | 汐止車站 | 板橋站 | none |
| 新北市深坑區北深路三段 | success | 25.005004 | 121.596352 | 泰山站 | 大坪林站 | 大坪林站 | 板橋站 | none |

Notes:

- Geocoding results and TDX MaaS responses are cached locally.
- The custom workplace is labeled as `我的工作地`, not as a station.
- This is still candidate-node to workplace-coordinate public transit, not door-to-door commuting.
