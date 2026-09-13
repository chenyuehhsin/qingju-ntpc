"""One CLI for local planning and future explicitly authorized deployment."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))
from aws_integration.config import Config, Blocked, verified_session
from aws_integration.sdk import capabilities, require_capabilities, request
from aws_integration.state import State
from aws_integration.documents import documents, manifest_digest
from aws_integration.deploy import Deployment, token
from aws_integration.packaging import package
from aws_integration.retrieval import test_queries, validate_results
from aws_integration.cleanup import cleanup
from aws_integration.gateway_client import GatewayClient
from policy_agent.registry import PolicyToolRegistry

COMMANDS = ["capabilities", "validate-kb", "package", "access", "s3", "kb", "ingest", "gateway", "lambda", "kb-target", "policy-target", "test-kb", "smoke", "cleanup"]


def parity_cases():
    return [("get_district_stats", {"district": "板橋區", "metrics": ["job_count"]}),
            ("compare_districts", {"districts": ["板橋區", "淡水區"], "metrics": ["salary"]}),
            ("get_district_stats", {"district": "板橋區", "metrics": ["opportunity_index"]}),
            ("forecast_employment_demand", {"district": "板橋區", "category": "all", "horizon": 3}),
            ("get_district_stats", {"district": "台北市"}), ("get_data_period", {})]


def smoke(deployment, session):
    state, c = deployment.state, deployment.c
    docs = documents(ROOT / "knowledge_base")
    objects = request(deployment.clients['s3'], 'list_objects_v2', Bucket=c.bucket, Prefix=c.document_prefix,
                      ExpectedBucketOwner=state.data['account'], MaxKeys=1)
    if not objects.get('Contents'):
        raise Blocked('S3 KB prefix is empty')
    kb_resource = request(deployment.clients['bedrock-agent'], 'get_knowledge_base', knowledgeBaseId=state.get('kb'))['knowledgeBase']
    if kb_resource['status'] != 'ACTIVE':
        raise Blocked('KB is not ACTIVE')
    job_id = state.data['ingestions'].get(manifest_digest(docs))
    if not job_id:
        raise Blocked('Current document manifest has no completed ingestion')
    job = request(deployment.clients['bedrock-agent'], 'get_ingestion_job', knowledgeBaseId=state.get('kb'), dataSourceId=state.get('data_source'), ingestionJobId=job_id)['ingestionJob']
    if job['status'] != 'COMPLETE' or job.get('statistics', {}).get('numberOfDocumentsFailed', 0):
        raise Blocked('KB ingestion incomplete')
    gw = request(deployment.clients["bedrock-agentcore-control"], "get_gateway", gatewayIdentifier=state.get("gateway"))
    if gw["status"] != "READY":
        raise Blocked("Gateway not READY")
    for key in ("kb_target", "policy_target"):
        target = request(deployment.clients["bedrock-agentcore-control"], "get_gateway_target", gatewayIdentifier=state.get("gateway"), targetId=state.get(key))
        if target["status"] != "READY":
            raise Blocked("Gateway target not READY")
        if token(target['targetConfiguration']) != state.data['resources'][key]['fingerprint']:
            raise Blocked('Gateway target binding changed')
    mcp = GatewayClient(gw["gatewayUrl"], c.region, session.get_credentials())
    mcp.initialize()
    names = {t["name"] for t in mcp.list_tools()}
    registry = PolicyToolRegistry()
    cases = []
    for name, args in parity_cases():
        remote_name = c.prefix + "-policy___" + name
        if remote_name not in names:
            raise Blocked("Tool not discoverable on Gateway: " + name)
        actual = mcp.call_tool(remote_name, args)
        expected = registry.execute(name, args)
        cases.append({"tool": name, "passed": actual == expected, "status": actual.get("status")})
    kb_name = c.prefix + "-knowledge___Retrieve"
    if kb_name not in names:
        raise Blocked("KB Retrieve target not discoverable")
    kb = mcp.call_tool(kb_name, {"retrievalQuery": {"text": "目前職缺資料有哪些限制？"}})
    validated = validate_results(kb, c.bucket, c.document_prefix, docs)
    if validated['status'] != 'success':
        raise Blocked("Gateway KB retrieval returned no evidence")
    return {"execution": "LIVE_AWS", "s3_nonempty": True, "kb_active": True, "ingestion_complete": True,
            "parity_cases": cases, "gateway_kb_results": len(validated['results']),
            "passed": all(c["passed"] for c in cases)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=COMMANDS)
    p.add_argument("--apply", action="store_true", help="Enable live AWS access/mutations; default is entirely offline")
    p.add_argument("--confirm-delete", action="store_true")
    args = p.parse_args(argv)
    if args.command == "capabilities":
        return capabilities()
    if args.command == "validate-kb":
        return {"status": "LOCAL_VALIDATED", "documents": len(documents(ROOT / "knowledge_base"))}
    if args.command == "package":
        return package(ROOT)
    if not args.apply:
        return {"status": "DRY_RUN", "aws_status": "AWS_DEPLOYMENT_BLOCKED", "command": args.command,
                "network_calls": 0, "resource_mutations": 0,
                "next": "Configure/verify AWS profile, region and IAM; obtain deployment authorization before --apply"}
    require_capabilities()
    config = Config.from_env()
    session, identity = verified_session(config)
    if args.command == "access":
        # Account/ARN are not credentials; persist only in ignored live artifacts.
        return {"status": "IDENTITY_VERIFIED", **identity}
    state = State(ROOT / ".aws/qingju-state.json", config.region, identity["account"])
    clients = {name: session.client(name) for name in ("s3", "bedrock-agent", "bedrock-agentcore-control", "lambda", "bedrock-agent-runtime")}
    deployment = Deployment(config, state, clients)
    docs = documents(ROOT / "knowledge_base")
    with state.locked():
        if args.command == "s3": result = deployment.s3_sync(docs)
        elif args.command == "kb": result = deployment.kb()
        elif args.command == "ingest": result = deployment.ingest(docs)
        elif args.command == "gateway": result = deployment.gateway()
        elif args.command == "lambda": result = deployment.lambda_function()
        elif args.command.endswith("-target"): result = deployment.target("kb" if args.command == "kb-target" else "policy", PolicyToolRegistry().list_tools())
        elif args.command == "test-kb":
            result = test_queries(clients["bedrock-agent-runtime"], state.get("kb"), config, docs)
        elif args.command == "smoke": result = smoke(deployment, session)
        elif args.command == "cleanup": result = cleanup(deployment, args.confirm_delete)
        (ROOT / ".aws" / (args.command + "-result.json")).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.command == "test-kb" and result["passed"] != result["total"] or args.command == "smoke" and not result["passed"]:
        raise Blocked("Live smoke failed; inspect ignored result artifact")
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(main(), ensure_ascii=False, indent=2))
    except Exception as exc:
        # Never dump a provider response or request headers which could contain secrets.
        message = str(exc) if isinstance(exc, (Blocked, ValueError)) else type(exc).__name__
        print(json.dumps({"status": "AWS_DEPLOYMENT_BLOCKED", "reason": message}, ensure_ascii=False))
        raise SystemExit(2)
