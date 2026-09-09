# 青聚 AI 政策助理 MVP：Audit 與完成報告

本次新增 Dashboard「青聚 AI 政策助理」，提供行政區查詢、多區比較、指標解釋與政策觀察。正式模式完全 deterministic，不需要 AWS credentials；既有求職助理保留，OpenAI 依賴與呼叫已移除。

## CURRENT_ARCHITECTURE（修改前盤點）

| 項目 | 實際實作與發現 |
|---|---|
| 前端 | `website/index.html`、`app.js`、`styles.css`；原生 JavaScript，靜態資料載入、地圖、排名、職缺、比較與歷史選擇。另有 `app.py` Streamlit 入口。 |
| 後端 | 可選 FastAPI `server/app.py`，原有 `/health`、`POST /api/assistant`；靜態網站預設使用本地求職引擎。 |
| AI decision engine | `src/ai_decision_engine.py`，已有 `Dataset`、`load_dataset`、`compare_districts`、`district_metric_evidence`、`top_by_metric`、`policy_insight`、歷史及時間證據。瀏覽器 `app.js` 有求職用途的對應實作。 |
| 正式資料 | `website/data/youth_employment_map.json` 含 29 區 `records`、`jobs_by_district`、`provenance`。正式 CSV 在 `data/processed/`。 |
| 青年人口 | 內政部戶政司單一年齡人口，18–35 歲彙總；沒有以五歲年齡組估算。 |
| Pipeline | `src/data_loader.py`、`data_cleaner.py`、`scripts/build_youth_employment_map.py` 讀取真實來源；`export_website_data.py` 匯出網站資料與方法。 |
| Opportunity Index | `src/metrics.py`：機會 40%、薪資 25%、多樣性 20%、全職比例 15%；缺失維度重新正規化。網站 provenance 已含正式 structured definitions。 |
| Reliability | 同檔 `RELIABILITY_CONFIG`、log saturation／coverage；樣本分析在 `index_sample_size_analysis.csv`，敏感度分析在 `index_reliability_analysis.json`。不等同就業品質。 |
| Temporal pipeline | `run_monthly_pipeline.py`、`create_monthly_snapshot.py`、`src/sources/`；既有 `data/history/2026-08/`、`data/raw_snapshots/2026-08/` 與 history JSON。 |
| Provenance | `data/raw/source_manifest.json` 記錄來源說明；`data/history/2026-08/source_manifest.json` 包含來源日期、檔案、row count 與 SHA-256。 |
| 時間語意 | `snapshot_month` 是分析標籤；`population_reference_month` 是人口統計月份；`jobs_reference_date` 是職缺參考日期；`jobs_snapshot_as_of` 是下載時間；`processed_at` 只是處理時間。 |
| 原有測試 | 資料／歷史驗證、6 項決策引擎測試、6 項趨勢測試、8 項月度管線測試與 13 項瀏覽器測試；另有 OpenAI fallback 測試。 |

## REUSABLE_COMPONENTS

沿用正式 JSON、決策引擎的讀取／證據／比較／排序方法、既有 policy_attention 清單、正式指標定義、29 區資料範圍、歷史 manifest 與前端 panel／table 樣式。沒有建立第二套 Index 或 ranking engine。

## MISSING_COMPONENTS

原有一般求職助理會把未辨識問題帶往推薦流程，不能直接作為嚴格政策查詢入口；缺少政策問題的白名單、统一回答 schema、完整低樣本與時間呈現。原有 OpenAI 可選呼叫不符合本次正式依賴限制。此外，既有 `policy_attention` 是人口優先的候選清單，不能直接宣稱其行政區「人口多且職缺不足」。

## IMPLEMENTATION_PLAN（已完成）

