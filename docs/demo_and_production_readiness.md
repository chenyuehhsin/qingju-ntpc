# Demo And Production Readiness

本文件說明「新北市青年就業地圖」Competition Demo & Production Readiness v1。目標是穩定、可重現、可離線展示，不改 Opportunity Index v1、Reliability methodology、Personal Match Score weights、raw data 或歷史 snapshot 數值。

## 1. Architecture

- Frontend：`website/index.html`、`website/app.js`、`website/styles.css`。
- Data：`website/data/youth_employment_map.json`、`website/data/youth_employment_history.json`、`website/data/new_taipei_districts.geojson`。
- Backend optional：`server/app.py` 提供 `/health` 與 `/api/assistant`。
- Deterministic AI：`src/ai_decision_engine.py`，前端也有 browser deterministic fallback。
- Monthly pipeline：`scripts/run_monthly_pipeline.py`。

核心 Dashboard 只需要 local static files，即使 backend 沒啟動也可運作。

## 2. Demo Startup

一鍵啟動：

```bash
python scripts/run_demo.py
```

功能：

- 檢查 Python dependencies。
- 檢查 required data files。
- 檢查 29 districts。
- 產生 `website/data/build_info.json`。
- 啟動 static website server。
- 視環境啟動 FastAPI backend。
- 顯示 frontend URL、backend health、政策助理 deterministic 狀態。

預設不需任何 LLM credentials：

```text
Policy assistant: deterministic
Deterministic assistant: enabled
```

## 3. Offline Behavior

核心頁面不依賴 CDN。Leaflet CDN 已從 `index.html` 移除；地圖使用 local GeoJSON 以 SVG fallback 繪製。

可離線使用：

- 新北 29 區地圖。
- KPI。
- Opportunity Index。
- Reliability。
- ranking。
- district comparison。
- filters。
- matching jobs。
- deterministic AI assistant。
- historical snapshot UI。

外部職缺 URL 只有在使用者點「查看職缺」時才會連到外部網站，不影響核心展示。

## 4. 政策助理與 AWS 擴充

後端與靜態網站均使用 deterministic explanation。OpenAI 正式依賴與呼叫已移除。
政策助理支援 `?policyApi=1`；API 異常或證據不同時回到經 SHA-256 核對的本地資料。
AWS Bedrock renderer 目前只是停用的 interface，尚未進行真實模型呼叫。
執行 `python scripts/test_policy_assistant.py` 驗證 grounding 與 fallback。

## 5. Backend Failure Handling

前端預設不呼叫 backend，使用 browser deterministic assistant。

若 URL 加上 `?assistantApi=1` 但 backend 不可用，前端會顯示：

```text
AI 語言解釋目前暫時不可用，已改用資料分析結果。
```

地圖、KPI、Index、Reliability、filters、comparison、history UI 都不受影響。

## 6. Playwright Tests

E2E 位於 `tests/e2e/`：

- `dashboard.spec.js`：首頁、29 區、無第 30 區、無 OpenStreetMap tiles、KPI、地圖指標切換、板橋點擊、ranking、comparison。
- `reliability.spec.js`：平溪區 Index 與 low reliability warning。
- `assistant.spec.js`：薪資、全職、可靠度說明、拒絕 fabricated job、backend fallback。
- `history.spec.js`：2026-08 only、forecast readiness 尚不足、MoM 尚無前期資料、temporal provenance。
- `responsive.spec.js`：1440x900、1280x720、390x844，確認無水平 overflow。
- `demo-flow.spec.js`：3 分鐘 Demo Flow。

所有測試監聽 `pageerror` 與 `console.error`，有 uncaught JavaScript error 會失敗。

## 7. Validation

一鍵驗證：

```bash
python scripts/validate_all.py
```

依序執行：

- data validation
- history validation
- AI deterministic tests
- Policy assistant tests
- trend tests
- monthly pipeline tests
- build info generation
- Python compile check
- JavaScript syntax check
- Playwright E2E，若已安裝

## 8. Preflight

比賽前執行：

```bash
python scripts/demo_preflight.py
```

檢查：

- 29 districts
- JSON exists
- GeoJSON exists
- latest snapshot valid
- index valid
- reliability valid
- AI deterministic engine valid
- history manifest valid
- no secret exposed
- frontend resources available
- backend health optional
- browser E2E passed
- performance sanity

成功輸出：

```text
DEMO READY
```

失敗輸出：

```text
DEMO NOT READY
```

## 9. Secrets

`.env` 已加入 `.gitignore`。範例檔：

```text
.env.example
```

內容只保留：

```text
DEMO_MODE=1
```

不要把真實 API key、token、password、secret 放入 repository。

## 10. Reproducibility

首次 setup：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
npm install
npx playwright install chromium
python scripts/run_demo.py
```

`website/data/build_info.json` 不含 API key、本機 username 或絕對路徑。

## 11. Demo Flow

自動化 3 分鐘 Demo Flow：

1. 開首頁。
2. 查看 KPI。
3. 切 Opportunity Index。
4. 點樹林區。
5. 查看 Index / Reliability。
6. 問「我想找月薪至少4萬的全職工作」。
7. 顯示推薦行政區。
8. 展開 evidence。
9. 切換資料可靠度。
10. 打開趨勢區。
11. 確認目前只有一個 period。

## 12. Known Limitations

- 目前只有 `2026-08` 一個真實 snapshot，不能顯示 MoM 趨勢或 forecast。
- `2026-09` 真實來源尚未發布時，pipeline 只允許 dry run，不建立假 snapshot。
- AWS 語言解釋僅為未來擴充，deterministic evidence 是核心。
- 外部職缺網站 URL 需網路才能開啟，但不影響本地 Dashboard Demo。
