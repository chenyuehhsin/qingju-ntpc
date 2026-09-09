const STANDARD_DISTRICTS = [
  "板橋區", "三重區", "中和區", "永和區", "新莊區", "新店區", "樹林區", "鶯歌區", "三峽區", "淡水區",
  "汐止區", "瑞芳區", "土城區", "蘆洲區", "五股區", "泰山區", "林口區", "深坑區", "石碇區", "坪林區",
  "三芝區", "石門區", "八里區", "平溪區", "雙溪區", "貢寮區", "金山區", "萬里區", "烏來區",
];

const BASE_METRICS = [
  { key: "youth_employment_opportunity_index", label: "青年就業機會指數", digits: 1, legendDigits: 0, domain: [0, 100] },
  { key: "index_reliability_score", label: "資料可靠度", digits: 1, legendDigits: 0, domain: [0, 100] },
  { key: "youth_population_18_35", label: "青年人口", digits: 0 },
  { key: "job_openings", label: "工作機會", digits: 0 },
  { key: "jobs_per_1000_youth", label: "每千名青年工作機會", digits: 1 },
  { key: "avg_salary", label: "平均薪資", digits: 0, needsData: true },
];

let records = [];
let recordByDistrict = new Map();
let jobsByDistrict = {};
let allJobs = [];
let filteredJobs = [];
let filteredMetrics = new Map();
let selectedDistrict = "板橋區";
let map;
let geoLayer;
let reliabilityBadgeLayer;
let layerByDistrict = new Map();
let geojsonCache;
let payloadCache;
let policyDatasetText;
let historyCache = null;
let buildInfo = null;
let activeSnapshotMonth = null;
let recommendedDistricts = new Set();

const ASSISTANT_ENDPOINT = "http://localhost:8000/api/assistant";
const USE_ASSISTANT_API = new URLSearchParams(window.location.search).get("assistantApi") === "1";
const PERSONAL_MATCH_WEIGHTS = {
  availability: 0.5,
  salary: 0.2,
  opportunity_index: 0.15,
  reliability: 0.15,
};

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const hasValue = (value) => value !== null && value !== undefined && !Number.isNaN(Number(value));