1. 新增獨立政策 query service，沿用決策引擎；共享 Python／JavaScript 問題規則。
2. Python 匯出正式證據 catalog，讓靜態網站只選取預先計算結果，不重做排名。
3. 以一致 schema 提供結論、證據、來源、時間、可靠度與限制。
4. Dashboard 增加入口及可選 API；移除 OpenAI，保留 AWS renderer／knowledge interface。
5. 完成 grounding、拒答、前後端一致性、來源時期、fallback 與 E2E 驗證。

## 1. FILES_CHANGED

| 類型 | 檔案 | 用途 |
|---|---|---|
| 新增 | `src/policy_assistant.py` | deterministic catalog、問題解析、證據查詢、回答 schema、AWS／knowledge interfaces |
| 新增 | `website/policy-contract.json` | 共用四類問題規則、欄位名稱與限制文字 |
| 新增 | `website/policy-assistant.js` | 瀏覽器問題解析、catalog 選取、分段 UI、資料驗證與 API fallback |
| 新增 | `website/data/policy_catalog.json` | 可重建的正式資料衍生證據；不含 raw jobs |
| 新增 | `scripts/export_policy_catalog.py` | 匯出及 `--check` 過期檢查 |
| 新增 | `scripts/test_policy_assistant.py` | 15 項政策助理測試 |
| 新增 | `tests/e2e/policy-assistant.spec.js` | 7 項政策助理瀏覽器測試 |
| 新增 | `docs/policy_assistant_mvp.md` | 本報告 |
| 修改 | `server/app.py`、`server/ai_service.py` | 政策 API／health；既有求職 API 改為固定 deterministic |
| 修改 | `src/config.py`、`requirements.txt`、`.env.example` | 移除 OpenAI 正式開關、套件與設定 |
| 修改 | `website/index.html`、`website/app.js`、`website/styles.css` | 新入口、啟動整合與沿用風格 |
| 修改 | `scripts/build_static_site.mjs`、`scripts/validate_all.py`、`scripts/demo_preflight.py`、`scripts/run_demo.py` | 檢查 catalog、整合測試及更新模式說明 |
| 修改 | `README.md`、`docs/ai_youth_employment_assistant.md`、`docs/demo_and_production_readiness.md` | 更新操作方式與正式服務限制 |
| 刪除 | `scripts/test_openai_fallback.py` | 以政策助理／AWS placeholder fallback 測試替代已移除的功能 |

未修改 raw、raw snapshots、人口／職缺來源值、processed CSV、歷史快照、原有 provenance hashes、Index 權重或 Reliability 規則。

## 2. ARCHITECTURE

```text
正式 website JSON + 對應 history/source_manifest + 正式方法定義
  ↓
Python build_catalog
  ├─ load_dataset / compare_districts / district_metric_evidence
  ├─ top_by_metric / policy_insight（既有排序）
  └─ 明示門檻的政策觀察篩選
  ↓
Structured Evidence Catalog
  ├─ 靜態：export_policy_catalog.py → policy_catalog.json
  │         ↓ SHA-256 核對目前正式 dataset
  │      使用者 → Dashboard → 共用規則 parser → 證據選取 → 本地 renderer → UI
  │
  └─ API：使用者 → POST /api/policy-assistant
                    → 共用規則 parser → 證據選取
                    → DeterministicRenderer → structured JSON
```

預設不需要後端。`?policyApi=1` 可呼叫 API，前端核對 intent、evidence、data_period，再使用本地可信 renderer 呈現。API 失敗、逾時或證據不一致會回退；正式 dataset 與 catalog 不一致則停用政策助理，其他 Dashboard 功能仍可使用。

## 3. DETERMINISTIC_VS_LLM_BOUNDARY

Deterministic 層負責行政區識別、資料取得、比較、沿用排序、政策條件、數值、可靠度、日期、來源與拒答。瀏覽器不計算另一組 Index／排名。

未來 Bedrock 可協助將問題轉成受限制的 structured request，以及為已選取的 evidence 提供文字解釋；不能取得整份原始 CSV 自行計算，也不能修改證據、排序、指標或來源。MVP 不呼叫任何生成式模型。

