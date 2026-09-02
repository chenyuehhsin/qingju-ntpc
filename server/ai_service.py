from __future__ import annotations

import json
import os
from typing import Any

from src.ai_decision_engine import answer_query


SYSTEM_PROMPT = """你是新北市青年就業決策助理。只能使用使用者提供的 Evidence Pack 回答。
不可自行發明職缺、薪資、公司、行政區指標、資料來源、通勤時間或政策結論。
如果 evidence 不足，回答「目前資料不足以判斷。」"""


def deterministic_answer(query: str) -> dict[str, Any]:
    return answer_query(query)


def llm_answer_from_evidence(query: str, evidence_result: dict[str, Any]) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    evidence = {
        "intent": evidence_result.get("intent"),
        "parsed_constraints": evidence_result.get("parsed_constraints"),
        "recommendations": evidence_result.get("recommendations", [])[:5],
        "matching_jobs": evidence_result.get("matching_jobs", [])[:10],
        "provenance": evidence_result.get("provenance"),
    }
    try:
        client = OpenAI(api_key=api_key, timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "12")))
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "請用繁體中文，根據 Evidence Pack 產生精簡、可驗證的回答。"
                        "保留所有重要數字，不要加入 evidence 沒有的事實。\n"
                        f"使用者問題：{query}\n"
                        f"Evidence Pack：{json.dumps(evidence, ensure_ascii=False)}"
                    ),
                },
            ],
            temperature=0.2,
        )
        output = getattr(response, "output_text", None)
        if not isinstance(output, str) or not output.strip():
            return None
        return output.strip()
    except Exception:
        return None


def assistant_response(query: str) -> dict[str, Any]:
    result = deterministic_answer(query)
    llm_text = llm_answer_from_evidence(query, result)
    result["answer_source"] = "openai" if llm_text else "deterministic_template"
    if llm_text:
        result["answer"] = llm_text
    return result
