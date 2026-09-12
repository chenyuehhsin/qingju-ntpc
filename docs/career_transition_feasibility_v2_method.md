# Career Transition Feasibility v2 Method

Purpose: add directional feasibility screening on top of symmetric O*NET skill similarity. This is not a transition success probability.

## Inputs

- Skill backbone: O*NET 31.0 `essential_skills.csv`, `transferable_skills.csv`, and `knowledge.csv`.
- Feasibility constraints: `job_zones.csv`, `job_zone_reference.csv`, `education.csv`, `education_categories.csv`, `training_and_experience.csv`, and `training_and_experience_categories.csv`.
- Support signal: `related_occupations.csv`, kept separate from skill similarity and feasibility labels.

## Directional Skill Metrics

`skill_similarity` keeps the v1 symmetric weighted cosine similarity. It uses O*NET IM scores divided by 5.0, L2-normalized within each skill type, then equally weights essential skills, transferable skills, and knowledge.

For an A -> B transition, directional coverage and gap use raw O*NET IM scores on the 0-5 importance scale, not occupation-level L2-normalized vectors.

Let `a_i` be source occupation A's raw IM score for feature `i`, and `b_i` be target occupation B's raw IM score. A target-required feature is included when `b_i >= 3.0`.

For each skill type `t`:

- `coverage_t(A -> B) = sum_i min(a_i, b_i) / sum_i b_i`, for target-required features in `t`.
- `gap_t(A -> B) = mean_i max(b_i - a_i, 0)`, for target-required features in `t`.

Overall directional metrics equally weight available skill types:

- `transferable_skill_coverage(A -> B) = mean_t coverage_t(A -> B)`; range 0-1, higher means more of B's required profile is already covered by A.
- `target_skill_gap(A -> B) = mean_t gap_t(A -> B)`; raw IM points, lower means fewer target-side missing requirements.

## Feasibility Constraints

- `job_zone_difference = target_job_zone - source_job_zone`; larger positive values imply more preparation than the source occupation.
- `education_barrier` uses O*NET required education distributions: weighted education category, modal education category, master's-or-higher share, doctoral/professional/postdoctoral share, and professional certification importance.
- `training_experience_barrier` uses modal and weighted related work experience, on-site training, on-the-job training, and apprenticeship importance.
- Education and training category distributions keep the full reported percentage distribution. Category-level `Recommend Suppress` flags are not filtered because removing a single category would distort modal and weighted-category summaries.
- `related_support` reports whether O*NET Related Occupations lists B from A; it does not change `skill_similarity`.
- `education_barrier=unknown` means the target occupation has no O*NET `RL` required-education distribution in the local raw data; it is not treated as evidence of low barrier.

## Feasibility Labels

- `Adjacent candidate`: strong directional skill coverage, small skill gap, low or medium preparation barriers, and either related support or no upward job-zone move.
- `Bridge candidate`: strong skill coverage with a visible but explainable education/training step, or a same-domain transition that needs additional credentials.
- `Infeasible / high-barrier`: skill-similar but blocked by physician/doctoral-professional preparation, large job-zone jump, or high education/training barrier without a same-domain bridge signal.

These labels are feasibility screens for exploration, not recommendations, market demand estimates, wage estimates, or success probabilities.