## 4. SUPPORTED_INTENTS

| Intent | 實際支援範例 |
|---|---|
| `district_lookup` | 板橋目前青年人口有多少？汐止目前有多少職缺？淡水每千名青年大約有多少職缺？新莊的薪資指標如何？ |
| `district_compare` | 比較板橋和淡水；比較汐止和淡水；板橋、新莊、淡水哪一區青年就業機會比較好？ |
| `metric_explain` | Opportunity Index 是什麼？Reliability 是什麼？為什麼淡水 Opportunity Index 比較高？為什麼平溪可靠度比較低？ |
| `policy_observation` | 哪些區值得政策觀察？哪些區青年就業機會較高？哪些區域青年人口很多但職缺相對不足？哪些區的職缺很多，但是職缺種類比較集中？ |

另外回傳 `unsupported`／`out_of_scope` 作為拒答狀態，不是新增聊天領域。此版本是有限語句規則，未辨識的改寫或「這區」等缺少明確行政區的問題會拒答，不猜測使用者意圖。助理固定使用 current 正式 dataset，不跟隨地圖月份／職缺篩選；UI 已明示。

## 5. DATA_GROUNDING

每區 evidence 來自正式 `records`，比較值透過既有 `compare_districts` 取得；三區以上逐區沿用同一投影，再附上正式維度分數、樣本與 coverage。比較最高 Index 沿用 `top_by_metric` 匯出的順序，並列最高一併列出。

指標定義直接引用 `provenance.opportunity_index`，測試與 `src/metrics.py` 的 `INDEX_WEIGHTS`／`RELIABILITY_CONFIG` 比對。輸出保留 null，不補 0。

新增兩個可解釋的觀察篩選，沒有新增分數：人口高於各區中位數且每千青年工作機會低於中位數；或職缺筆數高於中位數且職類多樣性分數低於中位數。條件、門檻及目前選取結果都進入回答。一般政策觀察仍沿用既有清單，並明示它本身不代表缺工或職缺不足。

`policy_catalog.json` 的 `dataset_sha256` 用 UTF-8／LF 正式 JSON 文字計算，兼容 Git 的 Windows CRLF 轉換。這是新增衍生資料核對機制，與歷史 manifest 中原有 raw-source SHA-256 分開。`--check` 比對完整重建結果，`npm run build` 拒絕部署過期 catalog。

## 6. RELIABILITY_HANDLING

每區輸出原有 score／level、職缺樣本數；Low 自動在結論與可靠度區顯示「適合做方向性觀察，不宜做過度推論」。Medium 提醒檢查資料支持度；缺失的 level 不視為 High。兩區／多區比較逐區保留警示，不因另一區 High 而省略。

完整 evidence 還包含 salary／diversity／stability sample size、coverage 與 dimension reliability，可從 UI「完整結構化依據」查看。沒有重算或覆寫 Reliability。

## 7. TEMPORAL_HANDLING

先核對正式 records 的人口、職缺、比率、薪資、Index、可靠度與來源檔名是否對應某期 29 區 history records，才載入該期 manifest。找不到一致快照時，保留未知日期及來源 hash，明示不能確認，不直接套用 latest label。

本期回答明確顯示：

| 欄位 | 值 |
|---|---|
| snapshot_month | 2026-08 |
| population_reference_month | 2026-07 |
| jobs_reference_date | 2026-08-29 |
| jobs_snapshot_as_of | 2026-08-30T00:45:24 |
| processed_at | 2026-08-31T02:57:11，標示為系統處理時間，非資料月份 |

來源 section 顯示實際使用的來源檔名、來源名稱、來源日期與 manifest 記錄的 SHA-256，不產生新來源或改寫原有雜湊。

## 8. HALLUCINATION_GUARDRAILS

