# Data Temporal Audit

本文件盤點目前 repository 中可確認的時間資訊。`processed_at` 只代表系統處理時間，不用來推測資料實際統計月份。

| dataset | source | available_date | date_granularity | district coverage | historical availability | can_be_used_for_trend |
| --- | --- | --- | --- | --- | --- | --- |
| `data/raw/ris_village_single_age_ntpc_11507_page1.json` | 內政部戶政司 ODRP014 村里戶數、單一年齡人口 | 民國 115 年 7 月，對應 `2026-07` | 月 | 可彙總至新北市 29 區 | 目前 repository 只有 1 個月份檔案 | 可以作為 snapshot 的人口基準；目前不能單獨做人口趨勢 |
| `data/raw/taiwanjobs/*.xml` | 勞動部勞動力發展署台灣就業通網站職缺清單 OpenData API | manifest `downloaded_at` 為 `2026-08-30`；職缺列有 `TRANDATE`，目前可見範圍含 2025-2026 多個更新日期 | 下載時間為秒；職缺更新日期為日 | 以新北市 29 區郵遞區號分區下載，已覆蓋 29 區 | 目前 repository 只有一次下載批次，不構成多期歷史 snapshot | 可用於建立單一 snapshot；未來每月保存下載批次後可做趨勢 |
| `data/raw/dgpa_public_sector_jobs.xml` | 行政院人事行政總處事求人機關徵才資料 | 原始列包含 `DATE_FROM` / `DATE_TO` 或類似公告/截止日期欄位；目前未建立多期保存 | 日 | 依工作地址可辨識的新北市行政區歸戶 | 目前只有 1 份 raw XML | 可納入單一 snapshot；需每月保存 raw 或 processed snapshot 才能趨勢化 |
| `data/raw/source_manifest.json` | 本專案下載腳本產生 | `updated_at = 2026-08-30T00:40:19` | 秒 | 描述來源，不是區級資料 | 目前只有目前狀態 | 只可作 provenance，不可當統計月份 |
| `data/raw/taiwanjobs_manifest.json` | 本專案台灣就業通下載腳本產生 | `updated_at = 2026-08-30T00:45:24`；每區有 `downloaded_at` | 秒 | 29 區 | 目前只有目前狀態 | 可作 snapshot metadata，不可單獨當趨勢 |
| `data/raw/new_taipei_districts.geojson` | 新北市政府行政區 ArcGIS 圖層 | repository 未提供圖層資料日期；source manifest 只有下載/保存狀態 | 尚待確認 | 29 區 | 空間邊界不是時間序列資料 | 不作趨勢，只作地圖邊界 |
| `data/processed/youth_employment_map.csv` | 本專案 build pipeline | `processed_at` 為處理時間；人口來源欄與職缺來源欄保留 source file | 秒；source file 可回推部分來源日期 | 29 區 | 目前是一份 current processed table | 可透過 snapshot script 固化成歷史期數；本身不代表歷史 |
| `website/data/youth_employment_map.json` | 本專案 export pipeline | `provenance.processed_at` 為處理時間；`jobs_by_district.updated_at` 為職缺更新日期 | 秒 / 日 | 29 區 | 目前是一份 current website payload | 可作本期 snapshot input，不可替代多期歷史 |
| `data/processed/index_sample_size_analysis.csv` | 本專案 reliability export | 繼承 current processed data；無獨立 source date | 無獨立統計日期 | 29 區 | 目前只有 current | 可隨 snapshot 保存，但不單獨做趨勢 |
| `data/processed/index_reliability_analysis.json` | 本專案 reliability export | 繼承 current processed data；無獨立 source date | 無獨立統計日期 | 29 區 | 目前只有 current | 可作當期可靠度說明，不作歷史來源 |
| `data/processed/job_data_quality.json` | 本專案 website export | 繼承 current jobs payload；無獨立 source date | 無獨立統計日期 | 全職缺資料 | 目前只有 current | 可作當期資料品質，不作趨勢 |

## 可確認的時間欄位

- `source_manifest.updated_at`：來源下載 manifest 更新時間。
- `taiwanjobs_manifest.updated_at`：台灣就業通下載 manifest 更新時間。
- `taiwanjobs_manifest.sources[].downloaded_at`：每個行政區職缺 XML 的下載時間。
- `jobs_by_district[].updated_at`：職缺列的更新日期，來自原始職缺資料。
- `jobs_by_district[].deadline`：職缺應徵截止日期。
- `records[].processed_at` / `provenance.processed_at`：本專案資料處理時間，不是資料來源統計月份。
- `ris_village_single_age_ntpc_11507_page1.json` 檔名與 source manifest limitation：可確認人口資料月份為民國 115 年 7 月，即 `2026-07`。

## 結論

目前 repository 可建立 1 個真實 snapshot period。尚不足以計算 month-over-month trend，也不能做 forecast。未來每月執行 snapshot script 後，才可開始顯示 MoM、category growth、demand growth signal 與 forecast readiness 的下一階段狀態。
