"""Idempotent, injected-client AWS operations. CLI gates all live access."""
import hashlib
import json
import time
from botocore.exceptions import ClientError
from .config import TAGS, Blocked
from .documents import manifest_digest
from .sdk import request, gateway_input_schema


def token(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def not_found(exc):
    return exc.response["Error"]["Code"] in {"404", "NoSuchBucket", "NoSuchKey", "ResourceNotFoundException"}


def wait_ready(read, field="status", ready=("READY",), timeout=600, sleep=time.sleep):
    deadline = time.monotonic() + timeout
    while True:
        value = read()
        status = value[field]
        if status in ready:
            return value
        if status not in {"CREATING", "UPDATING", "STARTING", "IN_PROGRESS", "Pending", "InProgress"}:
            raise Blocked("Resource not ready: " + str(status))
        if time.monotonic() >= deadline:
            raise Blocked("Readiness timeout; resource NOT complete. Rerun to resume.")
        sleep(min(5, max(0, deadline - time.monotonic())))


def pages(client, method, key, **kwargs):
    output = []
    while True:
        page = request(client, method, **kwargs)
        output.extend(page.get(key, []))
        if not page.get("nextToken"):
            return output
        kwargs["nextToken"] = page["nextToken"]


def same(actual, expected, label):
    if actual != expected:
        raise Blocked("Existing resource configuration conflict: " + label)


class Deployment:
    def __init__(self, config, state, clients, sleep=time.sleep):
        self.c, self.state, self.clients, self.sleep = config, state, clients, sleep

    def tags(self, actual):
        if any(actual.get(k) != v for k, v in TAGS.items()):
            raise Blocked("Resource ownership tags do not match; refusing shared resource")

    def s3_sync(self, docs):
        c, s3 = self.c, self.clients["s3"]
        account = self.state.data["account"]
        owned = {"Bucket": c.bucket, "ExpectedBucketOwner": account}
        created = False
        try:
            request(s3, "head_bucket", **owned)
        except ClientError as exc:
            if not not_found(exc):
                raise
            args = {"Bucket": c.bucket}
            if c.region != "us-east-1":
                args["CreateBucketConfiguration"] = {"LocationConstraint": c.region}
            request(s3, "create_bucket", **args)
            self.state.record("bucket", c.bucket, created=True)
            created = True
        if created:
            request(s3, "put_bucket_tagging", **owned, Tagging={"TagSet": [{"Key": k, "Value": v} for k, v in TAGS.items()]})
        else:
            self.tags({t["Key"]: t["Value"] for t in request(s3, "get_bucket_tagging", **owned)["TagSet"]})
        region = request(s3, "get_bucket_location", **owned).get("LocationConstraint") or "us-east-1"
        same("eu-west-1" if region == "EU" else region, c.region, "bucket region")
        request(s3, "put_public_access_block", **owned, PublicAccessBlockConfiguration={
            "BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
        self.state.record("bucket", c.bucket, created=created)
        uploaded = skipped = failed = 0
        failures = []
        for doc in docs:
            sidecar = json.dumps({"metadataAttributes": {"document_id": doc["id"], "category": doc["category"],
                                                        "sha256": doc["sha256"], "source_files": json.dumps(doc["sources"], ensure_ascii=False)}}, ensure_ascii=False).encode()
            for suffix, body, content_type in [("", doc["body"], "text/markdown; charset=utf-8"), (".metadata.json", sidecar, "application/json")]:
                key = c.document_prefix + doc["path"] + suffix
                digest = hashlib.sha256(body).hexdigest()
                try:
                    try:
                        old = request(s3, "head_object", **owned, Key=key)
                    except ClientError as exc:
                        if not not_found(exc):
                            raise
                        old = {}
                    if old.get("Metadata", {}).get("sha256") == digest:
                        skipped += 1
                        continue
                    request(s3, "put_object", **owned, Key=key, Body=body, ContentType=content_type,
                            ServerSideEncryption="AES256", Metadata={"sha256": digest, "document-id": doc["id"]})
                    uploaded += 1
                except ClientError:
                    failed += 1; failures.append(key)
        result = {"bucket": c.bucket, "prefix": c.document_prefix, "documents": len(docs),
                  "uploaded": uploaded, "skipped": skipped, "failed": failed, "failed_keys": failures,
                  "count_unit": "objects including metadata sidecars"}
        if failed:
            raise Blocked("S3 sync incomplete: " + json.dumps(result))
        return result

    def kb(self):
        c, client = self.c, self.clients["bedrock-agent"]
        c.require("kb_role")
        name = c.prefix + "-kb"
        config = {"type": "MANAGED", "managedKnowledgeBaseConfiguration": {"embeddingModelType": "MANAGED"}}
        identifier = c.kb_id or self.state.get("kb")
        if not identifier:
            matches = [r for r in pages(client, "list_knowledge_bases", "knowledgeBaseSummaries") if r["name"] == name]
            if len(matches) > 1:
                raise Blocked("Duplicate KB names")
            identifier = matches[0]["knowledgeBaseId"] if matches else None
        created = not identifier
        if created:
            args = {"name": name, "roleArn": c.kb_role, "knowledgeBaseConfiguration": config, "tags": TAGS}
            resource = request(client, "create_knowledge_base", **args, clientToken=token(args))["knowledgeBase"]
            identifier = resource["knowledgeBaseId"]
            self.state.record("kb", identifier, resource["knowledgeBaseArn"], created=True)
        resource = wait_ready(lambda: request(client, "get_knowledge_base", knowledgeBaseId=identifier)["knowledgeBase"], ready=("ACTIVE",), sleep=self.sleep)
        self.tags(request(client, "list_tags_for_resource", resourceArn=resource["knowledgeBaseArn"])["tags"])
        same(resource["name"], name, "KB name")
        same(resource["roleArn"], c.kb_role, "KB role")
        same(resource["knowledgeBaseConfiguration"], config, "Managed KB configuration")
        self.state.record("kb", identifier, resource["knowledgeBaseArn"], created=created)
        partition = resource["knowledgeBaseArn"].split(":")[1]
        ds_config = {"type": "S3", "s3Configuration": {"bucketArn": f"arn:{partition}:s3:::{c.bucket}", "inclusionPrefixes": [c.document_prefix]}}
        matches = [r for r in pages(client, "list_data_sources", "dataSourceSummaries", knowledgeBaseId=identifier) if r["name"] == c.prefix + "-documents"]
        if len(matches) > 1:
            raise Blocked("Duplicate data source names")
        ds_created = not matches
        if matches:
            ds_id = matches[0]["dataSourceId"]
        else:
            args = {"knowledgeBaseId": identifier, "name": c.prefix + "-documents", "dataSourceConfiguration": ds_config, "dataDeletionPolicy": "RETAIN"}
            ds = request(client, "create_data_source", **args, clientToken=token(args))["dataSource"]
            ds_id = ds["dataSourceId"]
            self.state.record("data_source", ds_id, created=True)
        ds = wait_ready(lambda: request(client, "get_data_source", knowledgeBaseId=identifier, dataSourceId=ds_id)["dataSource"], ready=("AVAILABLE",), sleep=self.sleep)
        same(ds["dataSourceConfiguration"], ds_config, "S3 data source prefix")
        same(ds.get("dataDeletionPolicy"), "RETAIN", "data retention")
        self.state.record("data_source", ds_id, created=ds_created)
        return {"kb_status": resource["status"], "data_source_status": ds["status"]}

    def ingest(self, docs):
        client = self.clients["bedrock-agent"]
        kb, ds = self.state.get("kb"), self.state.get("data_source")
        if not kb or not ds:
            raise Blocked("Run kb first")
        digest = manifest_digest(docs)
        old = self.state.data["ingestions"].get(digest)
        if not old:
            job = request(client, "start_ingestion_job", knowledgeBaseId=kb, dataSourceId=ds,
                          clientToken=token([kb, ds, digest]))["ingestionJob"]
            old = job["ingestionJobId"]
            self.state.data["ingestions"][digest] = old
            self.state.save()
        job = wait_ready(lambda: request(client, "get_ingestion_job", knowledgeBaseId=kb, dataSourceId=ds, ingestionJobId=old)["ingestionJob"], ready=("COMPLETE",), sleep=self.sleep)
        if job.get("statistics", {}).get("numberOfDocumentsFailed", 0):
            raise Blocked("Ingestion reports failed documents; not a passing sync")
        return {"status": job["status"], "statistics": job.get("statistics", {}), "ingestion_id": old}

    def gateway(self):
        c, client = self.c, self.clients["bedrock-agentcore-control"]
        c.require("gateway_role")
        name = c.prefix + "-gateway"
        identifier = c.gateway_id or self.state.get("gateway")
        if not identifier:
            matches = [r for r in pages(client, "list_gateways", "items") if r["name"] == name]
            if len(matches) > 1:
                raise Blocked("Duplicate gateway names")
            identifier = matches[0]["gatewayId"] if matches else None
        created = not identifier
        if created:
            args = {"name": name, "roleArn": c.gateway_role, "authorizerType": "AWS_IAM", "protocolType": "MCP", "tags": TAGS}
            resource = request(client, "create_gateway", **args, clientToken=token(args))
            identifier = resource["gatewayId"]
            self.state.record("gateway", identifier, resource["gatewayArn"], created=True)
        resource = wait_ready(lambda: request(client, "get_gateway", gatewayIdentifier=identifier), sleep=self.sleep)
        self.tags(request(client, "list_tags_for_resource", resourceArn=resource["gatewayArn"])["tags"])
        for field, value in {"name": name, "roleArn": c.gateway_role, "authorizerType": "AWS_IAM", "protocolType": "MCP"}.items():
            same(resource[field], value, "gateway " + field)
        self.state.record("gateway", identifier, resource["gatewayArn"], created=created)
        return {"status": resource["status"], "gateway_id": identifier}

    def lambda_function(self):
        c, client = self.c, self.clients["lambda"]
        c.require("lambda_role", "lambda_image")
        if "@sha256:" not in c.lambda_image:
            raise Blocked("Pin QINGJU_LAMBDA_IMAGE_URI to an immutable ECR digest")
        name, created = c.prefix + "-tools", False
        try:
            resource = request(client, "get_function", FunctionName=name)
        except ClientError as exc:
            if not not_found(exc):
                raise
            config = request(client, "create_function", FunctionName=name, Role=c.lambda_role, PackageType="Image",
                             Code={"ImageUri": c.lambda_image}, Architectures=["x86_64"], Timeout=60, MemorySize=2048, Tags=TAGS)
            self.state.record("lambda", name, config["FunctionArn"], created=True)
            created = True
        config = wait_ready(lambda: request(client, "get_function", FunctionName=name)["Configuration"], field="State", ready=("Active",), sleep=self.sleep)
        resource = request(client, "get_function", FunctionName=name)
        self.tags(request(client, "list_tags", Resource=config["FunctionArn"])["Tags"])
        same(config["Role"], c.lambda_role, "Lambda role")
        same(resource["Code"].get("ResolvedImageUri", resource["Code"].get("ImageUri")), c.lambda_image, "Lambda image; explicit update required on conflict")
        self.state.record("lambda", name, config["FunctionArn"], created=created)
        return {"status": config["State"], "function_name": name}

    def target(self, kind, schemas):
        client, gateway = self.clients["bedrock-agentcore-control"], self.state.get("gateway")
        if not gateway:
            raise Blocked("Run gateway first")
        name = self.c.prefix + ("-knowledge" if kind == "kb" else "-policy")
        if kind == "kb":
            kb = self.state.get("kb")
            if not kb:
                raise Blocked("Run kb first")
            config = {"mcp": {"connector": {"source": {"connectorId": "bedrock-knowledge-bases"}, "enabled": ["Retrieve"],
                      "configurations": [{"name": "Retrieve", "parameterValues": {"knowledgeBaseId": kb}}]}}}
        else:
            resource = self.state.data["resources"].get("lambda")
            if not resource:
                raise Blocked("Run lambda first")
            config = {"mcp": {"lambda": {"lambdaArn": resource["arn"], "toolSchema": {"inlinePayload": [
                {"name": t["name"], "description": t["description"], "inputSchema": gateway_input_schema(t["inputSchema"])} for t in schemas]}}}}
        matches = [r for r in pages(client, "list_gateway_targets", "items", gatewayIdentifier=gateway) if r["name"] == name]
        if len(matches) > 1:
            raise Blocked("Duplicate target names")
        created = not matches
        if created:
            args = {"gatewayIdentifier": gateway, "name": name, "targetConfiguration": config,
                    "credentialProviderConfigurations": [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]}
            resource = request(client, "create_gateway_target", **args, clientToken=token(args))
            identifier = resource["targetId"]
            self.state.record(kind + "_target", identifier, created=True)
        else:
            identifier = matches[0]["targetId"]
        resource = wait_ready(lambda: request(client, "get_gateway_target", gatewayIdentifier=gateway, targetId=identifier), sleep=self.sleep)
        same(resource["targetConfiguration"], config, "target binding and schema")
        same(resource["credentialProviderConfigurations"], [{"credentialProviderType": "GATEWAY_IAM_ROLE"}], "target credentials")
        self.state.record(kind + "_target", identifier, created=created, fingerprint=token(config))
        return {"status": resource["status"], "target_id": identifier}
