# 青聚新北網站：小幫手整合

## 正確的網站與入口

此版本以 GitHub `main` 的 `3d3cca0` 為基礎，入口是 `app/app.py`，頁面包含青年職涯探索、青年安居推薦、青年局 Policy Lens。先前獨立「新北市青年就業地圖」的 `website/index.html` 不屬於這個網站，本次不將它、它的資料或後端搬進來。

`main()` 在共用樣式套用後呼叫 `render_qingju_assistant(current_page)`，位於任何頁面分流 return 之前，因此三個頁面都會顯示小幫手。使用 Streamlit 1.45.1 原生 popover／form／session_state，沒有跨 iframe 控制、瀏覽器注入或第二個網站。

## 互動

右下角芽苗角色為開啟按鈕，點擊展開問答；點擊外側、再次點擊或 Esc 收起。頁面切換與 rerun 保留最近一次問答，面板顯示目前所在頁面。小螢幕限制面板寬高，內容獨立捲動；減少動態效果偏好會停用浮動動畫。

## 資料與責任分離

- `app/assistant_service.py`：只讀檢索、有限語句解析與有依據回答。
- `app/components/qingju_assistant.py`：原生 Streamlit UI 與狀態。
- `assets/illustrations/qingju_assistant.svg`：本地芽苗角色，無外部圖片依賴。
- `load_youth_job_opportunity_data()`：沿用網站每千名青年求才人數計算；沒有租金 benchmark 的行政區未納入既有分析時，不另造一套比率。
- `build_policy_intervention_matrix()`：原樣沿用網站透明規則與觀察文字；只顯示訊號／觀察／行政區，不把可評估工具轉為政策命令。
- 職涯方向沿用 `target_domain_evidence_rank`，不產生新的轉職分數或成功率。

一般行政區查詢保留 29 區人口及職缺，即使缺少租金也不丟掉該區。缺值保留 null。每次回答附資料期間、來源與衍生檔 SHA-256；人口來源另外保留既有 metadata 的 raw response hashes。處理／生成時間不當資料月份。

這個網站沒有另一個地圖專案的 Opportunity Index 或統一 Reliability 分數。小幫手會明確說明不能套用，改為顯示本網站的樣本數、職涯 mapping confidence 與限制。這是網站原有資料差異，不修改現有指標或補造分級。

沒有外部 LLM dependency，也不需要 API key。未來語言模型應只接收 `answer_question()` 的結構化結果，數字／排序／政策規則仍留在既有 deterministic 層；正式服務僅規劃 AWS。

## 驗證範圍

`scripts/product/test_qingju_assistant.py` 使用 unittest 與 Streamlit 原生 AppTest，覆蓋青聚正式資料值、比較比率、政策規則重用、缺值／未知問題／外縣市拒答、不混用舊指數、既有職涯證據順序、三個真實頁面有小幫手、原生表單作答及跨頁保留結果。

瀏覽器另外確認真實青聚頁面標題、右下角位置、popover 展開與 Esc 收起、資料查詢、三頁切換及手機版面板大小。原有安居／職涯／Policy Lens 元件與原始資料未重寫。
