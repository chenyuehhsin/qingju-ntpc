"""Existing job assistant remains deterministic; policy queries have a separate route."""
from src.ai_decision_engine import answer_query


def deterministic_answer(query: str) -> dict:
    return answer_query(query)


def assistant_response(query: str) -> dict:
    result = deterministic_answer(query)
    result["answer_source"] = "deterministic_template"
    return result
