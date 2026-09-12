# Target Domain Exploration v3.5 Method

Purpose: answer a source-to-domain question, starting with `Registered Nurses -> Technology / AI`, without relying on the source occupation's global cosine nearest neighbors.

## Candidate Generation

Candidate generation uses only local O*NET raw files and deterministic lexical retrieval. No LLM and no embedding model is used in v3.5.

Input fields:

- `occupation_data.csv`: occupation title and description.
- `task_statements.csv`: occupation tasks.
- `knowledge.csv`, `essential_skills.csv`, `transferable_skills.csv`: high-importance skill/knowledge labels where O*NET IM >= 3.0.
- `software_skills.csv`: software categories and workplace examples.

The Technology / AI target-domain lexicon includes clinical/health informatics, health information, medical records, clinical data, bioinformatics, biostatistics, data science, machine learning, artificial intelligence, software, computer systems, information systems, database, cybersecurity, medical equipment, medical device, and technology support terms.

Retrieval score is a transparent weighted keyword count. Title hits receive the highest weight, followed by description, tasks, skill/knowledge labels, and software text. O*NET major group 15 receives a small inclusion bonus; healthcare occupations with both healthcare and technology terms receive a healthcare-tech bridge bonus.

A candidate also needs a primary target-domain signal: O*NET SOC major group 15, a technology title, explicit healthcare-technology language in the occupation title/description, or a technical science/engineering title signal. Software-use evidence alone, such as using electronic medical records software in an otherwise non-technology occupation, is retained as evidence but does not create a candidate by itself.

The candidate pool is the union of high-scoring healthcare-tech, core technology, and strong-keyword matches after this primary-signal filter, capped at 50 occupations. This score is only for candidate generation, not a final recommendation score.

## Evidence Engine Reuse

Every target-domain candidate is passed through the same evidence dimensions used in v2/v3:

- `skill_similarity`: symmetric O*NET weighted cosine similarity.
- `transferable_skill_coverage` and `target_skill_gap`: directional raw O*NET IM metrics from RN -> target.
- education, credential, training/experience barriers.
- O*NET taxonomy distance and related-occupation support.
- TaiwanJobs mapping confidence and market evidence.

## Transition Span

Transition span combines two raw O*NET IM checks:

- overall RN -> target `transferable_skill_coverage` and `target_skill_gap` across required target skills/knowledge.
- `target_domain_technology_gap` on technology-specific O*NET features such as Computers and Electronics, Engineering and Technology, Mathematics, Programming, Technology Design, Systems Analysis, Systems Evaluation, Troubleshooting, and related technical skills/knowledge.

Rules:

- `High skill reuse`: coverage >= 0.85, gap <= 0.45, and technology gap <= 0.50.
- `Partial skill reuse`: coverage >= 0.65, gap <= 0.90, and technology gap <= 1.50.
- `Major reskilling`: all other candidates.

Transition span is not a good/bad score. It states how much RN skill/knowledge appears reusable for the target-domain occupation, with an explicit guard against treating generic social or work-style skill overlap as technology readiness.

## Interpretation Rules

The output keeps three dimensions separate: Feasibility, Market Opportunity, and Obviousness / Taxonomy Distance. It does not compute a transition success probability, a final ranking score, or final recommendations.

O*NET occupation titles may not have direct TaiwanJobs equivalents. Low-confidence or unmatched mappings are retained with `manual_review_needed=yes` rather than forced into a Taiwan occupation.

`hidden_path_candidate` is provisional. It requires cross/distant taxonomy, a healthcare-tech or health-data domain link, no high-barrier feasibility exclusion, and no major-reskilling span. Assistant/preparer/transcriptionist-style lower-value support roles are kept in the evidence table but not marked as hidden-path candidates. The flag is not derived from global cosine rank and is not a final recommendation.
