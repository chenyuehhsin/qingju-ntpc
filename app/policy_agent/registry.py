"""Single schema source of truth, validation, allowlist dispatch and AWS export."""
from copy import deepcopy
from pathlib import Path
from .contracts import PolicyToolResult, STATUSES
from .engine import METRICS, UNAVAILABLE, QingjuEngine
from .tools import PolicyTools
from .knowledge import LocalKnowledgeSearch


def obj(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False}


def array(items, minimum=1, maximum=29):
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": maximum, "uniqueItems": True}


DISTRICT = {"type": "string", "minLength": 1, "maxLength": 32}
METRIC = {"type": "string", "enum": [*METRICS, *UNAVAILABLE]}
METRIC_LIST = array(METRIC, maximum=9)
CONDITION = obj({"metric": METRIC, "operator": {"type": "string", "enum": ["high", "low"]}}, ["metric", "operator"])
OUTPUT = obj({"tool_name": {"type": "string"}, "status": {"type": "string", "enum": STATUSES},
              "data": {"type": "object"}, "evidence": {"type": "array"}, "sources": {"type": "array"},
              "data_period": {"type": "object"}, "reliability": {"type": "array"}, "limitations": {"type": "array"}},
             ["tool_name", "status", "data", "evidence", "sources", "data_period", "reliability", "limitations"])

SCHEMAS = [
    ("get_district_stats", "取得一個新北市行政區正式人口、刊登職缺、求才、薪資、租金及每千青年求才人數；不存在的指標回 unsupported，不以 KB 補值。",
     obj({"district": DISTRICT, "metrics": METRIC_LIST}, ["district"])),
    ("compare_districts", "比較兩個以上新北行政區原始指標；保留證據、缺值、期間、樣本警語；兩區時提供原始值方向 factors，非因果。",
     obj({"districts": array(DISTRICT, 2), "metrics": METRIC_LIST}, ["districts"])),
    ("rank_districts", "依一項既有指標原始值排序，不產生綜合評分；null 排除、相同值同名次、名稱決定展示順序、limit 限制列數。",
     obj({"metric": METRIC, "order": {"type": "string", "enum": ["ascending", "descending"]},
          "limit": {"type": "integer", "minimum": 1, "maximum": 29}}, ["metric"])),
    ("get_reliability", "取回指定區原有樣本證據與 warning；此網站尚無 high/medium/low 分級，回 insufficient_data 並保留樣本，不能自行評級。",
     obj({"districts": array(DISTRICT)}, ["districts"])),
    ("get_data_period", "取得來源資料期間；未確認欄位為 null，processed_at 不等於資料月份。", obj({})),
    ("explain_metric", "讀取專案正式方法說明；Opportunity Index、多樣性、穩定度不存在時回 unsupported。",
     obj({"metric": {"type": "string", "enum": [*METRICS, *UNAVAILABLE, "reliability"]}}, ["metric"])),
    ("find_policy_observations", "無 conditions 時沿用既有政策矩陣；只接受已審核的高青年人口且低每千青年求才數組合。最低可靠度要求未能驗證時拒絕強判斷。",
     obj({"conditions": array(CONDITION, 0, 5), "minimum_reliability": {"type": "string", "enum": ["low", "medium", "high"]}})),
    ("search_policy_knowledge", "檢索方法、定義、來源、限制文件。不可用於行政區數字、比較、排名或預測。",
     obj({"query": {"type": "string", "minLength": 1, "maxLength": 500}}, ["query"])),
    ("forecast_employment_demand", "未来需求預測契約；目前歷史資料與模型不足，一律 not_ready 且 prediction=null。",
     obj({"district": DISTRICT, "category": {"type": "string", "minLength": 1, "maxLength": 100},
          "horizon": {"type": "integer", "minimum": 1, "maximum": 12}}, ["district", "category", "horizon"])),
]


def validate(value, schema):
    """Validate the JSON Schema subset used above; reject unknown keys/types.

    Schema exports are also tested with an independent Draft 2020-12 validator.
    """
    kind = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "integer": int}
    if kind and (not isinstance(value, types[kind]) or kind == "integer" and isinstance(value, bool)):
        raise ValueError("Invalid argument type")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("Unsupported enum value")
    if kind == "object":
        if any(k not in value for k in schema.get("required", [])):
            raise ValueError("Missing required argument")
        if schema.get("additionalProperties") is False and set(value) - set(schema["properties"]):
            raise ValueError("Unknown argument")
        for key, item in value.items():
            if key in schema.get("properties", {}):
                validate(item, schema["properties"][key])
    if kind in ("array", "string"):
        low, high = ("minItems", "maxItems") if kind == "array" else ("minLength", "maxLength")
        if len(value) < schema.get(low, 0) or len(value) > schema.get(high, float("inf")):
            raise ValueError("Argument length out of bounds")
    if kind == "array":
        if schema.get("uniqueItems") and any(value[i] in value[:i] for i in range(len(value))):
            raise ValueError("Duplicate arguments")
        for item in value:
            if "items" in schema:
                validate(item, schema["items"])
    if kind == "integer" and not schema.get("minimum", -float("inf")) <= value <= schema.get("maximum", float("inf")):
        raise ValueError("Argument outside range")


class PolicyToolRegistry:
    def __init__(self, engine=None, knowledge=None):
        self.engine = engine or QingjuEngine()
        self.tools = PolicyTools(self.engine, knowledge or LocalKnowledgeSearch(Path(__file__).resolve().parents[2] / "knowledge_base"),
                                 Path(__file__).with_name("policy_rules.json"))
        self.definitions = {name: {"name": name, "description": desc, "inputSchema": schema,
                                   "outputSchema": OUTPUT} for name, desc, schema in SCHEMAS}
        self.handlers = {name: (lambda args, n=name: self.tools.call(n, args)) for name in self.definitions}

    def list_tools(self):
        return deepcopy(list(self.definitions.values()))

    def execute(self, name, arguments):
        if name not in self.handlers:
            return PolicyToolResult(str(name), "unsupported", data={"message": "Unknown tool"}).to_dict()
        try:
            validate(arguments, self.definitions[name]["inputSchema"])
        except ValueError as exc:
            return PolicyToolResult(name, "unsupported", data={"message": str(exc)}).to_dict()
        try:
            result = self.handlers[name](deepcopy(arguments))
            validate(result, OUTPUT)
            return result
        except (OSError, ValueError, KeyError, RuntimeError):
            return PolicyToolResult(name, "insufficient_data", data={"message": "正式資料或方法文件暫時無法讀取。"}).to_dict()


class AgentCoreToolAdapter:
    """Export-only boundary. Does not register a Gateway or call AWS."""
    def __init__(self, registry):
        self.registry = registry

    def mcp_tools(self):
        return self.registry.list_tools()

    def bedrock_tool_config(self):
        return {"tools": [{"toolSpec": {"name": t["name"], "description": t["description"],
                                        "inputSchema": {"json": t["inputSchema"]}}}
                          for t in self.registry.list_tools()]}

    def handler_mapping(self):
        return {name: f"PolicyToolRegistry.execute:{name}" for name in self.registry.handlers}

    def invoke(self, name, arguments):
        return self.registry.execute(name, arguments)
