# 新北市青年就業地圖

互動式「新北市青年就業地圖（Youth Employment Map）」用來整合新北市 29 個行政區的青年人口與職缺資料，協助使用者了解各區青年人口、工作機會、熱門職缺、薪資與青年就業機會分布。

## 青年定義

本專案固定使用 **18–35 歲** 作為青年定義。

## 資料來源

目前已放入幾份官方開放資料作為第一版真實資料來源。資料管線會讀取 `data/raw/` 底下的真實資料，並將資料來源檔名保留在 processed CSV 的 `population_source_file` 與 `jobs_source_file` 欄位。

已納入的官方資料：

- 新北市政府主計處「現住人口之年齡分配」：`data/raw/ntpc_population_age_5year.csv`。此檔有新北市行政區與 5 歲年齡組，但無法精確計算 18–35 歲，因此目前不產出 `youth_population_18_35`。
- 內政部統計處「人口數單一年齡組─按性別、區域別分」：`data/raw/moi_population_single_age_query_113.csv` 與 `data/raw/moi_population_single_age_by_area.csv`。此檔提供單一年齡欄位格式，但目前下載到的資源未包含新北市 29 行政區明細，因此不拿來推估行政區青年人口。
- 內政部戶政司「村里戶數、單一年齡人口（新增區域代碼）」：`data/raw/ris_village_single_age_ntpc_11507_page1.json`。此檔包含新北市村里層級單一年齡人口，彙總為 29 行政區 18–35 歲青年人口。
- 行政院人事行政總處「事求人機關徵才資料」：`data/raw/dgpa_public_sector_jobs.xml`。此檔用於公部門職缺刊登數與需求人數，依 `WORK_ADDRESS` 可辨識行政區者歸戶。
- 勞動部勞動力發展署「台灣就業通網站職缺清單」：`data/raw/taiwanjobs/*.xml`。此檔用於求職網站職缺刊登數、雇用人數、薪資上下限、職務類別與公司名稱。
- 新北市政府行政區 ArcGIS 圖層：`data/raw/new_taipei_districts.geojson`。此檔用於 dashboard choropleth 行政區邊界，座標系統指定 WGS84。
- 新北市政府民政局「新北市行政區域圖」：`data/raw/ntpc_admin_area_map_links.csv`。此檔記錄官方行政區域圖下載頁面。

來源下載與限制紀錄在 `data/raw/source_manifest.json`。

已預留支援的資料類型：

- 青年或人口資料：行政區、年齡、人口數，或 18–35 歲各年齡欄位。
- 職缺資料：行政區或工作地址、職缺刊登列、需求人數、薪資、職缺類別、職業、產業、公司名稱。
- 新北市行政區 GeoJSON：放在 `data/raw/` 或專案內，檔名或欄位需能辨識新北市行政區。

## 資料處理流程

1. 掃描 `data/raw/` 的 CSV。
2. 掃描 `data/raw/` 的 XML。
3. 讀取每份 CSV/XML，不修改 raw data。
4. 依欄位名稱與檔名判斷可能用途。
5. 將行政區統一為 `district`，例如 `板橋` 與 `板橋區` 都標準化為 `板橋區`。
6. 僅使用確定可辨識的新北市行政區名稱；不以模糊比對強制歸類不確定地址。
7. 依 18–35 歲定義，彙總 `people_age_018_m/f` 至 `people_age_035_m/f`，從村里層級加總為行政區青年人口。
8. 依行政區彙整職缺刊登數、工作機會數、薪資、熱門類別與公司數。
9. 輸出 `data/processed/youth_employment_map.csv`。
10. 輸出 `data/processed/source_data_profile.json` 作為來源資料檢查摘要。
11. 輸出 `data/processed/index_sample_size_analysis.csv` 與 `data/processed/index_reliability_analysis.json` 作為 reliability / robustness 分析摘要。

## 指標定義

- `district`：新北市標準行政區名稱。
- `youth_population_18_35`：18–35 歲青年人口。
- `job_postings`：職缺刊登筆數，一列職缺資料計為一筆。
- `job_openings`：實際需求人數，僅在原始資料有明確需求人數欄位時彙整。
- `jobs_per_1000_youth`：每千名青年工作機會。
- `opportunity_score`：依 `jobs_per_1000_youth` 在 29 區中的 percentile rank 轉為 0–100 分。
- `salary_score`：依 `median_salary` 在 29 區中的 percentile rank 轉為 0–100 分，只使用可解析月薪。
- `job_diversity_score`：依 `jobs_by_district.category` 分布計算 normalized Shannon entropy，轉為 0–100 分。
- `employment_stability_score`：依可辨識 `work_type` 中全職職缺比例計算，轉為 0–100 分。
- `youth_employment_opportunity_index`：青年就業機會指數 v1，為 prototype composite indicator，不是官方政府指標。
- `index_coverage`：該行政區實際納入 composite index 的原始權重總和百分比。
- `index_available_dimensions`：該行政區實際納入 composite index 的 dimension。
- `index_reliability_score`：0–100，表示目前資料量與欄位完整度對該區 Index 的支持程度，不代表就業品質。
- `index_reliability_level`：依 reliability score 分為 High / Medium / Low，網站顯示高 / 中 / 低。
- `index_rank_stability`：0–100，表示不同合理權重情境下排名是否穩定，不同於 `employment_stability_score`。

