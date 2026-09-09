# Youth Statistics Phase 6

Generated: 2026-09-02

This is a first-pass youth evidence inventory and descriptive analysis. It does not change raw data, v1-v4 career methodology, UI, or policy recommendations.

## Files Used

| filename | harmonization_status | intended_use |
| --- | --- | --- |
| population_single_age_by_area_2026.csv | Exact for 18-35 | New Taipei 18-35 population size and age/sex structure |
| ntpc_education_by_age.csv | Partial / Proxy for 18-35 | Education-related age/sex table; named degree categories require external metadata confirmation |
| ntpc_employed_age_structure.csv | Proxy for 18-35; official labels unresolved | Descriptive employment age-structure trend only; not an employment-rate measure |
| ntpc_unemployment_rate_by_age.csv | Proxy for 18-35; official labels unresolved | Descriptive unemployment-rate trend using provisional age groups |
| mol_youth_employment_survey_113.pdf | Proxy for 18-35 | Job-search, transition intention, credential, and training participation statistics |

## First-Pass Findings

1. New Taipei has 942,897 residents aged 18-35 in the exact single-age population table for `109年 10月`; the split is 51.5% male and 48.5% female.
2. Age-scope choice materially changes the denominator: the 15-29 proxy is much smaller than 18-35, while the 15-39 broad proxy is much larger.
3. Within the New Taipei employed-age-structure table, the provisional 15-39 proxy share declined from 2006 to 2024 for both column sides labeled male/female by pattern inference (50.7% to 40.0% and 60.0% to 43.9%). This describes age composition within employed people, not a youth employment-rate decline.
4. In the provisional 2024 unemployment proxy, the 15-24 column group is highest; rates are lower in the 25-29, 30-34, and 35-39 provisional groups.
5. The MOL 113 national 15-29 youth-worker survey provides directly relevant signals for career exploration: transition intention, job-search barriers, credential holding, and training participation/barriers.

## New Taipei 18-35 Population

- Exact source: `population_single_age_by_area_2026.csv`, using row labels for `109年 10月`.
- New Taipei age 18-35 population: 942,897.
- Male: 485,794 (51.5%). Female: 457,103 (48.5%).

Largest single-age cohorts within 18-35:

| age | population |
| --- | --- |
| 35 | 59340 |
| 30 | 57680 |
| 32 | 56449 |
| 27 | 55761 |
| 28 | 55393 |

Age-scope comparison, showing why proxy ranges must not be relabeled as 18-35:

| period | area | age_scope | harmonization_status | population |
| --- | --- | --- | --- | --- |
| 109年 10月 | 新北市 | 18-35 | Exact | 942897 |
| 109年 10月 | 新北市 | 15-29 | Proxy / MOL survey comparator | 716343 |
| 109年 10月 | 新北市 | 20-34 | Partial subset | 799334 |
| 109年 10月 | 新北市 | 15-39 | Broad proxy | 1322828 |

## Employment Trend

The New Taipei employed-age table uses generic raw headers. Phase 6 keeps a provisional age-sex mapping because alternating columns sum to about 100% by side, but the official column labels are unresolved from existing files. This can describe age-structure change only; it is not a youth employment-rate measure.

- Provisional 15-39 share on the column side labeled male by pattern inference: 50.7% in 2006 to 40.0% in 2024.
- Provisional 15-39 share on the column side labeled female by pattern inference: 60.0% in 2006 to 43.9% in 2024.
- Interpretation guardrail: this is an employed-population age-structure share, not the employment rate of young people.

## Unemployment Trend

The unemployment table is shown by provisional age groups because official column labels are absent from existing files. No 18-35 aggregate unemployment rate is calculated because labor-force denominators by single age and confirmed metadata are not available.

2024 youth-related unemployment-rate proxies, averaged across the male/female columns only for compact display:

| inferred_age_group | unemployment_rate_percent |
| --- | --- |
| 15-24 | 10.1 |
| 25-29 | 5.5 |
| 30-34 | 3.75 |
| 35-39 | 2.15 |

## Education Structure

