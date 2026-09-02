# 青年就業機會指數 Youth Employment Opportunity Index v1

## 1. 指標目的

青年就業機會指數 v1 用於比較新北市 29 個行政區的青年就業機會條件。它是 prototype composite indicator，不是官方政府指標、官方排名、AI 預測，也不是青年幸福指數。

指數設計原則是可解釋、可追溯、可拆解、可比較。每個行政區的總分都可以拆成工作機會、薪資、職類多樣性、工作穩定性四個 dimension。

## 2. 資料來源

- 青年人口：內政部戶政司「村里戶數、單一年齡人口（新增區域代碼）」原始檔 `data/raw/ris_village_single_age_ntpc_11507_page1.json`。
- 職缺資料：勞動部勞動力發展署「台灣就業通網站職缺清單」原始檔 `data/raw/taiwanjobs/*.xml`。
- 公部門職缺：行政院人事行政總處「事求人機關徵才資料」原始檔 `data/raw/dgpa_public_sector_jobs.xml`。
- 行政區邊界：新北市政府行政區 ArcGIS 圖層 `data/raw/new_taipei_districts.geojson`。

青年定義固定為 18-35 歲。

## 3. 四個 Dimensions

### Opportunity Score

工作機會密度，來源是 `jobs_per_1000_youth`。

```text
jobs_per_1000_youth = job_openings / youth_population_18_35 * 1000
```

`job_openings` 是需求人數，不是職缺刊登筆數。

### Salary Score

薪資水準，來源是 `median_salary`。薪資只使用可解析的月薪資料；面議、未知、空值不會當作 0 元。

### Job Diversity Score

職類多樣性，來源是 `jobs_by_district.category` 的分布，不只使用 `top_job_category`。

### Employment Stability Score

工作穩定性，來源是可辨識的 `work_type`。目前資料中可辨識值為「全職」與「兼職」，因此使用全職比例。

## 4. 原始公式

Job Diversity 使用 normalized Shannon entropy：

```text
H = -sum(p_i * ln(p_i))
job_diversity_score = H / ln(number_of_categories) * 100
```

如果只有一個 category，分數為 0。如果沒有可辨識 category，分數為 null。

Employment Stability：

```text
employment_stability_score = full_time_jobs / jobs_with_known_work_type * 100
```

如果沒有可辨識 work_type，分數為 null。

## 5. Normalization

Opportunity 與 Salary 先針對新北市 29 區做 percentile rank，轉成 0-100 分。

```text
score = (rank - 1) / (valid_district_count - 1) * 100
```

採用 percentile rank 是為了避免單一極端值讓其他行政區全部擠在低分。缺值不參與排名，也不會被當成 0。

Job Diversity 與 Employment Stability 本身已是 0-100 的比例或 entropy score，因此直接作為 sub-score。

## 6. Weighting

v1 權重集中定義在 `src/metrics.py` 的 `INDEX_WEIGHTS`：

```text
Opportunity Score: 40%
Salary Score: 25%
Job Diversity Score: 20%
Employment Stability Score: 15%
```

Composite formula：

```text
youth_employment_opportunity_index =
  opportunity_score * 0.40 +
  salary_score * 0.25 +
  job_diversity_score * 0.20 +
  employment_stability_score * 0.15
```

## 7. Missing-Data Handling

缺失 dimension 不會被當成 0。

如果某行政區缺少任一 sub-score，該區只使用有效 dimension，並將有效權重重新 normalize。

例如缺少 Stability：

```text
effective_weight_sum = 0.40 + 0.25 + 0.20
opportunity_effective_weight = 0.40 / effective_weight_sum
salary_effective_weight = 0.25 / effective_weight_sum
diversity_effective_weight = 0.20 / effective_weight_sum
```

輸出欄位：

- `index_available_dimensions`：該區實際納入 composite 的 dimension。
- `index_coverage`：該區納入的原始權重總和百分比。

## 8. Data Coverage

目前 job-level coverage 記錄在 `data/processed/job_data_quality.json`。

目前整體職缺資料：

- `category`: 3835 筆，100.0%
- `salary_min`: 3270 筆，85.3%
- `salary_max`: 2485 筆，64.8%
- `work_type`: 3538 筆，92.3%
- `company`: 3835 筆，100.0%
- `openings`: 3835 筆，100.0%

目前可辨識 `work_type` 值：

- 全職：3361 筆
- 兼職：177 筆

## 9. Limitations

- 指數只反映目前納入資料來源的職缺，不代表全部民間就業市場。
- 薪資分數只使用可解析月薪；時薪、面議、未知或空值不混入月薪中位數。
- 公部門資料的 `Work_Type` 數字代碼沒有在 repository 內找到可確認代碼表，因此不猜測其全職/兼職意義。
- 職類多樣性依目前 category label 計算；不同來源的分類粒度可能不完全一致。
- 指數是跨 29 區比較工具，不應解讀為個別青年一定能取得工作的機率。
- 小人口或小職缺樣本行政區可能因分母較小而得到較高的 `jobs_per_1000_youth`，因此需搭配 reliability layer 解讀。

## 10. Interpretation

分數越高代表在目前資料中，該行政區相對具備較高的青年就業機會條件。解讀時應同時查看四個 sub-score，避免只看總分。

