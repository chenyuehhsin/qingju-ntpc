"""Grounded Nova Lite answers for the independent youth-policy dashboard.

The model never receives unrestricted project files.  It receives only the
allowlisted policy-tool results, and provenance remains deterministic in the
returned envelope rather than being invented by the model.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .config import Blocked


MODEL_ID = os.environ.get("QINGJU_BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "ai_youth_dashboard" / "official_dashboard_snapshot.json"
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


def _load_snapshot(snapshot=None):
    if snapshot is not None:
        return snapshot
    try:
        return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Blocked("AI youth-policy source snapshot is unavailable") from exc


def _evidence(question, topic, snapshot=None):
    """Return the independent dashboard snapshot, never Qingju New Taipei data."""
    source = _load_snapshot(snapshot)
    payloads = source.get("api_payloads", {})
    scope = payloads.get("data_scope")
    if not isinstance(scope, dict):
        raise Blocked("AI youth-policy source snapshot is invalid")
    attention = payloads.get("policy_attention", {})
    selected_topic = next((item for item in attention.get("topics", []) if item.get("topic_name_zh") == topic), None)
    sources = [{
        "source_agency": scope.get("source_agency"),
        "survey_name": round_.get("survey_name"),
        "survey_year": round_.get("survey_year"),
        "reference_period": round_.get("reference_period"),
        "sample_size": round_.get("sample_size"),
        "survey_url": round_.get("survey_url"),
        "methodology_url": round_.get("methodology_url"),
    } for round_ in scope.get("rounds", [])]
    limitations = [scope.get("note"), attention.get("disclaimer_zh"), attention.get("ranking_note_zh")]
    if selected_topic:
        limitations.extend(selected_topic.get("limitations", []))
    return {
        "question": question,
        "topic": topic or "不限主題",
        "source_project": source.get("source_project"),
        "data_scope": scope,
        # The full chart snapshot is intentionally kept in the website, but it
        # is too large for an interactive model request.  Sending all chart
        # cells causes Nova to spend most of the Lambda window reading JSON.
        # These are the source-backed summaries needed for Q&A; detailed charts
        # remain visible in the dashboard itself.
        "dashboard_data": {
            key: payloads.get(key)
            for key in (
                "cards",
                "service_awareness",
                "policy_attention",
                "policy_topics",
                "policy_sensitivity",
                "analytics_summary",
            )
        },
        "sources": [item for item in sources if item.get("survey_name")],
        "limitations": [item for item in limitations if item],
    }


def answer_policy_question(question, topic=None, *, snapshot=None, client=None, model_id=None):
    question = _clean_text(question, "question", MAX_QUESTION_LENGTH)
    if topic is not None:
        topic = _clean_text(topic, "topic", MAX_TOPIC_LENGTH)
    evidence = _evidence(question, topic, snapshot)
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
        "evidence": {"data_scope": evidence["data_scope"], "source_project": evidence["source_project"]},
        "sources": evidence["sources"],
        "data_period": {"survey_years": evidence["data_scope"].get("survey_years", [])},
        "limitations": evidence["limitations"],
    }
