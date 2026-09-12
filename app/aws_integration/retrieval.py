"""Read-only AWS retrieval with manifest provenance checks and no generation."""
import json
from .config import Blocked
from .grounding import require_knowledge_query
from .sdk import request

QUERIES = [
    ("青年資料的年齡範圍是什麼？", "definitions"),
    ("目前職缺資料有哪些限制？", "limitations"),
    ("資料期間如何定義？", "methodology"),
    ("為什麼有些問題系統會拒答？", "definitions"),
    ("目前青聚有哪些資料來源？", "data_catalog"),
    ("Opportunity Index 是什麼？", "methodology"),
]


def retrieve(client, kb_id, query, bucket, prefix, docs):
    require_knowledge_query(query)
    response = request(client, "retrieve", knowledgeBaseId=kb_id, retrievalQuery={"text": query})
    return validate_results(response, bucket, prefix, docs)


def validate_results(response, bucket, prefix, docs):
    allowed = {f"s3://{bucket}/{prefix}{d['path']}": d for d in docs}
    results = []
    for item in response.get("retrievalResults", []):
        uri = item.get("location", {}).get("s3Location", {}).get("uri")
        doc = allowed.get(uri)
        if not doc or item.get("metadata", {}).get("sha256") != doc["sha256"]:
            raise Blocked("Retrieval returned unknown/stale source; refusing citation")
        results.append({"text": item.get("content", {}).get("text", ""), "source": uri,
                        "document_id": doc["id"], "category": doc["category"], "metadata": item.get("metadata", {}),
                        "score": item.get("score")})
    return {"status": "success" if results else "insufficient_data", "results": results}


def test_queries(client, kb_id, config, docs):
    cases = []
    for query, category in QUERIES:
        result = retrieve(client, kb_id, query, config.bucket, config.document_prefix, docs)
        passed = any(r["category"] == category for r in result["results"])
        if "Opportunity Index" in query:
            passed = passed and any(r["document_id"] == "opportunity_index" and "沒有" in r["text"] for r in result["results"])
        cases.append({"query": query, "passed": passed, **result})
    return {"execution": "LIVE_AWS", "passed": sum(c["passed"] for c in cases), "total": len(cases), "cases": cases}
