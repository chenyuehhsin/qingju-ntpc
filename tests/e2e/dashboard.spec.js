import { test, expect } from "@playwright/test";
import { openDashboard, expectNoConsoleErrors, readJson } from "./helpers.js";

test("dashboard loads New Taipei only and supports core interactions", async ({ page }) => {
  const errors = await openDashboard(page);
  const payload = readJson("youth_employment_map.json");
  const geojson = readJson("new_taipei_districts.geojson");
  const districts = payload.records.map((row) => row.district);

  await expect(page.locator("#district-select option")).toHaveCount(29);
  expect(new Set(districts).size).toBe(29);
  expect(geojson.features.filter((feature) => districts.includes(feature.properties.TOWNNAME))).toHaveLength(29);
  await expect(page.locator(".svg-district")).toHaveCount(29);
  await expect(page.locator(".leaflet-tile")).toHaveCount(0);
  expect((await page.locator("img").evaluateAll((imgs) => imgs.map((img) => img.src))).some((src) => src.includes("openstreetmap"))).toBe(false);

  await expect(page.locator("#kpi-youth")).not.toHaveText("--");
  await expect(page.locator("#kpi-postings")).not.toHaveText("--");
  await expect(page.locator("#kpi-openings")).not.toHaveText("--");
  await expect(page.locator("#data-sanity")).toContainText("行政區 29/29");

  for (const label of ["青年人口", "工作機會", "每千名青年工作機會", "平均薪資", "青年就業機會指數", "資料可靠度"]) {
    await page.locator("#metric-select").selectOption({ label });
    await expect(page.locator("#map-legend")).toContainText(label);
  }

  await page.locator('.svg-district[data-district="板橋區"]').click();
  await expect(page.locator("#district-detail .district-name")).toContainText("板橋區");

  await page.locator("#openings-ranking .rank-row").first().click();
  await expect(page.locator(".svg-district.is-selected")).toHaveCount(1);

  await page.locator("#compare-a").selectOption("板橋區");
  await page.locator("#compare-b").selectOption("新莊區");
  await expect(page.locator("#comparison-table")).toContainText("板橋區");
  await expect(page.locator("#comparison-table")).toContainText("新莊區");

  await expectNoConsoleErrors(errors);
});

test("core resources return HTTP 200", async ({ request }) => {
  for (const resource of [
    "/",
    "/app.js",
    "/styles.css",
    "/data/youth_employment_map.json",
    "/data/youth_employment_history.json",
    "/data/new_taipei_districts.geojson",
    "/data/build_info.json"
  ]) {
    const response = await request.get(resource);
    expect(response.status(), resource).toBe(200);
  }
});
