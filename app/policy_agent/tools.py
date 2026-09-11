"""Stateless tool adapters. Every call obtains fresh deterministic evidence."""
from copy import deepcopy
import json
from pathlib import Path
from .contracts import PolicyToolResult
from .engine import METRICS, ordered_rows, configured_observation


def resolve_district(name, context):
    names = [r["district"] for r in context["districts"]]
    aliases = {alias: d for d in names for alias in (d, d[:-1], "新北市" + d)}
    return aliases.get(name.strip())


class PolicyTools:
    def __init__(self, engine, knowledge, rules_path: Path):
        self.engine, self.knowledge = engine, knowledge
        self.rules_path = rules_path

    def call(self, name, args):
        context = self.engine.snapshot()
        result = PolicyToolResult(name, sources=deepcopy(context["sources"]),
                                  data_period=self.period(context),
                                  limitations=["資料只涵蓋新北市；相關不等於因果。", "不作強政策判斷或就業保證。"])
        districts = args.get("districts", [args["district"]] if "district" in args else [])
        resolved = [resolve_district(d, context) for d in districts]
        if any(d is None for d in resolved):
            result.status = "out_of_scope"
            result.data = {"message": "僅支援新北市 29 行政區；請提供可辨識的行政區。"}
            return result.to_dict()
        if len(set(resolved)) != len(resolved):
            result.status = "unsupported"
            result.data = {"message": "行政區別名解析後重複，請提供不同的行政區。"}
            return result.to_dict()
        if name == "search_policy_knowledge":
            result.sources, result.data_period = [], {}
            # Numeric queries must not be answered from documents.
            import re
            if re.search("多少|幾個|排名|排行|比較|預測|哪區|哪一區", args["query"]) or any(
                    r["district"][:-1] in args["query"] for r in context["districts"]):
                result.status = "unsupported"
                result.data = {"message": "數值、排名與比較必須使用 structured tools。"}
            else:
                matches = self.knowledge.search(args["query"])
                result.data = {"documents": matches}
                result.sources = [{"file": "knowledge_base/" + d["path"],
                                   "source": "青聚方法文件", "sha256": d["sha256"],
                                   "data_period": None, "source_files": d["source_files"]} for d in matches]
                result.status = "success" if matches else "insufficient_data"
            return result.to_dict()
        if name == "forecast_employment_demand":
            result.status = "not_ready"
            result.data = {"district": resolved[0], "category": args["category"],
                           "horizon": args["horizon"], "prediction": None,
                           "uncertainty": None, "training_period": None, "model_version": None,
                           "prediction_is_fact": False,
                           "message": "尚無經驗證的跨月職缺序列或已驗證模型，不能提供預測。"}
            return result.to_dict()
        if name == "get_data_period":
            result.data = dict(result.data_period)
            return result.to_dict()
        if name == "explain_metric":
            metric = args["metric"]
            docs = self.knowledge.search(metric)
            result.data = {"metric": metric, "definitions": docs}
            result.status = "success" if metric in METRICS or metric == "reliability" else "unsupported"
            result.data["message"] = ("本網站沒有此正式指標，不能套用其他專案的方法。"
                                       if result.status == "unsupported" else "請依附帶的正式方法與限制解讀。")
            return result.to_dict()
        if name == "find_policy_observations":
            config = json.loads(self.rules_path.read_text(encoding="utf-8"))
            conditions = args.get("conditions", [])
            canonical = lambda cs: sorted((c["metric"], c["operator"]) for c in cs)
            if conditions and canonical(conditions) != canonical(config["conditions"]):
                result.status = "unsupported"
                result.data = {"message": "未定義此條件組合的正式政策規則。"}
                return result.to_dict()
            if conditions:
                rows, thresholds = configured_observation(context, config)
                result.data = {"rule_id": config["rule_id"], "rule_version": config["version"],
                               "criteria": conditions, "thresholds": thresholds,
                               "cohort": config["cohort"], "districts": [r["district"] for r in rows]}
                result.evidence = rows
            else:
                result.data = {"observations": [{k: r[k] for k in ("資料訊號", "政策觀察", "涉及行政區")}
                                                for r in context["policy_matrix"]]}
                result.evidence = result.data["observations"]
            result.reliability = self.reliability([r["district"] for r in context["districts"]], context)
            result.data["recommendation_allowed"] = False
            if args.get("minimum_reliability"):
                result.status = "insufficient_data"
                result.data = {"unfiltered_observation": result.data, "filter_applied": False,
                               "message": "本網站沒有 high/medium/low 可靠度分級，無法確認符合最低可靠度的行政區。",
                               "recommendation_allowed": False}
            return result.to_dict()
        if name == "get_reliability":
            result.reliability = self.reliability(resolved, context)
            result.data = {"districts": resolved, "reliability": result.reliability,
                           "recommendation_allowed": False, "level_available": False}
            # Sample evidence is available; categorical comparison is not.
            result.status = "insufficient_data"
            result.data["message"] = "本網站保留刊登與租金樣本證據，未提供統一可靠度分級，不能比較哪區更可靠。"
            return result.to_dict()
        metrics = args.get("metrics", [args["metric"]] if "metric" in args else list(METRICS))
        unavailable = [m for m in metrics if m not in METRICS]
        if unavailable:
            result.status = "unsupported"
            result.data = {"unavailable_metrics": unavailable, "message": "本網站尚無所要求的正式指標。"}
            return result.to_dict()
        if name == "rank_districts":
            rows = ordered_rows(context["districts"], args["metric"], args.get("order", "descending"), args.get("limit", 5))
            resolved = [r["district"] for r in rows]
            result.data = {"metric": args["metric"], "order": args.get("order", "descending"), "ranking": rows,
                           "semantics": "raw_value_competition_rank; nulls excluded; ties display by district; limit caps rows",
                           "excluded_districts": [r["district"] for r in context["districts"] if r[METRICS[args["metric"]]] is None]}
        legacy = (self.engine.compare(resolved, context) if len(resolved) > 1
                  else self.engine.lookup(resolved[0], context) if resolved else {"evidence": [], "limitations": []})
        result.evidence = legacy["evidence"]
        result.limitations.extend(legacy["limitations"])
        result.reliability = self.reliability(resolved, context)
        result.data["metrics"] = [{"district": r["district"],
                                   "values": {m: r[METRICS[m]] for m in metrics}} for r in result.evidence]
        result.data["recommendation_allowed"] = False
        if not result.evidence or any(v is None for r in result.data["metrics"] for v in r["values"].values()):
            result.status = "insufficient_data"
        if name == "compare_districts" and len(resolved) == 2:
            a, b = result.data["metrics"]
            supporting, counter, caveats = [], [], ["僅比較指定原始值的大小，不是因果或綜合優劣；未提供統一可靠度分級。"]
            for metric in metrics:
                av, bv = a["values"][metric], b["values"][metric]
                factor = {"metric": metric, "first_district": a["district"], "second_district": b["district"],
                          "first_value": av, "second_value": bv}
                if av is None or bv is None:
                    caveats.append(f"{metric} 有缺值，無法判斷方向。")
                elif av > bv:
                    supporting.append(factor)
                else:
                    counter.append(factor)
            result.data["factors"] = {"claim": "first district has a higher raw value",
                                      "supporting_factors": supporting, "counter_factors": counter, "caveats": caveats}
        return result.to_dict()

    def reliability(self, districts, context):
        evidence = []
        for district in districts:
            existing = self.engine.lookup(district, context)["reliability"]
            for item in existing:
                # Preserve original fields and warnings byte-for-byte; missing != low.
                row = deepcopy(item)
                row.setdefault("level", None)
                row["language_mode"] = "cautious"
                row["recommendation_allowed"] = False
                evidence.append(row)
        return evidence

    @staticmethod
    def period(context):
        period = deepcopy(context["data_period"])
        # No single unified snapshot exists. Do not infer a month from build time.
        for key in ("snapshot_month", "population_reference_month", "jobs_reference_date", "jobs_snapshot_as_of", "processed_at"):
            period.setdefault(key, None)
        return period
