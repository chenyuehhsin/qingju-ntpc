# Policy tool to MCP / AgentCore mapping

`app/policy_agent/registry.py` is the single source of truth. `list_tools()`
returns name, description, inputSchema and outputSchema. `handlers` maps names
to callables. `AgentCoreToolAdapter` exports these definitions and a Bedrock
`toolConfig`; neither class starts a server or calls AWS.

| Local entry | Future transport |
|---|---|
| `registry.list_tools()` | MCP `tools/list` result tools |
| `registry.execute(name, arguments)` | MCP `tools/call` dispatch, allowlisted name, validated arguments |
| PolicyToolResult | JSON structured content; keep status and all evidence fields |
| `adapter.bedrock_tool_config()` | Bedrock Converse tool configuration |
| `adapter.handler_mapping()` | Local registration map, not an AWS ARN or deployment config |

Actual exports: `policy_tool_schemas.json`, `bedrock_tool_config.json`, and
`agentcore_handler_mapping.json`. The first includes the shared output envelope
for every tool. Errors remain typed unsupported/insufficient_data/out_of_scope/
not_ready results, never a fabricated model answer.

Future transport must implement authentication, request IDs, tool-use result
association, serialization, timeouts, retries, quotas and model loop limits.
Do not execute arbitrary import paths or tool names from a model. The current
planner caps execution at six calls. Registry itself has no session or UI state.
The EnginePort bridge still imports the existing Streamlit-based loaders; future
packaging should isolate those pure loaders or ship their exact dependencies.
This does not claim a production MCP server is ready.

AgentCore supports MCP discovery/invocation and several target types. Choose
Lambda or an authenticated MCP target during real deployment and validate the
selected schema/protocol against the live service. A KB is a separate retrieval
service called through a tool; it is not the source for numeric district queries.

Official references (checked 2026-09-12):
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-core-concepts.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use.html
