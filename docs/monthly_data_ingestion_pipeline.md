# Monthly Data Ingestion & Reproducibility Pipeline

本文件說明「新北市青年就業地圖」每月資料更新流程。重點是可重現、可追溯、可驗證；不使用 synthetic data 補月份，也不把處理時間誤當來源資料月份。

## 1. Source Adapters

每個來源用獨立 adapter 管理，放在 `src/sources/`：

- `src/sources/population_source.py`：人口資料 adapter。
- `src/sources/taiwanjobs_source.py`：台灣就業通與公部門職缺 adapter。
- `src/sources/base.py`：共用 interface、SHA-256、immutable copy、欄位驗證。

每個 adapter 至少提供：

- `fetch(target_dir, dry_run=False, force=False)`：把目前 repository 已存在 raw source 複製到 staging/raw snapshot。此 pipeline 不重新下載已存在資料。
- `validate_raw(paths)`：檢查必要欄位、29 區覆蓋與基本 row count。
- `extract_reference_date(paths)`：抽出來源實際參考日期或月份。
- `normalize(paths)`：保留未來擴充正式資料源的標準化入口。
- `get_provenance(paths)`：輸出來源檔案、row count、downloaded_at、reference date、SHA-256。

## 2. Temporal Semantics

本專案分開記錄以下時間欄位：

- `snapshot_month`：分析快照標籤，例如 `2026-08`。這是 dashboard 的比較期，不代表所有來源都剛好是 2026-08 資料。
- `snapshot_as_of`：建立快照的系統時間。
- `population_reference_month`：人口來源實際統計月份。目前從 `statistic_yyymm` 或檔名 `11507` 解析為 `2026-07`。
- `population_downloaded_at`：人口來源下載時間。目前 repository 未能確認，保留空值。
- `jobs_reference_date`：職缺資料列中可確認的最新職缺參考日期，例如 `TRANDATE`、`DATE_FROM`、`DATE_TO`。
- `jobs_snapshot_as_of` / `jobs_downloaded_at`：台灣就業通下載 manifest 中可確認的下載時間。
- `processed_at`：本專案處理資料時間，不能拿來推測來源統計月份。

## 3. Raw Preservation

正式月度執行會把 raw source 保存到：

```text
data/raw_snapshots/YYYY-MM/
```

目前結構：

```text
data/raw_snapshots/2026-08/
├── population/
├── jobs/
│   ├── taiwanjobs/
│   └── public_sector/
```

Raw snapshot 視為 immutable archive。既有月份預設不可覆寫；只有明確加上 `--force` 才允許替換，而且 pipeline 會先備份既有 raw snapshot。

## 4. Provenance And SHA-256

每個月會輸出：

```text
data/history/YYYY-MM/source_manifest.json
reports/pipeline_runs/YYYY-MM.json
data/history/history_manifest.json
```

`source_manifest.json` 記錄：

- snapshot month / snapshot_as_of
- population reference month
- jobs reference date
- jobs downloaded_at / snapshot_as_of
- 每個 raw 檔案的 SHA-256
- row count
- size bytes
- local path

SHA-256 可用來確認歷史月份是否被意外改動。

## 5. Schema Drift

來源欄位分為：

- Required：缺少即失敗。
- Observed / extra：保留 warning，不中斷 pipeline。

目前 required examples：

- 人口：`statistic_yyymm`、`site_id`、`people_age_018_m/f` 到 `people_age_035_m/f`。
- 台灣就業通：行政區/地址、需求人數、薪資、職類、職缺名稱、公司、更新日期相關欄位。
- 事求人：`ORG_NAME`、`TITLE`、`NUMBER_OF`、`WORK_ADDRESS`、`DATE_FROM`、`DATE_TO`。

## 6. Monthly Execution

Dry run，僅檢查來源與計畫，不寫檔：

```bash
python scripts/run_monthly_pipeline.py --month 2026-09 --dry-run
```

正式建立月份：

```bash
python scripts/run_monthly_pipeline.py --month 2026-08
```

若月份已存在，需明確要求覆寫：

```bash
python scripts/run_monthly_pipeline.py --month 2026-08 --force
```

Pipeline 順序：

1. Preflight：檢查月份格式、來源可用性、29 區、既有 snapshot、freshness。
2. Stage raw sources 到 `data/staging/YYYY-MM/`。
3. 執行 current build / website export / current validation。
4. Commit raw snapshot 到 `data/raw_snapshots/YYYY-MM/`。
5. 建立 `data/history/YYYY-MM/source_manifest.json`。
6. 執行 `scripts/create_monthly_snapshot.py --month YYYY-MM`。
7. 執行 `scripts/validate_historical_data.py`。
8. 輸出 `reports/pipeline_runs/YYYY-MM.json`。

## 7. Staging And Failure Recovery

Pipeline 先寫 staging，再提交到 raw snapshot 與 history snapshot。若 staging 後失敗：

- staging 會清除。
- 不會建立該月正式 `youth_employment_map.csv`。
- 不會用 partial output 更新官方 history snapshot。
- 既有歷史月份不會被修改。

## 8. Previous Available Period

MoM 比較使用上一個「可用 snapshot period」，不是直接假設上一個 calendar month 一定存在。

Example：

```text
available periods = [2026-08]
target snapshot = 2026-10
previous_available_period = 2026-08
period_gap_months = 2
```

若 2026-09 不存在，不會補 synthetic 2026-09。

## 9. September Workflow

若 2026-09 更新時來源尚未發布：

```bash
python scripts/run_monthly_pipeline.py --month 2026-09 --dry-run
```

會回報：

- `source_unavailable: true`
- `would_create_snapshot: false`
- 最新可用 snapshot
- population / jobs freshness status

此時不建立 `data/history/2026-09/`，也不產生假的 2026-09 dashboard data。

## 10. Validation

每次更新後建議執行：

```bash
python scripts/build_youth_employment_map.py
python scripts/export_website_data.py
python scripts/validate_youth_employment_data.py
python scripts/validate_historical_data.py
python scripts/test_trend_pipeline.py
python scripts/test_ai_decision_engine.py
python scripts/test_monthly_pipeline.py
node --check website/app.js
```

`scripts/test_monthly_pipeline.py` 覆蓋：

- 正常來源 adapter validation。
- snapshot 已存在時必須 `--force`。
- population source lag 必須保留真實月份。
- required source field 缺失會失敗。
- 缺少 29 區任一行政區可被偵測。
- previous available period gap 正確。
- pipeline 中途失敗不建立正式 history snapshot。
- dry run 不寫入缺失月份。
