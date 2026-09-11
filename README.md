# 青聚新北

青年安居 × 就業 × 交通機會推薦

## MVP
輸入青年偏好條件，整合新北居住、就業與交通資料，
推薦適合落腳的行政區，並提供 AI 解釋。

## Core dimensions
- Housing
- Employment
- Transportation

## Run the demo

The Streamlit entry point is `app/app.py`. A fresh clone can run the existing
preset Demo without external APIs, local raw-data caches, or credentials.

```bash
git clone <repo-url>
cd qingju-ntpc
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/app.py
```

## 青聚小幫手

在「青年職涯探索」、「青年安居推薦」及「青年局 Policy Lens」三個頁面右下角點擊芽苗角色，即可展開青聚小幫手。可詢問網站使用方式、護理轉職方向、行政區青年人口／职缺／租金、比較行政區及既有政策訊號。點擊外側或按 Esc 收起；切換頁面會保留最近一次問答。

小幫手直接使用這個 Streamlit 網站的既有資料與 Policy Lens 計算，不需要另啟 FastAPI、靜態地圖網站或外部 LLM API。啟動後預設網址為 `http://localhost:8501`。

離線驗證：

```bash
python scripts/product/test_qingju_assistant.py
```

整合說明見 [docs/qingju_assistant_integration.md](docs/qingju_assistant_integration.md)。

### Milestone 3 — Agent-ready policy tools

小幫手已接入本機 deterministic planner、九個 schema-defined tools 與 query-only session。
可問「薪資最高前5區」、先「比較板橋和淡水」再問「那薪資呢？」。
Opportunity Index、多樣性、穩定度及行政區可靠度分級尚未存在於本網站，會明確拒答；
不能將舊地圖的方法套入。預測只回 `not_ready`，AWS 尚未部署。

```bash
python scripts/product/test_policy_agent.py
python scripts/product/test_qingju_assistant.py
python scripts/product/evaluate_policy_agent.py
python scripts/product/forecast_readiness.py
```

測試使用 Streamlit/Altair 現有依賴的 `jsonschema` 做獨立 schema 驗證，未增加 runtime dependency。
方法文件與 schema 修改後執行 `python scripts/product/build_agent_assets.py` 更新匯出及文件 hash。
詳見 [M3 報告](docs/MILESTONE3_REPORT.md)、[工具 schemas](docs/policy_tool_schemas.json)、
[AWS 後續計畫](docs/AWS_AGENTCORE_PLAN.md)。

The default Housing quick preset uses versioned processed data and is available
offline. Custom workplace input is an optional online Beta feature: it uses
OpenStreetMap Nominatim for geocoding and TDX MaaS for transit routing.

For custom workplace routing, provide `TDX_CLIENT_ID` and `TDX_CLIENT_SECRET`
through environment variables. On Streamlit Community Cloud, configure these
as app secrets/environment variables; the service does not read a local `.env`
file. Never commit credentials. See `.env.example` only as a local template.

## Structure

```text
qingju-newtaipei/
├── data/
│   ├── raw/
│   └── processed/
├── notebooks/
├── backend/
├── frontend/
├── scripts/
├── docs/
└── .kiro/
    └── steering/
```