- 完整問題必須符合共用白名單規則；未知領域、年份、預測與附加捏造指令不會落入通用推薦。
- 外縣市／全台問題先做範圍拒答；行政區僅接受正式 29 區名稱及其短名。
- 缺乏資料回覆「目前資料不足以回答這個問題。」；不生成政策或補出不存在 dataset。
- 所有 evidence 可追溯正式欄位；catalog 過期停用、API 證據不同回退。
- 正式資料無任何寫入路徑；export 只寫新的衍生 catalog。
- 政策回答只描述觀察與後續確認，明示相關性不等於因果。
- 前端所有動態文字 HTML escape；不渲染使用者指令或任意 HTML。
- 無外部 LLM SDK／呼叫；測試在禁止 socket 的情況仍可回答。

## 9. AWS_BEDROCK_READINESS

`ResponseRenderer.render(grounded_result)` 是語言層邊界。`DeterministicRenderer` 已可用；`BedrockRenderer` 明確為尚未設定的 placeholder，會回退到 deterministic，不會因環境存在任意 API key 而啟用服務。

未來要接 AWS 時，在 `BedrockRenderer` 內加入正式 AWS SDK、region、model ID、IAM 與 timeout，僅傳入已選取的 result。啟用前必須實作輸出驗證，禁止更動 evidence／來源／日期，並拒絕未被 evidence 支持的文字主張；保留現有 fallback。

`KnowledgeProvider.retrieve(topic)` 預留文件檢索介面。方法文件、指標定義、資料目錄與限制可由 S3 → Bedrock／AgentCore Knowledge Base 檢索；district statistics 仍走 deterministic service。本次没有安裝 vector DB，也沒有假稱已連線到 AWS。

## 10. TEST_RESULTS

最終測試套件：**passed 55、failed 0、total 55**。

| 套件 | passed | failed | total |
|---|---:|---:|---:|
| 政策助理 Python／API contract／JS parity | 15 | 0 | 15 |
| 既有 AI decision engine | 6 | 0 | 6 |
| 既有 trend pipeline | 6 | 0 | 6 |
| 既有 monthly pipeline | 8 | 0 | 8 |
| Dashboard Playwright（含新增政策助理 7 項） | 20 | 0 | 20 |

要求的八項核心測試：

| 核心要求 | 結果 |
|---|---|
| 板橋青年人口值等於正式 structured data | PASS |
| 板橋／淡水比較等於既有 deterministic comparison | PASS |
| Opportunity Index 定義與 implementation 常數一致 | PASS |
| 政策觀察用保留語氣，不產生政策指令 | PASS |
| 缺少心理健康 dataset 時拒答 | PASS |
| 台北市問題回覆僅涵蓋新北市 | PASS |
| Low reliability 行政區與跨區比較包含警示 | PASS |
| 人口／職缺來源時間正確，processed_at 不冒充來源月份 | PASS |

其他驗證涵蓋：三區比較、所有需求範例、觀察門檻、未知期間不推測、null 保留／查詢不改資料、Bedrock placeholder 回退、HTTP request model 的長度與空白驗證、29 區與前端結果一致、HTML 注入拒答、API 錯誤回退、stale catalog 停用與 390px 手機版無頁面橫向溢出。

正式資料與歷史資料 validators 均為 0 errors；Python compile、JavaScript syntax、catalog freshness 與 `npm run build` 通過。初次瀏覽器啟動受沙箱 `spawn EPERM` 限制，改在核准環境執行後，20 項全部通過。最後再次執行 `python scripts/validate_all.py`，完整流程回報 `VALIDATION PASSED`。

## 11. REMAINING_TODO

- 接入真實 AWS Bedrock／AgentCore：IAM、模型選擇、SDK adapter、回應 grounding 驗證與 AWS 整合測試。
- 如啟用文件檢索，建置 S3 文件匯入及 KnowledgeProvider adapter。
- 擴充自然語言改寫支援時，逐條增加共用規則與拒答回歸測試，或加入受 schema 約束的 AWS intent parser。

上述為未來擴充；目前無 credentials 的 deterministic MVP 已可直接使用。
