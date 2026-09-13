"""Build reviewed methodology documents and schemas; never write datasets."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))
from policy_agent.registry import PolicyToolRegistry, AgentCoreToolAdapter


def write(path, text):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def main():
    docs = [
        ("methodology/opportunity_index.md", ["opportunity_index", "Opportunity Index", "就業機會指數"],
         ["app/assistant_service.py", "app/components/policy_lens.py"],
         "Opportunity Index availability", "本青聚網站沒有獨立 Opportunity Index、正式權重或綜合行政區排名。每千青年求才人數是另一個已存在指標，不能混稱 Opportunity Index。不得移植其他專案方法或由 LLM 補算。"),
        ("methodology/reliability_methodology.md", ["reliability", "可靠度", "可信度"], ["app/assistant_service.py"],
         "Reliability evidence", "本網站 assistant 保留職缺刊登筆數、租金契約樣本數與 warning；未提供統一 high/medium/low 分級。職涯 mapping confidence 是不同層級的證據，不能當行政區可靠度。缺少分級不等於 low。最低 medium 條件無法驗證時應回 insufficient_data，不自行評級。"),
        ("methodology/temporal_methodology.md", ["資料期間", "資料月份", "temporal"], ["app/assistant_service.py", "scripts/employment/build_new_taipei_employment_summary.py", "outputs/population/ntpc_district_youth_18_35_metadata.json"],
         "Temporal boundary", "人口參考月、職缺快照日、租金參考月各自保留；未確認的 snapshot_month、jobs_reference_date 與 processed_at 為 null。generated_at 是處理時間，不是 reference month。不同來源不能假定同期；所有實際時間值由 structured tool 取得。"),
        ("definitions/youth_definition.md", ["youth_population", "青年", "人口"], ["outputs/population/ntpc_district_youth_18_35_metadata.json", "docs/youth_age_harmonization.md"],
         "Youth definition", "Policy Lens 青年人口採 Exact 18–35 歲（含兩端），由戶政單一年齡男女資料彙整至行政區。這是本產品的分析定義，不能宣稱所有政府資料都採同一年齡；全台 15–29 proxy 與職涯頁歷史人口應分開解讀。不得把行政區人口當作車站生活圈人口。"),
        ("definitions/jobs_per_1000_youth.md", ["jobs_per_1000_youth", "每千", "求才", "hiring_count"], ["app/components/policy_lens.py"],
         "Jobs per thousand youth", "既有公式為 hiring_count / youth_18_35_count × 1000；分子是求才人數，不是刊登筆數。只有進入既有租金、人口與職缺 inner join 的行政區具有此衍生值；其他區保留 null，不另補算。它不是就業率、錄取機率或就業保證。"),
        ("definitions/salary.md", ["salary", "薪資"], ["scripts/employment/build_new_taipei_employment_summary.py"],
         "Salary", "既有 median_salary 使用月薪及部分工時(月薪)且薪資上下限皆大於零的職缺，先取上下限中點，再依行政區取中位數。此值為刊登薪資統計，不是青年實領薪資；缺值不得補造。"),
        ("definitions/job_diversity.md", ["job_diversity", "多樣性"], ["scripts/employment/build_new_taipei_employment_summary.py"],
         "Job diversity availability", "資料有 top_job_category，但沒有正式 job_diversity 指標或多樣性公式；不可把最常見類別轉成多樣性分數。查詢此指標應回 unsupported。"),
        ("definitions/employment_stability.md", ["employment_stability", "穩定度"], ["scripts/employment/build_new_taipei_employment_summary.py"],
         "Employment stability availability", "本網站未定義 employment_stability。單次職缺快照不能推論跨月穩定度；查詢此指標回 unsupported，不能用 LLM 或假歷史填補。"),
        ("data_catalog/population_source.md", ["人口資料來源", "population_source"], ["outputs/population/ntpc_district_youth_18_35_metadata.json"],
         "Population source", "人口來源是內政部戶政司 ODRP014 村里、單一年齡資料。既有 metadata 記錄來源 URL、期別、彙整方法與原始回應 hash。工具保留 provenance，不重抓或改寫原始資料；精確期別與數值請查 structured tool。"),
        ("data_catalog/jobs_source.md", ["job_count", "職缺資料", "jobs_source"], ["data/data_catalog.csv", "scripts/employment/build_new_taipei_employment_summary.py"],
         "Jobs source", "來源是 TaiwanJobs 新北職缺快照；job_postings 計刊登列數，hiring_count 合計求才人數，兩者不能混用。原始檔不納入 Git，部署讀取既有 processed summary；source_snapshot_date 是資料快照日期，不是 build 日期。"),
        ("data_catalog/district_coverage.md", ["行政區", "district_coverage"], ["app/assistant_service.py"],
         "District coverage", "Structured 查詢限定新北市 29 行政區，支援區名與省略區字的名稱；外縣市不在範圍。租金與衍生比率涵蓋範圍較小，人口及職缺仍保留全部行政區；不以零代替缺值。"),
        ("limitations/employment_data_limitations.md", ["職缺資料", "限制", "rent", "租金"], ["app/assistant_service.py"],
         "Data limitations", "刊登職缺快照不是完整就業市場或青年專屬需求。租金為行政區獨立套房 benchmark，不是即時房源。樣本數與地理尺度需一併揭露；低樣本或原有 warning 必須原樣保留。"),
        ("limitations/policy_interpretation.md", ["政策觀察", "政策", "因果"], ["app/components/policy_lens.py", "app/policy_agent/policy_rules.json"],
         "Policy interpretation", "既有政策矩陣使用可审查的中位數條件。M3 僅新增高青年人口且低每千青年求才數的條件組合，沿用既有 eligible cohort 與 high >= median、low < median；門檻由 deterministic code 取得。這是觀察，非因果、政策優先排序或正式處方。"),
    ]
    manifest = {"version": "m3-1", "numeric_source_of_truth": False, "documents": []}
    for path, keywords, sources, title, body in docs:
        content = f"# {title}\n\n{body}\n\n依據：" + "、".join(f"`{s}`" for s in sources) + "。\n"
        write("knowledge_base/" + path, content)
        manifest["documents"].append({"id": Path(path).stem, "path": path, "keywords": keywords,
                                      "source_files": sources,
                                      "sha256": hashlib.sha256((ROOT / "knowledge_base" / path).read_bytes()).hexdigest()})
    write("knowledge_base/manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    registry = PolicyToolRegistry()
    write("docs/policy_tool_schemas.json", json.dumps(registry.list_tools(), ensure_ascii=False, indent=2))
    adapter = AgentCoreToolAdapter(registry)
    write("docs/bedrock_tool_config.json", json.dumps(adapter.bedrock_tool_config(), ensure_ascii=False, indent=2))
    write("docs/agentcore_handler_mapping.json", json.dumps(adapter.handler_mapping(), indent=2))


if __name__ == "__main__":
    main()
