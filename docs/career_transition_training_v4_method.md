# Career Transition Training v4 Method

Purpose: estimate what skill gaps may be addressable by current public training supply for selected `Registered Nurses -> Technology / AI` career paths.

This stage does not build UI, does not use training data to compute transition success probability, and does not create a single career recommendation score.

## Training Inventory

- Raw file: `data/raw/career/training/industry_talent_training_courses_2026-09.csv`
- Encoding: `utf-8-sig`
- Rows: 1149
- Columns: 訓練單位名稱, 縣市別辦訓地, 課程代碼, 課程名稱, 訓練時數, 訓練人次, 每人訓練費用, 開訓日期, 結訓日期
- Course content field: not available in current raw file.
- Subsidy fields: not available in current raw file.
- Scheduling fields: only start/end dates are available; evening/weekend information is not available.
- Date range: 2026-08-13 to 2027-04-25
- Missing training hours: 0
- Missing fee: 0

## Target Skill Gap

Target-required skills are O*NET Essential Skills, Transferable Skills, and Knowledge with target IM importance >= 3.0. Source and target values remain on the raw 0-5 IM scale.

- `already_covered`: target-source raw gap <= 0.25.
- `partially_covered`: target-source raw gap > 0.25 and < 1.0.
- `missing`: target-source raw gap >= 1.0.

## Course -> Skill Mapping

Mapping uses deterministic keyword matching from course title to O*NET skill/knowledge names plus target-occupation domain terms. No embedding model and no LLM is used in v4.

- `mapping_method`: `deterministic_course_title_to_onet_skill_keyword_v1`.
- Threshold: mapping score >= 0.35 is retained.
- Confidence: High >= 0.75, Medium >= 0.55, Low >= 0.35.
- Low confidence rows are marked `manual_review_needed=yes`.
- Coverage calculations count only High and Medium mappings.

Because the raw file has no course description/content, mapping precision is limited and many rows require manual review before user-facing use.

## Training Coverage

`training_coverage_ratio = number_of_trainable_missing_skills_found / number_of_missing_skills`. If there are no missing skills, the ratio is set to 1.0.

`gap_skill_training_coverage_ratio = number_of_trainable_skills_found / number_of_gap_skills`, where gap skills include both `missing` and `partially_covered` skills.

Matched course hours and direct cost are summed over one best available course per missing or partially covered skill, deduplicated by course code. This estimates course burden, not total life cost.

## Time Scenarios

The 3, 6, and 12 month scenarios use `2026-09-01` as the observation date. A missing skill is counted as trainable in a scenario only if at least one High/Medium-confidence mapped course starts on or after the observation date and ends within the scenario window.

The scenario output means only: under current public course supply, a skill gap has some mapped course coverage in that time window. It does not claim career readiness or employment outcomes.

## Learning Plan

Phase 1, Phase 2, and Phase 3 text is generated only from matched courses and mapped target skills. If no course evidence supports a phase, it is marked unknown.

## Transition Burden

The output separates skill reuse, learning burden, training hours, direct learning cost, and possible income interruption. Income interruption remains `unknown` because the raw training data does not contain learner work-hour or opportunity-cost fields.
