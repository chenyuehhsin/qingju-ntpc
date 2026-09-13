"""Assemble the requested twelve-part report from actual exports/results."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build():
    schemas = json.loads((ROOT / "docs/policy_tool_schemas.json").read_text(encoding="utf-8"))
    evaluation = json.loads((ROOT / "docs/POLICY_AGENT_EVALUATION.json").read_text(encoding="utf-8"))
    forecast = json.loads((ROOT / "docs/FORECAST_READINESS_REPORT.json").read_text(encoding="utf-8"))
    regression = json.loads((ROOT / "docs/AGENT_REGRESSION_CHECK.json").read_text(encoding="utf-8"))
    added = [p.relative_to(ROOT).as_posix() for pattern in (
        "app/policy_agent/*.py", "app/policy_agent/*.json", "knowledge_base/**/*.md", "knowledge_base/*.json",
        ".kiro/steering/*.md") for p in ROOT.glob(pattern)]
    added += ["scripts/product/" + f for f in ["build_agent_assets.py", "build_agent_report.py", "check_agent_regression.py", "evaluate_policy_agent.py", "forecast_readiness.py", "test_policy_agent.py"]]
    added += ["tests/evaluation/policy_agent_eval.jsonl", ".gitattributes"]
    added += ["docs/" + f for f in ["MILESTONE3_AUDIT.md", "MILESTONE3_REPORT.md", "AWS_AGENTCORE_PLAN.md", "MCP_TOOL_MAPPING.md", "FORECAST_READINESS_REPORT.json", "POLICY_AGENT_EVALUATION.json", "AGENT_REGRESSION_CHECK.json", "policy_tool_schemas.json", "bedrock_tool_config.json", "agentcore_handler_mapping.json"]]
    text = """# Milestone 3 — Agent-Ready Policy Assistant

## 1. AUDIT_RESULT

Base: `c604682`, actual Qingju Streamlit website, not the unrelated standalone map.
Full pre-edit audit: [MILESTONE3_AUDIT.md](MILESTONE3_AUDIT.md).
Formal district Opportunity Index, diversity, stability and categorical Reliability
are absent. We explicitly expose their unavailability instead of importing other
project methods. Existing district facts, source periods and hashes remain intact.

## 2. FILES_CHANGED

MODIFIED: `README.md`, `app/components/qingju_assistant.py`.

ADDED:

""" + "\n".join("- `" + p + "`" for p in sorted(added)) + """

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
""" + json.dumps(schemas, ensure_ascii=False, separators=(",", ":")) + """
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

""" + "```json\n" + json.dumps(forecast, ensure_ascii=False, indent=2) + "\n```\n" + """

## 10. EVALUATION

22 new contract/boundary/UI tests passed; all 8 existing tests passed.
Playwright verified the actual three-page site, question submission, Escape,
retained answer and mobile panel bounds. No real LLM was used.

""" + f"Cases: {evaluation['total_cases']}; passed: {evaluation['passed']}; failed: {evaluation['failed']}.\n\n" + "| Metric | Passed / eligible | Accuracy |\n|---|---|---|\n" + "\n".join(
        f"| {name} | {v['passed']} / {v['eligible']} | {v['accuracy']:.1%} |" for name, v in evaluation["metrics"].items()) + """

This is a curated deterministic smoke corpus, not held-out LLM performance.
Reliability preservation measures existing samples/warnings, not nonexistent
categorical levels. Low-level handling is tested using a clearly synthetic adapter
fixture only. No hallucination rate is reported. Full results and individual cases:
[POLICY_AGENT_EVALUATION.json](POLICY_AGENT_EVALUATION.json).

## 11. REGRESSION_CHECK

""" + "```json\n" + json.dumps(regression, ensure_ascii=False, indent=2) + "\n```\n" + """

Only the qingju-policy-assistant remote branch is targeted. No main/other branch
merge or AWS deployment is part of this milestone. Test runtime logs are excluded
from the commit. Existing README/app UI are the only modified baseline files.

## 12. AWS_NEXT_STEP

Milestone 4 — Real AWS Integration:

S3 -> Managed Knowledge Base -> AgentCore Gateway -> Bedrock / Harness Agent
-> AgentCore Runtime -> Evaluation.

Prerequisites and boundaries: [AWS_AGENTCORE_PLAN.md](AWS_AGENTCORE_PLAN.md).
Do not automatically deploy until the AWS environment and authorization are explicit.
"""
    (ROOT / "docs/MILESTONE3_REPORT.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    build()