公式：

```text
jobs_per_1000_youth = job_openings / youth_population_18_35 * 1000
```

若分子或分母缺失，保留為 `NaN`，不自動補 0。

青年就業機會指數 v1 權重：

```text
Opportunity Score: 40%
Salary Score: 25%
Job Diversity Score: 20%
Employment Stability Score: 15%
```

Opportunity 與 Salary 使用 29 區 percentile rank 做 normalization，避免單一極端值主導結果；Diversity 使用 normalized Shannon entropy；Stability 使用可辨識 work_type 中的全職比例。任一 dimension 缺值時不當成 0，該區會以有效 dimension 重新 normalize 權重。

完整方法文件見 `docs/youth_employment_opportunity_index.md`。

AI 決策助理方法文件見 `docs/ai_youth_employment_assistant.md`。

歷史快照與趨勢管線文件見 `docs/youth_employment_trend_pipeline.md`，每月資料擷取與可重現流程見 `docs/monthly_data_ingestion_pipeline.md`，時間欄位盤點見 `docs/data_temporal_audit.md`。

Reliability layer 不修改 v1 index，只新增解讀層。它使用 log saturation function 評估樣本量支持度，並搭配 salary/category/work_type coverage。Sensitivity analysis 會計算 baseline、opportunity-heavy、salary-heavy、quality/diversity-heavy 四種情境的排名，輸出在 `data/processed/index_reliability_analysis.json`。

## 如何執行

首次 setup：

```bash
python -m venv .venv
```

Windows：

```bash
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
npm install
npx playwright install chromium
```

安裝依賴：

```bash
pip install -r requirements.txt
```

比賽 Demo 一鍵啟動。此模式固定使用目前 repository 中 latest validated dataset，不下載新來源：

```bash
python scripts/run_demo.py
```

一鍵驗證：

```bash
python scripts/validate_all.py
```

比賽前 preflight：

```bash
python scripts/demo_preflight.py
```

下載官方來源資料。預設不覆寫已存在 raw data：

```bash
python scripts/download_official_sources.py
```

下載台灣就業通求職網站職缺。每區以 3 碼郵遞區號查詢，API 單次上限 1000 筆：

```bash
python scripts/download_taiwanjobs_jobs.py
```

建立整合資料：

```bash
python scripts/build_youth_employment_map.py
```

驗證資料品質：

```bash
python scripts/validate_youth_employment_data.py
```

啟動 Dashboard：

```bash
streamlit run app.py
```

匯出靜態網站資料：

```bash
python scripts/export_website_data.py
```

啟動靜態網站：

```bash
cd website
python -m http.server 8080
```

打開 `http://localhost:8080`。

啟動助理後端（可選）。求職與政策助理預設均使用 deterministic mode，不需 API key：

```bash
uvicorn server.app:app --host 127.0.0.1 --port 8000
```

政策助理 API：`POST /api/policy-assistant`，body 為 `{"query":"比較板橋與淡水"}`。靜態網站無後端也可使用；加上 `?policyApi=1` 可核對 API 結果。

執行 AI deterministic tests：

```bash
python scripts/test_ai_decision_engine.py
```

執行政策助理 grounding、拒答與 AWS placeholder fallback tests：

```bash
python scripts/test_policy_assistant.py
```

建立每月歷史 snapshot。預設不覆蓋既有月份：

```bash
python scripts/create_monthly_snapshot.py --month 2026-08
```

驗證歷史資料：

```bash
python scripts/validate_historical_data.py
```

執行趨勢 deterministic tests：

```bash
python scripts/test_trend_pipeline.py
```

執行 Browser E2E：

```bash
npx playwright test
```

每月資料更新 dry run。此命令只檢查來源是否可用與 freshness，不寫入新月份：

```bash
python scripts/run_monthly_pipeline.py --month 2026-09 --dry-run
```

每月正式建立 snapshot：

```bash
python scripts/run_monthly_pipeline.py --month YYYY-MM
```

若目標月份已存在，預設會失敗；必須明確加上 `--force` 才會覆寫：

```bash
python scripts/run_monthly_pipeline.py --month YYYY-MM --force
```

月度管線測試：

```bash
python scripts/test_monthly_pipeline.py
```

時間欄位語意：

