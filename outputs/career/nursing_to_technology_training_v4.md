# Nursing to Technology Training Coverage v4

Question: after identifying career paths worth exploring, what skills need to be strengthened, how long might available public courses take, and how much direct course cost is visible in the raw data?

This is not a transition success probability, not a final career score, and not a training recommendation UI.

## Training Data Quality

- Raw training file: `industry_talent_training_courses_2026-09.csv`
- Encoding: `utf-8-sig`
- Rows: 1149
- Available fields: provider, location, course code, course name, training hours, capacity, fee per person, start date, end date.
- Missing fields for this stage: course content, subsidy eligibility/detail, evening/weekend schedule, online/offline mode, income interruption.

## Career Path Summary

| target_occupation_name | transition_span | number_of_missing_skills | number_of_gap_skills | number_of_trainable_skills_found | number_of_trainable_missing_skills_found | training_coverage_ratio | gap_skill_training_coverage_ratio | total_training_hours | estimated_direct_course_cost | learning_burden_level | market_validation | taiwanjobs_mapping_confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Health Informatics Specialists | Partial skill reuse | 3 | 11 | 1 | 1 | 0.333 | 0.091 | 30.0 | 5860.0 | high | Moderate | Medium |
| Clinical Data Managers | Partial skill reuse | 2 | 5 | 3 | 2 | 1.0 | 0.6 | 108.0 | 21430.0 | medium | Moderate | Medium |
| Clinical Research Coordinators | High skill reuse | 0 | 2 | 0 | 0 | 1.0 | 0.0 | 0.0 | 0.0 | low | Moderate | Medium |
| Medical Records Specialists | Partial skill reuse | 0 | 2 | 1 | 0 | 1.0 | 0.5 | 30.0 | 5860.0 | low | Moderate | Medium |
| Bioinformatics Technicians | Partial skill reuse | 3 | 5 | 5 | 3 | 1.0 | 1.0 | 153.0 | 29830.0 | medium | Moderate | Medium |
| Data Scientists | Major reskilling | 4 | 4 | 4 | 4 | 1.0 | 1.0 | 75.0 | 14610.0 | high | Moderate | Medium |

## Best Current Course Coverage

| target_occupation_name | training_coverage_ratio | gap_skill_training_coverage_ratio | number_of_missing_skills | number_of_gap_skills | trainable_missing_skills_found |
| --- | --- | --- | --- | --- | --- |
| Clinical Research Coordinators | 1.0 | 0.0 | 0 | 2 |  |
| Medical Records Specialists | 1.0 | 0.5 | 0 | 2 |  |
| Clinical Data Managers | 1.0 | 0.6 | 2 | 5 | Computers and Electronics; Programming |
| Bioinformatics Technicians | 1.0 | 1.0 | 3 | 5 | Computers and Electronics; Mathematics; Programming |
| Data Scientists | 1.0 | 1.0 | 4 | 4 | Computers and Electronics; Mathematics; Programming |
| Health Informatics Specialists | 0.333 | 0.091 | 3 | 11 | Computers and Electronics |

## Training Gaps

Paths with low coverage or high burden should be treated as exploration targets, not short-term transitions:

| target_occupation_name | learning_burden_level | number_of_missing_skills | training_coverage_ratio | total_training_hours | estimated_direct_course_cost |
| --- | --- | --- | --- | --- | --- |
| Data Scientists | high | 4 | 1.0 | 75.0 | 14610.0 |
| Health Informatics Specialists | high | 3 | 0.333 | 30.0 | 5860.0 |
| Bioinformatics Technicians | medium | 3 | 1.0 | 153.0 | 29830.0 |
| Clinical Data Managers | medium | 2 | 1.0 | 108.0 | 21430.0 |

## Time Scenarios

| target_occupation_name | scenario_3m_training_coverage_ratio | scenario_6m_training_coverage_ratio | scenario_12m_training_coverage_ratio | scenario_3m_feasibility_estimate | scenario_6m_feasibility_estimate | scenario_12m_feasibility_estimate |
| --- | --- | --- | --- | --- | --- | --- |
| Health Informatics Specialists | 0.333 | 0.333 | 0.333 | limited missing-skill coverage in window | limited missing-skill coverage in window | limited missing-skill coverage in window |
| Clinical Data Managers | 1.0 | 1.0 | 1.0 | most missing skills have matched courses in window | most missing skills have matched courses in window | most missing skills have matched courses in window |
| Clinical Research Coordinators | 1.0 | 1.0 | 1.0 | no missing skill gap | no missing skill gap | no missing skill gap |
| Medical Records Specialists | 1.0 | 1.0 | 1.0 | no missing skill gap | no missing skill gap | no missing skill gap |
| Bioinformatics Technicians | 1.0 | 1.0 | 1.0 | most missing skills have matched courses in window | most missing skills have matched courses in window | most missing skills have matched courses in window |
| Data Scientists | 1.0 | 1.0 | 1.0 | most missing skills have matched courses in window | most missing skills have matched courses in window | most missing skills have matched courses in window |

## Learning Plans

### Health Informatics Specialists

