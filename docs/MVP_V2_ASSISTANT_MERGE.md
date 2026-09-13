# 青聚小幫手整合至 integration/mvp-v2

2026-09-12：以 integration/mvp-v2 的 8ea1e2a 為基準，合併 milestone4a-local 的 70a9ad2；自動合併無衝突。

保留原有設計師／服務人員職涯案例、住宅控制介面、地圖更新方式及資料。app/app.py 僅新增小幫手 import 與 render 呼叫，右下角提供 M3 本機資料問答。

合併後驗證：AWS unit/mock 30/30、Policy Agent 22/22、Streamlit AppTest 8/8、deterministic evaluation 36/36、KB hash 13/13；git diff --check 通過。既有 data、outputs、requirements、data_loader、styles、career_evidence_viewer 與合併前目標分支內容一致。

AWS_DEPLOYMENT_BLOCKED：本次未啟用 AWS、未建立雲端資源。docs/MILESTONE4A_REPORT.md 與 AWS_LOCAL_TEST_RESULTS.json 為原 Milestone 4A 歷史報告；此文件記錄此次分支整合驗證。

Streamlit 若已追蹤 integration/mvp-v2，推送會交由平台自動更新；實際部署狀態需另於線上網站驗證。入口為 app/app.py。