- `snapshot_month`：分析快照標籤，不等於所有來源的實際資料月份。
- `population_reference_month`：人口來源實際統計月份。
- `jobs_reference_date`：職缺列可確認的最新參考日期。
- `jobs_snapshot_as_of` / `jobs_downloaded_at`：職缺下載批次時間。
- `processed_at`：系統處理時間，不用來推測來源統計月份。

## Dashboard 功能

- KPI cards：新北市 18–35 歲青年人口、職缺刊登數、工作機會總數、每千名青年工作機會。
- 行政區互動地圖：以 `data/raw/new_taipei_districts.geojson` choropleth 呈現青年就業機會指數、青年人口、工作機會、每千名青年工作機會與平均薪資。
- 行政區排名：青年就業機會指數 Top 10、青年工作機會最多行政區、每千名青年工作機會最高行政區、青年人口最多行政區。
- 行政區詳細資訊：可選擇行政區查看青年就業機會指數、四個 sub-score、青年人口、職缺、工作機會、熱門職缺、熱門產業與薪資資訊。
- 評分依據：行政區詳細資訊可展開查看四個 dimension 的計算依據與缺值處理。
- 職缺篩選：支援關鍵字、行政區、職業類別、公司名稱、最低薪資、最高薪資。
- 行政區比較：比較兩個行政區的青年就業機會指數、四個 sub-score、青年人口、工作機會與薪資。
- Data provenance / methodology：顯示資料來源、青年定義、指標公式、資料 coverage、index 權重與 normalization 方法。
- Reliability / robustness：顯示資料可靠度、排名穩定度、dimension-level reliability、「高機會・高資料可靠度」與「高潛力・需更多資料驗證」清單。
- AI 青年就業助理：支援自然語言輸入，先用 deterministic decision engine 解析條件、篩選職缺、彙總行政區與建立 evidence，再產生回答；推薦行政區會同步 highlight 在地圖上。
- 就業趨勢：讀取 `website/data/youth_employment_history.json`，顯示資料月份、forecast readiness、整體趨勢摘要、category demand summary 與行政區「與前期相比」。目前只有一個真實 snapshot 時，明確顯示「尚無前期資料」。
- 整合資料表：直接讀取 `data/processed/youth_employment_map.csv`。

另有靜態網站版本：

- `website/index.html`
- `website/app.js`
- `website/styles.css`
- `website/data/youth_employment_map.json`
- `website/data/new_taipei_districts.geojson`

## 已知資料限制

- 青年人口目前使用內政部戶政司 ODRP014 民國 115 年 7 月資料，從村里單一年齡人口加總至行政區。
- 目前職缺資料整合台灣就業通 OpenData 與行政院人事行政總處事求人資料。未授權或無公開 API 的民間求職網站不進行爬取，可由正式 API 或匯出檔接入。
- 目前已具備新北市 29 行政區 GeoJSON，可支援 choropleth 地圖。
- `job_postings` 與 `job_openings` 不會被混用；事求人資料中 `NUMBER_OF` 對應 `job_openings`。
- 薪資指標只使用可解析月薪；面議、未知、空值與非月薪資料不當成 0 元。
- 公部門資料的 `Work_Type` 數字代碼沒有在 repository 內找到可確認代碼表，因此不猜測其全職/兼職意義。
- 青年就業機會指數 v1 是 prototype composite indicator，不是官方政府指標、官方排名或 AI 預測。
- `jobs_per_1000_youth` 目前表示「每千名青年的台灣就業通與公部門事求人工作機會」，仍不是所有民間求職網站的完整市場。
- 目前歷史資料只有 `2026-08` 一個 snapshot period，尚不足以計算 MoM、連續下降或任何 forecast；系統不會用 synthetic data 補缺失月份。

## 青聚 AI 政策助理 MVP

點擊網頁右下角的「青聚小幫手」浮動角色即可展開政策助理；按 × 或 Esc 收起，問題與回答會保留。支援行政區資料查詢、二區／多區比較、指標解釋及政策觀察。既有求職助理保留。數值、Index、可靠度與排序由既有 Python decision layer 提供；不使用外部 LLM API。

資料更新並完成原有 validation 後，請更新政策助理衍生資料：

```bash
python scripts/export_policy_catalog.py
python scripts/export_policy_catalog.py --check
python scripts/test_policy_assistant.py
npm run build
```

`npm run build` 需要 Python 與專案 Python 依賴，會拒絕部署過期 catalog。可用 `PYTHON` 指定 Python 執行檔。靜態網站使用 HTTPS 或 localhost（來源核對使用 Web Crypto）。政策助理固定使用正式 current dataset，並明示自己的資料期間，不跟隨地圖篩選或歷史月份切換。

完整 audit、實作架構、測試結果與 AWS 接入邊界見 [政策助理報告](docs/policy_assistant_mvp.md)。
