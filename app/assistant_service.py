"""Read-only assistant for the actual Qingju Streamlit application.

Uses this repository's processed data and Policy Lens functions. No legacy
employment-map dataset, composite index, external LLM or separate server.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import pandas as pd

from data_loader import (
    PROJECT_ROOT, NTPC_DISTRICT_YOUTH_18_35_CSV, HOUSING_BENCHMARK_CSV,
    CAREER_V35_CANDIDATES_CSV, load_policy_lens_data,
)
from components.policy_lens import load_youth_job_opportunity_data, build_policy_intervention_matrix

EMPLOYMENT = PROJECT_ROOT / "data/processed/employment/new_taipei_employment_summary.csv"
INSUFFICIENT = "目前資料不足以回答這個問題。"
LABELS = {
    "district": "行政區", "youth_18_35_count": "青年人口（18–35 歲）",
    "job_postings": "職缺刊登筆數", "hiring_count": "求才人數",
    "median_salary": "月薪中位數（元）", "rent_median": "獨立套房租金中位數（元）",
    "youth_job_opportunity_per_1000": "每千名青年求才人數",
}
LIMITATIONS = [
    "青年人口為新北市 29 行政區 Exact 18–35 歲統計，不能當作車站生活圈人口。",
    "職缺是台灣就業通當期快照，不是完整就業市場；刊登筆數與求才人數不同。",
    "租金為 MOI 行政區獨立套房 benchmark，不是即時房源；部分行政區沒有租金資料。",
    "政策訊號只是後續觀察，不代表因果、正式優先排序或政府政策處方。",
]


def records(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.to_json(orient="records", force_ascii=False))


def source(path: Path, period: str | None = None) -> dict:
    relative = path.relative_to(PROJECT_ROOT).as_posix()
    catalog = pd.read_csv(PROJECT_ROOT / "data/data_catalog.csv", keep_default_na=False)
    matches = catalog[catalog["filename"].eq(relative)]
    entry = matches.iloc[0].to_dict() if not matches.empty else {}
    return {
        "file": relative, "source": entry.get("source_org") or "青聚網站既有衍生資料",
        "url": entry.get("source_url") or None,
        "data_period": period or entry.get("data_period") or None,
        "download_date": entry.get("download_date") or None,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "hash_scope": "目前衍生檔案；不是原始來源 hash",
    }


def load_context() -> dict:
    youth = pd.read_csv(NTPC_DISTRICT_YOUTH_18_35_CSV)
    work = pd.read_csv(EMPLOYMENT)
    rent = pd.read_csv(HOUSING_BENCHMARK_CSV)
    # Keep all 29 districts; missing rent never removes a population/job row.
    joined = youth[["district", "youth_18_35_count"]].merge(
        work[["district", "job_postings", "hiring_count", "median_salary"]],
        on="district", how="left", validate="one_to_one",
    ).merge(rent.loc[rent["city"].eq("新北市"), ["district", "rent_median", "contract_count"]],
            on="district", how="left", validate="one_to_one")
    opportunity = load_youth_job_opportunity_data()
    joined = joined.merge(opportunity[["district", "youth_job_opportunity_per_1000"]],
                          on="district", how="left", validate="one_to_one")
    policy = load_policy_lens_data()
    matrix = build_policy_intervention_matrix(policy, opportunity)
    population_meta = json.loads((PROJECT_ROOT / "outputs/population/ntpc_district_youth_18_35_metadata.json").read_text(encoding="utf-8"))
    catalog_sources = [source(NTPC_DISTRICT_YOUTH_18_35_CSV, str(youth.iloc[0]["source_period"])),
                       source(EMPLOYMENT, str(work.iloc[0]["source_snapshot_date"])),
                       source(HOUSING_BENCHMARK_CSV)]
    catalog_sources[0].update({"source": population_meta["source"]["organization"],
                               "url": population_meta["source"]["source_url"],
                               "raw_response_files": population_meta["source"]["raw_response_files"]})
    # Obtain the housing source period from the catalog, never a generated timestamp.
    catalog = pd.read_csv(PROJECT_ROOT / "data/data_catalog.csv", keep_default_na=False)
    rent_period = catalog.loc[catalog["dataset_id"].eq("moi_rent_total_quartiles_2026-03"), "data_period"]
    catalog_sources[2]["data_period"] = rent_period.iloc[0] if not rent_period.empty else None
    return {"districts": records(joined), "policy_matrix": records(matrix),
            "sources": catalog_sources, "career": records(pd.read_csv(CAREER_V35_CANDIDATES_CSV)),
            "data_period": {"population_reference_month": catalog_sources[0]["data_period"],
                            "jobs_snapshot_as_of": catalog_sources[1]["data_period"],
                            "rent_reference_month": catalog_sources[2]["data_period"]}}


def answer_question(question: str, context: dict, page: str = "") -> dict:
    result = {"intent": "unsupported", "answer": INSUFFICIENT, "evidence": [], "sources": [],
              "data_period": {}, "reliability": [], "limitations": list(LIMITATIONS),
              "page": page, "answer_source": "deterministic"}
    text = re.sub(r"[\s？?。！!]", "", question).lower()
    if not text or len(question) > 500:
        return result
    if re.search("台北市|臺北市|桃園|台中|臺中|高雄|台南|臺南|全台|全臺", text):
        result.update(intent="out_of_scope", answer="行政區資料查詢目前僅涵蓋新北市 29 區；網站的台北工作地預設僅用於通勤情境。")
        return result
    by_district = {r["district"]: r for r in context["districts"]}
    aliases = {a: d for d in by_district for a in (d, d[:-1])}
    districts = []
    def replace(match):
        district = aliases[match.group()]
        if district not in districts:
            districts.append(district)
        return "D"
    normalized = re.sub("|".join(sorted(aliases, key=len, reverse=True)), replace, text)
    if text in {"職涯探索可以看什麼", "青聚可以做什麼", "怎麼使用青聚", "青年安居推薦怎麼用"}:
        result.update(intent="site_guide", answer="青聚新北提供三個入口：青年職涯探索查看護理轉職的技能、職缺與課程證據；青年安居推薦依工作地比較租金、公共運輸及生活機能；青年局 Policy Lens 檢視居住與就業政策訊號。任意地址查詢需網路與 TDX 設定，固定預設可直接使用。",
                      sources=[source(PROJECT_ROOT / "README.md")])
    elif text in {"opportunityindex是什麼", "opportunityindex", "reliability是什麼", "可靠度是什麼"}:
        result.update(intent="metric_explain", answer="目前青聚網站沒有先前地圖專案的 Opportunity Index 或統一 Reliability 分數，不能套用。青聚使用每千名青年求才人數、租金 benchmark、通勤情境及職涯證據，並保留樣本數、mapping confidence 與資料限制。")
    elif text in {"每千名青年求才人數是什麼", "policy lens是什麼".replace(" ", ""), "policylens是什麼", "生活機能是什麼", "通勤時間怎麼算"}:
        result.update(intent="metric_explain", answer="每千名青年求才人數 = hiring_count / youth_18_35_count × 1000，沿用 Policy Lens 的既有實作；沒有租金 benchmark 的區域未進入該分析表，因此不補算其衍生比率。Policy Lens 用透明規則觀察，沒有綜合政策排名。通勤為代表節點至工作地的公共運輸情境，生活機能是周邊 800m OSM POI proxy。",
                      sources=[source(PROJECT_ROOT / "app/components/policy_lens.py"), source(PROJECT_ROOT / "app/app.py")])
    elif re.fullmatch(r"(請)?(查詢)?D(目前|現在)?(的)?(有多少)?(青年人口|職缺|求才人數|薪資|薪資指標|租金|每千名青年求才人數)(有多少|如何|是多少)?", normalized):
        key = next((k for token, k in [("每千", "youth_job_opportunity_per_1000"), ("青年人口", "youth_18_35_count"), ("租金", "rent_median"), ("薪資", "median_salary"), ("求才", "hiring_count"), ("職缺", "job_postings")] if token in text), None)
        row = by_district[districts[0]]
        result.update(intent="district_lookup", evidence=[row])
        if row.get(key) is not None:
            result["answer"] = f"依目前青聚資料，{districts[0]}的{LABELS[key]}為 {row[key]:,.2f}。"
    elif len(districts) >= 2 and re.fullmatch(r"(請)?(比較)?D([、,與和跟]|vs)D(([、,與和跟]|vs)D)*(的)?(青年人口|職缺|租金|就業機會)?(哪區較好|哪一區比較好|比較)?", normalized):
        result.update(intent="district_compare", answer="依目前青聚資料，各區的人口、職缺及租金比較如下。資料期間與地理尺度不同，不能据此宣稱哪一區一定較好。",
                      evidence=[by_district[d] for d in districts])
    elif text in {"哪些行政區值得進一步觀察", "哪些区值得政策觀察", "哪些區值得政策觀察", "有哪些政策訊號"}:
        # Reuse exactly the website's existing transparent rules, omit tool prescriptions.
        result.update(intent="policy_observation", answer="以下沿用青年局 Policy Lens 的資料訊號與政策觀察，可列為後續觀察對象，仍需其他資料確認；不是政策優先排序。",
                      evidence=[{k: r[k] for k in ("資料訊號", "政策觀察", "涉及行政區")} for r in context["policy_matrix"]],
                      sources=[source(PROJECT_ROOT / "data/processed/policy/policy_lens_v0.csv"), *context["sources"]],
                      data_period=dict(context["data_period"]))
    elif text in {"護理轉職科技有哪些方向", "護理轉職有哪些方向"}:
        rows = sorted(context["career"], key=lambda r: r["target_domain_evidence_rank"])[:5]
        fields = ("target_domain_evidence_rank", "target_occupation_name", "skill_similarity", "feasibility_level", "mapping_confidence", "manual_review_needed", "matched_job_count", "salary_basis")
        result.update(intent="career_evidence", answer="以下為青年職涯探索現有科技領域證據順序的前五個方向，不是錄取機率或轉職成功率。職業對應需人工確認，請進入職涯頁查看各項技能與職缺證據。",
                      evidence=[{k: r.get(k) for k in fields} for r in rows],
                      sources=[source(CAREER_V35_CANDIDATES_CSV)])
    if result["intent"] in {"district_lookup", "district_compare"}:
        result["sources"] = context["sources"]
        result["data_period"] = dict(context["data_period"])
        result["reliability"] = [{"district": r["district"], "job_postings": r["job_postings"],
                                  "rental_contract_count": r["contract_count"],
                                  "warning": "職缺樣本僅為當期刊登，請搭配樣本量解讀；本網站未提供統一可靠度分級，不自行新增。"}
                                 for r in result["evidence"]]
    return result
