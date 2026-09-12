"""Bounded deterministic planner. Model selection can replace the Protocol later."""
from dataclasses import asdict
import re
from .contracts import AgentPlan, ToolCall, SessionContext
from .engine import METRICS
from .registry import PolicyToolRegistry

TOKENS = {
    "opportunityindex": "opportunity_index", "就業機會指數": "opportunity_index",
    "每千名青年求才人數": "jobs_per_1000_youth", "每千青年求才人數": "jobs_per_1000_youth",
    "青年人口": "youth_population", "求才人數": "hiring_count", "職缺": "job_count",
    "薪資": "salary", "租金": "rent", "職缺多樣性": "job_diversity", "就業穩定度": "employment_stability",
}
CONDITIONS = [{"metric": "youth_population", "operator": "high"},
              {"metric": "jobs_per_1000_youth", "operator": "low"}]


class DeterministicAgentPlanner:
    def plan(self, question, session, districts):
        text = re.sub(r"[\s？?。！!]", "", question).lower()
        if not text or len(question) > 500:
            return AgentPlan(status="insufficient_data")
        if re.search("台北市|臺北市|桃園|台中|臺中|高雄|台南|臺南|全台|全臺", text):
            return AgentPlan(status="out_of_scope")
        if re.search("心理|健康如何|去年|明年|忽略|編造|<|http", text):
            return AgentPlan(status="insufficient_data")
        aliases = {a: d for d in districts for a in (d, d[:-1])}
        found = []
        def replace(match):
            district = aliases[match.group()]
            if district not in found:
                found.append(district)
            return "D"
        normalized = re.sub("|".join(sorted(aliases, key=len, reverse=True)), replace, text)
        metric = next((TOKENS[t] for t in sorted(TOKENS, key=len, reverse=True) if t in text), None)
        def plan(name, args, intent, extra=()):
            return AgentPlan([ToolCall(name, args), *extra], intent, districts=found, metric=metric)
        if text in {"那薪資呢", "那租金呢", "那職缺呢", "哪個資料比較可靠", "那可靠度呢"}:
            found = list(session.active_districts)
            if not found:
                return AgentPlan(status="insufficient_data")
            if "可靠" in text:
                return plan("get_reliability", {"districts": found}, "reliability")
            return plan("compare_districts" if len(found) > 1 else "get_district_stats",
                        {("districts" if len(found) > 1 else "district"): found if len(found) > 1 else found[0],
                         "metrics": [metric]}, "district_compare" if len(found) > 1 else "district_lookup")
        if re.fullmatch(r"D(的)?(可靠度|reliability)(如何|是多少)?", normalized):
            return plan("get_reliability", {"districts": found}, "reliability")
        if re.fullmatch(r"預測D(未來)?[1-9][0-9]?個月(的)?職缺需求", normalized):
            horizon = int(re.search(r"\d+", normalized).group())
            return plan("forecast_employment_demand", {"district": found[0], "category": "all", "horizon": horizon}, "forecast")
        if text in {"資料期間是什麼", "資料是哪個月份", "資料更新到什麼時候"}:
            return plan("get_data_period", {}, "data_period")
        if text in {"哪些行政區值得進一步觀察", "有哪些政策訊號", "哪些區值得政策觀察"}:
            return plan("find_policy_observations", {}, "policy_observation")
        if re.fullmatch(r"(哪些區|找)?青年人口(多|高)、?(但|且|而)?(職缺|工作)(相對)?少(、|，)?(而且|且|而)?(資料)?(可信度|可靠度|reliability)?(至少中等|>=medium)?", text):
            args = {"conditions": CONDITIONS}
            if "中等" in text or "medium" in text:
                args["minimum_reliability"] = "medium"
            return plan("find_policy_observations", args, "policy_observation",
                        [ToolCall("get_reliability", {"districts": districts}), ToolCall("get_data_period")])
        if metric and re.fullmatch(r"(請)?(依)?(.+?)(最高|最低|排名|排行|最多|最少)(的)?(前)?[1-9][0-9]?(區|名)", text):
            # Full text must consist of metric and ranking grammar, not another dataset.
            suffix = text
            for token in sorted(TOKENS, key=len, reverse=True):
                suffix = suffix.replace(token, "M")
            if re.fullmatch(r"(請)?(依)?M(最高|最低|排名|排行|最多|最少)(的)?(前)?[1-9][0-9]?(區|名)", suffix):
                return plan("rank_districts", {"metric": metric, "order": "ascending" if "最低" in text or "最少" in text else "descending",
                                               "limit": int(re.search(r"\d+", text).group())}, "ranking")
        metric_normalized = normalized
        for token in sorted(TOKENS, key=len, reverse=True):
            metric_normalized = metric_normalized.replace(token, "M")
        if metric and len(found) == 1 and re.fullmatch(r"(請)?(查詢)?D(目前|現在)?(的)?M(有多少|是多少|多少|如何)?", metric_normalized):
            return plan("get_district_stats", {"district": found[0], "metrics": [metric]}, "district_lookup")
        if len(found) >= 2 and re.fullmatch(r"(請)?比較D([與和跟、,]D)+(的)?M?", metric_normalized):
            args = {"districts": found}
            if metric:
                args["metrics"] = [metric]
            return plan("compare_districts", args, "district_compare", [ToolCall("get_data_period")])
        if len(found) == 2 and metric and re.fullmatch(r"為什麼D(的)?M(排名)?比D高", metric_normalized):
            return plan("compare_districts", {"districts": found, "metrics": [metric]}, "why",
                        [ToolCall("get_reliability", {"districts": found}), ToolCall("get_data_period")])
        if not found and text in {"opportunityindex是什麼", "reliability是什麼", "可靠度是什麼", "每千名青年求才人數是什麼", "薪資怎麼算", "职缺多樣性是什麼", "職缺多樣性是什麼", "就業穩定度是什麼"}:
            return plan("explain_metric", {"metric": metric or "reliability"}, "metric_explain")
        if not found and text in {"職缺資料有什麼限制", "青年為什麼定義18–35歲", "青年為什麼定義18-35歲", "人口資料來源是什麼", "資料期間有什麼限制", "政策觀察怎麼解讀", "opportunityindex為什麼這樣設計"}:
            return plan("search_policy_knowledge", {"query": question}, "knowledge_query")
        return AgentPlan(status="insufficient_data")


