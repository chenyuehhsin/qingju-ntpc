# 系統架構

1. `frontend/app.py` 接收職類、工作地點、租屋預算與通勤上限。
2. `backend/recommendation.py` 讀取行政區摘要及職類彙整，產生 3 個推薦與解釋。
3. `backend/visualization.py` 使用行政區 GeoJSON 建立工作機會、租屋成本地圖與散點圖。
4. `data/raw/` 保存推薦執行時仍需查詢的職缺明細；`data/processed/` 保存已整理的行政區指標與邊界。

目前交通輸入尚未參與排名。未來加入交通矩陣時，應在 `backend/` 新增獨立交通模組，避免將計算邏輯直接寫入介面。
