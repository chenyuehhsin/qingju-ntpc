// Selection and presentation only. Python exports all rankings and observation groups.
export function parseQuestion(question, catalog) {
  let text = question.replace(/[\s。？?！!]/g, "").toLowerCase();
  if (new RegExp(catalog.contract.scope_pattern).test(text)) return { intent: "out_of_scope", districts: [] };
  const aliases = new Map(Object.keys(catalog.districts).flatMap(d => [[d, d], [d.slice(0, -1), d]]));
  const districts = [];
  text = text.replace(new RegExp([...aliases.keys()].sort((a, b) => b.length - a.length).join("|"), "g"), alias => {
    const d = aliases.get(alias);
    if (!districts.includes(d)) districts.push(d);
    return "D";
  });
  for (const route of catalog.contract.routes) {
    if (new RegExp(route.pattern).test(text)) return { ...route, districts };
  }
  return { intent: "unsupported", districts: [] };
}

export function queryCatalog(question, catalog) {
  const request = parseQuestion(question, catalog);
  const selected = catalog.selections[request.selection] || {};
  const districts = selected.districts || request.districts;
  const rows = districts.map(d => structuredClone(catalog.districts[d]));
  const result = {
    schema_version: 1, intent: request.intent, answer_source: "deterministic_template",
    answer: "目前資料不足以回答這個問題。", districts, evidence: rows, sources: [],
    data_period: structuredClone(catalog.data_period), reliability: [],
    limitations: [...catalog.contract.limitations], definitions: {}, observation: selected,
  };
  if (request.intent === "out_of_scope") {
    result.answer = "目前系統分析範圍僅涵蓋新北市 29 行政區。";
  } else if (request.intent === "district_lookup" && rows.length) {
    const key = catalog.contract.lookup_metrics.find(([token]) => question.includes(token))?.[1];
    if (key && rows[0][key] != null) result.answer = `依目前資料，${districts[0]}的${catalog.contract.labels[key]}為 ${rows[0][key]}。其他指標見數據依據。`;
    else if (!key) result.answer = `依目前資料，${districts[0]}的各項指標如下，請搭配來源期間與可靠度解讀。`;
  } else if (request.intent === "district_compare" && rows.length >= 2) {
    result.answer = `依目前資料，比較「${districts.join("、")}」如下。請同時參考各區 Opportunity Index、各項數值與可靠度；不能據此認定哪一區一定比較好。`;
    const ordered = catalog.index_order.filter(d => districts.includes(d));
    if (ordered.length) {
      const highest = catalog.districts[ordered[0]].opportunity_index;
      const leaders = ordered.filter(d => catalog.districts[d].opportunity_index === highest);
      result.answer += ` 本次比較中，在有指標資料的行政區裡，既有 Index 最高為「${leaders.join("、")}」。`;
    }
  } else if (request.intent === "metric_explain") {
    result.definitions = structuredClone(catalog.definitions);
    result.answer = "Opportunity Index 綜合工作機會、薪資、職類多樣性與全職比例。有效分數乘以各自權重後加總，再除以有效權重總和；缺值不當成零。Reliability 表示樣本量與欄位完整度的支持程度，不代表就業品質。正式定義、權重及可靠度公式見數據依據；區域差異可由各分項分數與樣本支持度解讀，不能推論因果。";
  } else if (request.intent === "policy_observation") {
    result.answer = (rows.length ? `目前觀察到「${districts.join("、")}」可列為後續觀察對象，仍需搭配其他資料確認。` : "目前沒有符合此觀察條件的行政區；不代表沒有政策需求。") + (selected.rule || "");
  }
  for (const d of districts) {
    const row = catalog.districts[d];
    const level = row.reliability_level;
    const warning = level === "Low" ? "此行政區目前職缺樣本支持度較低，因此結果適合做方向性觀察，不宜做過度推論。"
      : level === "Medium" ? "資料支持度中等，請搭配樣本量與欄位涵蓋率確認。"
        : level !== "High" ? "資料可靠度尚未確認，不宜做確定結論。" : "";
    result.reliability.push({ district: d, level, score: row.reliability, job_postings: row.job_postings, warning });
    if (warning) result.answer += ` ${d}：${warning}`;
  }
  const names = new Set(districts.flatMap(d => catalog.source_ids[d]));
  result.sources = catalog.sources.filter(s => !["unsupported", "out_of_scope"].includes(request.intent) && (!districts.length || names.has(s.filename)));
  if (!result.data_period.snapshot_month) result.limitations.push("正式資料與歷史快照尚無可確認的對應；資料月份與來源 SHA-256 不推測。");
  return result;
}

const escape = value => String(value ?? "尚未確認").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const display = value => typeof value === "number" ? value.toLocaleString("zh-TW", { maximumFractionDigits: 2 }) : escape(value);

