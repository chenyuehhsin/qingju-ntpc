# 青聚新北｜青年就業 × 安居機會地圖

「青聚新北」是一套面向 18–35 歲青年的 Streamlit Prototype。使用者輸入工作職類、工作地點、可接受租屋成本與最大通勤時間後，系統會推薦 3 個新北市行政區，並以地圖比較工作機會和租屋成本。

## 專案結構

```text
qingju-newtaipei/
├── data/
│   ├── raw/                 # 推薦時使用的原始職缺資料
│   └── processed/           # 行政區摘要、資料描述與地圖邊界
├── notebooks/               # 探索性分析與資料驗證筆記
├── backend/                 # 推薦、行政區標準化及視覺化邏輯
├── frontend/                # Streamlit 使用者介面
├── scripts/                 # 啟動與快速驗證腳本
├── docs/                    # 架構及資料說明
├── .kiro/
│   └── steering/            # Kiro 專案規範
├── requirements.txt
└── README.md
```

## 本機執行

建議使用 Python 3.11 或 3.12：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run frontend/app.py
```

也可以在 Linux/macOS 執行：

```bash
./scripts/run_app.sh
```

## 快速驗證

```bash
python scripts/smoke_test.py
```

驗證內容包括產生 3 個推薦，以及建立工作、租屋與散點圖。

## 部署到 Streamlit Community Cloud

將整個專案推送到 GitHub，並在 Streamlit Community Cloud 將 Main file path 設為：

```text
frontend/app.py
```

所有執行所需資料均已收錄，不需要在部署環境重新執行資料清理。

## 目前推薦口徑

- 租屋預算：55%。
- 符合職類的公開工作機會：40%。
- 租賃資料量：5%。
- 租賃案件少於 10 件的行政區不納入推薦。
- 工作地點與通勤時間已接受輸入，但在 29 區交通時間矩陣完成前不納入排名。

公開職缺不是完整就業市場；租賃實價登錄案件也不是目前市場待租物件。結果應視為公開資料下的初步比較，不是個人實際錄取、租屋或完整宜居度保證。
