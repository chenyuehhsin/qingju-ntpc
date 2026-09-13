"""Thin Lambda boundary. Gateway passes args; trusted context supplies tool name."""
from policy_agent.registry import PolicyToolRegistry
from policy_agent.contracts import PolicyToolResult
from .bedrock_policy_answer import answer_policy_question


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
    if event["tool_name"] == "answer_policy_question":
        arguments = event["arguments"]
        if not isinstance(arguments, dict) or set(arguments) - {"question", "topic"} or "question" not in arguments:
            return PolicyToolResult("answer_policy_question", "unsupported", data={"message": "Invalid question envelope"}).to_dict()
        try:
            return answer_policy_question(arguments["question"], arguments.get("topic"))
        except Exception:
            return PolicyToolResult("answer_policy_question", "insufficient_data", data={"message": "AI 政策分析暫時無法完成，請稍後再試。"}).to_dict()
    return invoke(event["tool_name"], event["arguments"])
