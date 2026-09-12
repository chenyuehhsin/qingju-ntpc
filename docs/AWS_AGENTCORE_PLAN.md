# Milestone 4 — Real AWS Integration

No AWS calls, infrastructure changes or credentials are part of Milestone 3.
All schemas are local exports; Bedrock, AgentCore and SageMaker remain future
integration points. No OpenAI, Gemini or external Claude APIs are used.

## Phase A — S3 documents

Upload only the reviewed manifest-allowlisted methodology, definitions, source
explanations and limitations in `knowledge_base/`. Preserve document IDs, hashes,
source-file links and version metadata. Keep structured numeric datasets in a
separate read-only data path outside the KB ingestion prefix. Choose account,
region, encryption, IAM, retention and budget before provisioning.

## Phase B — Managed Knowledge Base

Create a Bedrock Managed Knowledge Base using that S3 document prefix, a chosen
embedding model and a supported managed store. Do not build a custom vector DB.
Ingest and test retrieval/citations. Implement `KnowledgeSearch` using retrieval
only; retrieved text is untrusted evidence, not executable instructions. District
values, rankings and forecasts must always use structured tools. Knowledge docs
contain no district numeric answer table. Rebuild manifest after reviewed edits.

## Phase C — AgentCore Gateway

Package validated PolicyToolRegistry handlers behind a supported Lambda or MCP
target. Register the exported name/description/input schemas and output contract.
Configure inbound authentication, target IAM and read-only dataset permissions,
timeouts and quotas. The Gateway exposes structured tools and a knowledge-search
tool, not unrestricted file access. Deployment must include the existing engine
and processed data versions; currently legacy loaders import Streamlit.

## Phase D — Harness / Bedrock Agent

Implement AgentPlanner against Bedrock tool use, preserving the existing
AgentOrchestrator contract and server-side argument validation. Associate tool
results with tool-use IDs; cap steps/cost/time; stop on unavailable evidence.
Generated explanation may only render verified factors, citations and caveats.
Do not use the previous model answer as evidence. Run the deterministic suite,
then a held-out real-model evaluation with numeric/citation checks before rollout.

## Phase E — Runtime deployment

Package the harness for AgentCore Runtime after selecting a supported runtime
protocol and container layout. Add authorization, telemetry without sensitive
query logs, health checks, operational limits, CI and rollback. The existing
Streamlit UI can call an authenticated service; do not embed AWS credentials in
the browser. None of these resources have been created by this milestone.

```text
User -> Policy harness / Bedrock planner -> AgentCore Gateway
                                         |-> Policy tools -> Existing engine -> Structured evidence
                                         |-> Knowledge search -> Managed KB <- S3 documents
                                         `-> Forecast tool -> not_ready (until model validated)
Evidence -> grounded renderer / future Bedrock explanation -> UI
```

The teaching diagram is adjusted so Bedrock selects tools and KB retrieval is a
side path. Knowledge text does not sit in front of numeric computation.

## Future SageMaker feasibility

See `FORECAST_READINESS_REPORT.json`. Only one verified employment month exists.
Collect comparable monthly district/category panels before feature engineering.
Proposed project gates: at least 12 comparable months for initial experiments,
24–36 for seasonal assessment, plus actual holdout and baseline performance.
These are planning targets, not evidence that a model will become adequate.

Historical snapshots -> feature engineering with leakage controls -> SageMaker
training -> rolling validation vs naive baselines -> approved batch/online endpoint
-> forecast_employment_demand -> policy agent. Future output must identify horizon,
uncertainty, training period and model version. Prediction != fact. The current
tool has no prediction values or model and always returns not_ready.

Official references (checked 2026-09-12):
- https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-ds.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-building.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-core-concepts.html
- https://docs.aws.amazon.com/sagemaker/latest/dg/how-it-works-training.html