`ntpc_education_by_age.csv` covers New Taipei from 1998-2024 and uses official age bins. It can support 20-34 partial-subset analysis and 15-39 broad-proxy context, but not exact 18-35. The raw file does not include named education-category labels; Phase 6 therefore preserves raw `itemvalue*` columns and does not claim a degree-level structure such as university / senior high / junior college.

Latest available official age-bin population totals in the education table, using `itemvalue4` as the reported total column:

| age_group | value | age_harmonization_status |
| --- | --- | --- |
| 15~19歲 | 169861.0 | Proxy; includes 15-17 and misses age 18-only separation |
| 20~24歲 | 207958.0 | Partial subset of 18-35 |
| 25~29歲 | 253037.0 | Partial subset of 18-35 |
| 30~34歲 | 278776.0 | Partial subset of 18-35 |
| 35~39歲 | 279657.0 | Proxy; includes 36-39 |

## MOL 113 Survey Extractable Topics

The PDF is a national 15-29 youth-worker survey. It is useful for job-search, transition, credential, and training context, but it is not New Taipei 18-35.

| topic | relevance | extractable_pages | age_harmonization_status |
| --- | --- | --- | --- |
| 初次尋職前做過的準備 | job search preparation | pages 19-20, 83 | Proxy for 18-35 |
| 認為對初次尋職有幫助的就業資訊 | job-search information needs | pages 21, 85 | Proxy for 18-35 |
| 初次尋職時選擇工作的考慮因素 | job choice factors | page 22 | Proxy for 18-35 |
| 初次尋職遭遇的困難 | job-search barriers | page 23 | Proxy for 18-35 |
| 青年勞工打算轉換工作情形 | transition intention and reasons | pages 25, 95 | Proxy for 18-35 |
| 青年勞工持有證照情形 | credential holding | pages 26, 102-105 | Proxy for 18-35 |
| 青年勞工過去一年參加教育訓練情形 | training participation and barriers | pages 27, 107-109 | Proxy for 18-35 |

Selected extracted statistics:

| indicator | percent | denominator_note | survey_age_scope |
| --- | --- | --- | --- |
| 認為就業資訊有助於初次尋職 | 85.4 | all | 15-29 youth workers |
| 技能不足 | 31.0 | among difficulty responses | 15-29 youth workers |
| 有打算轉換工作 | 33.9 | all | 15-29 youth workers |
| 近一年有參加教育訓練 | 50.8 | all | 15-29 youth workers |
| 不知道哪裡有提供訓練課程的機構 | 20.8 | among non-participants | 15-29 youth workers |
| 參加訓練的費用太高，負擔不起 | 8.1 | among non-participants | 15-29 youth workers |

## Charts

- `outputs/career/youth_statistics/ntpc_population_18_35_by_age_109_10.png`
- `outputs/career/youth_statistics/ntpc_population_18_35_by_sex_109_10.png`
- `outputs/career/youth_statistics/ntpc_employed_youth_proxy_trend_2006_2024.png`
- `outputs/career/youth_statistics/ntpc_unemployment_youth_proxy_trend_2006_2024.png`
- `outputs/career/youth_statistics/mol_youth_job_transition_training_stats_113.png`

## Data Limitations

- Exact 18-35 is available only for the population single-age table.
- Employment and unemployment age labels are unresolved from existing files; current long outputs use provisional pattern inference only.
- Education degree-category labels are not present in the raw CSV headers, so named degree composition remains a manual-review item.
- MOL 113 survey results are national 15-29 youth-worker statistics and should not be interpreted as New Taipei 18-35.

## Career Policy Lens-Ready Inputs

These are descriptive inputs that can be connected to a later Career Policy Lens without making policy recommendations in Phase 6:

- Exact New Taipei 18-35 denominator and sex/age structure.
- Age-scope harmonization flags so later analysis can separate Exact, Partial, and Proxy evidence.
- Youth-related employment and unemployment trends only after unresolved labor-table column labels are confirmed.
- MOL survey indicators on job-search uncertainty, transition intention, credential holding, training participation, and training access barriers.
- Manual-review needs for education category metadata and labor-table column labels.