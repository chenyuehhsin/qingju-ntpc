"""IAM-signed MCP client for future explicit live smoke; never generates answers."""
import json
from urllib.parse import urlparse
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from .config import Blocked


class GatewayClient:
    def __init__(self, endpoint, region, credentials):
        url = urlparse(endpoint)
        if url.scheme != "https" or not url.hostname or not url.hostname.endswith(f".gateway.bedrock-agentcore.{region}.amazonaws.com") or url.path != "/mcp":
            raise Blocked("Untrusted gateway endpoint")
        self.endpoint, self.region, self.credentials = endpoint, region, credentials
        self.session_id = None
        self.counter = 0

    def rpc(self, method, params, notification=False):
        self.counter += 1
        envelope = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            envelope["id"] = self.counter
        data = json.dumps(envelope)
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-03-26"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        request = AWSRequest(method="POST", url=self.endpoint, data=data, headers=headers)
        SigV4Auth(self.credentials.get_frozen_credentials(), "bedrock-agentcore", self.region).add_auth(request)
        response = requests.post(self.endpoint, data=data, headers=dict(request.headers), timeout=60, allow_redirects=False)
        response.raise_for_status()
        if not 200 <= response.status_code < 300:
            raise Blocked("Gateway redirect refused")
        self.session_id = response.headers.get("Mcp-Session-Id", self.session_id)
        if notification:
            return None
        if "text/event-stream" in response.headers.get("Content-Type", ""):
            packets = [json.loads(line[5:].strip()) for line in response.text.splitlines() if line.startswith("data:") and line[5:].strip()]
            payload = next((p for p in packets if p.get("id") == self.counter), {})
        else:
            payload = response.json()
        if payload.get("id") != self.counter or payload.get("error") or "result" not in payload:
            raise Blocked("Gateway MCP request failed")
        return payload["result"]

    def initialize(self):
        response = self.rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "qingju-local-smoke", "version": "4a"}})
        if response.get("protocolVersion") != "2025-03-26":
            raise Blocked("Unsupported negotiated MCP version")
        self.rpc("notifications/initialized", {}, notification=True)
        return response

    def list_tools(self):
        result, cursor = [], None
        while True:
            response = self.rpc("tools/list", {"cursor": cursor} if cursor else {})
            result.extend(response["tools"])
            cursor = response.get("nextCursor")
            if not cursor:
                return result

    def call_tool(self, name, arguments):
        result = self.rpc("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise Blocked("Gateway returned tool error")
        if "structuredContent" in result:
            return result["structuredContent"]
        text = "\n".join(c["text"] for c in result.get("content", []) if c.get("type") == "text")
        try:
            return json.loads(text)
        except ValueError:
            raise Blocked("Gateway did not return a serializable tool result") from None
