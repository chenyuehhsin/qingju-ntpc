# Youth Statistics Phase 6.1 Semantic QA

Generated: 2026-09-02

Scope: semantic QA for `data/raw/career/youth/`. Raw data was not modified. This QA uses only existing local files and marks unresolved items explicitly.

## QA Summary

| File / topic | QA status | What is confirmed from existing files | What remains unresolved |
|---|---|---|---|
| `ntpc_employed_age_structure.csv` | unresolved official metadata | Rows cover 2006-2024. The file has one year column and 20 numeric `percent*` columns. Alternating columns sum to about 100% by side, so the Phase 6 age-sex mapping is a pattern-based provisional inference. | Official column names, official age groups, official sex ordering, and exact indicator definition are not present in the raw file. Do not treat the provisional mapping as official. |
| `ntpc_unemployment_rate_by_age.csv` | unresolved official metadata | Rows cover 2006-2024. The filename suggests unemployment rate by age; values are rate-like. The file has one year column and 20 numeric `item value*` columns. | Official age groups, sex ordering, and unemployment-rate denominator/formula are not present in the raw file. Do not aggregate to 18-35. |
| `ntpc_education_by_age.csv` | partially confirmed | Year, age group, and sex fields are present. Age groups are official bins in the file. Sex values are `計`, `男`, `女`. | Chinese education-degree labels for `itemvalue4` through `itemvalue31` are not present in the raw file. Phase 6 cannot name degree categories without external metadata. |
| `mol_youth_employment_survey_113.pdf` | confirmed for requested indicators | The requested transition and training indicators can be verified in the PDF text, including denominator notes and whether follow-up options are multiple choice. | The PDF is a national 15-29 youth-worker survey, not New Taipei 18-35. |

## 1. `ntpc_employed_age_structure.csv`

Raw columns:

`field1`, `percent2`, `percent3`, ..., `percent21`

Confirmed from the file:

- `field1` ranges from 2006 to 2024.
- There are 20 numeric percentage columns.
- The raw CSV does not include Chinese labels for `percent2` through `percent21`.
- In 2006, all 20 percentage columns sum to about 200. Alternating columns sum to about 100 and 100.
- In 2024, all 20 percentage columns sum to about 199.9. Alternating columns sum to about 100 and 99.9.

QA interpretation:

- The previous Phase 6 mapping to ten age groups by two sex columns is plausible as a pattern inference, but it is not officially confirmed from existing files.
- Status: unresolved.
- Use only as provisional age-structure context until source metadata is available.

Required wording correction:

- Correct: "15-39 provisional proxy share within the employed-age-structure table declined."
- Incorrect: "youth employment rate declined."
- This file describes a structure/share among employed people, not the employment rate of young people.

## 2. `ntpc_unemployment_rate_by_age.csv`

Raw columns:

`field1`, `item value2`, `item value3`, ..., `item value21`

Confirmed from the file:

- `field1` ranges from 2006 to 2024.
- There are 20 numeric columns.
- The filename suggests the indicator is unemployment rate by age.
- The raw CSV does not include Chinese labels for the 20 rate columns.

Unresolved:

- Official age groups.
- Official sex ordering.
- Exact unemployment-rate denominator and formula.
- Whether the 20 columns are age-sex pairs cannot be confirmed from existing files alone.

QA interpretation:

- Current Phase 6 long output should remain marked as provisional.
- Do not calculate a combined 18-35 unemployment rate from this file.
- Do not average or weight groups into a policy metric until official column metadata is recovered.

## 3. `ntpc_education_by_age.csv`

Confirmed age groups:

- `15歲以上總人口`
- `15~19歲`
- `20~24歲`
- `25~29歲`
- `30~34歲`
- `35~39歲`
- `40~44歲`
- `45~49歲`
- `50~54歲`
- `55~59歲`
- `60~64歲`
- `65歲以上`

Confirmed sex values:

- `計`
- `男`
- `女`

Confirmed years:

- 1998-2024

Unresolved education metadata:

- The raw CSV uses generic `itemvalue4` through `itemvalue31`.
- Existing files do not provide Chinese labels for each education-degree column.
- `itemvalue4` appears to behave like a total column in inspected rows, but this is still not a complete official metadata definition for all education columns.

QA interpretation:

- Age groups and sex values can be used as-is.
- Exact 18-35 cannot be produced because the file uses 5-year bins.
- Education-degree structure cannot be named safely in Phase 6.1 without metadata.

## 4. MOL 113 Youth Labor Survey Indicators

Source file: `mol_youth_employment_survey_113.pdf`

Survey scope:

- National youth-worker survey.
- Age scope: 15-29.
- Not New Taipei-only.
- Not exact 18-35.

### 33.9% 有打算轉換工作

Confirmed from PDF:

- Topic: 青年勞工打算轉換工作情形.
- Main result: 66.1% want to continue in current job; 33.9% have an intention to change jobs.
- Denominator: all youth workers in the survey table.
- Questionnaire wording: currently whether the respondent has an intention to change jobs.
- Multiple choice: the yes/no intention itself is not multiple choice. Follow-up reasons among those intending to change jobs are "可選1至3項".

QA status: confirmed.

### 50.8% 近一年有參加教育訓練

Confirmed from PDF:

- Topic: 青年勞工近一年參加教育訓練情形.
- Main result: 50.8% participated in education/training in the past year; 49.2% did not.
- Denominator: all youth workers in the survey table.
- Questionnaire wording includes education/training provided by the workplace.
- Multiple choice: participation yes/no is not multiple choice. Training items among participants are multiple choice.

QA status: confirmed.

### 20.8% 不知道哪裡有提供訓練課程的機構

Confirmed from PDF:

- Topic: reason for not participating in training.
- Denominator: youth workers who did not participate in training.
- Question type: the questionnaire states the main reason for non-participation is single choice.
- This item is one of the listed non-participation reasons.

QA status: confirmed.

### 8.1% 參加訓練的費用太高，負擔不起

Confirmed from PDF:

- Topic: reason for not participating in training.
- Denominator: youth workers who did not participate in training.
- Question type: single choice main reason for non-participation.
- This item is one of the listed non-participation reasons.

QA status: confirmed.

## Phase 6 Document Corrections Made

The generated Phase 6 script and reports were updated so that:

- Employment CSV column labels are marked unresolved instead of official.
- Unemployment CSV column labels are marked unresolved instead of official.
- The 15-39 employed table statement is framed as age-structure change only.
- The report explicitly says this is not evidence of youth employment-rate decline.
- Charts using employment/unemployment proxy labels now say provisional / unresolved mapping.

## Remaining Manual Review Needs

- Official metadata for `ntpc_employed_age_structure.csv`.
- Official metadata for `ntpc_unemployment_rate_by_age.csv`.
- Chinese education-degree labels for `ntpc_education_by_age.csv`.
- Source organization and source URL for the three New Taipei CSVs, if not recoverable from existing project catalog.
