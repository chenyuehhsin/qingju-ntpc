import { test, expect } from "@playwright/test";
import { openDashboard, expectNoConsoleErrors } from "./helpers.js";

test("3-minute competition demo flow", async ({ page }) => {
  const errors = await openDashboard(page);
  await expect(page.locator("#kpi-youth")).not.toHaveText("--");

  await page.locator("#metric-select").selectOption("youth_employment_opportunity_index");
  await expect(page.locator("#map-legend")).toContainText("青年就業機會指數");

  await page.locator('.svg-district[data-district="樹林區"]').click();
  await expect(page.locator("#district-detail .district-name")).toContainText("樹林區");
  await expect(page.locator("#district-detail")).toContainText("青年就業機會指數");
  await expect(page.locator("#district-detail")).toContainText("資料可靠度");

  await page.locator("#assistant-query").fill("我想找月薪至少4萬的全職工作");
  await page.locator("#assistant-submit").click();
  await expect(page.locator("#assistant-output")).toContainText(/依目前職缺資料|目前沒有找到/);
  await page.locator(".assistant-evidence summary").click();
  await expect(page.locator(".assistant-evidence pre")).toBeVisible();

  await page.locator("#metric-select").selectOption("index_reliability_score");
  await expect(page.locator("#map-legend")).toContainText("資料可靠度");

  await expect(page.locator("#trend-summary")).toContainText("1 個月份");
  await expect(page.locator("#trend-summary")).toContainText("尚無前期資料");

  await expectNoConsoleErrors(errors);
});
