# Youth Age Harmonization Rules

Generated: 2026-09-02

Target policy-analysis age concept: 18-35.

## Rule Classes

- Exact: the raw file has single-year ages or exact bins that can be summed to 18-35 without interpolation.
- Partial: the raw file covers only part of 18-35, such as 20-34. It must be labeled as a subset, not as 18-35.
- Proxy: the raw file uses nearby or official groups, such as 15-29, 15-24, or 35-39. It can support context but cannot be relabeled as 18-35.

## Applied Rules

| Dataset | Rule | Phase 6 treatment |
|---|---|---|
| `population_single_age_by_area_2026.csv` | Exact | Sum single ages 18 through 35 for New Taipei. |
| `ntpc_education_by_age.csv` | Partial / Proxy | Use official bins as-is. 20-34 is a partial subset; 15-39 is a broad proxy. Named education-category labels are unavailable in the raw CSV. |
| `ntpc_employed_age_structure.csv` | Proxy / unresolved labels | Raw headers do not confirm official age/sex labels. Current long output keeps provisional column mapping for QA only. Treat as age-structure context, not youth employment rate. |
| `ntpc_unemployment_rate_by_age.csv` | Proxy / unresolved labels | Raw headers do not confirm official age/sex labels. Plot provisional groups separately; do not average into an 18-35 rate without denominators and metadata. |
| `mol_youth_employment_survey_113.pdf` | Proxy | Use as national 15-29 youth-worker survey evidence. Do not treat as New Taipei 18-35. |

## New Taipei Population Scope Comparison

| period | area | age_scope | harmonization_status | population |
| --- | --- | --- | --- | --- |
| 109年 10月 | 新北市 | 18-35 | Exact | 942897 |
| 109年 10月 | 新北市 | 15-29 | Proxy / MOL survey comparator | 716343 |
| 109年 10月 | 新北市 | 20-34 | Partial subset | 799334 |
| 109年 10月 | 新北市 | 15-39 | Broad proxy | 1322828 |

## Guardrails

- Do not treat 15-24, 15-29, 20-34, 35-39, or 15-39 as exact 18-35.
- Do not interpolate single ages into grouped labor-market rates in Phase 6.
- When source headers are generic, keep raw column names and mark inferred labels unresolved until official metadata is available.