const formatNumber = (value, digits = 0) => {
  if (!hasValue(value)) return "暫無資料";
  return Number(value).toLocaleString("zh-TW", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
};

const formatMoney = (value) => (hasValue(value) ? `NT$ ${formatNumber(value)}` : "暫無資料");
const formatScore = (value) => (hasValue(value) ? `${formatNumber(value, 1)} / 100` : "資料不足");
const formatPercent = (value) => (hasValue(value) ? `${formatNumber(value, 1)}%` : "暫無資料");
const reliabilityLabel = (value) => ({ High: "高", Medium: "中", Low: "低" })[value] || "暫無資料";
const sumKnown = (items, key) => items.reduce((sum, row) => (hasValue(row[key]) ? sum + Number(row[key]) : sum), 0);
const sumKnownOrNull = (items, key) => {
  const values = items.map((row) => row[key]).filter(hasValue);
  return values.length ? values.reduce((sum, value) => sum + Number(value), 0) : null;
};

function setAppStatus(message, state = "ready") {
  const element = document.querySelector("#app-status");
  if (!element) return;
  element.textContent = message;
  element.className = `app-status is-${state}`;
}

function recordsForSnapshot(month) {
  const currentByDistrict = new Map((payloadCache?.records || []).map((row) => [row.district, row]));
  const historyRows = (historyCache?.records || []).filter((row) => row.snapshot_month === month && STANDARD_DISTRICTS.includes(row.district));
  if (!historyRows.length) return (payloadCache?.records || []).filter((row) => STANDARD_DISTRICTS.includes(row.district));
  return STANDARD_DISTRICTS.map((district) => ({
    ...(currentByDistrict.get(district) || {}),
    ...(historyRows.find((row) => row.district === district) || {}),
  }));
}

function previousSnapshotMonth(month) {
  const periods = historyCache?.periods || [];
  const index = periods.indexOf(month);
  return index > 0 ? periods[index - 1] : null;
}

function historyRecord(district, month = activeSnapshotMonth) {
  return (historyCache?.records || []).find((row) => row.snapshot_month === month && row.district === district) || null;
}

function formatSignedChange(value, digits = 1, suffix = "%") {
  if (!hasValue(value)) return "尚無前期資料";
  const numeric = Number(value);
  const arrow = numeric > 0 ? "▲" : numeric < 0 ? "▼" : "●";
  return `${arrow} ${formatNumber(Math.abs(numeric), digits)}${suffix}`;
}

function formatTrendValue(value, formatter = formatNumber) {
  return hasValue(value) ? formatter(value) : "暫無資料";
}

function percentChange(current, previous) {
  if (!hasValue(current) || !hasValue(previous) || Number(previous) === 0) return null;
  return ((Number(current) - Number(previous)) / Number(previous)) * 100;
}

function renderDistrictTrendBlock(district) {
  const row = historyRecord(district);
  const periods = historyCache?.periods || [];
  if (!historyCache || !row) {
    return `
      <div class="district-trend-box">
        <h3>與前期相比</h3>
        <p>尚未建立歷史快照。</p>
      </div>
    `;
  }
  const trendRows = [
    ["工作機會", row.job_openings, row.job_openings_mom_pct, "%"],
    ["平均薪資", row.avg_salary, row.salary_mom_pct, "%"],
    ["每千青年工作機會", row.jobs_per_1000_youth, row.jobs_per_1000_youth_mom_pct, "%"],
    ["Opportunity Index", row.youth_employment_opportunity_index, row.index_mom_change, ""],
  ];
  const chartRows = periods
    .map((month) => historyRecord(district, month))
    .filter(Boolean);
  const hasTrend = periods.length >= 2;
  return `
    <div class="district-trend-box">
      <h3>與前期相比</h3>
      <div class="district-trend-grid">
        ${trendRows
          .map(
            ([label, value, change, suffix]) => `
              <div>
                <span>${escapeHtml(label)}</span>
                <strong>${label.includes("薪資") ? formatMoney(value) : formatNumber(value, label.includes("Index") || label.includes("每千") ? 1 : 0)}</strong>
                <small>${hasTrend ? formatSignedChange(change, 1, suffix) : "尚無前期資料"}</small>
              </div>
            `,
          )
          .join("")}
      </div>
      ${
        hasTrend
          ? `<div class="district-mini-chart">${chartRows
              .map((item) => `<span><strong>${escapeHtml(item.snapshot_month)}</strong> 工作機會 ${formatNumber(item.job_openings)}｜每千青年 ${formatNumber(item.jobs_per_1000_youth, 1)}｜Index ${formatNumber(item.youth_employment_opportunity_index, 1)}</span>`)
              .join("")}</div>`
          : `<p>目前只有 ${formatNumber(periods.length)} 個 snapshot，尚無前期資料可比較。</p>`
      }
    </div>
  `;
}

function scoreBar(label, value) {
  const width = hasValue(value) ? Math.max(0, Math.min(100, Number(value))) : 0;
  return `
    <div class="score-row ${hasValue(value) ? "" : "is-missing"}">
      <span>${escapeHtml(label)}</span>
      <div class="score-track" aria-hidden="true"><span style="width:${width}%"></span></div>
      <strong>${hasValue(value) ? formatNumber(value, 1) : "資料不足"}</strong>
    </div>
  `;
}

const colorScale = (value, min, max) => {
  if (!hasValue(value)) return "#d8dee7";
  if (max === min) return "#2563eb";
  const t = Math.max(0, Math.min(1, (Number(value) - min) / (max - min)));
  const hue = 198 - t * 165;
  return `hsl(${hue}, 68%, ${43 + t * 5}%)`;
};

async function loadSiteData() {
  const cacheBust = `?v=${Date.now()}`;
  const [dataResponse, geoResponse] = await Promise.all([
    fetch(`./data/youth_employment_map.json${cacheBust}`, { cache: "no-store" }),
    fetch(`./data/new_taipei_districts.geojson${cacheBust}`, { cache: "no-store" }),
  ]);
  if (!dataResponse.ok || !geoResponse.ok) throw new Error("資料檔載入失敗");

  policyDatasetText = await dataResponse.text();
  payloadCache = JSON.parse(policyDatasetText);
  geojsonCache = await geoResponse.json();
  const historyResponse = await fetch(`./data/youth_employment_history.json${cacheBust}`, { cache: "no-store" }).catch(() => null);
  historyCache = historyResponse?.ok ? await historyResponse.json() : null;
  const buildInfoResponse = await fetch(`./data/build_info.json${cacheBust}`, { cache: "no-store" }).catch(() => null);
  buildInfo = buildInfoResponse?.ok ? await buildInfoResponse.json() : null;
  activeSnapshotMonth = historyCache?.latest_snapshot || null;
  records = activeSnapshotMonth ? recordsForSnapshot(activeSnapshotMonth) : payloadCache.records.filter((row) => STANDARD_DISTRICTS.includes(row.district));
  recordByDistrict = new Map(records.map((row) => [row.district, row]));
  jobsByDistrict = Object.fromEntries(
    STANDARD_DISTRICTS.map((district) => [district, payloadCache.jobs_by_district?.[district] || []]),
  );
  allJobs = Object.entries(jobsByDistrict).flatMap(([district, jobs]) =>
    jobs.map((job) => ({ ...job, district: job.district || district })),
  );
  filteredJobs = allJobs;
}

function availableMetrics() {
  return BASE_METRICS.filter((metric) => !metric.needsData || records.some((row) => hasValue(row[metric.key])));
}

function currentMetric() {
  return availableMetrics().find((metric) => metric.key === document.querySelector("#metric-select").value) || BASE_METRICS[0];
}

function filtersAreActive() {
  return Boolean(
    document.querySelector("#keyword-filter")?.value.trim() ||
      document.querySelector("#company-filter")?.value.trim() ||
      document.querySelector("#job-district-filter")?.value !== "all" ||
      document.querySelector("#category-filter")?.value !== "all" ||
      document.querySelector("#salary-min-filter")?.value ||
      document.querySelector("#salary-max-filter")?.value,
  );
}

function mapRows() {
  const metricKey = currentMetric().key;
  const filterSensitiveMetrics = new Set(["job_postings", "job_openings", "jobs_per_1000_youth", "avg_salary"]);
  if (!filtersAreActive() || !filterSensitiveMetrics.has(metricKey)) return records;
  return records.map((row) => ({ ...row, ...(filteredMetrics.get(row.district) || {}) }));
}

function renderMetricSelect() {
  document.querySelector("#metric-select").innerHTML = availableMetrics()
    .map((metric) => `<option value="${metric.key}">${metric.label}</option>`)
    .join("");
}

function renderKpis() {
  const totalYouth = sumKnown(records, "youth_population_18_35");
  const totalPostings = sumKnown(records, "job_postings");
  const totalOpenings = sumKnown(records, "job_openings");
  const rate = totalYouth > 0 ? (totalOpenings / totalYouth) * 1000 : null;
  document.querySelector("#kpi-youth").textContent = `${formatNumber(totalYouth)} 人`;
  document.querySelector("#kpi-postings").textContent = formatNumber(totalPostings);
  document.querySelector("#kpi-openings").textContent = `${formatNumber(totalOpenings)} 人`;
  document.querySelector("#kpi-rate").textContent = formatNumber(rate, 1);
  const latest = activeSnapshotMonth || records.find((row) => row.processed_at)?.processed_at;
  document.querySelector("#snapshot-date").textContent = latest ? String(latest).replace("T", " ") : "尚待確認";
  renderDataSanity();
}

function renderDataSanity() {
  const temporal = currentTemporalEvidence();
  const districtCount = records.filter((row) => STANDARD_DISTRICTS.includes(row.district)).length;
  const validation = buildInfo?.validation_status === "passed" ? "已驗證" : "已載入";
  document.querySelector("#data-sanity").textContent =
    `資料狀態：${validation}｜行政區 ${districtCount}/29｜快照 ${temporal.latest_snapshot || "尚待確認"}｜人口 ${temporal.population_reference_month || "尚待確認"}`;
}

function aggregateFilteredMetrics() {
  filteredMetrics = new Map();
  for (const district of STANDARD_DISTRICTS) {
    const jobs = filteredJobs.filter((job) => job.district === district);
    const openings = sumKnownOrNull(jobs, "openings");
    const monthlySalary = jobs
      .filter((job) => job.salary_text?.startsWith("月薪"))
      .map((job) => {
        if (hasValue(job.salary_min) && hasValue(job.salary_max)) return (Number(job.salary_min) + Number(job.salary_max)) / 2;
        if (hasValue(job.salary_min)) return Number(job.salary_min);
        if (hasValue(job.salary_max)) return Number(job.salary_max);
        return null;
      })
      .filter(hasValue);
    const youth = recordByDistrict.get(district)?.youth_population_18_35;
    filteredMetrics.set(district, {
      job_postings: jobs.length,
      job_openings: openings,
      jobs_per_1000_youth: hasValue(openings) && hasValue(youth) && Number(youth) > 0 ? (Number(openings) / Number(youth)) * 1000 : null,
      avg_salary: monthlySalary.length
        ? monthlySalary.reduce((sum, value) => sum + Number(value), 0) / monthlySalary.length
        : null,
    });
  }
}

function passesFilters(job) {
  const keyword = document.querySelector("#keyword-filter").value.trim().toLowerCase();
  const company = document.querySelector("#company-filter").value.trim().toLowerCase();
  const district = document.querySelector("#job-district-filter").value;
  const category = document.querySelector("#category-filter").value;
  const salaryMin = Number(document.querySelector("#salary-min-filter").value);
  const salaryMax = Number(document.querySelector("#salary-max-filter").value);
  const haystack = [job.title, job.company, job.category, job.address, job.source].filter(Boolean).join(" ").toLowerCase();

  if (keyword && !haystack.includes(keyword)) return false;
  if (company && !String(job.company || "").toLowerCase().includes(company)) return false;
  if (district !== "all" && job.district !== district) return false;
  if (category !== "all" && job.category !== category) return false;
  if (Number.isFinite(salaryMin) && salaryMin > 0 && !(hasValue(job.salary_max) ? Number(job.salary_max) >= salaryMin : hasValue(job.salary_min) && Number(job.salary_min) >= salaryMin)) return false;
  if (Number.isFinite(salaryMax) && salaryMax > 0 && !(hasValue(job.salary_min) ? Number(job.salary_min) <= salaryMax : hasValue(job.salary_max) && Number(job.salary_max) <= salaryMax)) return false;
  return true;
}

function applyFilters() {
  filteredJobs = allJobs.filter(passesFilters);
  aggregateFilteredMetrics();
  renderFilteredCount();
  renderFilteredJobs();
  renderMap(geojsonCache);
  renderHoverJobs(selectedDistrict);
  renderDistrictDetail(selectedDistrict);
}

function renderFilterControls() {
  document.querySelector("#job-district-filter").innerHTML = ["all", ...STANDARD_DISTRICTS]
    .map((district) => `<option value="${district}">${district === "all" ? "全新北" : district}</option>`)
    .join("");

  const categories = [...new Set(allJobs.map((job) => job.category).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "zh-Hant"),
  );
  document.querySelector("#category-filter").innerHTML = [
    `<option value="all">全部</option>`,
    ...categories.map((category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`),
  ].join("");

  ["#keyword-filter", "#job-district-filter", "#category-filter", "#company-filter", "#salary-min-filter", "#salary-max-filter"].forEach(
    (selector) => {
      const element = document.querySelector(selector);
      element.addEventListener("input", applyFilters);
      element.addEventListener("change", applyFilters);
    },
  );
}

function renderFilteredCount() {
  const openings = sumKnown(filteredJobs, "openings");
  document.querySelector("#filtered-count").textContent = `篩選結果 ${formatNumber(filteredJobs.length)} 筆｜需求 ${formatNumber(openings)} 人`;
}

function featureStyle(metricKey) {
  const metric = currentMetric();
  const rows = mapRows();
  const values = rows.map((row) => row[metricKey]).filter(hasValue);
  const min = metric.domain ? metric.domain[0] : values.length ? Math.min(...values) : 0;
  const max = metric.domain ? metric.domain[1] : values.length ? Math.max(...values) : 0;
  return (feature) => {
    const district = feature.properties.TOWNNAME;
    const row = rows.find((item) => item.district === district);
    const recommended = recommendedDistricts.has(district);
    return {
      color: district === selectedDistrict ? "#111827" : recommended ? "#b45309" : "#ffffff",
      weight: district === selectedDistrict || recommended ? 3 : 1,
      dashArray: recommended && district !== selectedDistrict ? "5 4" : null,
      fillColor: row ? colorScale(row[metricKey], min, max) : "#d8dee7",
      fillOpacity: 0.86,
    };
  };
}

function districtJobs(district) {
  const jobs = filtersAreActive() ? filteredJobs : allJobs;
  return jobs.filter((job) => job.district === district);
}

function jobLine(job) {
  const company = job.company ? `｜${escapeHtml(job.company)}` : "";
  const openings = hasValue(job.openings) ? `｜${formatNumber(job.openings)} 人` : "";
  const salary = job.salary_text ? `｜${escapeHtml(job.salary_text)}` : "";
  return `${escapeHtml(job.title || "未提供職務名稱")}${company}${openings}${salary}`;
}

function tooltipHtml(district) {
  const base = recordByDistrict.get(district);
  const display = filtersAreActive() ? { ...base, ...(filteredMetrics.get(district) || {}) } : base;
  const jobs = districtJobs(district).slice(0, 4);
  const items = jobs.length
    ? jobs.map((job) => `<div class="job-tooltip-item"><strong>${escapeHtml(job.title || "未提供職務名稱")}</strong><span>${jobLine(job)}</span></div>`).join("")
    : `<div class="job-tooltip-item"><strong>暫無職缺明細</strong><span>目前篩選條件下沒有資料</span></div>`;
  return `
    <h3>${escapeHtml(district)}</h3>
    <div class="tooltip-summary">
      <span>青年就業機會指數 ${formatScore(base?.youth_employment_opportunity_index)}</span>
      <span>資料可靠度 ${formatScore(base?.index_reliability_score)}｜${reliabilityLabel(base?.index_reliability_level)}</span>
      <span>青年人口 ${formatNumber(base?.youth_population_18_35)} 人</span>
      <span>工作機會 ${formatNumber(display?.job_openings)} 人</span>
      <span>每千青年 ${formatNumber(display?.jobs_per_1000_youth, 1)}</span>
      ${hasValue(display?.avg_salary) ? `<span>平均薪資 ${formatMoney(display.avg_salary)}</span>` : ""}
    </div>
    <div class="job-tooltip-list">${items}</div>
  `;
}

function popupHtml(district) {
  const row = recordByDistrict.get(district);
  if (!row) return `<strong>${escapeHtml(district)}</strong><br>暫無資料`;
  return `
    <strong>${escapeHtml(district)}</strong><br>
    青年人口：${formatNumber(row.youth_population_18_35)} 人<br>
    青年就業機會指數：${formatScore(row.youth_employment_opportunity_index)}<br>
    資料可靠度：${formatScore(row.index_reliability_score)}（${reliabilityLabel(row.index_reliability_level)}）<br>
    職缺刊登：${formatNumber(row.job_postings)}<br>
    工作機會：${formatNumber(row.job_openings)} 人<br>
    每千名青年工作機會：${formatNumber(row.jobs_per_1000_youth, 1)}<br>
    平均薪資：${formatMoney(row.avg_salary)}
  `;
}

function renderLegend(metricKey) {
  const metric = availableMetrics().find((item) => item.key === metricKey) || BASE_METRICS[0];
  const values = mapRows().map((row) => row[metricKey]).filter(hasValue);
  const min = metric.domain ? metric.domain[0] : values.length ? Math.min(...values) : null;
  const max = metric.domain ? metric.domain[1] : values.length ? Math.max(...values) : null;
  document.querySelector("#map-legend").innerHTML = `
    <div><strong>${escapeHtml(metric.label)}</strong><span>${metric.domain ? "0–100 分" : filtersAreActive() && metricKey !== "youth_population_18_35" ? "依職缺篩選結果著色" : "全新北資料"}</span></div>
    <div class="legend-scale" aria-hidden="true"></div>
    <div class="legend-values"><span>${formatNumber(min, metric.legendDigits ?? metric.digits)}</span><span>${formatNumber(max, metric.legendDigits ?? metric.digits)}</span></div>
  `;
}

function geojsonCoordinates(geometry, output = []) {
  if (!geometry) return output;
  const walk = (item) => {
    if (!Array.isArray(item)) return;
    if (item.length >= 2 && typeof item[0] === "number" && typeof item[1] === "number") {
      output.push(item);
      return;
    }
    item.forEach(walk);
  };
  walk(geometry.coordinates);
  return output;
}

function geometryRings(geometry) {
  if (!geometry) return [];
  if (geometry.type === "Polygon") return geometry.coordinates;
  if (geometry.type === "MultiPolygon") return geometry.coordinates.flat();
  return [];
}

function svgProjection(features, width, height) {
  const coordinates = features.flatMap((feature) => geojsonCoordinates(feature.geometry, []));
  const xs = coordinates.map((coordinate) => coordinate[0]);
  const ys = coordinates.map((coordinate) => coordinate[1]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const padding = 26;
  const scale = Math.min((width - padding * 2) / (maxX - minX), (height - padding * 2) / (maxY - minY));
  const usedWidth = (maxX - minX) * scale;
  const usedHeight = (maxY - minY) * scale;
  const offsetX = (width - usedWidth) / 2;
  const offsetY = (height - usedHeight) / 2;
  return ([lon, lat]) => [offsetX + (lon - minX) * scale, offsetY + (maxY - lat) * scale];
}

function svgPathForFeature(feature, project) {
  return geometryRings(feature.geometry)
    .map((ring) =>
      ring
        .map((coordinate, index) => {
          const [x, y] = project(coordinate);
          return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" ") + " Z",
    )
    .join(" ");
}

function svgCentroid(feature, project) {
  const coordinates = geojsonCoordinates(feature.geometry, []);
  if (!coordinates.length) return [0, 0];
  const projected = coordinates.map(project);
  return [
    projected.reduce((sum, coordinate) => sum + coordinate[0], 0) / projected.length,
    projected.reduce((sum, coordinate) => sum + coordinate[1], 0) / projected.length,
  ];
}

function renderSvgMap(filteredGeojson, metricKey) {
  const mapElement = document.querySelector("#map");
  const width = 860;
  const height = 560;
  const rows = mapRows();
  const metric = currentMetric();
  const values = rows.map((row) => row[metricKey]).filter(hasValue);
  const min = metric.domain ? metric.domain[0] : values.length ? Math.min(...values) : 0;
  const max = metric.domain ? metric.domain[1] : values.length ? Math.max(...values) : 0;
  const project = svgProjection(filteredGeojson.features, width, height);
  layerByDistrict = new Map();
  geoLayer = null;
  reliabilityBadgeLayer = null;
  const paths = filteredGeojson.features
    .map((feature) => {
      const district = feature.properties.TOWNNAME;
      const row = rows.find((item) => item.district === district);
      const recommended = recommendedDistricts.has(district);
      const selected = district === selectedDistrict;
      const fill = row ? colorScale(row[metricKey], min, max) : "#d8dee7";
      const [cx, cy] = svgCentroid(feature, project);
      const warning = metricKey === "youth_employment_opportunity_index" && recordByDistrict.get(district)?.index_reliability_level === "Low";
      return `
        <path class="svg-district ${selected ? "is-selected" : ""}" data-district="${escapeHtml(district)}" d="${svgPathForFeature(feature, project)}" fill="${fill}" stroke="${recommended ? "#b45309" : "#ffffff"}" stroke-width="${selected || recommended ? 2.4 : 0.7}">
          <title>${escapeHtml(district)}｜${escapeHtml(metric.label)} ${formatNumber(row?.[metricKey], metric.digits)}</title>
        </path>
        <text class="svg-map-label" x="${cx.toFixed(1)}" y="${cy.toFixed(1)}">${warning ? "!" : escapeHtml(district.replace("區", ""))}</text>
      `;
    })
    .join("");
  mapElement.innerHTML = `<svg class="svg-map" viewBox="0 0 ${width} ${height}" role="img" aria-label="新北市29行政區互動地圖">${paths}</svg>`;
  mapElement.querySelectorAll(".svg-district").forEach((path) => {
    const district = path.dataset.district;
    layerByDistrict.set(district, path);
    path.addEventListener("mouseenter", () => renderHoverJobs(district));
    path.addEventListener("focus", () => renderHoverJobs(district));
    path.addEventListener("click", () => selectDistrict(district, true));
    path.setAttribute("tabindex", "0");
    path.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") selectDistrict(district, true);
    });
  });
  renderLegend(metricKey);
}

function renderMap(geojson) {
  const metricKey = currentMetric().key;
  const filteredGeojson = {
    ...geojson,
    features: geojson.features.filter((feature) => STANDARD_DISTRICTS.includes(feature.properties.TOWNNAME)),
  };
  if (!window.L) {
    renderSvgMap(filteredGeojson, metricKey);
    return;
  }
  if (!map) {
    map = L.map("map", {
      scrollWheelZoom: false,
      attributionControl: false,
      zoomControl: true,
      maxBoundsViscosity: 1,
    }).setView([25.02, 121.58], 10);
  }
  if (geoLayer) geoLayer.remove();
  if (reliabilityBadgeLayer) reliabilityBadgeLayer.remove();
  layerByDistrict = new Map();
  geoLayer = L.geoJSON(filteredGeojson, {
    style: featureStyle(metricKey),
    onEachFeature: (feature, layer) => {
      const district = feature.properties.TOWNNAME;
      layerByDistrict.set(district, layer);
      layer.bindTooltip(tooltipHtml(district), { sticky: true, direction: "auto", className: "job-tooltip", opacity: 0.98 });
      layer.bindPopup(popupHtml(district));
      layer.on("mouseover", () => {
        layer.setStyle({ weight: 3, color: "#0f766e", fillOpacity: 0.95 });
        renderHoverJobs(district);
      });
      layer.on("mouseout", () => geoLayer.resetStyle(layer));
      layer.on("click", () => selectDistrict(district, true));
    },
  }).addTo(map);
  const bounds = geoLayer.getBounds();
  map.fitBounds(bounds, { padding: [14, 14], animate: false });
  map.setMaxBounds(bounds.pad(0.04));
  map.options.minZoom = map.getZoom();
  renderLegend(metricKey);
  renderReliabilityBadges(metricKey);
}

function renderReliabilityBadges(metricKey) {
  if (!window.L) return;
  reliabilityBadgeLayer = L.layerGroup();
  if (metricKey !== "youth_employment_opportunity_index") return;

  for (const [district, layer] of layerByDistrict.entries()) {
    const row = recordByDistrict.get(district);
    if (row?.index_reliability_level !== "Low") continue;
    const marker = L.marker(layer.getBounds().getCenter(), {
      icon: L.divIcon({
        className: "reliability-badge",
        html: "!",
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      }),
      interactive: false,
    });
    marker.addTo(reliabilityBadgeLayer);
  }
  reliabilityBadgeLayer.addTo(map);
}

function jobCards(jobs, limit = 12) {
  const visibleJobs = jobs.slice(0, limit);
  if (!visibleJobs.length) {
    return `<div class="job-card"><strong>暫無資料</strong><div class="job-meta">目前條件下沒有可顯示的職缺</div></div>`;
  }
  return visibleJobs
    .map(
      (job) => `
        <article class="job-card">
          <strong>${escapeHtml(job.title || "未提供職缺名稱")}</strong>
          <div class="job-meta">
            <span>${escapeHtml(job.company || "暫無資料")}</span>
            <span>${escapeHtml(job.district || "暫無資料")}</span>
            <span>${escapeHtml(job.category || "暫無資料")}</span>
            <span>${escapeHtml(job.work_type || "工作型態暫無資料")}</span>
            <span>需求 ${formatNumber(job.openings)} 人</span>
            <span>${escapeHtml(job.salary_text || "薪資暫無資料")}</span>
          </div>
          <div class="job-address">${escapeHtml(job.address || "工作地址暫無資料")}</div>
          ${job.url ? `<a href="${escapeHtml(job.url)}" target="_blank" rel="noreferrer">查看職缺</a>` : ""}
        </article>
      `,
    )
    .join("");
}

function renderHoverJobs(district) {
  const row = recordByDistrict.get(district);
  const jobs = districtJobs(district);
  document.querySelector("#hover-jobs").innerHTML = `
    <h3>${escapeHtml(district)}職缺快覽</h3>
    <div class="hover-summary">
      <span>職缺刊登 ${formatNumber(filtersAreActive() ? jobs.length : row?.job_postings)}</span>
      <span>工作機會 ${formatNumber(filtersAreActive() ? sumKnownOrNull(jobs, "openings") : row?.job_openings)} 人</span>
      <span>平均薪資 ${formatMoney(filtersAreActive() ? filteredMetrics.get(district)?.avg_salary : row?.avg_salary)}</span>
    </div>
    <div class="job-list">${jobCards(jobs, 3)}</div>
  `;
}

function renderDistrictSelect() {
  const options = records.map((row) => `<option value="${row.district}">${row.district}</option>`).join("");
  document.querySelector("#district-select").innerHTML = options;
  document.querySelector("#district-select").addEventListener("change", (event) => selectDistrict(event.target.value, true));
  document.querySelector("#compare-a").innerHTML = options;
  document.querySelector("#compare-b").innerHTML = options;
  document.querySelector("#compare-a").value = "板橋區";
  document.querySelector("#compare-b").value = "新莊區";
  document.querySelector("#compare-a").addEventListener("change", renderComparison);
  document.querySelector("#compare-b").addEventListener("change", renderComparison);
}

function selectDistrict(district, pan = false) {
  selectedDistrict = district;
  document.querySelector("#district-select").value = district;
  renderDistrictDetail(district);
  renderHoverJobs(district);
  if (geoLayer) geoLayer.setStyle(featureStyle(currentMetric().key));
  const layer = layerByDistrict.get(district);
  if (layer instanceof SVGElement) {
    document.querySelectorAll(".svg-district").forEach((path) => path.classList.toggle("is-selected", path.dataset.district === district));
  } else if (layer && pan && map) {
    map.fitBounds(layer.getBounds(), { padding: [28, 28], maxZoom: Math.max(map.getZoom(), 11) });
    layer.openTooltip();
  }
}

function renderDistrictDetail(district) {
  const row = recordByDistrict.get(district);
  const jobs = districtJobs(district);
  const availableDimensions = row?.index_available_dimensions
    ? String(row.index_available_dimensions)
        .split(";")
        .filter(Boolean)
        .join("、")
    : "暫無資料";
  document.querySelector("#district-detail").innerHTML = `
    <h2 class="district-name">${escapeHtml(district)}</h2>
    <div class="index-card">
      <span>青年就業機會指數</span>
      <strong>${formatScore(row?.youth_employment_opportunity_index)}</strong>
      <small>資料完整度 ${formatPercent(row?.index_coverage)}｜有效面向：${escapeHtml(availableDimensions)}</small>
    </div>
    <div class="reliability-card" title="可靠度反映目前資料量與欄位完整度，不代表該區就業品質。">
      <div>
        <span>資料可靠度</span>
        <strong>${formatScore(row?.index_reliability_score)}</strong>
        <small>${reliabilityLabel(row?.index_reliability_level)}</small>
      </div>
      <div>
        <span>排名穩定度</span>
        <strong>${formatScore(row?.index_rank_stability)}</strong>
        <small>權重敏感度 ${formatNumber(row?.rank_range)} 名</small>
      </div>
    </div>
    <div class="score-bars">
      ${scoreBar("工作機會", row?.opportunity_score)}
      ${scoreBar("薪資", row?.salary_score)}
      ${scoreBar("職類多樣性", row?.job_diversity_score)}
      ${scoreBar("工作穩定性", row?.employment_stability_score)}
    </div>
    <div class="score-bars compact">
      ${scoreBar("機會可靠度", row?.opportunity_reliability)}
      ${scoreBar("薪資可靠度", row?.salary_reliability)}
      ${scoreBar("多樣性可靠度", row?.diversity_reliability)}
      ${scoreBar("穩定性可靠度", row?.stability_reliability)}
    </div>
    <details class="score-method">
      <summary>查看評分依據</summary>
      <p>工作機會分數：依據每千名青年工作機會計算。</p>
      <p>薪資分數：依據該區職缺薪資中位數計算，只使用可解析月薪。</p>
      <p>職類多樣性：依據職缺 category 分布計算 normalized Shannon entropy。</p>
      <p>工作穩定性：依據可辨識 work_type 中全職比例計算。</p>
      <p>缺失 dimension 不當成 0，會以該區可用 dimension 重新分配權重。</p>
      <p>資料可靠度：反映目前資料量與欄位完整度，不代表該區就業品質。</p>
    </details>
    ${renderDistrictTrendBlock(district)}
    <div class="detail-grid">
      <div class="detail-item"><span>青年人口</span><strong>${formatNumber(row?.youth_population_18_35)} 人</strong></div>
      <div class="detail-item"><span>職缺刊登</span><strong>${formatNumber(row?.job_postings)}</strong></div>
      <div class="detail-item"><span>工作機會</span><strong>${formatNumber(row?.job_openings)} 人</strong></div>
      <div class="detail-item"><span>每千名青年工作機會</span><strong>${formatNumber(row?.jobs_per_1000_youth, 1)}</strong></div>
      <div class="detail-item"><span>平均薪資</span><strong>${formatMoney(row?.avg_salary)}</strong></div>
      <div class="detail-item"><span>薪資中位數</span><strong>${formatMoney(row?.median_salary)}</strong></div>
      <div class="detail-item"><span>公司數</span><strong>${formatNumber(row?.company_count)}</strong></div>
      <div class="detail-item"><span>熱門職類</span><strong>${escapeHtml(row?.top_job_category || "暫無資料")}</strong></div>
      <div class="detail-item"><span>熱門職缺</span><strong>${escapeHtml(row?.top_occupation || "暫無資料")}</strong></div>
      <div class="detail-item"><span>熱門產業</span><strong>${escapeHtml(row?.top_industry || "暫無資料")}</strong></div>
    </div>
  `;
  document.querySelector("#district-jobs").innerHTML = jobCards(jobs, 12);
}

function renderFilteredJobs() {
  document.querySelector("#filtered-jobs").innerHTML = jobCards(filteredJobs, 30);
}

function renderRanking(target, key, digits = 0) {
  const rows = records
    .filter((row) => hasValue(row[key]))
    .sort((a, b) => Number(b[key]) - Number(a[key]))
    .slice(0, 10);
  const max = Math.max(...rows.map((row) => Number(row[key])));
  const container = document.querySelector(target);
  container.innerHTML = rows
    .map(
      (row) => `
      <button class="rank-row" type="button" data-district="${escapeHtml(row.district)}">
        <strong>${escapeHtml(row.district)}</strong>
        <span class="bar-track"><span class="bar" style="width:${(Number(row[key]) / max) * 100}%"></span></span>
        <span>${formatNumber(row[key], digits)}${key === "youth_employment_opportunity_index" ? `<small>可靠度：${reliabilityLabel(row.index_reliability_level)}</small>` : ""}</span>
      </button>
    `,
    )
    .join("");
  container.querySelectorAll(".rank-row").forEach((button) => {
    button.addEventListener("click", () => selectDistrict(button.dataset.district, true));
  });
}

function renderAllRankings() {
  renderRanking("#index-ranking", "youth_employment_opportunity_index", 1);
  renderRanking("#openings-ranking", "job_openings");
  renderRanking("#rate-ranking", "jobs_per_1000_youth", 1);
  renderRanking("#youth-ranking", "youth_population_18_35");
  renderRobustList();
}

function renderTrendControls() {
  const select = document.querySelector("#snapshot-month-select");
  const periods = historyCache?.periods || [];
  if (!periods.length) {
    select.innerHTML = `<option value="current">目前資料</option>`;
    select.disabled = true;
    renderTrendSummary();
    return;
  }
  select.innerHTML = periods.map((month) => `<option value="${escapeHtml(month)}">${escapeHtml(month)}</option>`).join("");
  select.value = activeSnapshotMonth || periods[periods.length - 1];
  select.addEventListener("change", () => {
    activeSnapshotMonth = select.value;
    records = recordsForSnapshot(activeSnapshotMonth);
    recordByDistrict = new Map(records.map((row) => [row.district, row]));
    aggregateFilteredMetrics();
    renderKpis();
    renderAllRankings();
    renderComparison();
    renderTrendSummary();
    renderMap(geojsonCache);
    selectDistrict(selectedDistrict, false);
  });
  renderTrendSummary();
}

function renderTrendSummary() {
  const container = document.querySelector("#trend-summary");
  const periods = historyCache?.periods || [];
  const readiness = historyCache?.forecast_readiness;
  const previous = activeSnapshotMonth ? previousSnapshotMonth(activeSnapshotMonth) : null;
  const overallRows = historyCache?.overall_trend || [];
  const currentOverall = overallRows.find((row) => row.snapshot_month === activeSnapshotMonth);
  const previousOverall = previous ? overallRows.find((row) => row.snapshot_month === previous) : null;
  const openingsPct = currentOverall && previousOverall ? percentChange(currentOverall.total_job_openings, previousOverall.total_job_openings) : null;
  const postingsPct = currentOverall && previousOverall ? percentChange(currentOverall.total_job_postings, previousOverall.total_job_postings) : null;
  const ratePct = currentOverall && previousOverall ? percentChange(currentOverall.jobs_per_1000_youth, previousOverall.jobs_per_1000_youth) : null;
  const demandTop = historyCache?.category_trends?.current_demand_top || [];
  const increaseTop = historyCache?.category_trends?.demand_increase_top || [];
  const decreaseTop = historyCache?.category_trends?.demand_decrease_top || [];
  container.innerHTML = `
    <div class="trend-cards">
      <div><span>目前歷史資料</span><strong>${formatNumber(periods.length)} 個月份</strong></div>
      <div><span>預測準備度</span><strong>${escapeHtml(readiness?.label || "尚不足")}</strong><small>${escapeHtml(readiness?.note || "尚未建立歷史快照")}</small></div>
      <div><span>目前月份</span><strong>${escapeHtml(activeSnapshotMonth || "目前資料")}</strong><small>${previous ? `前期 ${escapeHtml(previous)}` : "尚無前期資料"}</small></div>
      <div><span>整體工作機會 MoM</span><strong>${formatSignedChange(openingsPct)}</strong><small>整體每千青年：${formatSignedChange(ratePct)}</small></div>
    </div>
    <div class="trend-sections">
      <div>
        <h3>新北市整體青年就業趨勢</h3>
        <div class="mini-trend-list">
          <span>青年人口 ${formatTrendValue(currentOverall?.total_youth_population, (value) => `${formatNumber(value)} 人`)}</span>
          <span>職缺刊登 ${formatTrendValue(currentOverall?.total_job_postings)}</span>
          <span>工作機會 ${formatTrendValue(currentOverall?.total_job_openings, (value) => `${formatNumber(value)} 人`)}</span>
          <span>每千青年 ${formatTrendValue(currentOverall?.jobs_per_1000_youth, (value) => formatNumber(value, 1))}</span>
          <span>職缺刊登 MoM ${formatSignedChange(postingsPct)}</span>
        </div>
      </div>
      <div>
        <h3>熱門／成長職類</h3>
        <div class="category-trend-columns">
          ${categoryTrendList("目前需求最多", demandTop, "job_openings")}
          ${categoryTrendList("需求增加最多", increaseTop, "absolute_openings_change")}
          ${categoryTrendList("需求減少最多", decreaseTop, "absolute_openings_change")}
        </div>
      </div>
    </div>
  `;
}

function categoryTrendList(title, rows, key) {
  if (!rows.length) {
    return `<div><strong>${escapeHtml(title)}</strong><p>尚無前期資料</p></div>`;
  }
  return `
    <div>
      <strong>${escapeHtml(title)}</strong>
      ${rows
        .slice(0, 5)
        .map((row) => `<span>${escapeHtml(row.category || "暫無資料")}：${formatNumber(row[key], key.includes("change") ? 0 : 0)}</span>`)
        .join("")}
    </div>
  `;
}

function renderRobustList() {
  const cutoff = records
    .map((row) => row.youth_employment_opportunity_index)
    .filter(hasValue)
    .sort((a, b) => Number(a) - Number(b))[Math.floor((records.filter((row) => hasValue(row.youth_employment_opportunity_index)).length - 1) * 0.75)];
  const robust = records
    .filter((row) => hasValue(row.youth_employment_opportunity_index) && Number(row.youth_employment_opportunity_index) >= Number(cutoff) && row.index_reliability_level === "High")
    .sort((a, b) => Number(b.youth_employment_opportunity_index) - Number(a.youth_employment_opportunity_index));
  const needsMoreData = records
    .filter((row) => hasValue(row.youth_employment_opportunity_index) && Number(row.youth_employment_opportunity_index) >= Number(cutoff) && row.index_reliability_level === "Low")
    .sort((a, b) => Number(b.youth_employment_opportunity_index) - Number(a.youth_employment_opportunity_index));
  const card = (row, badge) => `
    <button class="robust-card" type="button" data-district="${escapeHtml(row.district)}">
      <strong>${escapeHtml(row.district)}</strong>
      <span>${escapeHtml(badge)}</span>
      <small>Index ${formatNumber(row.youth_employment_opportunity_index, 1)}｜可靠度 ${formatNumber(row.index_reliability_score, 1)}（${reliabilityLabel(row.index_reliability_level)}）</small>
    </button>
  `;
  document.querySelector("#robust-list").innerHTML = `
    <div>
      <h3>高機會・高資料可靠度</h3>
      ${robust.map((row) => card(row, "高機會・高資料可靠度")).join("") || `<p>暫無資料</p>`}
    </div>
    <div>
      <h3>高潛力・需更多資料驗證</h3>
      ${needsMoreData.map((row) => card(row, "高潛力・需更多資料驗證")).join("") || `<p>暫無資料</p>`}
    </div>
  `;
  document.querySelectorAll(".robust-card").forEach((button) => {
    button.addEventListener("click", () => selectDistrict(button.dataset.district, true));
  });
}

function renderComparison() {
  const left = recordByDistrict.get(document.querySelector("#compare-a").value);
  const right = recordByDistrict.get(document.querySelector("#compare-b").value);
  const metricRows = [
    ["青年就業機會指數", "youth_employment_opportunity_index", formatScore],
    ["資料可靠度", "index_reliability_score", formatScore],
    ["排名穩定度", "index_rank_stability", formatScore],
    ["Opportunity 工作機會", "opportunity_score", (value) => formatNumber(value, 1)],
    ["Salary 薪資", "salary_score", (value) => formatNumber(value, 1)],
    ["Diversity 職類多樣性", "job_diversity_score", (value) => formatNumber(value, 1)],
    ["Stability 工作穩定性", "employment_stability_score", (value) => formatNumber(value, 1)],
    ["Opportunity 可靠度", "opportunity_reliability", (value) => formatNumber(value, 1)],
    ["Salary 可靠度", "salary_reliability", (value) => formatNumber(value, 1)],
    ["Diversity 可靠度", "diversity_reliability", (value) => formatNumber(value, 1)],
    ["Stability 可靠度", "stability_reliability", (value) => formatNumber(value, 1)],
    ["青年人口", "youth_population_18_35", formatNumber],
    ["工作機會", "job_openings", formatNumber],
    ["每千名青年工作機會", "jobs_per_1000_youth", (value) => formatNumber(value, 1)],
    ["平均薪資", "avg_salary", formatMoney],
    ["公司數", "company_count", formatNumber],
  ].filter(([, key]) => hasValue(left?.[key]) || hasValue(right?.[key]));
  document.querySelector("#comparison-table").innerHTML = `
    <table class="compare-table">
      <thead><tr><th>指標</th><th>${escapeHtml(left.district)}</th><th>${escapeHtml(right.district)}</th></tr></thead>
      <tbody>${metricRows.map(([label, key, formatter]) => `<tr><td>${label}</td><td>${formatter(left[key])}</td><td>${formatter(right[key])}</td></tr>`).join("")}</tbody>
    </table>
  `;
}

function currentTemporalEvidence() {
  const periods = historyCache?.history_manifest?.available_periods || historyCache?.periods || [];
  const latestSnapshot = activeSnapshotMonth || historyCache?.latest_snapshot || periods[periods.length - 1] || null;
  const latestRows = (historyCache?.records || []).filter((row) => row.snapshot_month === latestSnapshot);
  const first = latestRows[0] || {};
  return {
    latest_snapshot: latestSnapshot,
    available_periods: periods,
    period_count: periods.length,
    snapshot_as_of: first.snapshot_as_of || null,
    population_reference_month: first.population_reference_month || null,
    population_downloaded_at: first.population_downloaded_at || null,
    jobs_reference_date: first.jobs_reference_date || null,
    jobs_snapshot_as_of: first.jobs_snapshot_as_of || null,
    jobs_downloaded_at: first.jobs_downloaded_at || null,
    previous_available_period: first.previous_available_period || null,
    period_gap_months: first.period_gap_months || null,
    population_data_freshness_status: first.population_data_freshness_status || null,
    population_lag_months: first.population_lag_months || null,
    jobs_data_freshness_status: first.jobs_data_freshness_status || null,
    jobs_lag_months: first.jobs_lag_months || null,
    processed_at: first.processed_at || payloadCache?.provenance?.processed_at || null,
  };
}

function renderProvenance() {
  const provenance = payloadCache.provenance || {};
  const temporal = currentTemporalEvidence();
  const index = provenance.opportunity_index || {};
  const reliability = index.reliability || {};
  const quality = provenance.job_data_quality || {};
  const coverageRows = Object.entries(quality.field_coverage || {})
    .map(
      ([field, value]) => `
        <li>
          <strong>${escapeHtml(field)}</strong>
          <span>${formatNumber(value.non_null_count)} 筆｜${formatPercent(value.coverage_percentage)}</span>
        </li>
      `,
    )
    .join("");
  const workTypeRows = (quality.work_type_values || [])
    .map((item) => `${escapeHtml(item.value)} ${formatNumber(item.count)} 筆`)
    .join("、");
  const categoryRows = (quality.category_values || [])
    .slice(0, 12)
    .map((item) => `${escapeHtml(item.value)} ${formatNumber(item.count)} 筆`)
    .join("、");
  const weights = index.weights || {};
  const thresholds = reliability.sample_thresholds || {};
  const levels = reliability.level_thresholds || {};
  const sourceRows = (provenance.source_manifest?.sources || [])
    .map(
      (source) => `
        <li>
          <strong>${escapeHtml(source.publisher || "尚待確認")}</strong>
          ${escapeHtml(source.dataset || "尚待確認")}
          <span>${escapeHtml(source.local_path || source.filename || "尚待確認")}</span>
        </li>
      `,
    )
    .join("");
  document.querySelector("#provenance").innerHTML = `
    <div class="provenance-grid">
      <div><span>青年人口定義</span><strong>${escapeHtml(provenance.youth_definition || "18–35 歲")}</strong></div>
      <div><span>分析快照月份</span><strong>${escapeHtml(temporal.latest_snapshot || "尚待確認")}</strong></div>
      <div><span>人口參考月份</span><strong>${escapeHtml(temporal.population_reference_month || "尚待確認")}</strong></div>
      <div><span>職缺下載時間</span><strong>${escapeHtml(temporal.jobs_snapshot_as_of || temporal.jobs_downloaded_at || "尚待確認")}</strong></div>
      <div><span>職缺最新參考日</span><strong>${escapeHtml(temporal.jobs_reference_date || "尚待確認")}</strong></div>
      <div><span>資料處理時間</span><strong>${escapeHtml(provenance.processed_at || "尚待確認")}</strong></div>
      <div><span>台灣就業通下載區數</span><strong>${formatNumber(provenance.taiwanjobs_manifest?.sources?.length)}</strong></div>
      <div><span>每千青年工作機會</span><strong>job_openings / youth_population_18_35 * 1000</strong></div>
    </div>
    <div class="methodology-box">
      <h3>青年就業機會指數說明</h3>
      <p>這是 prototype composite indicator，不是官方政府指標、AI 預測或官方排名。</p>
      <p>權重：工作機會 ${formatPercent((weights.opportunity || 0) * 100)}、薪資 ${formatPercent((weights.salary || 0) * 100)}、職類多樣性 ${formatPercent((weights.diversity || 0) * 100)}、工作穩定性 ${formatPercent((weights.stability || 0) * 100)}。</p>
      <p>Normalization：${escapeHtml(index.normalization || "尚待確認")}</p>
      <p>缺失值：${escapeHtml(index.missing_data || "尚待確認")}</p>
      <p>Reliability：${escapeHtml(reliability.formula || "尚待確認")}</p>
      <p>Reliability level：高 >= ${formatNumber(levels.high)}，中 >= ${formatNumber(levels.medium)}，低 < ${formatNumber(levels.medium)}。</p>
      <p>Sample threshold：職缺刊登 ${formatNumber(thresholds.job_postings)}、需求人數 ${formatNumber(thresholds.job_openings)}、薪資樣本 ${formatNumber(thresholds.salary_sample_size)}、職類樣本 ${formatNumber(thresholds.diversity_sample_size)}、工作型態樣本 ${formatNumber(thresholds.stability_sample_size)}、青年人口分母 ${formatNumber(thresholds.youth_denominator)}。</p>
      <p>Ranking stability：${escapeHtml(reliability.rank_stability || "尚待確認")}</p>
      <p>work_type 實際值：${workTypeRows || "尚待確認"}</p>
      <p>category 主要值：${categoryRows || "尚待確認"}</p>
      <ul class="coverage-list">${coverageRows || "<li>尚待確認</li>"}</ul>
    </div>
    <ul class="source-list">${sourceRows || "<li>尚待確認</li>"}</ul>
  `;
}

const chineseDigits = { 零: 0, 〇: 0, 一: 1, 二: 2, 兩: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9 };

function parseChineseNumber(text) {
  if (!text) return null;
  if (/^\d+(\.\d+)?$/.test(text)) return Number(text);
  if (Object.prototype.hasOwnProperty.call(chineseDigits, text)) return chineseDigits[text];
  if (text.includes("十")) {
    const [left, right = ""] = text.split("十");
    const tens = left ? chineseDigits[left] : 1;
    const ones = right ? chineseDigits[right] : 0;
    return Number.isFinite(tens) && Number.isFinite(ones) ? tens * 10 + ones : null;
  }
  let value = 0;
  for (const char of text) {
    if (!Object.prototype.hasOwnProperty.call(chineseDigits, char)) return null;
    value = value * 10 + chineseDigits[char];
  }
  return value;
}

function parseAssistantSalary(query) {
  const compact = query.replaceAll(",", "").replaceAll("，", "");
  const regex = /(\d+(?:\.\d+)?|[零〇一二兩三四五六七八九十]+)\s*(萬|千)?/g;
  let minimum = null;
  let maximum = null;
  for (const match of compact.matchAll(regex)) {
    const number = parseChineseNumber(match[1]);
    if (!Number.isFinite(number)) continue;
    let amount = number;
    if (match[2] === "萬") amount *= 10000;
    if (match[2] === "千") amount *= 1000;
    if (amount < 1000 && compact.includes("薪")) amount *= 10000;
    const start = Math.max(0, match.index - 8);
    const end = Math.min(compact.length, match.index + match[0].length + 8);
    const windowText = compact.slice(start, end);
    if (["至少", "以上", "不低於", "起", ">=", "高於"].some((token) => windowText.includes(token))) minimum = Math.round(amount);
    else if (["最高", "以下", "以內", "不超過", "<="].some((token) => windowText.includes(token))) maximum = Math.round(amount);
    else if (windowText.includes("薪")) minimum = Math.round(amount);
  }
  return { minimum_salary: minimum, maximum_salary: maximum };
}

function assistantCategories() {
  return [...new Set(allJobs.map((job) => job.category).filter(Boolean))].sort((a, b) => a.localeCompare(b, "zh-Hant"));
}

function assistantCategoryFromQuery(query) {
  const categories = assistantCategories();
  const aliases = {
    資訊: ["資訊", "軟體", "系統", "工程師", "程式"],
    餐飲: ["餐飲", "旅遊", "休閒"],
    醫療: ["醫療", "美容", "保健"],
    製造: ["製造", "品管", "環衛"],
    物流: ["物流", "運輸", "資材"],
    行政: ["行政", "總務", "經營"],
    客服: ["客服", "門市"],
    營建: ["營建", "製圖", "施作"],
    業務: ["業務", "貿易", "銷售"],
    清潔: ["清潔", "家事", "托育"],
  };
  const direct = categories.find((category) => query.includes(category));
  if (direct) return direct;
  for (const [trigger, fragments] of Object.entries(aliases)) {
    if (query.includes(trigger) || fragments.some((fragment) => query.includes(fragment))) {
      return categories.find((category) => fragments.some((fragment) => category.includes(fragment))) || null;
    }
  }
  return null;
}

function assistantDistrictsInQuery(query) {
  const compact = query.replace(/\s+/g, "");
  return STANDARD_DISTRICTS.filter((district) => compact.includes(district) || compact.includes(district.replace("區", "")));
}

function parseAssistantConstraints(query) {
  const compact = query.replace(/\s+/g, "");
  const salaries = parseAssistantSalary(compact);
  const districts = assistantDistrictsInQuery(compact);
  const keywordTokens = ["資訊", "軟體", "工程師", "程式", "餐飲", "醫療", "製造", "物流", "行政", "客服", "門市", "業務"];
  const companyMatch = compact.match(/([\w\u4e00-\u9fff]{2,20}公司)/);
  return {
    target_job_keyword: keywordTokens.find((token) => compact.includes(token)) || null,
    target_category: assistantCategoryFromQuery(compact),
    preferred_district: districts[0] || null,
    minimum_salary: salaries.minimum_salary,
    maximum_salary: salaries.maximum_salary,
    work_type: compact.includes("全職") ? "全職" : compact.includes("兼職") ? "兼職" : null,
    company_keyword: companyMatch ? companyMatch[1] : null,
  };
}

function classifyAssistantIntent(query, constraints) {
  const compact = query.replace(/\s+/g, "");
  const lower = compact.toLowerCase();
  const districts = assistantDistrictsInQuery(compact);
  const hasPersonalConstraint = [
    "target_job_keyword",
    "target_category",
    "minimum_salary",
    "maximum_salary",
    "work_type",
    "company_keyword",
  ].some((key) => constraints[key]);
  if (["幾月資料", "資料月份", "資料日期", "更新日期", "什麼時候", "何時更新", "來源時間", "資料多新"].some((token) => compact.includes(token))) {
    return "data_freshness";
  }
  if (["增加最多", "成長最快", "正在增加", "趨勢", "最近", "下降", "減少"].some((token) => compact.includes(token))) {
    if (compact.includes("職類") || (compact.includes("類") && (compact.includes("資訊") || compact.includes("餐飲") || compact.includes("需求")))) {
      return "category_trend";
    }
    if (districts.length >= 1) return "district_trend";
    return "district_growth_ranking";
  }
  if (districts.length >= 2 && (compact.includes("比") || lower.includes("vs"))) return "compare_districts";
  if (compact.includes("為什麼") || compact.includes("原因") || compact.includes("怎麼會")) return "explain_district";
  if (compact.includes("工作機會最多")) return "rank_job_openings";
  if (compact.includes("可靠度") && (compact.includes("高") || lower.includes("highest")) && (compact.includes("指數") || lower.includes("index"))) return "high_index_high_reliability";
  if ((compact.includes("機會") || compact.includes("指數") || lower.includes("index")) && compact.includes("可靠度") && (compact.includes("不高") || compact.includes("低") || compact.includes("小心"))) return "high_index_low_reliability";
  if (compact.includes("青年人口多") && (compact.includes("工作機會") || compact.includes("相對少"))) return "population_high_openings_low";
  if (compact.includes("需求高") && compact.includes("薪資")) return "openings_high_salary_low";
  if (compact.includes("資源") || compact.includes("政策") || compact.includes("關注")) return "policy_attention";
  if (hasPersonalConstraint) return "personalized_recommendation";
  return "general_recommendation";
}

function salaryMidpoint(job) {
  const low = hasValue(job.salary_min) ? Number(job.salary_min) : null;
  const high = hasValue(job.salary_max) ? Number(job.salary_max) : null;
  if (low !== null && high !== null) return (low + high) / 2;
  return low ?? high;
}

function assistantSalaryMatches(job, constraints) {
  const low = hasValue(job.salary_min) ? Number(job.salary_min) : null;
  const high = hasValue(job.salary_max) ? Number(job.salary_max) : null;
  if (constraints.minimum_salary !== null && constraints.minimum_salary !== undefined) {
    if (low === null || low < Number(constraints.minimum_salary)) return false;
  }
  if (constraints.maximum_salary !== null && constraints.maximum_salary !== undefined) {
    const comparable = low ?? high;
    if (comparable === null || comparable > Number(constraints.maximum_salary)) return false;
  }
  return true;
}

function assistantJobMatches(job, constraints, allowUnknownSalary = false) {
  if (constraints.target_category && job.category !== constraints.target_category) return false;
  const haystack = [job.title, job.company, job.category, job.address, job.source].filter(Boolean).join(" ");
  if (constraints.target_job_keyword && !haystack.includes(constraints.target_job_keyword)) return false;
  if (constraints.work_type && job.work_type !== constraints.work_type) return false;
  if (constraints.company_keyword && !String(job.company || "").includes(constraints.company_keyword)) return false;
  if (constraints.minimum_salary || constraints.maximum_salary) {
    if (allowUnknownSalary && salaryMidpoint(job) === null) return true;
    return assistantSalaryMatches(job, constraints);
  }
  return true;
}

function medianNumber(values) {
  const clean = values.filter(hasValue).map(Number).sort((a, b) => a - b);
  if (!clean.length) return null;
  const mid = Math.floor(clean.length / 2);
  return clean.length % 2 ? clean[mid] : (clean[mid - 1] + clean[mid]) / 2;
}

function minMaxScores(valuesByDistrict) {
  const entries = Object.entries(valuesByDistrict);
  if (!entries.length) return {};
  const values = entries.map(([, value]) => value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) return Object.fromEntries(entries.map(([district]) => [district, 100]));
  return Object.fromEntries(entries.map(([district, value]) => [district, ((value - min) / (max - min)) * 100]));
}

function aggregateAssistantMatches(constraints) {
  const strictJobs = allJobs.filter((job) => assistantJobMatches(job, constraints));
  const secondarySalaryUnknown =
    constraints.minimum_salary || constraints.maximum_salary
      ? allJobs.filter((job) => assistantJobMatches(job, constraints, true) && salaryMidpoint(job) === null)
      : [];
  const aggregates = new Map();
  for (const district of STANDARD_DISTRICTS) {
    const jobs = strictJobs.filter((job) => job.district === district);
    const salaries = jobs.map(salaryMidpoint).filter(hasValue);
    aggregates.set(district, {
      district,
      matching_job_postings: jobs.length,
      matching_job_openings: jobs.reduce((sum, job) => sum + (hasValue(job.openings) ? Number(job.openings) : 0), 0),
      matching_company_count: new Set(jobs.map((job) => job.company).filter(Boolean)).size,
      matching_median_salary: medianNumber(salaries),
      matching_salary_known_count: salaries.length,
      matching_jobs: jobs
        .slice()
        .sort((a, b) => (Number(b.openings || 0) - Number(a.openings || 0)) || String(a.title || "").localeCompare(String(b.title || ""), "zh-Hant"))
        .slice(0, 12),
      district_metrics: recordByDistrict.get(district) || {},
    });
  }
  return { aggregates, strictJobs, secondarySalaryUnknown };
}

function buildPersonalRecommendations(aggregates) {
  const candidates = [...aggregates.values()].filter((row) => row.matching_job_postings > 0);
  const availabilityRaw = Object.fromEntries(
    candidates.map((row) => [row.district, row.matching_job_openings * 0.7 + row.matching_job_postings * 0.3]),
  );
  const availabilityScores = minMaxScores(availabilityRaw);
  const salaryScores = minMaxScores(
    Object.fromEntries(candidates.filter((row) => hasValue(row.matching_median_salary)).map((row) => [row.district, row.matching_median_salary])),
  );
  return candidates
    .map((row) => {
      const metrics = row.district_metrics;
      const components = {
        availability: availabilityScores[row.district] ?? 0,
        salary: salaryScores[row.district] ?? null,
        opportunity_index: hasValue(metrics.youth_employment_opportunity_index) ? Number(metrics.youth_employment_opportunity_index) : null,
        reliability: hasValue(metrics.index_reliability_score) ? Number(metrics.index_reliability_score) : null,
      };
      const usable = Object.entries(components).filter(([, value]) => value !== null);
      const weightSum = usable.reduce((sum, [key]) => sum + PERSONAL_MATCH_WEIGHTS[key], 0);
      const score = weightSum
        ? usable.reduce((sum, [key, value]) => sum + Number(value) * PERSONAL_MATCH_WEIGHTS[key] / weightSum, 0)
        : null;
      return {
        district: row.district,
        personal_match_score: score === null ? null : Number(score.toFixed(1)),
        score_components: Object.fromEntries(Object.entries(components).map(([key, value]) => [key, value === null ? null : Number(value.toFixed(1))])),
        matching_job_postings: row.matching_job_postings,
        matching_job_openings: row.matching_job_openings,
        matching_company_count: row.matching_company_count,
        matching_median_salary: row.matching_median_salary,
        opportunity_index: metrics.youth_employment_opportunity_index,
        reliability: metrics.index_reliability_score,
        reliability_level: metrics.index_reliability_level,
        rank_stability: metrics.index_rank_stability,
        matching_jobs: row.matching_jobs,
      };
    })
    .sort((a, b) => (Number(b.personal_match_score || -1) - Number(a.personal_match_score || -1)) || b.matching_job_openings - a.matching_job_openings);
}

function districtEvidence(row) {
  return {
    district: row.district,
    youth_population_18_35: row.youth_population_18_35,
    job_postings: row.job_postings,
    job_openings: row.job_openings,
    jobs_per_1000_youth: row.jobs_per_1000_youth,
    avg_salary: row.avg_salary,
    median_salary: row.median_salary,
    company_count: row.company_count,
    top_job_category: row.top_job_category,
    top_occupation: row.top_occupation,
    opportunity_score: row.opportunity_score,
    salary_score: row.salary_score,
    job_diversity_score: row.job_diversity_score,
    employment_stability_score: row.employment_stability_score,
    opportunity_index: row.youth_employment_opportunity_index,
    reliability: row.index_reliability_score,
    reliability_level: row.index_reliability_level,
    rank_stability: row.index_rank_stability,
    baseline_rank: row.baseline_rank,
    rank_min: row.rank_min,
    rank_max: row.rank_max,
    rank_range: row.rank_range,
  };
}

function assistantHighIndexCutoff() {
  const values = records.map((row) => row.youth_employment_opportunity_index).filter(hasValue).map(Number).sort((a, b) => a - b);
  return values.length ? values[Math.floor((values.length - 1) * 0.75)] : 0;
}

function topAssistantMetric(metric, limit = 10, reliabilityLevel = null) {
  return records
    .filter((row) => hasValue(row[metric]) && (!reliabilityLevel || row.index_reliability_level === reliabilityLevel))
    .slice()
    .sort((a, b) => Number(b[metric]) - Number(a[metric]))
    .slice(0, limit)
    .map(districtEvidence);
}

function policyAssistantInsight(intent) {
  const cutoff = assistantHighIndexCutoff();
  if (intent === "high_index_low_reliability") {
    return records
      .filter((row) => hasValue(row.youth_employment_opportunity_index) && Number(row.youth_employment_opportunity_index) >= cutoff && row.index_reliability_level === "Low")
      .sort((a, b) => Number(b.youth_employment_opportunity_index) - Number(a.youth_employment_opportunity_index))
      .map(districtEvidence);
  }
  if (intent === "high_index_high_reliability") {
    return records
      .filter((row) => hasValue(row.youth_employment_opportunity_index) && Number(row.youth_employment_opportunity_index) >= cutoff && row.index_reliability_level === "High")
      .sort((a, b) => Number(b.youth_employment_opportunity_index) - Number(a.youth_employment_opportunity_index))
      .map(districtEvidence);
  }
  if (intent === "population_high_openings_low") {
    return records
      .filter((row) => hasValue(row.youth_population_18_35) && hasValue(row.jobs_per_1000_youth))
      .sort((a, b) => (Number(b.youth_population_18_35) - Number(a.youth_population_18_35)) || (Number(a.jobs_per_1000_youth) - Number(b.jobs_per_1000_youth)))
      .slice(0, 10)
      .map(districtEvidence);
  }
  if (intent === "openings_high_salary_low") {
    return records
      .filter((row) => hasValue(row.job_openings) && hasValue(row.salary_score))
      .sort((a, b) => (Number(b.job_openings) - Number(a.job_openings)) || (Number(a.salary_score) - Number(b.salary_score)))
      .slice(0, 10)
      .map(districtEvidence);
  }
  return records
    .filter((row) => hasValue(row.youth_population_18_35) && hasValue(row.jobs_per_1000_youth))
    .sort((a, b) => (Number(b.youth_population_18_35) - Number(a.youth_population_18_35)) || (Number(a.jobs_per_1000_youth) - Number(b.jobs_per_1000_youth)))
    .slice(0, 10)
    .map(districtEvidence);
}

function localNoTrendResult() {
  const periods = historyCache?.periods || [];
  return {
    current_period: periods[periods.length - 1] || null,
    previous_period: periods.length >= 2 ? periods[periods.length - 2] : null,
    period_count: periods.length,
    forecast_readiness: historyCache?.forecast_readiness || { period_count: 0, level: "insufficient", label: "尚不足" },
    reason: "目前尚無足夠歷史資料進行趨勢比較。",
  };
}

function historyPeriodsReady() {
  return (historyCache?.periods || []).length >= 2;
}

function localTrendEvidence(row) {
  return {
    snapshot_month: row.snapshot_month,
    district: row.district,
    current_period: row.snapshot_month,
    job_postings: row.job_postings,
    job_openings: row.job_openings,
    jobs_per_1000_youth: row.jobs_per_1000_youth,
    median_salary: row.median_salary,
    opportunity_index: row.youth_employment_opportunity_index,
    job_postings_mom_pct: row.job_postings_mom_pct,
    job_openings_mom_pct: row.job_openings_mom_pct,
    salary_mom_pct: row.salary_mom_pct,
    jobs_per_1000_youth_mom_pct: row.jobs_per_1000_youth_mom_pct,
    index_mom_change: row.index_mom_change,
    trend_label: row.job_opportunity_trend,
    demand_growth_signal: row.demand_growth_signal,
  };
}

function localDistrictTrend(query) {
  if (!historyPeriodsReady()) return { noTrend: localNoTrendResult(), recommendations: [] };
  const periods = historyCache.periods;
  const currentPeriod = periods[periods.length - 1];
  const previousPeriod = periods[periods.length - 2];
  const district = assistantDistrictsInQuery(query)[0];
  const current = (historyCache.records || []).find((row) => row.snapshot_month === currentPeriod && row.district === district);
  const previous = (historyCache.records || []).find((row) => row.snapshot_month === previousPeriod && row.district === district);
  if (!current || !previous) return { noTrend: { reason: "目前資料不足以判斷。", current_period: currentPeriod, previous_period: previousPeriod }, recommendations: [] };
  const evidence = {
    ...localTrendEvidence(current),
    previous_period: previousPeriod,
    current_value: current.job_openings,
    previous_value: previous.job_openings,
    absolute_change: hasValue(current.job_openings) && hasValue(previous.job_openings) ? Number(current.job_openings) - Number(previous.job_openings) : null,
    percentage_change: current.job_openings_mom_pct,
  };
  return { noTrend: null, recommendations: [evidence] };
}

function localDistrictGrowthRanking() {
  if (!historyPeriodsReady()) return [];
  const currentPeriod = historyCache.periods[historyCache.periods.length - 1];
  return (historyCache.records || [])
    .filter((row) => row.snapshot_month === currentPeriod && hasValue(row.job_openings_mom_pct))
    .map(localTrendEvidence)
    .sort((a, b) => Number(b.job_openings_mom_pct) - Number(a.job_openings_mom_pct));
}

function localCategoryTrend(query) {
  if (!historyPeriodsReady()) return [];
  const periods = historyCache.periods;
  const currentPeriod = periods[periods.length - 1];
  let rows = (historyCache.category_history || []).filter((row) => row.snapshot_month === currentPeriod && hasValue(row.job_openings_mom_pct));
  if (query.includes("資訊")) rows = rows.filter((row) => String(row.category || "").includes("資訊"));
  if (query.includes("餐飲")) rows = rows.filter((row) => String(row.category || "").includes("餐飲"));
  return rows
    .sort((a, b) => Number(b.job_openings_mom_pct) - Number(a.job_openings_mom_pct))
    .slice(0, 10)
    .map((row) => ({
      current_period: currentPeriod,
      previous_period: periods[periods.length - 2],
      district: row.district,
      category: row.category,
      current_value: row.job_openings,
      absolute_change: row.absolute_openings_change,
      percentage_change: row.job_openings_mom_pct,
      trend_label: row.demand_growth_signal,
    }));
}

function buildLocalAssistantResult(query) {
  const constraints = parseAssistantConstraints(query);
  const intent = classifyAssistantIntent(query, constraints);
  const temporal = currentTemporalEvidence();
  const result = {
    query,
    intent,
    parsed_constraints: constraints,
    personal_match_weights: PERSONAL_MATCH_WEIGHTS,
    recommendations: [],
    matching_jobs: [],
    secondary_salary_unknown_jobs: [],
    evidence: {},
    answer_source: "browser_deterministic_template",
    provenance: {
      youth_definition: payloadCache?.provenance?.youth_definition || "18–35 歲",
      data_scope: "新北市29區",
      processed_at: payloadCache?.provenance?.processed_at || null,
      historical_period_count: temporal.period_count,
      latest_snapshot: temporal.latest_snapshot,
      temporal,
      assistant_note: "AI 建議為資料輔助結果，不代表政府官方推薦。",
    },
  };

  if (intent === "data_freshness") {
    result.temporal_evidence = temporal;
    result.evidence = { temporal };
  } else if (intent === "personalized_recommendation") {
    const { aggregates, strictJobs, secondarySalaryUnknown } = aggregateAssistantMatches(constraints);
    result.recommendations = buildPersonalRecommendations(aggregates).slice(0, 5);
    result.matching_jobs = strictJobs.slice(0, 40);
    result.secondary_salary_unknown_jobs = secondarySalaryUnknown.slice(0, 20);
    result.evidence = { district_aggregates: result.recommendations, strict_match_count: strictJobs.length };
  } else if (intent === "compare_districts") {
    result.comparison = assistantDistrictsInQuery(query)
      .slice(0, 2)
      .map((district) => recordByDistrict.get(district))
      .filter(Boolean)
      .map(districtEvidence);
    result.recommendations = result.comparison;
    result.evidence = { comparison: result.comparison };
  } else if (intent === "explain_district") {
    const district = assistantDistrictsInQuery(query)[0] || constraints.preferred_district;
    const row = district ? recordByDistrict.get(district) : null;
    result.district_explanation = row ? districtEvidence(row) : null;
    result.recommendations = result.district_explanation ? [result.district_explanation] : [];
    result.evidence = { district: result.district_explanation };
  } else if (intent === "rank_job_openings") {
    result.recommendations = topAssistantMetric("job_openings", 10);
    result.evidence = { metric: "job_openings", ranking: result.recommendations };
  } else if (["high_index_low_reliability", "high_index_high_reliability", "population_high_openings_low", "openings_high_salary_low", "policy_attention"].includes(intent)) {
    result.recommendations = policyAssistantInsight(intent);
    result.evidence = { policy_insight: result.recommendations };
  } else if (intent === "district_trend") {
    const trend = localDistrictTrend(query);
    result.trend_evidence = trend.noTrend || trend.recommendations[0];
    result.recommendations = trend.recommendations;
    result.evidence = { trend: result.trend_evidence };
  } else if (intent === "district_growth_ranking") {
    result.trend_evidence = historyPeriodsReady() ? null : localNoTrendResult();
    result.recommendations = localDistrictGrowthRanking();
    result.evidence = { trend_ranking: result.recommendations, trend: result.trend_evidence };
  } else if (intent === "category_trend") {
    result.trend_evidence = historyPeriodsReady() ? null : localNoTrendResult();
    result.recommendations = localCategoryTrend(query);
    result.evidence = { category_trend: result.recommendations, trend: result.trend_evidence };
  } else {
    result.recommendations = topAssistantMetric("youth_employment_opportunity_index", 5, "High");
    result.evidence = { metric: "youth_employment_opportunity_index", ranking: result.recommendations };
  }
  result.temporal_evidence = temporal;
  result.evidence.temporal = temporal;
  result.answer = localAssistantAnswer(result);
  return result;
}

function localAssistantAnswer(result) {
  const recs = result.recommendations || [];
  if (result.intent === "data_freshness") {
    const temporal = result.temporal_evidence || {};
    return `目前網站使用的 snapshot_month 是 ${temporal.latest_snapshot || "尚待確認"}。青年人口來源月份是 ${temporal.population_reference_month || "尚待確認"}，職缺資料下載時間是 ${temporal.jobs_snapshot_as_of || temporal.jobs_downloaded_at || "尚待確認"}，職缺列最新參考日期是 ${temporal.jobs_reference_date || "尚待確認"}。processed_at 只代表系統處理時間：${temporal.processed_at || "尚待確認"}。`;
  }
  if (["district_trend", "district_growth_ranking", "category_trend"].includes(result.intent) && result.trend_evidence?.reason) {
    return result.trend_evidence.reason;
  }
  if (result.intent === "district_trend") {
    const item = recs[0];
    if (!item) return "目前尚無足夠歷史資料進行趨勢比較。";
    return `${item.district}相較 ${item.previous_period}，${item.current_period} 工作機會為 ${formatNumber(item.current_value)} 人，前期為 ${formatNumber(item.previous_value)} 人，變化 ${formatNumber(item.absolute_change)} 人，MoM ${formatNumber(item.percentage_change, 1)}%，趨勢標籤：${item.trend_label || "暫無資料"}。`;
  }
  if (result.intent === "category_trend") {
    if (!recs.length) return "目前尚無足夠歷史資料進行趨勢比較。";
    return [
      "目前職類需求變化如下：",
      ...recs.slice(0, 5).map((item, index) => `${index + 1}. ${item.district} ${item.category}：需求 ${formatNumber(item.current_value)} 人，變化 ${formatNumber(item.absolute_change)} 人，MoM ${formatNumber(item.percentage_change, 1)}%，${item.trend_label || "暫無資料"}`),
    ].join("\n");
  }
  if (result.intent === "district_growth_ranking") {
    if (!recs.length) return "目前尚無足夠歷史資料進行趨勢比較。";
    return [
      "這個月工作機會增加最多的行政區：",
      ...recs.slice(0, 5).map((item, index) => `${index + 1}. ${item.district}：工作機會 ${formatNumber(item.job_openings)} 人，MoM ${formatNumber(item.job_openings_mom_pct, 1)}%，${item.trend_label || "暫無資料"}`),
    ].join("\n");
  }
  if (result.intent === "personalized_recommendation") {
    if (!recs.length) return "目前沒有找到符合條件的職缺。薪資條件只使用可解析薪資資料，未知薪資不會被視為符合。";
    const lines = ["依目前職缺資料，我會優先看："];
    recs.slice(0, 3).forEach((rec, index) => {
      const warning = rec.reliability_level === "Low" ? "；但資料可靠度偏低，建議搭配實際職缺逐筆確認" : "";
      lines.push(`${index + 1}. ${rec.district}`);
      lines.push(`匹配職缺：${formatNumber(rec.matching_job_postings)} 筆，需求人數：${formatNumber(rec.matching_job_openings)} 人，公司數：${formatNumber(rec.matching_company_count)}`);
      lines.push(`薪資中位數：${formatMoney(rec.matching_median_salary)}，青年就業機會指數：${formatNumber(rec.opportunity_index, 1)}，資料可靠度：${formatNumber(rec.reliability, 1)}${warning}`);
    });
    lines.push("注意事項：本結果依目前已收錄職缺計算，不代表所有市場職缺。");
    return lines.join("\n");
  }
  if (result.intent === "compare_districts") {
    const [a, b] = result.comparison || [];
    if (!a || !b) return "目前資料不足以完成兩個行政區比較。";
    const better = Number(a.opportunity_index || -1) >= Number(b.opportunity_index || -1) ? a : b;
    return `${a.district}與${b.district}比較：目前青年就業機會指數較高的是${better.district}。${a.district}工作機會 ${formatNumber(a.job_openings)} 人、每千青年 ${formatNumber(a.jobs_per_1000_youth, 1)}；${b.district}工作機會 ${formatNumber(b.job_openings)} 人、每千青年 ${formatNumber(b.jobs_per_1000_youth, 1)}。`;
  }
  if (result.intent === "explain_district") {
    const row = result.district_explanation;
    if (!row) return "目前資料不足以判斷。";
    const warning = row.reliability_level === "Low" ? " 不過資料可靠度偏低，因此不建議只根據 Index 做決策。" : "";
    return `${row.district}的青年就業機會指數為 ${formatNumber(row.opportunity_index, 1)}，資料可靠度為 ${formatNumber(row.reliability, 1)}（${reliabilityLabel(row.reliability_level)}）。工作機會 ${formatNumber(row.job_openings)} 人、每千名青年工作機會 ${formatNumber(row.jobs_per_1000_youth, 1)}、薪資分數 ${formatNumber(row.salary_score, 1)}、職類多樣性 ${formatNumber(row.job_diversity_score, 1)}。${warning}`;
  }
  if (!recs.length) return "目前資料不足以判斷。";
  const prefixByIntent = {
    high_index_low_reliability: "目前看起來機會較高、但資料可靠度偏低的行政區：",
    high_index_high_reliability: "目前資料同時顯示較高機會與較高資料支持度的行政區：",
    rank_job_openings: "目前工作機會最多的行政區：",
    population_high_openings_low: "目前資料顯示可能值得進一步關注的行政區：",
    openings_high_salary_low: "目前資料顯示可能值得進一步關注的行政區：",
    policy_attention: "目前資料顯示可能值得進一步關注的行政區：",
  };
  return [
    prefixByIntent[result.intent] || "依目前資料可優先觀察：",
    ...recs.slice(0, 5).map((rec, index) => `${index + 1}. ${rec.district}：工作機會 ${formatNumber(rec.job_openings)} 人，Index ${formatNumber(rec.opportunity_index, 1)}，可靠度 ${formatNumber(rec.reliability, 1)}`),
  ].join("\n");
}

async function runAssistant(query) {
  const response = await fetch(ASSISTANT_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!response.ok) throw new Error(`assistant api ${response.status}`);
  return response.json();
}

function assistantRecommendationDistricts(result) {
  return (result.recommendations || [])
    .map((item) => item.district)
    .filter((district) => STANDARD_DISTRICTS.includes(district))
    .slice(0, 5);
}

function evidenceTableRows(recommendations) {
  return recommendations
    .map(
      (rec) => `
        <tr>
          <td>${escapeHtml(rec.district)}</td>
          <td>${formatNumber(rec.matching_job_postings ?? rec.job_postings)}</td>
          <td>${formatNumber(rec.matching_job_openings ?? rec.job_openings)}</td>
          <td>${formatMoney(rec.matching_median_salary ?? rec.median_salary)}</td>
          <td>${formatNumber(rec.personal_match_score, 1)}</td>
          <td>${formatNumber(rec.opportunity_index, 1)}</td>
          <td>${formatNumber(rec.reliability, 1)}（${reliabilityLabel(rec.reliability_level)}）</td>
          <td>${formatNumber(rec.rank_stability, 1)}</td>
        </tr>
      `,
    )
    .join("");
}

function renderAssistantResult(result) {
  const output = document.querySelector("#assistant-output");
  const districts = assistantRecommendationDistricts(result);
  recommendedDistricts = new Set(districts);
  if (geoLayer) geoLayer.setStyle(featureStyle(currentMetric().key));
  if (districts[0]) selectDistrict(districts[0], true);

  const recommendedJobs =
    result.intent === "personalized_recommendation"
      ? (result.recommendations || []).flatMap((rec) => rec.matching_jobs || []).slice(0, 12)
      : [];
  const constraints = result.parsed_constraints || {};
  output.innerHTML = `
    <div class="assistant-answer">
      <h3>分析結果</h3>
      <pre>${escapeHtml(result.answer || "目前資料不足以判斷。")}</pre>
    </div>
    <div class="assistant-evidence-summary">
      <span>模式：${escapeHtml(result.answer_source || "deterministic")}</span>
      <span>Intent：${escapeHtml(result.intent || "尚待確認")}</span>
      <span>Snapshot：${escapeHtml(result.provenance?.temporal?.latest_snapshot || result.provenance?.latest_snapshot || "尚待確認")}</span>
      <span>人口月份：${escapeHtml(result.provenance?.temporal?.population_reference_month || "尚待確認")}</span>
      <span>職缺時間：${escapeHtml(result.provenance?.temporal?.jobs_snapshot_as_of || result.provenance?.temporal?.jobs_downloaded_at || "尚待確認")}</span>
      <span>青年定義：${escapeHtml(result.provenance?.youth_definition || "18–35 歲")}</span>
      <span>資料範圍：${escapeHtml(result.provenance?.data_scope || "新北市29區")}</span>
    </div>
    <div class="assistant-constraints">
      ${Object.entries(constraints)
        .filter(([, value]) => value !== null && value !== undefined && value !== "")
        .map(([key, value]) => `<span>${escapeHtml(key)}：${escapeHtml(value)}</span>`)
        .join("") || "<span>未解析出職缺篩選條件，改以行政區指標回答。</span>"}
    </div>
    <div class="assistant-recommendations">
      ${(result.recommendations || [])
        .slice(0, 5)
        .map(
          (rec, index) => `
            <button class="assistant-rec-card" type="button" data-district="${escapeHtml(rec.district)}">
              <strong>${index + 1}. ${escapeHtml(rec.district)}</strong>
              <span>Personal ${formatNumber(rec.personal_match_score, 1)}｜Index ${formatNumber(rec.opportunity_index, 1)}｜可靠度 ${formatNumber(rec.reliability, 1)}</span>
              ${rec.reliability_level === "Low" ? "<small>資料可靠度偏低，建議謹慎解讀。</small>" : ""}
            </button>
          `,
        )
        .join("")}
    </div>
    ${recommendedJobs.length ? `<h3>符合條件的職缺</h3><div class="job-list">${jobCards(recommendedJobs, 12)}</div>` : ""}
    <details class="assistant-evidence">
      <summary>查看分析依據</summary>
      <div class="assistant-evidence-table">
        <table class="compare-table">
          <thead><tr><th>行政區</th><th>匹配職缺</th><th>需求人數</th><th>薪資中位數</th><th>Personal</th><th>Index</th><th>可靠度</th><th>排名穩定</th></tr></thead>
          <tbody>${evidenceTableRows(result.recommendations || []) || `<tr><td colspan="8">目前資料不足以判斷。</td></tr>`}</tbody>
        </table>
      </div>
      <pre>${escapeHtml(JSON.stringify(result.evidence || {}, null, 2))}</pre>
    </details>
    <p class="assistant-note">資料基礎：18–35 歲、新北市 29 區、處理時間 ${escapeHtml(result.provenance?.processed_at || "尚待確認")}。AI 建議為資料輔助結果，不代表政府官方推薦。</p>
  `;
  output.querySelectorAll(".assistant-rec-card").forEach((button) => {
    button.addEventListener("click", () => selectDistrict(button.dataset.district, true));
  });
}

function renderAssistantError(message) {
  document.querySelector("#assistant-output").innerHTML = `
    <div class="assistant-answer is-error">
      <h3>分析失敗</h3>
      <p>${escapeHtml(message)}</p>
    </div>
  `;
}

function setupAssistant() {
  const queryInput = document.querySelector("#assistant-query");
  const submit = document.querySelector("#assistant-submit");
  const status = document.querySelector("#assistant-status");
  const analyze = async () => {
    const query = queryInput.value.trim();
    if (!query) {
      renderAssistantError("請先輸入問題。");
      return;
    }
    submit.disabled = true;
    status.textContent = "分析中";
    try {
      const result = USE_ASSISTANT_API ? await runAssistant(query) : buildLocalAssistantResult(query);
      status.textContent = "資料驅動模式";
      renderAssistantResult(result);
    } catch (_error) {
      const result = buildLocalAssistantResult(query);
      status.textContent = "AI 語言解釋目前暫時不可用，已改用資料分析結果。";
      renderAssistantResult(result);
    } finally {
      submit.disabled = false;
    }
  };
  submit.addEventListener("click", analyze);
  document.querySelectorAll(".suggested-questions button").forEach((button) => {
    button.addEventListener("click", () => {
      queryInput.value = button.dataset.query;
      analyze();
    });
  });
}

loadSiteData()
  .then(() => {
    renderMetricSelect();
    aggregateFilteredMetrics();
    renderKpis();
    renderTrendControls();
    renderFilterControls();
    renderDistrictSelect();
    renderAllRankings();
    renderComparison();
    renderProvenance();
    renderFilteredCount();
    renderFilteredJobs();
    renderMap(geojsonCache);
    selectDistrict(selectedDistrict, false);
    setupAssistant();
    import("./policy-assistant.js?v=20260909-policy-pet").then(module => module.setupPolicyAssistant(policyDatasetText)).catch(() => {
      document.querySelector("#policy-status").textContent = "政策助理暫時無法載入";
    });
    document.querySelector("#metric-select").addEventListener("change", () => renderMap(geojsonCache));
    setAppStatus("資料已載入：新北市 29 行政區、職缺、歷史快照與本地 AI 分析可用。", "ready");
  })
  .catch((error) => {
    document.querySelector("#snapshot-date").textContent = "資料載入失敗";
    document.querySelector("#data-sanity").textContent = "資料狀態：載入失敗";
    setAppStatus("資料載入失敗，請重新整理或確認資料檔案。", "error");
    document.querySelector("#map").innerHTML = `<div class="load-error">資料載入失敗：${escapeHtml(error.message)}</div>`;
  });