class PolicyAgentOrchestrator:
    def __init__(self, registry=None, planner=None):
        self.registry = registry or PolicyToolRegistry()
        self.planner = planner or DeterministicAgentPlanner()

    def run(self, question, session=None):
        session = session or SessionContext()
        try:
            context = self.registry.engine.snapshot()
        except (OSError, ValueError, KeyError, RuntimeError):
            return {"intent": "unsupported", "status": "insufficient_data", "answer": "正式資料暫時無法讀取。",
                    "evidence": [], "sources": [], "reliability": [], "limitations": [], "data_period": {},
                    "tool_results": [], "session_context": asdict(session), "answer_source": "deterministic",
                    "plan": asdict(AgentPlan(status="insufficient_data"))}
        districts = [r["district"] for r in context["districts"]]
        plan = self.planner.plan(question, session, districts)
        results = []
        if len(plan.calls) > 6:
            plan = AgentPlan(status="unsupported")
        for call in plan.calls:
            results.append(self.registry.execute(call.name, call.arguments))
        status = plan.status
        for result in results:
            if result["status"] != "success":
                status = result["status"]
                break
        next_session = SessionContext(list(session.active_districts), session.active_metric, session.previous_intent)
        if plan.calls and all(d in districts for d in plan.districts):
            if plan.districts:
                next_session.active_districts = list(plan.districts)
            next_session.active_metric = plan.metric or session.active_metric
            next_session.previous_intent = plan.intent
        answer = render_answer(plan, results, status)
        combined = {k: [] for k in ("evidence", "sources", "reliability", "limitations")}
        periods = {}
        for result in results:
            for key in combined:
                for item in result[key]:
                    if item not in combined[key]:
                        combined[key].append(item)
            periods.update(result["data_period"])
        return {"intent": plan.intent, "status": status, "answer": answer, **combined,
                "data_period": periods, "tool_results": results, "session_context": asdict(next_session),
                "answer_source": "deterministic", "plan": asdict(plan)}


def render_answer(plan, results, status):
    if status == "out_of_scope":
        return "行政區查詢僅涵蓋新北市 29 區。"
    if not results:
        return "目前資料不足以回答這個問題。"
    first = results[0]
    if status != "success":
        message = next((r["data"].get("message") for r in results if r["status"] != "success" and r["data"].get("message")), None)
        return message or "目前資料不足以完整回答；缺值或未定義指標不能補造。"
    if plan.intent == "district_lookup":
        from assistant_service import LABELS
        row = first["data"]["metrics"][0]
        return "依目前青聚資料，" + row["district"] + "的" + "、".join(
            f"{LABELS[METRICS[m]]}為 {v:,.2f}" for m, v in row["values"].items()) + "。"
    if plan.intent == "district_compare":
        return "依目前青聚資料，各區比較如下；不同資料期間與尺度不能直接解讀為哪區一定較好。"
    if plan.intent == "ranking":
        rows = first["data"]["ranking"]
        return "依指定指標原始值排序（非政策優先順序）：" + "；".join(f"{r['rank']}. {r['district']}：{r['value']:,.2f}" for r in rows)
    if plan.intent == "policy_observation":
        return "以下是透明規則產生的觀察，僅供後續檢視，不是政策優先排序。"
    if plan.intent in ("knowledge_query", "metric_explain"):
        docs = first["data"].get("documents", first["data"].get("definitions", []))
        return "\n\n".join(d["text"] for d in docs) or first["data"].get("message", "目前資料不足。")
    return "請依下列正式證據、資料期間與限制解讀；相關不等於因果。"
