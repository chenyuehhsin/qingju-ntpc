import { test, expect } from "@playwright/test";
import { openDashboard, expectNoConsoleErrors, readJson } from "./helpers.js";

test("Pingxi reliability warning matches official dataset", async ({ page }) => {
  const errors = await openDashboard(page);
  const payload = readJson("youth_employment_map.json");
  const pingxi = payload.records.find((row) => row.district === "平溪區");
  expect(pingxi).toBeTruthy();

  await page.locator('.svg-district[data-district="平溪區"]').click();
  await expect(page.locator("#district-detail .district-name")).toContainText("平溪區");
  await expect(page.locator("#district-detail")).toContainText("資料可靠度");
  await expect(page.locator("#district-detail")).toContainText("低");
  await expect(page.locator("#district-detail")).toContainText(String(Math.round(pingxi.youth_employment_opportunity_index * 10) / 10).split(".")[0]);

  await page.locator("#assistant-query").fill("平溪為什麼 Index 高？");
  await page.locator("#assistant-submit").click();
  await expect(page.locator("#assistant-output")).toContainText(/資料可靠度偏低|資料量|可靠度/);

  await expectNoConsoleErrors(errors);
});
