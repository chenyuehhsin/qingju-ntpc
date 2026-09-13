"""Offline service-model validation; no client/identity/network in capability audit."""
import boto3
import botocore
import botocore.session
from botocore.validate import validate_parameters
from .config import Blocked

OPERATIONS = {
    "s3": ["HeadBucket", "CreateBucket", "GetBucketLocation", "GetBucketTagging", "PutBucketTagging", "PutPublicAccessBlock", "HeadObject", "PutObject", "ListObjectsV2"],
    "bedrock-agent": ["ListKnowledgeBases", "GetKnowledgeBase", "CreateKnowledgeBase", "ListTagsForResource", "ListDataSources", "GetDataSource", "CreateDataSource", "StartIngestionJob", "GetIngestionJob", "DeleteDataSource", "DeleteKnowledgeBase"],
    "bedrock-agentcore-control": ["CreateGateway", "ListGateways", "GetGateway", "ListTagsForResource", "ListGatewayTargets", "CreateGatewayTarget", "GetGatewayTarget", "DeleteGatewayTarget", "DeleteGateway"],
    "lambda": ["GetFunction", "CreateFunction", "ListTags", "Invoke", "DeleteFunction"],
    "bedrock-agent-runtime": ["Retrieve"], "sts": ["GetCallerIdentity"],
}


def capabilities():
    session = botocore.session.get_session()
    results, missing = {}, []
    for service, operations in OPERATIONS.items():
        try:
            model = session.get_service_model(service)
            results[service] = {name: name in model.operation_names for name in operations}
            missing += [service + ":" + name for name, present in results[service].items() if not present]
        except botocore.exceptions.UnknownServiceError:
            results[service] = {name: False for name in operations}
            missing.append(service)
    try:
        a = session.get_service_model("bedrock-agent")
        g = session.get_service_model("bedrock-agentcore-control")
        nested = {"MANAGED_KB": "MANAGED" in a.shape_for("KnowledgeBaseConfiguration").members["type"].enum,
                  "MANAGED_EMBEDDINGS": "MANAGED" in a.shape_for("ManagedKnowledgeBaseConfiguration").members["embeddingModelType"].enum,
                  "NATIVE_KB_CONNECTOR": "connector" in g.shape_for("McpTargetConfiguration").members,
                  "AWS_IAM_GATEWAY": "AWS_IAM" in g.shape_for("CreateGatewayRequest").members["authorizerType"].enum}
        missing += [k for k, v in nested.items() if not v]
    except (KeyError, botocore.exceptions.BotoCoreError):
        nested = {}; missing.append("Nested Managed KB / Gateway schemas")
    return {"boto3": boto3.__version__, "botocore": botocore.__version__, "operations": results,
            "features": nested, "supported": not missing, "missing": missing,
            "scope": "SDK schemas only; credentials, region availability and IAM not verified"}


def require_capabilities():
    report = capabilities()
    if not report["supported"]:
        raise Blocked("SDK missing APIs: " + ", ".join(report["missing"]) + "; update isolated SDK or follow manual fallback")


def request(client, method, **kwargs):
    operation = client.meta.method_to_api_mapping.get(method)
    if not operation or not callable(getattr(client, method, None)):
        raise Blocked("SDK method unavailable: " + method)
    validate_parameters(kwargs, client.meta.service_model.operation_model(operation).input_shape)
    return getattr(client, method)(**kwargs)


def gateway_input_schema(schema):
    """Project to the actual Gateway JsonSchema subset; runtime stays strict.

    Current SDK omits enum/bounds/additionalProperties. Preserve those constraints
    as description text for tool selection, while the unchanged M3 registry
    continues enforcing the full JSON Schema on every invocation.
    """
    import json
    model = botocore.session.get_session().get_service_model("bedrock-agentcore-control")
    shape = model.operation_model("CreateGatewayTarget").input_shape.members["targetConfiguration"].members["mcp"].members["lambda"].members["toolSchema"].members["inlinePayload"].member.members["inputSchema"]
    def project(value):
        projected = {}
        for key, item in value.items():
            if key not in shape.members:
                continue
            if key == "properties": projected[key] = {k: project(v) for k, v in item.items()}
            elif key == "items": projected[key] = project(item)
            else: projected[key] = item
        omitted = {k: v for k, v in value.items() if k not in shape.members}
        if omitted:
            projected["description"] = (projected.get("description", "") + " Runtime-enforced constraints: " + json.dumps(omitted, ensure_ascii=False)).strip()
        return projected
    return project(schema)
