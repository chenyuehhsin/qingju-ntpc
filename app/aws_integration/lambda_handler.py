"""Thin Lambda boundary. Gateway passes args; trusted context supplies tool name."""
from policy_agent.registry import PolicyToolRegistry
from policy_agent.contracts import PolicyToolResult


def invoke(name, arguments, registry=None):
    return (registry or PolicyToolRegistry()).execute(name, arguments)


def handler(event, context):
    custom = getattr(getattr(context, "client_context", None), "custom", {}) or {}
    full_name = custom.get("bedrockAgentCoreToolName")
    if full_name:
        # Gateway tool names are targetName___toolName. Exact registry allowlist follows.
        name = full_name.split("___", 1)[-1]
        return invoke(name, event)
    # Direct Lambda invocation is IAM-protected; strict transport envelope only.
    if not isinstance(event, dict) or set(event) != {"tool_name", "arguments"} or not isinstance(event["tool_name"], str):
        return PolicyToolResult("invalid", "unsupported", data={"message": "Invalid invocation envelope"}).to_dict()
    return invoke(event["tool_name"], event["arguments"])
