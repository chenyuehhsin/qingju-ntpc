# Youth Employment Trend & Historical Snapshot Pipeline v1

## Historical Data Model

歷史資料以每月 snapshot 保存，不修改 raw historical files，也不覆蓋舊 snapshot。

```text
data/history/
  2026-08/
    youth_employment_map.csv
    metadata.json
```

Master tables：

- `data/processed/youth_employment_history.csv`
- `data/processed/job_category_history.csv`
- `website/data/youth_employment_history.json`

## Snapshot Mechanism

使用：

```bash
python scripts/create_monthly_snapshot.py --month 2026-08
```

預設不覆蓋既有 snapshot。若確認要重建同一月份：

```bash
python scripts/create_monthly_snapshot.py --month 2026-08 --force
```

script 會先執行目前 processed data validation，確認新北市 29 區完整後才建立 snapshot。

## Source Date vs Processed Date

- `source_date`：資料來源可確認的時間資訊，例如人口檔名 `11507` 對應 `2026-07`、職缺列 `updated_at`、台灣就業通 `downloaded_at`。
- `processed_at`：本專案處理資料的時間，不代表來源資料統計月份。
- `snapshot_month`：本專案保存快照的月份，用於歷史追蹤。

## Month-over-Month Calculation

至少兩個 snapshot period 才計算 MoM：

```text
job_openings_mom_pct = (current - previous) / previous * 100
```

同樣規則用於：

- `job_postings_mom_pct`
- `salary_mom_pct`
- `jobs_per_1000_youth_mom_pct`

`index_mom_change` 使用絕對分數差：

```text
current_index - previous_index
```

如果 previous 為 0 或缺值，percentage change 設為 null，不除以 0。

## Category Trend

`job_category_history.csv` 保存完整 category distribution，不只保存 top category。欄位包括：

- `snapshot_month`
- `district`
- `category`
- `job_postings`
- `job_openings`
- `median_salary`
- `company_count`
- MoM 欄位

未來可支援：

- 需求增加最多
- 需求減少最多
- 目前需求最多

這三者分開計算，不混為同一個指標。

## Demand Growth Signal

`demand_growth_signal` 是 descriptive label，不是 forecast。

初版依 job openings、job postings、company count 的可用 MoM 平均判斷：

- `> +5%`：需求增加
- `-5% ~ +5%`：相對穩定
- `< -5%`：需求下降

只有一個 snapshot 時為 null。

## Forecast Readiness

forecast readiness 只表示資料量準備度，不代表預測可靠。

```text
< 3 periods: Insufficient / 尚不足
3-5 periods: Trend only / 可做初步趨勢
>= 6 periods: Experimental forecasting possible / 可進行實驗性預測準備
>= 12 periods: Better seasonal analysis candidate / 較適合評估季節性分析
```

本輪不做 ARIMA、Prophet、LSTM、XGBoost、LLM forecast 或 synthetic history。

## Missing Month Handling

如果只有：

```text
2026-07
2026-09
```

系統不會創造 `2026-08`。Trend chart 只顯示實際存在的 snapshot period，不做 interpolation。

## Limitations

- 目前 repository 只有一個真實 snapshot：`2026-08`。
- 因為只有一個 period，MoM、連續下降、成長最快與 forecast 都不能實質判斷。
- 目前職缺歷史是 snapshot-based，不代表外部求職市場完整歷史。
- `source_date` 可保存目前可確認的來源時間，但部分來源仍只有下載時間或職缺更新日期，沒有統一統計月份。

## Future Forecasting Plan

1. 每月固定保存 raw download batch 與 processed snapshot。
2. 至少 3 期後開啟 descriptive trend review。
3. 至少 6 期後只做 experimental forecasting readiness review，不直接對使用者發布預測。
4. 至少 12 期後評估季節性、異常值、資料缺口與職類分類穩定性。
