# AI 青年就業決策助理 v1

## Goal

「AI 青年就業決策助理 v1」用本專案現有 structured data 回答青年求職與政策洞察問題。所有推薦、排名、數字、職缺與行政區分析都先由 deterministic decision engine 計算，再產生自然語言說明。

AI 建議為資料輔助結果，不代表政府官方推薦。

## Architecture

```text
User query
  -> intent / constraint parser
  -> job filter
  -> district aggregation
  -> candidate ranking
  -> evidence pack
  -> deterministic template or optional LLM explanation
  -> dashboard UI
```

核心 engine 位於 `src/ai_decision_engine.py`。靜態網站也有對應的 browser deterministic fallback；即使沒有啟動後端或沒有 `OPENAI_API_KEY`，仍可回傳資料驅動推薦。

## Query Parsing

目前支援的 constraints：

- `target_job_keyword`
- `target_category`
- `preferred_district`
- `minimum_salary`
- `maximum_salary`
- `work_type`
- `company_keyword`

行政區只解析新北市 29 區標準名稱與去掉「區」的明確名稱，例如「新莊」會解析為「新莊區」。

## Job Filtering

職缺資料來自 `website/data/youth_employment_map.json` 的 `jobs_by_district`。可用欄位包括 `title`、`company`、`district`、`address`、`category`、`openings`、`salary_min`、`salary_max`、`salary_text`、`work_type`、`deadline`、`updated_at`、`url`。

薪資條件只使用可解析薪資資料。未知薪資不會被當成 0，也不會被宣稱符合「至少 X 元」。

## Personal Match Score

`personal_match_score` 與 `youth_employment_opportunity_index` 完全分開。

初版權重集中在 `PERSONAL_MATCH_WEIGHTS`：

```text
matching job availability: 50%
salary match: 20%
overall opportunity index: 15%
reliability: 15%
```

availability 由 matching openings 與 matching postings 組成，salary 使用符合條件職缺的薪資中位數，各 component 轉為 0-100 後加權。

## Evidence Pack

每次回答都會建立 evidence，例如：

```json
{
  "district": "汐止區",
  "matching_job_postings": 42,
  "matching_job_openings": 95,
  "matching_company_count": 28,
  "matching_median_salary": 43000,
  "opportunity_index": 80.3,
  "reliability": 97.7,
  "rank_stability": 88.0
}
```

網站會在「查看分析依據」中顯示 evidence table 與 JSON 摘要。

## Reliability Integration

Index 與 Reliability 是不同概念。高 Index 但 Low reliability 的行政區會被標示為需要謹慎解讀；回答不可直接宣稱該區就是最適合青年就業的地方。

## LLM Role

後端 `server/app.py` 提供 `POST /api/assistant`。如果環境有 `OPENAI_API_KEY`，`server/ai_service.py` 可用 Evidence Pack 產生自然語言說明；如果沒有 API key，使用 deterministic template。

LLM 不是 ranking engine。排名、推薦與數字均來自 deterministic engine。

## Hallucination Safeguards

LLM prompt 明確限制：

- 不可 invent job
- 不可 invent salary
- 不可 invent company
- 不可 invent district metrics
- 不可 invent government policy
- 不可 invent data source
- 不可 invent commute time

Evidence 不足時回答「目前資料不足以判斷。」

## Limitations

- 目前只使用 repository 已存在的新北市 29 區資料。
- 民間求職網站若無正式 API 或授權匯出檔，不會任意爬取。
- `preferred_district` 目前用於理解使用者所在地，不等同於通勤時間推估。
- 個人化分數是 prototype decision aid，不是官方排名。
