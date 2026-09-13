"""Offline deterministic evaluation. No LLM hallucination metrics are claimed."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))
from assistant_service import load_context, answer_question
from policy_agent.orchestrator import PolicyAgentOrchestrator
from policy_agent.engine import METRICS


def evaluate():
    agent = PolicyAgentOrchestrator()
    baseline = load_context()
    rows = {r["district"]: r for r in baseline["districts"]}
    names = ["Tool Selection Accuracy", "District Resolution Accuracy", "Unsupported Rejection Accuracy",
             "Out-of-Scope Rejection Accuracy", "Reliability Preservation", "Temporal Metadata Preservation", "Numeric Consistency"]
    counts = {n: {"passed": 0, "eligible": 0} for n in names}
    cases = []
    def record(name, ok):
        counts[name]["eligible"] += 1
        counts[name]["passed"] += int(ok)
        return ok
    for line in (ROOT / "tests/evaluation/policy_agent_eval.jsonl").read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        result = agent.run(case["question"])
        checks = [record(names[0], [r["tool_name"] for r in result["tool_results"]] == case["expected_tool"]),
                  record(names[1], result["plan"]["districts"] == case["expected_districts"]),
                  result["status"] == case["expected_status"]]
        if case["category"] == "unsupported":
            checks.append(record(names[2], result["status"] == case["expected_status"]))
        if case["category"] == "out_of_scope":
            checks.append(record(names[3], result["status"] == "out_of_scope"))
        for tool in result["tool_results"]:
            if tool["data_period"]:
                checks.append(record(names[5], all(tool["data_period"].get(k) == v for k, v in baseline["data_period"].items())
                                     and all(tool["data_period"].get(k) is None for k in ("snapshot_month", "jobs_reference_date", "processed_at"))))
            expected_districts = {r["district"] for r in tool["evidence"] if "district" in r}
            actual_districts = {r["district"] for r in tool["reliability"]}
            if expected_districts or tool["reliability"]:
                preserved = expected_districts <= actual_districts
                for item in tool["reliability"]:
                    original = answer_question(f"{item['district']}青年人口是多少", baseline)["reliability"][0]
                    preserved &= all(item.get(k) == v for k, v in original.items())
                checks.append(record(names[4], preserved))
            values = tool["data"].get("metrics", [])
            if values:
                correct = all(row["values"][metric] == rows[row["district"]][METRICS[metric]]
                              for row in values for metric in row["values"])
                checks.append(record(names[6], correct))
        cases.append({"question": case["question"], "passed": all(checks), "actual_status": result["status"],
                      "actual_tools": [r["tool_name"] for r in result["tool_results"]]})
    for metric in counts.values():
        metric["accuracy"] = metric["passed"] / metric["eligible"] if metric["eligible"] else None
    report = {"total_cases": len(cases), "passed": sum(c["passed"] for c in cases),
              "failed": sum(not c["passed"] for c in cases), "metrics": counts, "cases": cases,
              "scope": "Curated deterministic smoke corpus, not held-out model performance; no LLM is connected.",
              "reliability_scope": "Preserves existing samples/warnings; no real categorical high/medium/low layer exists."}
    return report


if __name__ == "__main__":
    report = evaluate()
    (ROOT / "docs/POLICY_AGENT_EVALUATION.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}, ensure_ascii=False, indent=2))
    print(json.dumps([c for c in report["cases"] if not c["passed"]], ensure_ascii=False))
    raise SystemExit(1 if report["failed"] else 0)
