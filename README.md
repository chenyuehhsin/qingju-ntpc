# 青聚新北｜2026 新北黑客松 AI 智慧城市

參賽組別：D_青年局_正在輸入中....

青年安居 × 就業 × 交通機會推薦。整合新北市的居住、就業與交通資料，協助青年與政策端在同一介面上探索轉職路徑、比較生活圈，並觀察政策訊號。

## Live demo

線上 Demo：<https://qingju-ntpc-test.streamlit.app/>

固定示範資料可離線直接使用；自訂工作地為選用的線上 Beta 功能（詳見下方說明）。

## 功能總覽

網站以 Streamlit 建置，入口為 `app/app.py`，包含三個主要頁面與一個角色小幫手：

- **青年職涯探索**：以護理師為完整示範，整合技能可轉移性、台灣職缺訊號與職訓課程證據，用雷達圖與證據卡呈現各條轉職路徑的「轉職接近度、能力沿用、學習輕鬆度、市場訊號」。不預測個人轉職成功率。
- **青年安居推薦**：依工作地與偏好（省租型 / 平衡型 / 通勤型 / 生活品質型），比較新北生活圈的租金、公共運輸通勤時間與生活機能，並在地圖上呈現 Top 生活圈。
- **青年局 Policy Lens**：分為職涯政策觀察（護理人力政策：留任改善與轉職支持）與安居政策觀察（租金、交通可達、生活機能、青年人口等行政區訊號地圖）。定位為政策初篩與資料缺口辨識，不產生排名、分數或補助金額。
- **青聚小幫手**：三個頁面右下角的芽苗角色，可詢問網站使用方式、護理轉職方向、行政區青年人口／職缺／租金、比較行政區與既有政策訊號。點擊外側或按 Esc 收起，切換頁面會保留最近一次問答。

## 資料來源與尺度

各指標保留其量測尺度與時間，並在介面標註證據等級，缺值不補造：

- **租金｜MOI**：行政區獨立套房官方租金 benchmark（行政區尺度），非即時房源。
- **通勤｜TDX MaaS**：平日情境的公共運輸通勤時間（Derived scenario），非 door-to-door。
- **生活機能｜OSM / Overpass**：候選站點周邊 800m POI 的 Derived proxy，不代表完整生活品質。
- **青年人口｜RIS 戶政司**：新北 29 行政區 Exact 18–35 人口；為行政區背景，非生活圈人口。
- **就業｜TaiwanJobs**：行政區求才人數 snapshot（Derived），非就業率或錄取機率。
- **職涯證據｜O*NET / 產業人才投資方案課程**：外部職業與課程參考，台灣職稱與制度可能不同。

## 本機執行

需要 Python 3.11。

```bash
git clone <repo-url>
cd qingju-ntpc
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/app.py
```

啟動後預設網址為 `http://localhost:8501`。全新 clone 即可用內建 preset 示範，不需外部 API、憑證或本機 raw-data 快取。

### 自訂工作地（選用的線上 Beta）

安居推薦的固定 quick preset 使用版本化的 processed 資料、可離線使用。自訂工作地為選用的線上功能，會呼叫 OpenStreetMap Nominatim 進行地址定位、TDX MaaS 計算通勤：

- 透過環境變數提供 `TDX_CLIENT_ID` 與 `TDX_CLIENT_SECRET`。
- 在 Streamlit Community Cloud 以 app secrets／環境變數設定；服務不讀取本機 `.env`。
- 切勿提交任何憑證，`.env.example` 僅供本機範本參考。

## 青聚小幫手

小幫手直接使用本網站既有的資料與 Policy Lens 計算，不需另啟 FastAPI、靜態地圖網站或外部 LLM API。它接入本機 deterministic planner、schema 定義的政策工具與 query-only session：可問「薪資最高前 5 區」，或先「比較板橋和淡水」再追問「那薪資呢？」。

本網站不存在 Opportunity Index、多樣性、穩定度或行政區可靠度分級等指標，小幫手會明確拒答，不套用舊地圖的方法；預測類問題僅回覆 `not_ready`。

離線驗證：

```bash
python scripts/product/test_qingju_assistant.py
python scripts/product/test_policy_agent.py
python scripts/product/evaluate_policy_agent.py
python scripts/product/forecast_readiness.py
```

整合說明見 [docs/qingju_assistant_integration.md](docs/qingju_assistant_integration.md)。

## 專案結構

```text
qingju-ntpc/
├── app/            # Streamlit 應用（app.py 入口、components、data_loader、政策工具、小幫手）
├── data/           # raw（不可變原始資料）/ interim / processed / reference，另含 data_catalog.csv
├── outputs/        # 由 scripts 產出的可重現分析結果（如 career 各階段）
├── scripts/        # 各主題資料處理與產品測試腳本
├── docs/           # 方法說明、資料盤點與相關文件
├── knowledge_base/ # 方法與定義的知識庫文件
├── assets/         # 頁面插圖等靜態資源
└── .kiro/          # steering、specs、hooks 等專案設定
```

## 資料治理原則

- `data/raw/` 為不可變原始資料，只可重新命名／分類／搬移，不在原地清洗或合併。
- 衍生資料寫入 `data/interim/` 或 `data/processed/`，並盡量可由程式重現。
- 保留資料來源、期間、地理範圍與缺值；不虛構未取得的資料，改以「待補」明確標示。
- 新增外部資料集時更新 `data/data_catalog.csv`。細節見 [docs/data_conventions.md](docs/data_conventions.md)。
