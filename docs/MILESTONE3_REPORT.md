# Milestone 3 — Agent-Ready Policy Assistant

## 1. AUDIT_RESULT

Base: `c604682`, actual Qingju Streamlit website, not the unrelated standalone map.
Full pre-edit audit: [MILESTONE3_AUDIT.md](MILESTONE3_AUDIT.md).
Formal district Opportunity Index, diversity, stability and categorical Reliability
are absent. We explicitly expose their unavailability instead of importing other
project methods. Existing district facts, source periods and hashes remain intact.

## 2. FILES_CHANGED

MODIFIED: `README.md`, `app/components/qingju_assistant.py`.

ADDED:

- `.gitattributes`
- `.kiro/steering/ai-policy.md`
- `.kiro/steering/architecture.md`
- `.kiro/steering/data-governance.md`
- `.kiro/steering/product.md`
- `app/policy_agent/__init__.py`
- `app/policy_agent/contracts.py`
- `app/policy_agent/engine.py`
- `app/policy_agent/knowledge.py`
- `app/policy_agent/orchestrator.py`
- `app/policy_agent/policy_rules.json`
- `app/policy_agent/registry.py`
- `app/policy_agent/tools.py`
- `docs/AGENT_REGRESSION_CHECK.json`
- `docs/AWS_AGENTCORE_PLAN.md`
- `docs/FORECAST_READINESS_REPORT.json`
- `docs/MCP_TOOL_MAPPING.md`
- `docs/MILESTONE3_AUDIT.md`
- `docs/MILESTONE3_REPORT.md`
- `docs/POLICY_AGENT_EVALUATION.json`
- `docs/agentcore_handler_mapping.json`
- `docs/bedrock_tool_config.json`
- `docs/policy_tool_schemas.json`
- `knowledge_base/data_catalog/district_coverage.md`
- `knowledge_base/data_catalog/jobs_source.md`
- `knowledge_base/data_catalog/population_source.md`
- `knowledge_base/definitions/employment_stability.md`
- `knowledge_base/definitions/job_diversity.md`
- `knowledge_base/definitions/jobs_per_1000_youth.md`
- `knowledge_base/definitions/salary.md`
- `knowledge_base/definitions/youth_definition.md`
- `knowledge_base/limitations/employment_data_limitations.md`
- `knowledge_base/limitations/policy_interpretation.md`
- `knowledge_base/manifest.json`
- `knowledge_base/methodology/opportunity_index.md`
- `knowledge_base/methodology/reliability_methodology.md`
- `knowledge_base/methodology/temporal_methodology.md`
- `scripts/product/build_agent_assets.py`
- `scripts/product/build_agent_report.py`
- `scripts/product/check_agent_regression.py`
- `scripts/product/evaluate_policy_agent.py`
- `scripts/product/forecast_readiness.py`
- `scripts/product/test_policy_agent.py`
- `tests/evaluation/policy_agent_eval.jsonl`

## 3. FINAL_ARCHITECTURE

```text
User / unchanged corner pet UI
  |
  v
PolicyAgentOrchestrator / future Bedrock AgentPlanner
  | query-only SessionContext, maximum six tool calls
  v
PolicyToolRegistry (validate -> allowlist -> execute)
  |
  +-- get_district_stats
  +-- compare_districts
  +-- rank_districts
  +-- get_reliability
  +-- get_data_period
  +-- find_policy_observations
  +-- explain_metric
  |       |
  |       v
  |   Existing deterministic engine + reviewed raw-sort / predicate wrapper
  |       |
  |       v
  |   Structured Evidence -> grounded deterministic response
  |
  +-- search_policy_knowledge -> local allowlisted methodology
  |                              `-> future Bedrock Managed KB <- S3
  |
  `-- forecast_employment_demand -> not_ready
                                   `-> future validated SageMaker model
