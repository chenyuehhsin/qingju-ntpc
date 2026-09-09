# Career Transition Market v3 Method

Purpose: add occupation taxonomy distance and TaiwanJobs market evidence to the v2 feasibility screen. This does not calculate transition success probability or a final recommendation score.

## TaiwanJobs Inventory and Quality

- Raw file: `data/raw/career/jobs/taiwanjobs_open_jobs_2026-09-01.csv`.
- Rows: 1000.
- Columns: OCCU_DESC（職務名稱）, WK_TYPE（職務性質）, CJOB1_COUNT（職務大類別代碼）, CJOB_NAME1（職務大類別名稱）, CJOB2_COUNT（職務小類別代碼）, CJOB_NAME2（職務小類別名稱）, JOB_PERSON（雇用人數）, STOP_DATE（應徵截止日期）, JOB_DETAIL（工作內容）, CITYNAME（工作地點）, EXPERIENCE（工作經驗）, WKTIME（工作時間）, SALARYCD（核薪方式）, NT_L（薪資範圍下限）, NT_U（薪資範圍上限）, EDGRDESC（最低學歷要求）, URL_QUERY（職缺資料URL）, COMPNAME（公司名稱）, TRANDATE（職缺更新日期）.
- Missing values by column: {'OCCU_DESC（職務名稱）': 1, 'WK_TYPE（職務性質）': 0, 'CJOB1_COUNT（職務大類別代碼）': 0, 'CJOB_NAME1（職務大類別名稱）': 0, 'CJOB2_COUNT（職務小類別代碼）': 0, 'CJOB_NAME2（職務小類別名稱）': 0, 'JOB_PERSON（雇用人數）': 0, 'STOP_DATE（應徵截止日期）': 0, 'JOB_DETAIL（工作內容）': 0, 'CITYNAME（工作地點）': 0, 'EXPERIENCE（工作經驗）': 0, 'WKTIME（工作時間）': 75, 'SALARYCD（核薪方式）': 0, 'NT_L（薪資範圍下限）': 0, 'NT_U（薪資範圍上限）': 0, 'EDGRDESC（最低學歷要求）': 0, 'URL_QUERY（職缺資料URL）': 0, 'COMPNAME（公司名稱）': 0, 'TRANDATE（職缺更新日期）': 0}.
- Salary type distribution: {'月薪': 734, '時薪': 166, '依學經歷、證照核薪(每月經常性薪資達4萬元以上)': 82, '日薪': 8, '論件計酬': 6, '部分工時(月薪)': 4}.
- Education requirement distribution: {'不拘': 381, '專科': 187, '高中': 174, '大學': 113, '高職': 106, '國中': 22, '國小': 12, '碩士': 5}.
- Experience requirement distribution: {'無': 795, '1年以上': 74, '2年以上': 55, '3年以上': 37, '5年以上': 17, '1年內': 10, '10年以上': 4, '4年以上': 3, '6年以上': 2, '15年以上': 1, '8年以上': 1, '7年以上': 1}.
- Main locations: {'台北市大安區': 136, '台北市內湖區': 135, '台北市不限': 116, '台北市中山區': 110, '台北市信義區': 94, '台北市松山區': 80, '台北市中正區': 78, '台北市北投區': 61, '台北市大同區': 53, '台北市士林區': 39}.

Salary handling: `matched_job_count` and `total_demand_persons` include all matched rows. Salary medians use only rows with `SALARYCD（核薪方式） = 月薪` and parse numeric `NT_L`/`NT_U`; hourly, daily, piece-rate, and negotiated salary rows are excluded from salary medians.

## Occupation Taxonomy Distance

O*NET-SOC codes are parsed as `major = first two digits`, `family = first five characters such as 29-11`, and `detailed = part before the decimal such as 29-1141`.

- `same_major_group`: source and target share the same two-digit SOC major group.
- `same_occupation_family`: source and target share the same `XX-YY` family prefix.
- `taxonomy_distance_level = Same / very close`: same detailed SOC code, same family, or O*NET Primary-Short related support.
- `taxonomy_distance_level = Adjacent category`: same major group or O*NET Primary-Long/Supplemental related support.
- `taxonomy_distance_level = Cross-category`: source/target cross the O*NET 29/31 healthcare practitioner/support boundary.
- `taxonomy_distance_level = Distant category`: none of the above.

`hidden_path_candidate` is a flag for Cross-category or Distant-category occupations that are not v2 high-barrier and are not flagged as likely downward/low-value mobility. It is not a Hidden Path label.

## TaiwanJobs Mapping

Mapping is deterministic and reproducible. It uses a transparent bilingual healthcare keyword lexicon by O*NET occupation pattern. The lexicon is applied to TaiwanJobs `OCCU_DESC`, `CJOB_NAME1`, `CJOB_NAME2`, and `JOB_DETAIL`.

Job-level score components:

- strong keyword in `OCCU_DESC`: +0.55
- strong keyword in `CJOB_NAME2`: +0.45
- strong keyword in `JOB_DETAIL`: +0.25
- positive keyword in `OCCU_DESC`: +0.20
- positive keyword in `CJOB_NAME2`: +0.18
- positive keyword in `JOB_DETAIL`: +0.08
- broad TaiwanJobs category match: +0.10
- negative keyword in title/category/detail: subtract up to 0.35

For regulated or US-specific occupations such as nurses, physicians, midwives, physician assistants, and physical therapists, a rule can require at least one strong keyword in the TaiwanJobs occupation title or small occupation category before a job is considered a match. This prevents generic healthcare detail text from becoming a forced mapping.

Some rules also exclude negative title/category terms such as `獸醫`, or require a combination of keyword groups. For example, Nursing Instructor requires both a nursing term and an education/teaching term, not either term alone.

The final job score is clipped to 0-1. Occupation-level `mapping_score` is the mean of the top five matched job scores. Low-confidence rows are retained for review but are not treated as strong market evidence.

Mapping confidence:

- `High`: score >= 0.70 and at least 2 matched jobs.
- `Medium`: score >= 0.50 and at least 1 matched job.
- `Low`: score >= 0.35 and at least 1 matched job.
- `Unmatched`: no job above threshold.

## Market Validation

- `Strong`: High confidence, at least 5 matched jobs, and at least 10 total demand persons.
- `Moderate`: High/Medium confidence with at least 2 matched jobs or at least 3 total demand persons.
- `Weak`: Low confidence or one matched job.
- `Unknown`: no reliable mapping.

Market validation is a data-availability and demand-evidence label, not a recommendation score.
