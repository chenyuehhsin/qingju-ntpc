"""Read-only policy queries; the static client consumes this engine's exported catalog.

No raw jobs or ranking calculations are delegated to a language provider.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Protocol

from src.ai_decision_engine import (
    DEFAULT_DATA_PATH, PROJECT_ROOT, compare_districts, district_metric_evidence,
    load_dataset, load_history, median, policy_insight, top_by_metric,
)

CONTRACT_PATH = PROJECT_ROOT / "website/policy-contract.json"
INSUFFICIENT = "目前資料不足以回答這個問題。"
PERIOD_FIELDS = ("snapshot_month", "population_reference_month", "jobs_reference_date",
                 "jobs_snapshot_as_of", "processed_at")


class KnowledgeProvider(Protocol):
    """Future document retrieval only; never district statistics or rankings."""
    def retrieve(self, topic: str) -> list[dict]: ...


class ResponseRenderer(Protocol):
    """Input contains only selected, structured evidence, never the entire dataset."""
    def render(self, grounded_result: dict) -> dict: ...


class DeterministicRenderer:
    def render(self, grounded_result: dict) -> dict:
        return deepcopy(grounded_result)


class BedrockRenderer:
    def render(self, grounded_result: dict) -> dict:
        # Deliberately disabled until an AWS adapter AND output validation exist.
        raise NotImplementedError("Bedrock 尚未設定；使用 deterministic renderer。")


def build_catalog(data_path: Path = DEFAULT_DATA_PATH, history: dict | None = None) -> dict:
    dataset = load_dataset(data_path)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    history = load_history() if history is None else history
    records = dataset.record_by_district
    evidence = {}
    for district, row in records.items():
        # Preserve the established comparison output; add existing dimension evidence.
        evidence[district] = {**district_metric_evidence(row), **compare_districts(dataset, [district])[0]}
        for key in ("salary_sample_size", "diversity_sample_size", "stability_sample_size",
                    "salary_data_coverage", "category_data_coverage", "work_type_data_coverage",
                    "opportunity_reliability", "salary_reliability", "diversity_reliability",
                    "stability_reliability", "index_coverage", "index_available_dimensions"):
            evidence[district][key] = row.get(key)

    # Bind periods to matching records, not merely the latest history label or processed_at.
    matched = None
    shared = ["youth_population_18_35", "job_postings", "job_openings", "jobs_per_1000_youth",
              "median_salary", "youth_employment_opportunity_index", "index_reliability_score",
              "population_source_file", "jobs_source_file"]
    for month in reversed((history or {}).get("periods", [])):
        candidates = {r["district"]: r for r in history.get("records", []) if r.get("snapshot_month") == month}
        if len(candidates) == len(records) == 29 and all(
            d in candidates and all(candidates[d].get(k) == r.get(k) for k in shared)
            for d, r in records.items()
        ):
            matched = month
            break
    manifest = {}
    if matched and re.fullmatch(r"\d{4}-\d{2}", matched):
        path = PROJECT_ROOT / "data/history" / matched / "source_manifest.json"
        if path.exists():
            manifest = json.loads(path.read_text(encoding="utf-8"))
    period = {k: manifest.get(k) for k in PERIOD_FIELDS}
    period["processed_at"] = dataset.provenance.get("processed_at")
    sources = [f for group in manifest.get("sources", {}).values() for f in group.get("files", [])]
    source_ids = {}
    for d, row in records.items():
        names = set(str(row.get("population_source_file") or "").split(";"))
        names.update(str(row.get("jobs_source_file") or "").split(";"))
        source_ids[d] = sorted(names - {""})
    known = {s["filename"] for s in sources}
    for name in sorted({n for names in source_ids.values() for n in names} - known):
        sources.append({"filename": name, "sha256": None, "source": "正式 dataset 的來源檔名；追溯資訊尚未確認"})

    # New conjunctive observation filters, not new scores or rankings.
    # Existing policy_attention is a population-first candidate list, NOT proof of shortage.
    def mid(field):
        return median([r[field] for r in records.values() if isinstance(r.get(field), (int, float))])
    thresholds = {k: mid(k) for k in ("youth_population_18_35", "jobs_per_1000_youth", "job_postings", "job_diversity_score")}
    def above(row, field):
        return isinstance(row.get(field), (int, float)) and thresholds[field] is not None and row[field] > thresholds[field]
    def below(row, field):
        return isinstance(row.get(field), (int, float)) and thresholds[field] is not None and row[field] < thresholds[field]
    ranking = [r["district"] for r in top_by_metric(dataset, "youth_employment_opportunity_index", limit=29)]
    # An unavailable Index must not exclude a district from unrelated observations.
    observation_order = ranking + [d for d in records if d not in ranking]
    selections = {
        "opportunity": {"districts": ranking[:5], "rule": "依既有 Opportunity Index 由高至低取前五區；並列分數不表示優劣。"},
        "attention": {"districts": [r["district"] for r in policy_insight(dataset, "policy_attention")],
                      "rule": "沿用既有 policy_attention：青年人口優先、每千青年工作機會次序的前十區觀察清單；此清單本身不代表職缺不足。"},
        "population_gap": {"districts": [d for d in observation_order if above(records[d], "youth_population_18_35") and below(records[d], "jobs_per_1000_youth")],
                           "rule": "青年人口高於 29 區中位數，且每千名青年工作機會低於中位數；只是相對觀察門檻。"},
        "concentrated": {"districts": [d for d in observation_order if above(records[d], "job_postings") and below(records[d], "job_diversity_score")],
                         "rule": "職缺刊登筆數高於 29 區中位數，且既有職類多樣性分數低於中位數；只是相對觀察門檻。"},
    }
    for selection in selections.values():
        selection["thresholds"] = thresholds
    return {"schema_version": 1, "contract": contract, "districts": evidence,
            "sources": sources, "source_ids": source_ids, "data_period": period,
            "definitions": dataset.provenance.get("opportunity_index", {}),
            "metric_definitions": dataset.provenance.get("metric_definitions", {}),
            "selections": selections, "index_order": ranking,
            # Git may convert CRLF on Windows; hash the UTF-8 text with LF line endings.
            # This export check is separate from the unchanged raw-source provenance hashes.
            "dataset_sha256": hashlib.sha256(Path(data_path).read_text(encoding="utf-8").encode("utf-8")).hexdigest()}


def parse_question(question: str, catalog: dict) -> dict:
    text = re.sub(r"[\s。？?！!]", "", question).lower()
    if re.search(catalog["contract"]["scope_pattern"], text):
        return {"intent": "out_of_scope", "districts": []}
    districts = []
    aliases = {alias: d for d in catalog["districts"] for alias in (d, d[:-1])}
    def replace(match):
        d = aliases[match.group()]
        if d not in districts:
            districts.append(d)
        return "D"
    text = re.sub("|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True)), replace, text)
    for route in catalog["contract"]["routes"]:
        if re.fullmatch(route["pattern"], text):
            return {**route, "districts": districts}
    return {"intent": "unsupported", "districts": []}


def query_catalog(question: str, catalog: dict) -> dict:
    request = parse_question(question, catalog)
    intent = request["intent"]
    selected = catalog["selections"].get(request.get("selection"), {})
    districts = selected.get("districts", request["districts"])
    rows = [deepcopy(catalog["districts"][d]) for d in districts]
    result = {"schema_version": 1, "intent": intent, "answer_source": "deterministic_template",
              "answer": INSUFFICIENT, "districts": districts, "evidence": rows,
              "sources": [], "data_period": deepcopy(catalog["data_period"]),
              "reliability": [], "limitations": list(catalog["contract"]["limitations"]),
              "definitions": {}, "observation": selected}
    if intent == "out_of_scope":
        result["answer"] = "目前系統分析範圍僅涵蓋新北市 29 行政區。"
    elif intent == "district_lookup" and rows:
        key = next((key for token, key in catalog["contract"]["lookup_metrics"] if token in question), None)
        if key and rows[0].get(key) is not None:
            result["answer"] = f"依目前資料，{districts[0]}的{catalog['contract']['labels'][key]}為 {rows[0][key]}。其他指標見數據依據。"
        elif not key:
            result["answer"] = f"依目前資料，{districts[0]}的各項指標如下，請搭配來源期間與可靠度解讀。"
    elif intent == "district_compare" and len(rows) >= 2:
        result["answer"] = "依目前資料，比較「" + "、".join(districts) + "」如下。請同時參考各區 Opportunity Index、各項數值與可靠度；不能據此認定哪一區一定比較好。"
        ordered = [d for d in catalog["index_order"] if d in districts]
        if ordered:
            highest = catalog["districts"][ordered[0]]["opportunity_index"]
            leaders = [d for d in ordered if catalog["districts"][d]["opportunity_index"] == highest]
            result["answer"] += " 本次比較中，在有指標資料的行政區裡，既有 Index 最高為「" + "、".join(leaders) + "」。"
    elif intent == "metric_explain":
        result["definitions"] = deepcopy(catalog["definitions"])
        result["answer"] = "Opportunity Index 綜合工作機會、薪資、職類多樣性與全職比例。有效分數乘以各自權重後加總，再除以有效權重總和；缺值不當成零。Reliability 表示樣本量與欄位完整度的支持程度，不代表就業品質。正式定義、權重及可靠度公式見數據依據；區域差異可由各分項分數與樣本支持度解讀，不能推論因果。"
    elif intent == "policy_observation":
        result["answer"] = ("目前觀察到「" + "、".join(districts) + "」可列為後續觀察對象，仍需搭配其他資料確認。" if rows else "目前沒有符合此觀察條件的行政區；不代表沒有政策需求。") + selected.get("rule", "")
    for d in districts:
        row = catalog["districts"][d]
        level = row.get("reliability_level")
        warning = ""
        if level == "Low":
            warning = "此行政區目前職缺樣本支持度較低，因此結果適合做方向性觀察，不宜做過度推論。"
        elif level == "Medium":
            warning = "資料支持度中等，請搭配樣本量與欄位涵蓋率確認。"
        elif level != "High":
            warning = "資料可靠度尚未確認，不宜做確定結論。"
        result["reliability"].append({"district": d, "level": level, "score": row.get("reliability"), "job_postings": row.get("job_postings"), "warning": warning})
        if warning:
            result["answer"] += f" {d}：{warning}"
    names = {n for d in districts for n in catalog["source_ids"][d]}
    result["sources"] = [deepcopy(s) for s in catalog["sources"]
                         if intent not in {"unsupported", "out_of_scope"} and (not districts or s["filename"] in names)]
    if not result["data_period"].get("snapshot_month"):
        result["limitations"].append("正式資料與歷史快照尚無可確認的對應；資料月份與來源 SHA-256 不推測。")
    return result


def answer_policy_question(question: str, *, renderer: ResponseRenderer | None = None) -> dict:
    grounded = query_catalog(question, build_catalog())
    try:
        return (renderer or DeterministicRenderer()).render(grounded)
    except (NotImplementedError, TimeoutError):
        return DeterministicRenderer().render(grounded)