```

## 4. TOOL_REGISTRY

All outputs use PolicyToolResult: tool_name, status, data, evidence, sources,
data_period, reliability, limitations. Missing fields/unknown arguments are rejected.

| name | input | data output | source |
|---|---|---|---|
| get_district_stats | district, optional metrics | requested values + full raw evidence | existing lookup / processed district data |
| compare_districts | districts, optional metrics | values, two-district supporting/counter factors | existing comparison |
| rank_districts | metric, order, limit | raw-value competition rank, null exclusions | existing values; thin deterministic sorter |
| get_reliability | districts | original samples/warnings; level=null, insufficient_data | existing assistant reliability evidence |
| get_data_period | none | source-specific periods; unknown fields=null | existing context metadata |
| find_policy_observations | conditions, minimum_reliability | original matrix or configured conjunction; unavailable reliability filter explicitly not applied | existing matrix + policy_rules.json |
| explain_metric | metric | methodology documents; absent metrics unsupported | reviewed repo definitions |
| search_policy_knowledge | query | document IDs, text, hashes, source paths | knowledge_base manifest allowlist |
| forecast_employment_demand | district, category, horizon | not_ready, prediction=null | readiness boundary, no trained model |

Raw ranking does not create a score: nulls excluded, ties share competition rank,
district names break display ties and limit caps rows. Higher rent is not better.
The additional policy conjunction uses the existing eligible cohort and median
predicates (high >= median, low < median). It is versioned as `m3-1`; other new
condition combinations are unsupported. No original policy matrix was changed.

## 5. TOOL_SCHEMA

Actual machine-readable definitions below are copied from the registry export.
The readable JSON file is [policy_tool_schemas.json](policy_tool_schemas.json).

```json
[{"name":"get_district_stats","description":"取得一個新北市行政區正式人口、刊登職缺、求才、薪資、租金及每千青年求才人數；不存在的指標回 unsupported，不以 KB 補值。","inputSchema":{"type":"object","properties":{"district":{"type":"string","minLength":1,"maxLength":32},"metrics":{"type":"array","items":{"type":"string","enum":["youth_population","job_count","hiring_count","jobs_per_1000_youth","salary","rent","opportunity_index","job_diversity","employment_stability"]},"minItems":1,"maxItems":9,"uniqueItems":true}},"required":["district"],"additionalProperties":false},"outputSchema":{"type":"object","properties":{"tool_name":{"type":"string"},"status":{"type":"string","enum":["success","unsupported","insufficient_data","out_of_scope","not_ready"]},"data":{"type":"object"},"evidence":{"type":"array"},"sources":{"type":"array"},"data_period":{"type":"object"},"reliability":{"type":"array"},"limitations":{"type":"array"}},"required":["tool_name","status","data","evidence","sources","data_period","reliability","limitations"],"additionalProperties":false}},{"name":"compare_districts","description":"比較兩個以上新北行政區原始指標；保留證據、缺值、期間、樣本警語；兩區時提供原始值方向 factors，非因果。","inputSchema":{"type":"object","properties":{"districts":{"type":"array","items":{"type":"string","minLength":1,"maxLength":32},"minItems":2,"maxItems":29,"uniqueItems":true},"metrics":{"type":"array","items":{"type":"string","enum":["youth_population","job_count","hiring_count","jobs_per_1000_youth","salary","rent","opportunity_index","job_diversity","employment_stability"]},"minItems":1,"maxItems":9,"uniqueItems":true}},"required":["districts"],"additionalProperties":false},"outputSchema":{"type":"object","properties":{"tool_name":{"type":"string"},"status":{"type":"string","enum":["success","unsupported","insufficient_data","out_of_scope","not_ready"]},"data":{"type":"object"},"evidence":{"type":"array"},"sources":{"type":"array"},"data_period":{"type":"object"},"reliability":{"type":"array"},"limitations":{"type":"array"}},"required":["tool_name","status","data","evidence","sources","data_period","reliability","limitations"],"additionalProperties":false}},{"name":"rank_districts","description":"依一項既有指標原始值排序，不產生綜合評分；null 排除、相同值同名次、名稱決定展示順序、limit 限制列數。","inputSchema":{"type":"object","properties":{"metric":{"type":"string","enum":["youth_population","job_count","hiring_count","jobs_per_1000_youth","salary","rent","opportunity_index","job_diversity","employment_stability"]},"order":{"type":"string","enum":["ascending","descending"]},"limit":{"type":"integer","minimum":1,"maximum":29}},"required":["metric"],"additionalProperties":false},"outputSchema":{"type":"object","properties":{"tool_name":{"type":"string"},"status":{"type":"string","enum":["success","unsupported","insufficient_data","out_of_scope","not_ready"]},"data":{"type":"object"},"evidence":{"type":"array"},"sources":{"type":"array"},"data_period":{"type":"object"},"reliability":{"type":"array"},"limitations":{"type":"array"}},"required":["tool_name","status","data","evidence","sources","data_period","reliability","limitations"],"additionalProperties":false}},{"name":"get_reliability","description":"取回指定區原有樣本證據與 warning；此網站尚無 high/medium/low 分級，回 insufficient_data 並保留樣本，不能自行評級。","inputSchema":{"type":"object","properties":{"districts":{"type":"array","items":{"type":"string","minLength":1,"maxLength":32},"minItems":1,"maxItems":29,"uniqueItems":true}},"required":["districts"],"additionalProperties":false},"outputSchema":{"type":"object","properties":{"tool_name":{"type":"string"},"status":{"type":"string","enum":["success","unsupported","insufficient_data","out_of_scope","not_ready"]},"data":{"type":"object"},"evidence":{"type":"array"},"sources":{"type":"array"},"data_period":{"type":"object"},"reliability":{"type":"array"},"limitations":{"type":"array"}},"required":["tool_name","status","data","evidence","sources","data_period","reliability","limitations"],"additionalProperties":false}},{"name":"get_data_period","description":"取得來源資料期間；未確認欄位為 null，processed_at 不等於資料月份。","inputSchema":{"type":"object","properties":{},"required":[],"additionalProperties":false},"outputSchema":{"type":"object","properties":{"tool_name":{"type":"string"},"status":{"type":"string","enum":["success","unsupported","insufficient_data","out_of_scope","not_ready"]},"data":{"type":"object"},"evidence":{"type":"array"},"sources":{"type":"array"},"data_period":{"type":"object"},"reliability":{"type":"array"},"limitations":{"type":"array"}},"required":["tool_name","status","data","evidence","sources","data_period","reliability","limitations"],"additionalProperties":false}},{"name":"explain_metric","description":"讀取專案正式方法說明；Opportunity Index、多樣性、穩定度不存在時回 unsupported。","inputSchema":{"type":"object","properties":{"metric":{"type":"string","enum":["youth_population","job_count","hiring_count","jobs_per_1000_youth","salary","rent","opportunity_index","job_diversity","employment_stability","reliability"]}},"required":["metric"],"additionalProperties":false},"outputSchema":{"type":"object","properties":{"tool_name":{"type":"string"},"status":{"type":"string","enum":["success","unsupported","insufficient_data","out_of_scope","not_ready"]},"data":{"type":"object"},"evidence":{"type":"array"},"sources":{"type":"array"},"data_period":{"type":"object"},"reliability":{"type":"array"},"limitations":{"type":"array"}},"required":["tool_name","status","data","evidence","sources","data_period","reliability","limitations"],"additionalProperties":false}},{"name":"find_policy_observations","description":"無 conditions 時沿用既有政策矩陣；只接受已審核的高青年人口且低每千青年求才數組合。最低可靠度要求未能驗證時拒絕強判斷。","inputSchema":{"type":"object","properties":{"conditions":{"type":"array","items":{"type":"object","properties":{"metric":{"type":"string","enum":["youth_population","job_count","hiring_count","jobs_per_1000_youth","salary","rent","opportunity_index","job_diversity","employment_stability"]},"operator":{"type":"string","enum":["high","low"]}},"required":["metric","operator"],"additionalProperties":false},"minItems":0,"maxItems":5,"uniqueItems":true},"minimum_reliability":{"type":"string","enum":["low","medium","high"]}},"required":[],"additionalProperties":false},"outputSchema":{"type":"object","properties":{"tool_name":{"type":"string"},"status":{"type":"string","enum":["success","unsupported","insufficient_data","out_of_scope","not_ready"]},"data":{"type":"object"},"evidence":{"type":"array"},"sources":{"type":"array"},"data_period":{"type":"object"},"reliability":{"type":"array"},"limitations":{"type":"array"}},"required":["tool_name","status","data","evidence","sources","data_period","reliability","limitations"],"additionalProperties":false}},{"name":"search_policy_knowledge","description":"檢索方法、定義、來源、限制文件。不可用於行政區數字、比較、排名或預測。","inputSchema":{"type":"object","properties":{"query":{"type":"string","minLength":1,"maxLength":500}},"required":["query"],"additionalProperties":false},"outputSchema":{"type":"object","properties":{"tool_name":{"type":"string"},"status":{"type":"string","enum":["success","unsupported","insufficient_data","out_of_scope","not_ready"]},"data":{"type":"object"},"evidence":{"type":"array"},"sources":{"type":"array"},"data_period":{"type":"object"},"reliability":{"type":"array"},"limitations":{"type":"array"}},"required":["tool_name","status","data","evidence","sources","data_period","reliability","limitations"],"additionalProperties":false}},{"name":"forecast_employment_demand","description":"未来需求預測契約；目前歷史資料與模型不足，一律 not_ready 且 prediction=null。","inputSchema":{"type":"object","properties":{"district":{"type":"string","minLength":1,"maxLength":32},"category":{"type":"string","minLength":1,"maxLength":100},"horizon":{"type":"integer","minimum":1,"maximum":12}},"required":["district","category","horizon"],"additionalProperties":false},"outputSchema":{"type":"object","properties":{"tool_name":{"type":"string"},"status":{"type":"string","enum":["success","unsupported","insufficient_data","out_of_scope","not_ready"]},"data":{"type":"object"},"evidence":{"type":"array"},"sources":{"type":"array"},"data_period":{"type":"object"},"reliability":{"type":"array"},"limitations":{"type":"array"}},"required":["tool_name","status","data","evidence","sources","data_period","reliability","limitations"],"additionalProperties":false}}]
```

## 6. DATA_BOUNDARY

Structured tools own factual values, comparisons, ordering, sample evidence and
policy predicates. KB contains only methodology, definitions, sources and limits;
13 Markdown documents, manifest paths and content hashes are checked before use.
Numeric district queries never use KB to supply missing facts. Future forecasts
are predictions with uncertainty/training period/version, never factual snapshots.
Session stores only active_districts, active_metric and previous_intent. Each tool
call reloads the engine context; old generated answers never become evidence.
The planner is intentionally finite and deterministic, not a general language model.

## 7. AGENTCORE_READINESS

Implemented: EnginePort, AgentPlanner/AgentOrchestrator/KnowledgeSearch protocols,
validated registry, export-only AgentCoreToolAdapter, Bedrock toolConfig, handler
map and MCP mapping docs. Missing: real endpoint/server, IAM/authentication, target
registration, tool-use ID handling, retries/timeouts, runtime packaging and cloud
evaluation. Existing legacy loader imports Streamlit; future runtime packaging
must preserve/isolate that dependency. No claim of production MCP readiness.

## 8. KNOWLEDGE_BASE_READINESS

Local deterministic retrieval and integrity manifest are implemented. Next, upload
only reviewed documents to S3, ingest into Managed KB, implement KnowledgeSearch,
and test citation/metadata fidelity. Numeric datasets remain outside that prefix.
No S3 bucket, KB, vector store or external model was created. See
[AWS_AGENTCORE_PLAN.md](AWS_AGENTCORE_PLAN.md) for the source-backed AWS plan.

## 9. FORECAST_READINESS_REPORT

```json
{
  "status": "not_ready",
  "available_months": [
    "2026-08"
  ],
  "snapshot_dates": [
    "2026-08-25"
  ],
  "verified_monthly_series_count": 0,
  "evidence_files": [
    "data/processed/employment/new_taipei_employment_summary.csv"
  ],
  "minimum_data_requirement": {
    "exploratory_gate": "12 comparable consecutive monthly snapshots plus rolling validation",
    "seasonality_goal": "24–36 months; still requires coverage/stability audit and baseline evaluation",
    "basis": "Proposed project collection gates, not an AWS requirement or guarantee of sufficiency"
  },
  "candidate_target": "district × stable occupation category monthly unique postings / hiring demand proxy, not confirmed vacancies",
  "candidate_features": [
    "lagged postings and hiring counts",
    "seasonality",
    "salary sample coverage",
    "source coverage",
    "same-period youth population with availability lag"
  ],
  "data_gaps": [
    "One employment snapshot is not a monthly time series.",
    "Summary has only top_job_category, no complete district/category panel.",
    "Cross-month occupation taxonomy, deduplication and district coverage are unverified.",
    "Annual age-proxy unemployment series cannot replace monthly district/category job demand.",
    "Raw employment file is excluded from Git; no reproducible historical archive is available in this checkout."
  ],
  "recommended_collection_plan": [
    "Archive immutable monthly source responses, fetch dates, reference periods and hashes.",
    "Record taxonomy version, job IDs, district mapping, missing and late records.",
    "Build comparable district/category panels; distinguish zero from missing.",
    "Use chronological holdout and rolling-origin backtests against seasonal/naive baselines before SageMaker deployment."
  ],
  "forecast_contract": {
    "prediction": null,
    "uncertainty": null,
    "training_period": null,
    "model_version": null,
    "prediction_is_fact": false
  }
}
```


## 10. EVALUATION

22 new contract/boundary/UI tests passed; all 8 existing tests passed.
Playwright verified the actual three-page site, question submission, Escape,
retained answer and mobile panel bounds. No real LLM was used.

Cases: 36; passed: 36; failed: 0.

| Metric | Passed / eligible | Accuracy |
|---|---|---|
| Tool Selection Accuracy | 36 / 36 | 100.0% |
| District Resolution Accuracy | 36 / 36 | 100.0% |
| Unsupported Rejection Accuracy | 5 / 5 | 100.0% |
| Out-of-Scope Rejection Accuracy | 2 / 2 | 100.0% |
| Reliability Preservation | 23 / 23 | 100.0% |
| Temporal Metadata Preservation | 37 / 37 | 100.0% |
| Numeric Consistency | 14 / 14 | 100.0% |

This is a curated deterministic smoke corpus, not held-out LLM performance.
Reliability preservation measures existing samples/warnings, not nonexistent
categorical levels. Low-level handling is tested using a clearly synthetic adapter
fixture only. No hallucination rate is reported. Full results and individual cases:
[POLICY_AGENT_EVALUATION.json](POLICY_AGENT_EVALUATION.json).

## 11. REGRESSION_CHECK

```json
{
  "baseline": "c604682c89bb69c8aae2c2a1318080a23c16c195",
  "protected_paths": [
    "data",
    "outputs",
    "app/assistant_service.py",
    "app/components/policy_lens.py",
    "app/data_loader.py",
    "requirements.txt",
    "scripts/employment",
    "scripts/population",
    "scripts/policy"
  ],
  "protected_tracked_content_unchanged": true,
  "opportunity_index": "Absent at baseline; no index or weights introduced",
  "reliability": "Existing samples/warnings and rules unchanged; no categorical levels introduced",
  "raw_data": "No raw writes or downloads; raw employment absent in this checkout and ignored by Git",
  "snapshots_and_provenance": "Tracked data/outputs unchanged, including original source hash metadata",
  "existing_assistant": "Original service unchanged; UI delegates policy queries to new tools"
}
```


Only the qingju-policy-assistant remote branch is targeted. No main/other branch
merge or AWS deployment is part of this milestone. Test runtime logs are excluded
from the commit. Existing README/app UI are the only modified baseline files.

## 12. AWS_NEXT_STEP

Milestone 4 — Real AWS Integration:

S3 -> Managed Knowledge Base -> AgentCore Gateway -> Bedrock / Harness Agent
-> AgentCore Runtime -> Evaluation.

Prerequisites and boundaries: [AWS_AGENTCORE_PLAN.md](AWS_AGENTCORE_PLAN.md).
Do not automatically deploy until the AWS environment and authorization are explicit.
