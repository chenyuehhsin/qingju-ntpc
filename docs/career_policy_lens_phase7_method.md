# Career Policy Lens Phase 7 Method

Generated: 2026-09-03

Phase 7 creates a first policy-analysis lens by integrating existing outputs only. It does not modify raw data, v1-v4 methodology, Career Discovery UI, or recommendation results.

## Inputs

| Evidence area | Files | Use |
|---|---|---|
| Youth status | `data/processed/career/youth/*phase6*.csv`, `docs/youth_statistics_phase6_qa.md` | 18-35 exact population and proxy youth labor/training signals. |
| Career opportunity | `outputs/career/nursing_to_technology_training_v4.csv`, `outputs/career/nursing_to_beauty_candidates_phase5.csv` | Feasibility, transition span, skill reuse, education/credential/training barriers. |
| Market demand | Existing TaiwanJobs fields in career outputs | High-relevance job evidence where available; aggregate market validation otherwise stays labeled aggregate-only. |
| Skill gap | Existing missing/partial skill columns | Common missing skills and repeated capability gaps. |
| Training gap | Existing course mapping and training coverage fields | Potential course coverage, hours, direct course cost, and uncovered missing skills. |

## Evidence Guardrails

- Exact / Partial / Proxy labels are preserved.
- Unresolved New Taipei employment/unemployment metadata is not used for strong policy claims.
- High-relevance TaiwanJobs evidence is counted only when an existing output provides job-level High relevance counts.
- High=0 is interpreted as `公開市場證據不足`, not market absence.
- Training coverage is named `potential_training_coverage_ratio`; it does not mean a skill has been fully acquired.
- No youth transition success probability, final recommendation score, or subsidy amount is calculated.
- No concrete policy prescription is produced in Phase 7.

## Output Unit

One row represents one source-target career path from Registered Nurses to an explored target occupation. The table keeps independent dimensions instead of collapsing them into a single score:

- Youth context
- Career opportunity / feasibility
- Market demand evidence
- Skill gap
- Training gap
- Data limitations