"""Dry-run inventory; delete only project-tagged resources created in this state.

S3 data/buckets are intentionally retained. IAM roles and reused resources are
never deleted. Explicit apply + confirm-delete is required by CLI.
"""
from .config import Blocked, TAGS
from .sdk import request


def cleanup(deployment, confirm=False):
    state, clients = deployment.state, deployment.clients
    resources = state.data["resources"]
    plan = [{"resource": k, "action": ("manual_cleanup" if k in {"kb", "gateway"} else "delete") if v["created"] and k != "bucket" else "retain", "id": v["id"]} for k, v in resources.items()]
    if not confirm:
        return {"dry_run": True, "plan": plan}
    # Reverify parent identity/tags before removing targets or data sources.
    if state.get("gateway"):
        c = clients["bedrock-agentcore-control"]
        gateway = request(c, "get_gateway", gatewayIdentifier=state.get("gateway"))
        deployment.tags(request(c, "list_tags_for_resource", resourceArn=gateway["gatewayArn"])["tags"])
    if state.get("kb"):
        c = clients["bedrock-agent"]
        kb = request(c, "get_knowledge_base", knowledgeBaseId=state.get("kb"))["knowledgeBase"]
        deployment.tags(request(c, "list_tags_for_resource", resourceArn=kb["knowledgeBaseArn"])["tags"])
    # Each invocation deletes leaf resources only; rerun after AWS deletion completes.
    count = 0
    for key in ("kb_target", "policy_target", "data_source", "lambda"):
        r = resources.get(key)
        if not r or not r["created"]:
            continue
        if key.endswith("_target"):
            from .deploy import token
            target = request(clients["bedrock-agentcore-control"], "get_gateway_target", gatewayIdentifier=state.get("gateway"), targetId=r["id"])
            if not target["name"].startswith(deployment.c.prefix + "-") or token(target["targetConfiguration"]) != r["fingerprint"]:
                raise Blocked("Cleanup target identity/configuration changed")
            request(clients["bedrock-agentcore-control"], "delete_gateway_target", gatewayIdentifier=state.get("gateway"), targetId=r["id"])
        elif key == "data_source":
            ds = request(clients["bedrock-agent"], "get_data_source", knowledgeBaseId=state.get("kb"), dataSourceId=r["id"])["dataSource"]
            if ds["name"] != deployment.c.prefix + "-documents":
                raise Blocked("Cleanup data source identity changed")
            request(clients["bedrock-agent"], "delete_data_source", knowledgeBaseId=state.get("kb"), dataSourceId=r["id"])
        else:
            deployment.tags(request(clients["lambda"], "list_tags", Resource=r["arn"])["Tags"])
            request(clients["lambda"], "delete_function", FunctionName=r["id"])
        count += 1
    return {"dry_run": False, "delete_requests_sent": count > 0, "delete_request_count": count,
            "remaining": "Wait for leaf deletion, then manually delete created KB/Gateway after confirming no shared targets. Retain bucket/documents and IAM roles."}
