# Multi-Workplace Validation

Scenario: public transit, weekday 08:00 Asia/Taipei, independent-suite rent benchmark.

| workplace | commute rows | 省租型 Top 1 | 平衡型 Top 1 | 通勤型 Top 1 | 生活品質型 Top 1 |
|---|---:|---|---|---|---|
| 港墘站｜內湖 | 16/16 | 淡水站 | 汐止車站 | 板橋站 | 板橋站 |
| 市政府站｜信義 | 16/16 | 泰山站 | 頂溪站 | 板橋站 | 板橋站 |
| 台北車站｜中正 | 16/16 | 泰山站 | 板橋站 | 板橋站 | 板橋站 |
| 南港站｜南港 | 16/16 | 泰山站 | 汐止車站 | 汐止車站 | 板橋站 |
| 新板特區｜板橋 | 16/16 | 泰山站 | 樹林車站 | 樹林車站 | 板橋站 |
| 新莊副都心｜新莊 | 16/16 | 泰山站 | 泰山站 | 泰山站 | 板橋站 |
| 汐止科學園區｜汐止 | 16/16 | 泰山站 | 汐止車站 | 汐止車站 | 板橋站 |
| 中和科技園區｜中和 | 16/16 | 泰山站 | 景安站 | 景安站 | 板橋站 |
| 土城產業園區｜土城 | 16/16 | 三峽北大特區 | 三峽北大特區 | 土城站 | 板橋站 |

Checks:

- Every workplace has 16 successful candidate commute rows.
- Rent and livability inputs are unchanged across workplaces.
- Rent x Commute modes rank Pareto-efficient candidates first; if a workplace has fewer than three Pareto candidates, the remaining Top-3 slots are filled from the same weighted score across all candidates.
- 生活品質型 ranks all 16 candidates per workplace using the existing MVP weights.
