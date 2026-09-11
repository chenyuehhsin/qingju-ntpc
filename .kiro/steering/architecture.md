# Architecture

UI -> bounded PolicyAgentOrchestrator -> schema-validated PolicyToolRegistry ->
EnginePort -> existing deterministic handlers/data. KnowledgeSearch handles
methodology only. AgentCoreToolAdapter exports contracts without AWS SDK coupling.
SessionContext contains query context only. Future Bedrock implements planner;
future SageMaker serves separately validated forecasts, never factual statistics.
