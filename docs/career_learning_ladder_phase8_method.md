# Career Learning Ladder Phase 8 Method

Generated: 2026-09-03

Phase 8 translates existing Phase 7 evidence into explainable learning-ladder and policy-intervention candidates. It does not modify raw data, v1-v4 analysis, Career Discovery, Phase 7 calculations, or UI.

## Inputs

- `outputs/career/career_policy_lens_phase7.csv` as the structured source for skill gap, market evidence, training evidence, MOL proxy signals, and Phase 7 data limitations.
- `data/processed/career/career_training_skill_mapping.csv` for course-level hours and fee fields when Phase 7 matched course codes can be traced to course candidates.
- `outputs/career/career_policy_lens_phase7.md` remains the human-readable upstream summary, but the Phase 8 script does not parse narrative text.

## Representative Path Selection

Phase 8 does not build full ladders for all 18 Phase 7 rows. It selects representative paths that cover different evidence situations:

- high nursing skill reuse with low missing-skill gap
- healthcare technology bridge path with training gap
- clinical data bridge path with matched courses
- major-reskilling technology comparator
- beauty / personal-care paths with High-relevance market evidence
- paths where public market evidence is insufficient

Selected paths are not rankings.

## Ladder Structure

Each ladder has five stages:

1. Exploration direction
2. Foundation skill boost
3. Learning milestone / capability validation
4. Advanced training
5. Market job linkage

## Policy Intervention Type Rules

| Type | Rule | Guardrail |
|---|---|---|
| Public learning | Missing skills include standardizable foundations such as Programming, Computers and Electronics, Mathematics, Sales and Marketing, Persuasion, Design, or Communications and Media. | Suitable for public digital materials, not proof of transition success. |
| Training guidance | Existing matched course evidence is available. | Uses MOL 15-29 Proxy finding that some non-participants do not know where courses are available. |
| Subsidy candidate | The matched-course candidate set includes at least one higher-burden single course: single-course fee at least NT$18,000 or single-course hours at least 80. | This only flags cost-burden review; it does not set subsidy amount, total transition cost, total transition time, or imply all candidate courses must be taken. |
| Cohort / partnership candidate | High-relevance market evidence exists and skill gap is explicit while potential course coverage is weak; or a training gap is visible but market validation must precede scale-up. | Does not claim a cohort or partnership would be effective. |
| Market validation needed | High-relevance job evidence is zero or unavailable. | High=0 means public market evidence is insufficient, not market absence. |

## Training Evidence Semantics

- Matched courses are not a complete transition curriculum.
- Currently found related-course hours / cost do not represent total time or total cost required to complete a career transition.
- Potential training coverage only means a gap skill has a possible related-course match in current public training data.
- Potential training coverage does not prove course depth is sufficient and does not mean the skill has been acquired.
- Training evidence is separated into: potential course found, course depth unknown, and complete pathway unknown.
- Candidate course hours and fees are summarized as single-course median and range.
- Cumulative course hours or cumulative course fees must not be displayed unless there is evidence that the courses form a sequential learning pathway.
- Phase 8 currently sets sequential-learning-pathway evidence to `not established` for all selected paths.
- Major-reskilling paths such as Data Scientists must remain major-reskilling comparators even when potential training coverage is 100%.

## Interpretation Rules

- Do not calculate success probability.
- Do not calculate a single career score.
- Do not infer policy effectiveness.
- Do not propose subsidy amounts.
- Do not treat potential training coverage as course depth, a complete curriculum, or skill acquisition.
- Be conservative when market evidence is insufficient.