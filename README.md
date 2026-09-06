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
