# AI policy

- LLM output is never source of truth; structured data is source of truth.
- LLM must not compute metrics, rankings, reliability or dates.
- Opportunity Index weights must not change; this site has no such index, so reject requests for its value.
- Reliability rules must not change; missing categorical levels are not low reliability.
- Preserve low-reliability warnings where supplied; never invent a level.
- processed_at is not reference month.
- Structured district tools only support New Taipei City's 29 districts.
- KB explains methods, definitions, sources and limitations; never computes rankings.
- Correlation != causation; forecast != fact.
- Session memory contains query context, never model answers as evidence.
- Only future AWS Bedrock / AgentCore / SageMaker integration is planned.
- No real AWS deployment without an explicitly provided environment and authorization.
