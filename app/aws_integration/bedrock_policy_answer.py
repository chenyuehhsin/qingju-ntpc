"""Grounded Nova Lite answers for the independent youth-policy dashboard.

The model never receives unrestricted project files.  It receives only the
allowlisted policy-tool results, and provenance remains deterministic in the
returned envelope rather than being invented by the model.
"""
from __future__ import annotations

import json
import os

from .config import Blocked
from policy_agent.registry import PolicyToolRegistry


MODEL_ID = os.environ.get("QINGJU_BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
MAX_QUESTION_LENGTH = 500
MAX_TOPIC_LENGTH = 80
SYSTEM_PROMPT = """你是「AI 青年政策智慧儀表板」的證據整理助手。
只可根據提供的 EVIDENCE JSON 回答，不能補充其中不存在的數字、年度、因果關係、政策成效或建議。
使用繁體中文，先直接回答，再說明資料範圍與限制。若證據不足，明確回答「現有資料不足以判斷」。
不要聲稱已瀏覽網路或引用未提供的來源；來源、期間與限制由系統另行呈現。"""


def _clean_text(value, label, maximum):
    if not isinstance(value, str):
        raise Blocked(label + " must be text")
    value = value.strip()
    if not value or len(value) > maximum:
        raise Blocked(label + " is missing or too long")
    return value


def _evidence(question, topic, registry):
    """Return only deterministic, tool-produced evidence for model context."""
    knowledge = registry.execute("search_policy_knowledge", {"query": question})
    period = registry.execute("get_data_period", {})
    return {
        "question": question,
        "topic": topic or "不限主題",
        "knowledge": knowledge,
        "data_period": period,
    }


def answer_policy_question(question, topic=None, *, registry=None, client=None, model_id=None):
    question = _clean_text(question, "question", MAX_QUESTION_LENGTH)
    if topic is not None:
        topic = _clean_text(topic, "topic", MAX_TOPIC_LENGTH)
    evidence = _evidence(question, topic, registry or PolicyToolRegistry())
    if client is None:
        import boto3
        client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-west-2"))
    try:
        response = client.converse(
            modelId=model_id or MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": "EVIDENCE JSON:\n" + json.dumps(evidence, ensure_ascii=False)}]}],
            inferenceConfig={"maxTokens": 650, "temperature": 0.2, "topP": 0.9},
        )
    except Exception as exc:  # SDK exceptions vary by deployment account; never disclose internals to callers.
        raise Blocked("Bedrock model is temporarily unavailable") from exc
    content = response.get("output", {}).get("message", {}).get("content", [])
    answer = next((item.get("text") for item in content if isinstance(item, dict) and item.get("text")), "")
    if not answer:
        raise Blocked("Bedrock returned no text")
    return {
        "status": "success",
        "model_id": model_id or MODEL_ID,
        "answer": answer,
        "evidence": evidence["knowledge"].get("evidence", []),
        "sources": evidence["knowledge"].get("sources", []),
        "data_period": evidence["data_period"].get("data_period", {}),
        "limitations": evidence["knowledge"].get("limitations", []) + evidence["data_period"].get("limitations", []),
    }