例如某區總分高，可能是因為工作機會密度高，但薪資分數較低；另一區可能薪資高，但職缺數較少。Dashboard 會同時顯示總分與四個 sub-score，方便比較差異來源。

高 Index 不等於一定有較好的青年就業環境。它只表示依目前納入資料與 v1 methodology，該行政區的相對機會指標較高。

## 11. Reliability Methodology

Reliability layer 不修改 `youth_employment_opportunity_index`。它另外產生 `index_reliability_score`，表示該行政區目前有多少資料支持這個 Index。Reliability 不是就業好壞，也不是職缺品質。

Reliability 使用 sample saturation function：

```text
sample_reliability = min(1, log(1+n) / log(1+threshold)) * 100
```

採用 log saturation 是因為樣本數從 5 增加到 50 的資訊增益通常比 500 增加到 550 更大。超過 threshold 後不再持續獎勵樣本量，避免人口多或職缺多的行政區天然壟斷 100 分。

Threshold 依目前 29 區資料分布設定，集中放在 `src/metrics.py` 的 `RELIABILITY_CONFIG`：

```text
job_postings threshold: 240
job_openings threshold: 800
salary_sample_size threshold: 150
diversity_sample_size threshold: 240
stability_sample_size threshold: 220
youth_denominator threshold: 5000
```

其中 `job_postings` 與 `job_openings` 約對應目前 29 區分布的 75 分位量級；`youth_denominator` 設為 5000，只作為 small denominator 的溫和提醒，不讓大人口行政區天然取得滿分。

## 12. Dimension-Level Reliability

Opportunity reliability：

```text
0.55 * sample_reliability(job_postings, 240)
+ 0.35 * sample_reliability(job_openings, 800)
+ 0.10 * sample_reliability(youth_population_18_35, 5000)
```

Salary reliability：

```text
0.70 * sample_reliability(salary_sample_size, 150)
+ 0.30 * salary_data_coverage
```

Diversity reliability：

```text
0.70 * sample_reliability(diversity_sample_size, 240)
+ 0.30 * category_data_coverage
```

Stability reliability：

```text
0.70 * sample_reliability(stability_sample_size, 220)
+ 0.30 * work_type_data_coverage
```

Composite reliability 使用 v1 dimension 權重重新加權：

```text
index_reliability_score =
  opportunity_reliability * 0.40 +
  salary_reliability * 0.25 +
  diversity_reliability * 0.20 +
  stability_reliability * 0.15
```

缺值不當成 0；若某 reliability dimension 缺失，會用可用 reliability dimension 重新 normalize。

Reliability level：

```text
High >= 80
Medium >= 60
Low < 60
```

網站中文顯示為：高、中、低。

## 13. Sample Size Handling

每區輸出：

- `salary_valid_count`
- `category_valid_count`
- `work_type_valid_count`
- `salary_sample_size`
- `diversity_sample_size`
- `stability_sample_size`
- `company_count`

`salary_sample_size` 等於可解析月薪筆數。`diversity_sample_size` 等於可辨識 category 筆數。`stability_sample_size` 等於可辨識 work_type 筆數。

完整 sample-size table 輸出在 `data/processed/index_sample_size_analysis.csv`。

## 14. Small Denominator Limitation

`jobs_per_1000_youth` 使用青年人口作為分母。當行政區青年人口很少時，少量職缺也可能推高每千名青年工作機會。

因此 reliability layer 另外檢查：

- `youth_population_18_35` 與 `jobs_per_1000_youth` 的 correlation
- `job_openings` 與 `jobs_per_1000_youth` 的 correlation
- `jobs_per_1000_youth` Top 10 的青年人口與 job_openings

Correlation 只作為描述性診斷，不代表因果。

## 15. Sensitivity Analysis

Baseline 權重不修改 v1 index：

```text
Scenario A baseline: 40 / 25 / 20 / 15
Scenario B opportunity-heavy: 50 / 20 / 15 / 15
Scenario C salary-heavy: 30 / 35 / 20 / 15
Scenario D quality/diversity-heavy: 30 / 20 / 30 / 20
```

每個 scenario 都重新計算 29 區排名，但不覆蓋 baseline index。輸出：

- `baseline_rank`
- `scenario_b_rank`
- `scenario_c_rank`
- `scenario_d_rank`
- `rank_min`
- `rank_max`
- `rank_range`

## 16. Rank Stability

`index_rank_stability` 用來描述合理權重變動下排名是否穩定。它不是 `employment_stability_score`。

```text
index_rank_stability = (1 - rank_range / 28) * 100
```

29 區最大可能 rank range 是 28。rank range 越小，`index_rank_stability` 越高。

## 17. Robust High Opportunity Districts

高機會 × 高資料可靠度使用資料驅動條件：

```text
youth_employment_opportunity_index >= 29 districts 75th percentile
AND
index_reliability_score >= 80
```

高 Index + Low Reliability 使用：

```text
youth_employment_opportunity_index >= 29 districts 75th percentile
AND
index_reliability_level == Low
```

網站標記為「高機會・高資料可靠度」與「高潛力・需更多資料驗證」。不使用「最佳行政區」或「最適合青年」等過度結論。
