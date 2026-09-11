"""Contract, boundary, regression and adverse-input tests for Milestone 3."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "scripts/product"))
from assistant_service import load_context, answer_question
from policy_agent.engine import QingjuEngine, METRICS, ordered_rows
from policy_agent.registry import PolicyToolRegistry, AgentCoreToolAdapter
from policy_agent.orchestrator import PolicyAgentOrchestrator
from policy_agent.contracts import SessionContext, AgentPlan, ToolCall
from policy_agent.knowledge import LocalKnowledgeSearch
from forecast_readiness import audit
from jsonschema import Draft202012Validator


class MutableEngine(QingjuEngine):
    def __init__(self, context):
        self.context = deepcopy(context)
        self.reads = 0

    def snapshot(self):
        self.reads += 1
        return deepcopy(self.context)


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context()

    def setUp(self):
        self.engine = MutableEngine(self.context)
        self.registry = PolicyToolRegistry(self.engine)
        self.agent = PolicyAgentOrchestrator(self.registry)

    def test_registry_schema_and_exports(self):
        expected = {"get_district_stats", "compare_districts", "rank_districts", "get_reliability", "get_data_period", "explain_metric", "find_policy_observations", "search_policy_knowledge", "forecast_employment_demand"}
        self.assertEqual(set(self.registry.handlers), expected)
        self.assertEqual(self.registry.list_tools(), json.loads((ROOT / "docs/policy_tool_schemas.json").read_text(encoding="utf-8")))
        for t in self.registry.list_tools():
            Draft202012Validator.check_schema(t["inputSchema"])
            Draft202012Validator.check_schema(t["outputSchema"])
        adapter = AgentCoreToolAdapter(self.registry)
        self.assertEqual(len(adapter.bedrock_tool_config()["tools"]), 9)
        self.assertEqual(set(adapter.handler_mapping()), expected)
        self.assertEqual(adapter.invoke("get_data_period", {}), self.registry.execute("get_data_period", {}))

    def test_stats_exact_existing_engine(self):
        actual = self.registry.execute("get_district_stats", {"district": "板橋"})
        expected = answer_question("板橋青年人口是多少", self.context)
        self.assertEqual(actual["evidence"], expected["evidence"])
        self.assertEqual(actual["sources"], expected["sources"])

    def test_compare_exact_existing_engine(self):
        actual = self.registry.execute("compare_districts", {"districts": ["板橋區", "淡水區"]})
        self.assertEqual(actual["evidence"], answer_question("比較板橋與淡水", self.context)["evidence"])
        for metric in METRICS:
            values = actual["data"]["metrics"]
            self.assertEqual(values[0]["values"][metric], actual["evidence"][0][METRICS[metric]])

    def test_raw_sort_no_scoring_and_nulls(self):
        result = self.registry.execute("rank_districts", {"metric": "salary", "limit": 5})
        expected = sorted([r["median_salary"] for r in self.context["districts"] if r["median_salary"] is not None], reverse=True)[:5]
        self.assertEqual([r["value"] for r in result["data"]["ranking"]], expected)
        tied = [{"district": "A", "median_salary": 2}, {"district": "B", "median_salary": 2}, {"district": "C", "median_salary": 1}, {"district": "D", "median_salary": None}]
        self.assertEqual([r["rank"] for r in ordered_rows(tied, "salary", "descending", 4)], [1, 1, 3])

    def test_reliability_preserved_unknown_not_invented(self):
        result = self.registry.execute("get_reliability", {"districts": ["板橋區"]})
        original = answer_question("板橋青年人口是多少", self.context)["reliability"][0]
        self.assertTrue(all(result["reliability"][0][k] == v for k, v in original.items()))
        self.assertIsNone(result["reliability"][0]["level"])
        self.assertEqual(result["status"], "insufficient_data")

    def test_synthetic_low_warning_preservation(self):
        # Synthetic adapter fixture only; the real repo has no low/high layer.
        original = self.engine.lookup
        def low(d, ctx):
            result = original(d, ctx)
            result["reliability"][0].update(level="low", warning="synthetic low warning")
            return result
        self.engine.lookup = low
        result = self.registry.execute("get_district_stats", {"district": "板橋區"})
        self.assertEqual(result["reliability"][0]["warning"], "synthetic low warning")
        self.assertFalse(result["data"]["recommendation_allowed"])

    def test_period_preserved_without_fabricating_dates(self):
        period = self.registry.execute("get_data_period", {})["data"]
        for k, v in self.context["data_period"].items():
            self.assertEqual(period[k], v)
        for k in ("processed_at", "snapshot_month", "jobs_reference_date"):
            self.assertIsNone(period[k])

    def test_existing_policy_matrix_exact(self):
        r = self.registry.execute("find_policy_observations", {})
        self.assertEqual(r["data"]["observations"], [{k: row[k] for k in ("資料訊號", "政策觀察", "涉及行政區")} for row in self.context["policy_matrix"]])

    def test_structured_policy_thresholds_and_minimum_reliability(self):
        import pandas as pd
        from components.policy_lens import load_youth_job_opportunity_data
        data = load_youth_job_opportunity_data()
        expected = data[data.youth_18_35_count.ge(data.youth_18_35_count.median()) & data.youth_job_opportunity_per_1000.lt(data.youth_job_opportunity_per_1000.median())]
        conditions = [{"metric": "jobs_per_1000_youth", "operator": "low"}, {"metric": "youth_population", "operator": "high"}]
        r = self.registry.execute("find_policy_observations", {"conditions": conditions})
        self.assertEqual(set(r["data"]["districts"]), set(expected.district))
        r = self.registry.execute("find_policy_observations", {"conditions": conditions, "minimum_reliability": "medium"})
        self.assertEqual(r["status"], "insufficient_data")
        self.assertFalse(r["data"]["filter_applied"])
        self.assertEqual(self.registry.execute("find_policy_observations", {"conditions": [{"metric": "salary", "operator": "high"}]})["status"], "unsupported")

    def test_multi_tool_is_not_false_success(self):
        r = self.agent.run("哪些區青年人口多、職缺相對少，而且資料可信度至少中等？")
        self.assertEqual(len(r["tool_results"]), 3)
        self.assertEqual(r["status"], "insufficient_data")
        self.assertIn("無法確認", r["answer"])

    def test_knowledge_and_numeric_boundary(self):
        r = self.agent.run("Opportunity Index 是什麼？")
        self.assertEqual(r["tool_results"][0]["tool_name"], "explain_metric")
        self.assertEqual(r["status"], "unsupported")
        r = self.agent.run("淡水 Opportunity Index 是多少？")
        self.assertEqual(r["tool_results"][0]["tool_name"], "get_district_stats")
        self.assertEqual(self.registry.execute("search_policy_knowledge", {"query": "淡水有多少職缺"})["status"], "unsupported")

    def test_outside_scope_and_unsupported(self):
        self.assertEqual(self.agent.run("台北市哪區最好？")["status"], "out_of_scope")
        self.assertEqual(self.agent.run("青年心理健康如何？")["status"], "insufficient_data")
        self.assertEqual(self.registry.execute("get_district_stats", {"district": "臺北市板橋區"})["status"], "out_of_scope")

    def test_multi_turn_fresh_numeric_data(self):
        first = self.agent.run("比較板橋和淡水")
        session = SessionContext(**first["session_context"])
        self.assertEqual(set(first["session_context"]), {"active_districts", "active_metric", "previous_intent"})
        row = next(r for r in self.engine.context["districts"] if r["district"] == "板橋區")
        row["median_salary"] = 123.0  # fixture changes only; never write real data.
        second = self.agent.run("那薪資呢？", session)
        self.assertEqual(second["tool_results"][0]["data"]["metrics"][0]["values"]["salary"], 123.0)
        self.assertGreater(self.engine.reads, 2)
        self.assertEqual(self.agent.run("哪個資料比較可靠？", SessionContext(**second["session_context"]))["status"], "insufficient_data")
        self.assertEqual(self.agent.run("那薪資呢？")["status"], "insufficient_data")

    def test_forecast_not_ready(self):
        result = self.registry.execute("forecast_employment_demand", {"district": "板橋區", "category": "all", "horizon": 3})
        self.assertEqual(result["status"], "not_ready")
        self.assertIsNone(result["data"]["prediction"])
        self.assertEqual(audit()["available_months"], sorted({r["source_snapshot_date"][:7] for r in __import__("csv").DictReader((ROOT / "data/processed/employment/new_taipei_employment_summary.csv").read_text(encoding="utf-8-sig").splitlines())}))

    def test_why_factors_not_assumed_premise(self):
        r = self.registry.execute("compare_districts", {"districts": ["淡水區", "板橋區"], "metrics": ["salary"]})
        factors = r["data"]["factors"]
        for f in factors["supporting_factors"]:
            self.assertGreater(f["first_value"], f["second_value"])
        for f in factors["counter_factors"]:
            self.assertLessEqual(f["first_value"], f["second_value"])

    def test_malformed_calls_and_alias_duplicates(self):
        for name, args in [("unknown", {}), ("get_district_stats", {"district": "板橋區", "sql": "drop"}),
                           ("get_district_stats", {"district": "板橋区", "metrics": []}),
                           ("rank_districts", {"metric": "salary", "limit": True}),
                           ("rank_districts", {"metric": "salary", "limit": 30}),
                           ("compare_districts", {"districts": ["板橋", "板橋區"]})]:
            self.assertEqual(self.registry.execute(name, args)["status"], "unsupported")

    def test_serializable_readonly_and_nulls(self):
        before = deepcopy(self.engine.context)
        row = next(r for r in before["districts"] if r["rent_median"] is None)
        result = self.registry.execute("get_district_stats", {"district": row["district"], "metrics": ["rent"]})
        self.assertEqual(result["status"], "insufficient_data")
        json.dumps(result, allow_nan=False)
        self.assertEqual(self.engine.context, before)

    def test_knowledge_manifest_integrity(self):
        import hashlib
        manifest = json.loads((ROOT / "knowledge_base/manifest.json").read_text(encoding="utf-8"))
        for document in manifest["documents"]:
            content = (ROOT / "knowledge_base" / document["path"]).read_bytes()
            self.assertNotIn(b"\r\n", content)
            self.assertEqual(hashlib.sha256(content).hexdigest(), document["sha256"])
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory)
            (path / "manifest.json").write_text(json.dumps({"documents": [{"path": "../README.md", "keywords": ["x"]}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                LocalKnowledgeSearch(path).search("x")

    def test_missing_source_fail_closed(self):
        self.engine.snapshot = lambda: (_ for _ in ()).throw(OSError("missing"))
        self.assertEqual(self.registry.execute("get_data_period", {})["status"], "insufficient_data")
        self.assertEqual(self.agent.run("板橋薪資是多少")["status"], "insufficient_data")

    def test_outputs_validate_independently(self):
        inputs = {"get_district_stats": {"district": "板橋區"},
                  "compare_districts": {"districts": ["板橋區", "淡水區"]},
                  "rank_districts": {"metric": "salary"}, "get_reliability": {"districts": ["板橋區"]},
                  "get_data_period": {}, "explain_metric": {"metric": "salary"},
                  "find_policy_observations": {}, "search_policy_knowledge": {"query": "職缺資料有什麼限制"},
                  "forecast_employment_demand": {"district": "板橋區", "category": "all", "horizon": 3}}
        for name, args in inputs.items():
            result = self.registry.execute(name, args)
            Draft202012Validator(self.registry.definitions[name]["outputSchema"]).validate(result)
            json.dumps(result, allow_nan=False)

    def test_ui_multi_turn_queries_real_engine(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT / "app/app.py"), default_timeout=60).run()
        for query in ("比較板橋和淡水", "那薪資呢？"):
            app.text_input(key="qingju_assistant_question").input(query)
            next(b for b in app.button if b.label == "詢問小幫手").click().run()
            self.assertEqual(list(app.exception), [])
        result = app.session_state.qingju_assistant_answer
        self.assertEqual(result["tool_results"][0]["tool_name"], "compare_districts")
        self.assertEqual(result["session_context"]["active_metric"], "salary")
        self.assertEqual(result["tool_results"][0]["data"]["metrics"][0]["values"]["salary"],
                         next(r["median_salary"] for r in self.context["districts"] if r["district"] == "板橋區"))

    def test_bounded_planner(self):
        class TooMany:
            def plan(self, *args):
                return AgentPlan([ToolCall("get_data_period") for _ in range(7)])
        agent = PolicyAgentOrchestrator(self.registry, TooMany())
        self.assertEqual(agent.run("x")["status"], "unsupported")


if __name__ == "__main__":
    unittest.main(verbosity=2)
