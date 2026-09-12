"""Validate structured claims, not unrestricted prose. Not wired to generation."""
import re


def value_at(value, pointer):
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer required")
    for segment in pointer[1:].split("/"):
        key = segment.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def validate_agent_evidence(answer, results):
    """answer={statuses:[...],claims:[{tool_index,path,value}],districts:[],sources:[]}.

    Numeric claims must point to numeric structured data/evidence, not KB text,
    dates, a score elsewhere or generated prose. No tolerance-based guessing.
    """
    errors = []
    if answer.get("text"):
        errors.append("Free-text semantic claims are not validated by this boundary")
    if answer.get("statuses") != [r["status"] for r in results]:
        errors.append("Tool statuses changed or omitted")
    district_set = {e["district"] for r in results for e in r["evidence"] if "district" in e}
    sources = [s for r in results for s in r["sources"]]
    if not set(answer.get("districts", [])) <= district_set:
        errors.append("District not supported by evidence")
    if any(s not in sources for s in answer.get("sources", [])):
        errors.append("Invented source")
    for claim in answer.get("claims", []):
        try:
            index, pointer = claim["tool_index"], claim["path"]
            if type(index) is not int or not 0 <= index < len(results):
                raise ValueError("Invalid tool index")
            result = results[index]
            if result["status"] != "success" or result["tool_name"] in {"search_policy_knowledge", "explain_metric", "forecast_employment_demand"}:
                raise ValueError("Not factual numeric evidence")
            if not pointer.startswith(("/data/", "/evidence/")):
                raise ValueError("Only factual data/evidence paths allowed")
            value = value_at(result, pointer)
            if type(value) not in (int, float) or type(claim["value"]) not in (int, float) or value != claim["value"]:
                raise ValueError("Numeric claim mismatch")
        except (KeyError, IndexError, ValueError, TypeError):
            errors.append("Unsupported numeric claim")
    return {"valid": not errors, "errors": errors, "scope": "structured claims only; free-text semantic validation not implemented"}


def require_knowledge_query(query):
    # Conservative explicit methodology grammar; this is not a general classifier.
    if not isinstance(query, str) or len(query) > 500 or re.search("多少|幾個|排名|排行|比較|預測|哪區|哪一區", query):
        raise ValueError("Policy Tool required for numeric/comparison/forecast query")
    if not re.search("方法|定義|來源|限制|期間|年齡範圍|拒答|是什麼", query):
        raise ValueError("Only explicit methodology questions may use KB")
