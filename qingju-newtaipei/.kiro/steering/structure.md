# Structure steering

- `frontend/` 只放介面與互動流程。
- `backend/` 放可獨立測試的推薦、資料標準化與視覺化邏輯。
- `data/raw/` 放仍需由程式查詢的來源資料；`data/processed/` 放部署用衍生資料。
- `scripts/` 放可重複執行的命令列工作。
- `notebooks/` 僅供探索，不作為正式應用程式相依項。
- `docs/` 記錄架構、資料口徑與限制。
