# Milestone 3 audit and implementation plan

Audit date: 2026-09-12. Remote fetched before editing. Working baseline:
`origin/qingju-policy-assistant = c604682`; actual website main `3d3cca0`.
Other remote branches were not merged or modified.

## CURRENT_ARCHITECTURE

The actual Qingju site is `app/app.py`, a Streamlit three-page app. The common
`render_qingju_assistant()` call precedes page returns. `app/assistant_service.py`
loads processed district data and delegates ratio/policy calculations to
`app/components/policy_lens.py`. This is not the old standalone HTML employment
map preserved only in earlier Git ancestry. No raw dataset was migrated.

## CURRENT_ASSISTANT_FLOW

Question -> whole-string deterministic intent parser -> inline district alias
resolution -> handler -> structured answer/evidence/sources/period/reliability/
limitations -> native Streamlit popover. No HTTP assistant API, planner/provider
abstraction, function registry or model invocation existed at the baseline.

## EXISTING_DETERMINISTIC_CAPABILITIES

| Requested area | Audit result / source |
|---|---|
| Entry / router / resolver / schema | `app/assistant_service.py:answer_question` |
| District data / comparison | Existing `load_context` and answer handlers; 29 districts |
| Policy engine | `build_policy_intervention_matrix`, transparent median predicates |
| Per-thousand metric | `load_youth_job_opportunity_data`, hiring count / youth population × 1000 |
| Opportunity Index | Absent in this website; do not introduce foreign weights |
| Reliability | Existing assistant sample counts and warnings; no categorical district levels |
| Diversity / stability | No formal metrics; top category is not diversity |
| Ranking | Career ranks exist; no formal composite district ranking. M3 only adds raw-value ordering |
| Temporal | Population source period, jobs snapshot date, rent catalog period; no unified temporal pipeline |
| Provenance | `data/data_catalog.csv`, population metadata with raw hashes; existing assistant derived file SHA-256 |
| Frontend | Streamlit native popover; no separate FastAPI/UI server |
| Tests | 8 existing unittest/AppTest tests and Playwright three-page smoke |
| AWS / provider / tool calling | None in app/docs/requirements at baseline |
| Knowledge base | No `knowledge_base/` |
| Steering | `.kiro/steering/.gitkeep` only |

Ratios cover the existing inner-join cohort (21 eligible districts), while
district population/jobs retain all 29. Missing rent or ratios must stay null.
Employment snapshot is 2026-08-25; population source period 2026-07; rent source
period 2026-03. Annual proxy unemployment records are not monthly job snapshots.
Raw employment data is excluded from Git and absent from this checkout.

## EXISTING_AWS_PREPARATION

No boto3, Bedrock, AgentCore, remote knowledge retrieval, MCP runtime or deployed
forecast endpoint in the working tree. No AWS credentials were requested or used.

## MISSING_AGENT_CAPABILITIES

Typed tool results, validated schemas, tool registry, multi-step execution,
query-only session contract, knowledge allowlist, AWS export adapters, forecast
readiness audit and deterministic agent evaluation. Missing formal indicators
remain unsupported; missing categorical reliability is insufficient_data.

## IMPLEMENTATION_PLAN

1. Wrap existing handlers through an injectable EnginePort; preserve raw evidence.
2. Add nine schema-defined tools and bounded deterministic orchestration.
3. Reuse policy matrix. Add one explicit, reviewable conjunction in
   `app/policy_agent/policy_rules.json`: high youth AND low per-thousand demand,
   using the existing eligible cohort and median predicates. This new rule is
   not an amendment to the original matrix or an LLM-selected threshold.
4. Separate allowlisted methodology documents from numeric evidence.
5. Preserve three-page UI and existing site/career answers; add query-only session.
6. Export Bedrock/MCP contracts, document AWS phases, do not deploy AWS.
7. Add 20 contract/boundary tests, retain 8 baseline tests, evaluate 36 queries.

Audit was reported in the conversation before implementation began.