export function renderPolicyResult(result, catalog, output) {
  const periods = { snapshot_month: "分析快照", population_reference_month: "人口來源月份", jobs_reference_date: "職缺參考日期", jobs_snapshot_as_of: "職缺下載時間", processed_at: "系統處理時間（非資料月份）" };
  const columns = Object.entries(catalog.contract.labels);
  output.innerHTML = `
    <div class="assistant-answer"><h3>觀察結果</h3><p>${escape(result.answer)}</p></div>
    <h3>數據依據</h3>
    ${result.evidence.length ? `<div class="assistant-evidence-table"><table><thead><tr><th>行政區</th>${columns.map(([, label]) => `<th>${escape(label)}</th>`).join("")}</tr></thead><tbody>${result.evidence.map(row => `<tr><th>${escape(row.district)}</th>${columns.map(([key]) => `<td>${display(row[key])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>` : "<p>此問題無行政區數值依據。</p>"}
    ${Object.keys(result.definitions).length ? `<div class="policy-method"><p>正式權重：${Object.entries(result.definitions.weights || {}).map(([k, v]) => `${escape(k)} ${display(v * 100)}%`).join("、")}</p><p>${escape(result.definitions.normalization)}</p><p>${escape(result.definitions.missing_data)}</p><p>可靠度公式：${escape(result.definitions.reliability?.formula)}</p></div>` : ""}
    ${result.observation.rule ? `<p>${escape(result.observation.rule)}</p><p>本期各區中位數門檻：${Object.entries(result.observation.thresholds).map(([k, v]) => `${escape(catalog.contract.labels[k] || k)} ${display(v)}`).join("；")}</p>` : ""}
    <h3>資料期間</h3><ul>${Object.entries(periods).map(([key, label]) => `<li>${label}：${escape(result.data_period[key])}</li>`).join("")}</ul>
    <h3>資料可靠度／樣本警示</h3>${result.reliability.length ? result.reliability.map(r => `<p>${escape(r.district)}：${escape(r.level)}／${display(r.score)}，職缺 ${display(r.job_postings)} 筆。${escape(r.warning)}</p>`).join("") : "<p>未指定行政區，無區域可靠度判定。</p>"}
    <h3>資料來源</h3><details><summary>查看來源檔案與 SHA-256（${result.sources.length} 份）</summary><ul class="policy-sources">${result.sources.map(s => `<li>${escape(s.source)}：${escape(s.filename)}<br>來源日期：${escape(s.reference_date)}<br>SHA-256：<code>${escape(s.sha256)}</code></li>`).join("")}</ul></details>
    <h3>資料限制</h3><ul>${result.limitations.map(s => `<li>${escape(s)}</li>`).join("")}</ul>
    <details><summary>查看完整結構化依據（含分項樣本及定義）</summary><pre>${escape(JSON.stringify(result, null, 2))}</pre></details>`;
}

export async function setupPolicyAssistant(datasetText) {
  const panel = document.querySelector("#policy-panel");
  const launcher = document.querySelector("#policy-launcher");
  const close = document.querySelector("#policy-close");
  const form = document.querySelector("#policy-form");
  const input = document.querySelector("#policy-query");
  const button = document.querySelector("#policy-submit");
  const output = document.querySelector("#policy-output");
  const status = document.querySelector("#policy-status");
  const setOpen = open => {
    panel.hidden = !open;
    launcher.setAttribute("aria-expanded", String(open));
    launcher.setAttribute("aria-label", open ? "收起青聚 AI 政策助理" : "開啟青聚 AI 政策助理");
    if (open) input.focus({ preventScroll: true });
    else launcher.focus({ preventScroll: true });
  };
  launcher.disabled = false;
  launcher.addEventListener("click", () => setOpen(panel.hidden));
  close.addEventListener("click", () => setOpen(false));
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !panel.hidden) {
      event.preventDefault();
      setOpen(false);
    }
  });
  let catalog;
  try {
    const response = await fetch("./data/policy_catalog.json", { cache: "no-store" });
    if (!response.ok) throw new Error("catalog unavailable");
    catalog = await response.json();
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(datasetText.replace(/\r\n/g, "\n")));
    const hash = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
    if (catalog.schema_version !== 1 || hash !== catalog.dataset_sha256) throw new Error("stale catalog");
  } catch {
    status.textContent = "資料尚未就緒";
    output.textContent = "目前資料不足以回答這個問題。政策助理資料無法驗證，請稍後再試。";
    return;
  }
  button.disabled = false;
  status.textContent = `資料驅動模式 · ${catalog.data_period.snapshot_month || "月份未確認"}`;
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const question = input.value.trim();
    if (!question || question.length > 500) { output.textContent = "請輸入 1–500 字的問題。"; return; }
    button.disabled = true;
    status.textContent = "查詢中";
    let result = queryCatalog(question, catalog);
    try {
      if (new URLSearchParams(location.search).get("policyApi") === "1") {
        const response = await fetch("http://localhost:8000/api/policy-assistant", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: question }), signal: AbortSignal.timeout(5000),
        });
        if (!response.ok) throw new Error("API unavailable");
        const candidate = await response.json();
        // Fail closed on response drift; API cannot replace local authoritative evidence.
        if (JSON.stringify(candidate.evidence) !== JSON.stringify(result.evidence)
            || JSON.stringify(candidate.data_period) !== JSON.stringify(result.data_period)
            || candidate.intent !== result.intent) throw new Error("API evidence mismatch");
        // MVP renderer is deliberately local, even when retrieval is verified through API.
        status.textContent = "API 資料已核對";
      } else status.textContent = "本地資料驅動模式";
    } catch { status.textContent = "API 暫時無法使用，已使用經驗證的本地資料"; }
    renderPolicyResult(result, catalog, output);
    button.disabled = false;
    const body = panel.querySelector(".policy-panel-body");
    body.scrollTop += output.getBoundingClientRect().top - body.getBoundingClientRect().top - 12;
  });
  document.querySelectorAll("#policy-panel [data-policy-query]").forEach(item => {
    item.addEventListener("click", () => {
      if (button.disabled) return;
      input.value = item.dataset.policyQuery;
      form.requestSubmit();
    });
  });
}