- Skill reuse: Partial skill reuse; missing skills: 3; training coverage: 0.333.
- Phase 1 Foundational skills: Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics)
- Phase 2 Domain / technical skills: Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics)
- Phase 3 Portfolio / job preparation: Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics)
- Missing skills: Design (knowledge, gap 1.9); Computers and Electronics (knowledge, gap 1.61); Engineering and Technology (knowledge, gap 1.59)
- Transition burden: hours=30.0, direct cost=5860.0, income interruption=unknown.

### Clinical Data Managers

- Skill reuse: Partial skill reuse; missing skills: 2; training coverage: 1.0.
- Phase 1 Foundational skills: AI應用Power BI智慧商業數據分析實務班 (36h, maps Mathematics); Python與PyTorch神經網路訓練實作班 (42h, maps Programming); Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics)
- Phase 2 Domain / technical skills: Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics)
- Phase 3 Portfolio / job preparation: AI應用Power BI智慧商業數據分析實務班 (36h, maps Mathematics); Python與PyTorch神經網路訓練實作班 (42h, maps Programming); Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics)
- Missing skills: Programming (transferable_skill, gap 1.63); Computers and Electronics (knowledge, gap 1.36)
- Transition burden: hours=108.0, direct cost=21430.0, income interruption=unknown.

### Clinical Research Coordinators

- Skill reuse: High skill reuse; missing skills: 0; training coverage: 1.0.
- Phase 1 Foundational skills: unknown: no matched course evidence
- Phase 2 Domain / technical skills: unknown: no matched course evidence
- Phase 3 Portfolio / job preparation: unknown: no matched course evidence
- Missing skills: (none)
- Transition burden: hours=0.0, direct cost=0.0, income interruption=unknown.

### Medical Records Specialists

- Skill reuse: Partial skill reuse; missing skills: 0; training coverage: 1.0.
- Phase 1 Foundational skills: Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics)
- Phase 2 Domain / technical skills: Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics)
- Phase 3 Portfolio / job preparation: Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics)
- Missing skills: (none)
- Transition burden: hours=30.0, direct cost=5860.0, income interruption=unknown.

### Bioinformatics Technicians

- Skill reuse: Partial skill reuse; missing skills: 3; training coverage: 1.0.
- Phase 1 Foundational skills: AI應用Power BI智慧商業數據分析實務班 (36h, maps Mathematics); Python與PyTorch神經網路訓練實作班 (42h, maps Programming); Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics); Python網路爬蟲與資料分析實務班 (45h, maps Biology)
- Phase 2 Domain / technical skills: Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics)
- Phase 3 Portfolio / job preparation: AI應用Power BI智慧商業數據分析實務班 (36h, maps Mathematics); Python與PyTorch神經網路訓練實作班 (42h, maps Programming); Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics)
- Missing skills: Computers and Electronics (knowledge, gap 2.18); Programming (transferable_skill, gap 1.5); Mathematics (knowledge, gap 1.07)
- Transition burden: hours=153.0, direct cost=29830.0, income interruption=unknown.

### Data Scientists

- Skill reuse: Major reskilling; missing skills: 4; training coverage: 1.0.
- Phase 1 Foundational skills: Python資料科學大數據處理應用班 (45h, maps Mathematics); Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics)
- Phase 2 Domain / technical skills: Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics)
- Phase 3 Portfolio / job preparation: Python資料科學大數據處理應用班 (45h, maps Mathematics); Python與AI應用於資料庫分析班 (30h, maps Computers and Electronics)
- Missing skills: Programming (transferable_skill, gap 2.13); Computers and Electronics (knowledge, gap 1.65); Mathematics (essential_skill, gap 1.5); Mathematics (knowledge, gap 1.09)
- Transition burden: hours=75.0, direct cost=14610.0, income interruption=unknown.

## Manual Review / Limitations

| target_occupation_name | taiwanjobs_mapping_confidence | taiwanjobs_manual_review_needed | limitation |
| --- | --- | --- | --- |
| Health Informatics Specialists | Medium | yes | TaiwanJobs mapping requires manual review |
| Clinical Data Managers | Medium | yes | TaiwanJobs mapping requires manual review |
| Clinical Research Coordinators | Medium | yes | TaiwanJobs mapping requires manual review |
| Medical Records Specialists | Medium | yes | TaiwanJobs mapping requires manual review |
| Bioinformatics Technicians | Medium | yes | TaiwanJobs mapping requires manual review |
| Data Scientists | Medium | yes | TaiwanJobs mapping requires manual review |

## Interpretation

- Clinical Research Coordinators has the lowest training burden in this run, but its TaiwanJobs mapping still needs review and its mapped market signal is not a success probability.
- Health Informatics Specialists, Clinical Data Managers, Medical Records Specialists, and Bioinformatics Technicians show plausible course coverage through data, systems, medical information, Python, statistics, and database-related courses.
- Data Scientists is retained as the Major Reskilling comparator: current courses can cover some data/AI gaps, but the technology-specific gap and learning burden remain higher.
- Course matching is limited by course-title-only evidence. Course content, subsidy, schedule, and learner opportunity cost are unavailable in the current raw file.
