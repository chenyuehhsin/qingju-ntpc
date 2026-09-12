"""Offline tests. Synthetic resources never leave process; no identity created."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import boto3
from botocore import UNSIGNED
from botocore.config import Config as ClientConfig
from botocore.exceptions import ClientError
from botocore.stub import Stubber

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "scripts/aws"))
from aws_integration.config import Config, Blocked, TAGS
from aws_integration.documents import documents
from aws_integration.sdk import capabilities, request
from aws_integration.state import State
from aws_integration.deploy import Deployment, wait_ready, pages
from aws_integration.lambda_handler import handler
from aws_integration.grounding import validate_agent_evidence, require_knowledge_query
from aws_integration.retrieval import retrieve
from aws_integration.cleanup import cleanup
from policy_agent.registry import PolicyToolRegistry
from manage import main, parity_cases


def client(service):
    # Unsigned clients avoid credential lookup entirely. Endpoint transport is
    # also disabled for this suite; Stubber intercepts requests before transport.
    return boto3.Session().client(service, region_name="us-east-1", config=ClientConfig(signature_version=UNSIGNED))


class MemoryService:
    """Stateful fake behind real botocore request shape validation."""
    def __init__(self, service):
        self.real = client(service)
        self.meta = self.real.meta
        self.calls, self.kb, self.ds, self.gw, self.targets = [], None, None, None, []

    def __getattr__(self, name):
        def call(**args):
            self.calls.append((name, args))
            now = __import__("datetime").datetime(2026, 1, 1)
            if name == "list_knowledge_bases": return {"knowledgeBaseSummaries": [] if not self.kb else [{"knowledgeBaseId": self.kb['knowledgeBaseId'], "name": self.kb['name'], "status": "ACTIVE", "updatedAt": now}]}
            if name == "create_knowledge_base":
                self.kb = {k: args[k] for k in ("name", "roleArn", "knowledgeBaseConfiguration")}
                self.kb.update(knowledgeBaseId="MOCKKB0001", knowledgeBaseArn="arn:aws:bedrock:us-east-1:000000000000:knowledge-base/MOCKKB0001", status="ACTIVE", createdAt=now, updatedAt=now)
                return {"knowledgeBase": deepcopy(self.kb)}
            if name == "get_knowledge_base": return {"knowledgeBase": deepcopy(self.kb)}
            if name == "list_data_sources": return {"dataSourceSummaries": [] if not self.ds else [{"knowledgeBaseId": self.ds['knowledgeBaseId'], "dataSourceId": self.ds['dataSourceId'], "name": self.ds['name'], "status": "AVAILABLE", "updatedAt": now}]}
            if name == "create_data_source":
                self.ds = {k: args[k] for k in ("name", "knowledgeBaseId", "dataSourceConfiguration", "dataDeletionPolicy")}
                self.ds.update(dataSourceId="MOCKDS0001", status="AVAILABLE", createdAt=now, updatedAt=now)
                return {"dataSource": deepcopy(self.ds)}
            if name == "get_data_source": return {"dataSource": deepcopy(self.ds)}
            if name in ("start_ingestion_job", "get_ingestion_job"):
                return {"ingestionJob": {"knowledgeBaseId": args["knowledgeBaseId"], "dataSourceId": args["dataSourceId"], "ingestionJobId": "MOCKJOB001", "status": "COMPLETE", "startedAt": now, "updatedAt": now, "statistics": {"numberOfDocumentsFailed": 0}}}
            if name == "list_gateways": return {"items": [] if not self.gw else [{"gatewayId": self.gw['gatewayId'], "name": self.gw['name'], "status": "READY", "createdAt": now, "updatedAt": now}]}
            if name == "create_gateway":
                self.gw = {k: args[k] for k in ("name", "roleArn", "authorizerType", "protocolType")}
                self.gw.update(gatewayId="mock-gateway", gatewayArn="arn:aws:bedrock-agentcore:us-east-1:000000000000:gateway/mock-gateway", status="READY", createdAt=now, updatedAt=now, gatewayUrl="https://mock.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp")
                return deepcopy(self.gw)
            if name == "get_gateway": return deepcopy(self.gw)
            if name == "list_gateway_targets": return {"items": [{"targetId": t['targetId'], "name": t['name'], "status": "READY", "createdAt": now, "updatedAt": now} for t in self.targets]}
            if name == "create_gateway_target":
                result = {k: args[k] for k in ("name", "targetConfiguration", "credentialProviderConfigurations")}
                result.update(targetId="mock-target-" + str(len(self.targets)), gatewayArn=self.gw['gatewayArn'], status="READY", createdAt=now, updatedAt=now)
                self.targets.append(result)
                return deepcopy(result)
            if name == "get_gateway_target": return deepcopy(next(t for t in self.targets if t['targetId'] == args['targetId']))
            if name == "list_tags_for_resource": return {"tags": TAGS.copy()}
            raise AssertionError("Unimplemented mock operation " + name)
        return call


class LocalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = patch("botocore.endpoint.Endpoint.make_request", side_effect=AssertionError("LIVE AWS FORBIDDEN"))
        cls.network.start()
        cls.registry = PolicyToolRegistry()

    @classmethod
    def tearDownClass(cls):
        cls.network.stop()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = State(Path(self.tmp.name) / "state.json", "us-east-1", "000000000000")
        self.config = Config(region="us-east-1", bucket="qingju-policy-assistant-mock", kb_role="arn:aws:iam::000000000000:role/mock", gateway_role="arn:aws:iam::000000000000:role/mock")

    def test_capabilities_offline(self):
        r = capabilities()
        self.assertTrue(r["supported"], r)
        self.assertTrue(r["features"]["MANAGED_KB"])

    def test_config_region_precedence_and_missing(self):
        self.assertEqual(Config.from_env({"AWS_REGION": "us-west-2", "AWS_DEFAULT_REGION": "us-east-1"}).region, "us-west-2")
        with self.assertRaises(Blocked): Config().validate()
        self.config.validate()

    def test_no_aws_calls_in_dry_run(self):
        with patch("manage.verified_session", side_effect=AssertionError("No credentials lookup")):
            for command in ("s3", "kb", "ingest", "gateway", "lambda", "kb-target", "policy-target", "test-kb", "smoke", "cleanup", "access"):
                self.assertEqual(main([command])["network_calls"], 0)

    def test_state_region_conflict_and_creation_flag(self):
        self.state.record("kb", "mock", created=True)
        self.state.record("kb", "mock", created=False)
        self.assertTrue(self.state.data["resources"]["kb"]["created"])
        with self.assertRaises(Blocked): State(self.state.path, "us-west-2", "000000000000")
        with self.assertRaises(Blocked): self.state.record("kb", "other")

    def test_lock_exclusive(self):
        with self.state.locked():
            with self.assertRaises(Blocked):
                with self.state.locked(): pass

    def test_kb_manifest_hashes(self):
        self.assertEqual(len(documents(ROOT / "knowledge_base")), 13)

    def test_bad_manifest_rejected_before_upload(self):
        root = Path(self.tmp.name)
        (root / "manifest.json").write_text(json.dumps({"documents": [{"path": "../oops.md"}]}))
        with self.assertRaises(Blocked): documents(root)

    def test_s3_existing_upload_and_skip_stubber(self):
        s3 = client("s3")
        d = Deployment(self.config, self.state, {"s3": s3})
        doc = documents(ROOT / "knowledge_base")[0]
        account = {"Bucket": self.config.bucket, "ExpectedBucketOwner": "000000000000"}
        with Stubber(s3) as stub:
            stub.add_response("head_bucket", {}, account)
            stub.add_response("get_bucket_tagging", {"TagSet": [{"Key": k, "Value": v} for k, v in TAGS.items()]}, account)
            stub.add_response("get_bucket_location", {}, account)
            stub.add_response("put_public_access_block", {}, {**account, "PublicAccessBlockConfiguration": {"BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": True, "RestrictPublicBuckets": True}})
            stub.add_response("head_object", {"Metadata": {"sha256": doc['sha256']}}, {**account, "Key": self.config.document_prefix + doc['path']})
            stub.add_client_error("head_object", service_error_code="404", http_status_code=404, expected_params={**account, "Key": self.config.document_prefix + doc['path'] + ".metadata.json"})
            stub.add_response("put_object", {})
            r = d.s3_sync([doc])
            self.assertEqual((r['uploaded'], r['skipped'], r['failed']), (1, 1, 0))
            stub.assert_no_pending_responses()

    def test_s3_permission_error_is_not_missing(self):
        s3 = client("s3")
        with Stubber(s3) as stub:
            stub.add_client_error("head_bucket", service_error_code="403", http_status_code=403)
            with self.assertRaises(ClientError): Deployment(self.config, self.state, {"s3": s3}).s3_sync([])
            self.assertFalse(self.state.data['resources'])

    def test_sdk_rejects_unknown_arguments(self):
        with self.assertRaises(Exception): request(client("s3"), "create_bucket", Bucket="valid-name", imaginaryParameter=True)

    def test_kb_gateway_and_ingestion_idempotent(self):
        a, g = MemoryService("bedrock-agent"), MemoryService("bedrock-agentcore-control")
        d = Deployment(self.config, self.state, {"bedrock-agent": a, "bedrock-agentcore-control": g})
        for _ in range(2):
            self.assertEqual(d.kb()['kb_status'], "ACTIVE")
            self.assertEqual(d.ingest(documents(ROOT / "knowledge_base"))['status'], "COMPLETE")
            self.assertEqual(d.gateway()['status'], "READY")
            self.assertEqual(d.target("kb", self.registry.list_tools())['status'], "READY")
        self.assertEqual(sum(n == 'create_knowledge_base' for n, _ in a.calls), 1)
        self.assertEqual(sum(n == 'start_ingestion_job' for n, _ in a.calls), 1)
        self.assertEqual(sum(n == 'create_gateway' for n, _ in g.calls), 1)
        self.assertEqual(sum(n == 'create_gateway_target' for n, _ in g.calls), 1)
        self.assertEqual(g.targets[0]['targetConfiguration']['mcp']['connector']['enabled'], ['Retrieve'])

    def test_policy_target_contains_only_registry_schemas(self):
        a, g = MemoryService("bedrock-agent"), MemoryService("bedrock-agentcore-control")
        d = Deployment(self.config, self.state, {"bedrock-agent": a, "bedrock-agentcore-control": g})
        d.gateway()
        self.state.record('lambda', 'mock', 'arn:aws:lambda:us-east-1:000000000000:function:mock')
        d.target('policy', self.registry.list_tools())
        schemas = g.targets[0]['targetConfiguration']['mcp']['lambda']['toolSchema']['inlinePayload']
        self.assertEqual({t['name'] for t in schemas}, set(self.registry.handlers))

    def test_reuse_conflicting_config_fails(self):
        a = MemoryService("bedrock-agent")
        d = Deployment(self.config, self.state, {"bedrock-agent": a})
        d.kb()
        a.kb['knowledgeBaseConfiguration'] = {'type': 'VECTOR'}
        with self.assertRaises(Blocked): d.kb()

    def test_readiness_does_not_accept_creating_or_failed(self):
        with self.assertRaises(Blocked): wait_ready(lambda: {'status': 'CREATING'}, timeout=0)
        with self.assertRaises(Blocked): wait_ready(lambda: {'status': 'FAILED'})
        values = iter([{'status': 'CREATING'}, {'status': 'READY'}])
        self.assertEqual(wait_ready(lambda: next(values), sleep=lambda _: None)['status'], 'READY')

    def test_lambda_direct_and_gateway_parity(self):
        for name, args in parity_cases():
            expected = self.registry.execute(name, args)
            self.assertEqual(handler({'tool_name': name, 'arguments': args}, None), expected)
            ctx = SimpleNamespace(client_context=SimpleNamespace(custom={'bedrockAgentCoreToolName': 'mock___' + name}))
            self.assertEqual(handler(args, ctx), expected)

    def test_lambda_malicious_names_rejected(self):
        self.assertEqual(handler({'tool_name': 'exec', 'arguments': {'code': 'delete'}}, None)['status'], 'unsupported')
        self.assertEqual(handler({'tool_name': 'get_data_period', 'arguments': {}, 'shell': 'x'}, None)['status'], 'unsupported')

    def test_forecast_and_missing_metrics_not_fabricated(self):
        r = handler({'tool_name': 'forecast_employment_demand', 'arguments': {'district': '板橋區', 'category': 'all', 'horizon': 3}}, None)
        self.assertEqual(r['status'], 'not_ready'); self.assertIsNone(r['data']['prediction'])
        for metric in ['opportunity_index', 'job_diversity', 'employment_stability']:
            self.assertEqual(handler({'tool_name': 'get_district_stats', 'arguments': {'district': '板橋區', 'metrics': [metric]}}, None)['status'], 'unsupported')

    def test_grounding_rejects_modified_values_status_sources(self):
        r = self.registry.execute('get_district_stats', {'district': '板橋區', 'metrics': ['job_count']})
        claim = {'tool_index': 0, 'path': '/data/metrics/0/values/job_count', 'value': r['data']['metrics'][0]['values']['job_count']}
        answer = {'statuses': ['success'], 'districts': ['板橋區'], 'sources': r['sources'], 'claims': [claim]}
        self.assertTrue(validate_agent_evidence(answer, [r])['valid'])
        for field, value in [('statuses', ['unsupported']), ('districts', ['台北市']), ('sources', [{'url': 'invented'}])]:
            self.assertFalse(validate_agent_evidence({**answer, field: value}, [r])['valid'])
        answer['claims'][0]['value'] += 1
        self.assertFalse(validate_agent_evidence(answer, [r])['valid'])

    def test_knowledge_numeric_boundary_and_empty_retrieval(self):
        for query in ['板橋目前有多少職缺？', '比較板橋跟淡水', 'Opportunity Index 是多少？']:
            with self.assertRaises(ValueError): require_knowledge_query(query)
        runtime = client('bedrock-agent-runtime')
        with Stubber(runtime) as stub:
            stub.add_response('retrieve', {'retrievalResults': []}, {'knowledgeBaseId': 'MOCKKB0001', 'retrievalQuery': {'text': '目前職缺資料有哪些限制？'}})
            r = retrieve(runtime, 'MOCKKB0001', '目前職缺資料有哪些限制？', self.config.bucket, self.config.document_prefix, documents(ROOT / 'knowledge_base'))
            self.assertEqual(r['status'], 'insufficient_data')

    def test_retrieval_citations_and_stale_hash(self):
        docs = documents(ROOT / 'knowledge_base')
        doc = docs[0]
        uri = f"s3://{self.config.bucket}/{self.config.document_prefix}{doc['path']}"
        runtime = client('bedrock-agent-runtime')
        for digest, valid in [(doc['sha256'], True), ('invalid', False)]:
            with Stubber(runtime) as stub:
                stub.add_response('retrieve', {'retrievalResults': [{'content': {'text': doc['body'].decode()}, 'location': {'type': 'S3', 's3Location': {'uri': uri}}, 'metadata': {'sha256': digest}}]})
                if valid:
                    self.assertEqual(retrieve(runtime, 'MOCKKB0001', '方法是什麼？', self.config.bucket, self.config.document_prefix, docs)['results'][0]['source'], uri)
                else:
                    with self.assertRaises(Blocked): retrieve(runtime, 'MOCKKB0001', '方法是什麼？', self.config.bucket, self.config.document_prefix, docs)

    def test_cleanup_dryrun_preserves_shared_resources(self):
        self.state.record('bucket', 'mock', created=True)
        self.state.record('lambda', 'shared', created=False)
        d = Deployment(self.config, self.state, {})
        plan = cleanup(d)
        self.assertTrue(plan['dry_run'])
        self.assertTrue(all(p['action'] == 'retain' for p in plan['plan']))

    def test_state_rejects_unexpected_secret_fields(self):
        self.state.data['credential'] = 'not-a-real-key'
        with self.assertRaises(Blocked): self.state.save()

    def test_gateway_projection_keeps_runtime_constraints(self):
        from aws_integration.sdk import gateway_input_schema
        original = self.registry.definitions['rank_districts']['inputSchema']
        before = deepcopy(original)
        projected = gateway_input_schema(original)
        self.assertNotIn('additionalProperties', projected)
        self.assertIn('maximum', projected['properties']['limit']['description'])
        self.assertEqual(original, before)
        self.assertEqual(handler({'tool_name': 'rank_districts', 'arguments': {'metric': 'salary', 'limit': 999}}, None)['status'], 'unsupported')

    def test_s3_create_region_and_ownership(self):
        s3 = client('s3')
        owned = {'Bucket': self.config.bucket, 'ExpectedBucketOwner': '000000000000'}
        with Stubber(s3) as stub:
            stub.add_client_error('head_bucket', service_error_code='404', http_status_code=404, expected_params=owned)
            stub.add_response('create_bucket', {}, {'Bucket': self.config.bucket})
            stub.add_response('put_bucket_tagging', {})
            stub.add_response('get_bucket_location', {})
            stub.add_response('put_public_access_block', {})
            Deployment(self.config, self.state, {'s3': s3}).s3_sync([])
            self.assertTrue(self.state.data['resources']['bucket']['created'])
            stub.assert_no_pending_responses()

    def test_lambda_reuse_image_conflict(self):
        from dataclasses import replace
        c = replace(self.config, lambda_role='arn:aws:iam::000000000000:role/mock', lambda_image='mock.dkr.ecr.us-east-1.amazonaws.com/qingju@sha256:' + 'a' * 64)
        lam = client('lambda')
        configuration = {'FunctionArn': 'arn:aws:lambda:us-east-1:000000000000:function:mock', 'Role': c.lambda_role, 'State': 'Active'}
        response = {'Configuration': configuration, 'Code': {'ResolvedImageUri': c.lambda_image}}
        with Stubber(lam) as stub:
            for _ in range(3): stub.add_response('get_function', response)
            stub.add_response('list_tags', {'Tags': TAGS})
            self.assertEqual(Deployment(c, self.state, {'lambda': lam}).lambda_function()['status'], 'Active')
        response['Code']['ResolvedImageUri'] = c.lambda_image + 'changed'
        with Stubber(lam) as stub:
            for _ in range(3): stub.add_response('get_function', response)
            stub.add_response('list_tags', {'Tags': TAGS})
            with self.assertRaises(Blocked): Deployment(c, self.state, {'lambda': lam}).lambda_function()

    def test_missing_sdk_method_clear_blocker(self):
        with self.assertRaises(Blocked): request(client('s3'), 'imaginary_aws_method')

    def test_cleanup_confirm_cannot_delete_shared_lambda(self):
        self.state.record('lambda', 'shared', created=False)
        result = cleanup(Deployment(self.config, self.state, {}), confirm=True)
        self.assertFalse(result['delete_requests_sent'])
        self.assertEqual(self.state.get('lambda'), 'shared')

    def test_arbitrary_endpoint_and_free_text_rejected(self):
        from aws_integration.gateway_client import GatewayClient
        with self.assertRaises(Blocked): GatewayClient('https://example.com/mcp', 'us-east-1', None)
        self.assertFalse(validate_agent_evidence({'statuses': [], 'text': 'Invented numeric answer'}, [])['valid'])


class TransportTests(unittest.TestCase):
    def test_mcp_json_response_id_and_redirect(self):
        from unittest.mock import Mock, patch
        from aws_integration.gateway_client import GatewayClient
        gateway = GatewayClient('https://mock.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp', 'us-east-1', Mock())
        response = Mock(status_code=200, headers={})
        response.json.return_value = {'jsonrpc': '2.0', 'id': 1, 'result': {'tools': []}}
        # Signing is mocked: no credentials (real or fabricated) are used.
        with patch('aws_integration.gateway_client.SigV4Auth'), patch('aws_integration.gateway_client.requests.post', return_value=response) as post:
            self.assertEqual(gateway.list_tools(), [])
            self.assertFalse(post.call_args.kwargs['allow_redirects'])
            with self.assertRaises(Blocked): gateway.list_tools()
            response.status_code = 302
            with self.assertRaises(Blocked): gateway.list_tools()

    def test_mcp_initialization_and_pagination(self):
        from unittest.mock import patch
        from aws_integration.gateway_client import GatewayClient
        gateway = GatewayClient('https://mock.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp', 'us-east-1', None)
        with patch.object(gateway, 'rpc', side_effect=[{'protocolVersion': '2025-03-26'}, None, {'tools': [{'name': 'one'}], 'nextCursor': 'next'}, {'tools': [{'name': 'two'}]}]) as rpc:
            gateway.initialize()
            self.assertEqual([t['name'] for t in gateway.list_tools()], ['one', 'two'])
            self.assertEqual(rpc.call_args_list[1].args[0], 'notifications/initialized')
            self.assertEqual(rpc.call_args_list[-1].args[1], {'cursor': 'next'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
