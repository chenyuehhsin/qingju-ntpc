"""Server-side client for the IAM-protected policy-answer Lambda.

This is intentionally for a Streamlit server or AWS-hosted web backend, not
browser JavaScript: AWS credentials never reach a visitor's browser.
"""
from __future__ import annotations

import json
import os

from .config import Blocked


def answer_policy_question(question: str, topic: str | None = None) -> dict:
    function_name = os.environ.get("QINGJU_AI_LAMBDA_NAME", "").strip()
    if not function_name:
        raise Blocked("AI policy Lambda is not configured")
    try:
        import boto3
        response = boto3.client("lambda", region_name=os.environ.get("AWS_REGION", "us-west-2")).invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps({"tool_name": "answer_policy_question", "arguments": {"question": question, "topic": topic}}).encode(),
        )
        payload = json.loads(response["Payload"].read().decode("utf-8"))
    except Exception as exc:
        raise Blocked("AI policy service is unavailable") from exc
    if response.get("FunctionError") or payload.get("status") != "success":
        raise Blocked("AI policy service could not answer")
    return payload
