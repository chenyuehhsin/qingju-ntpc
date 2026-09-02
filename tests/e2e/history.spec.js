import { test, expect } from "@playwright/test";
import { openDashboard, expectNoConsoleErrors } from "./helpers.js";

test("historical UI shows only supported 2026-08 snapshot", async ({ page }) => {
  const errors = await openDashboard(page);
  await expect(page.locator("#snapshot-month-select")).toHaveValue("2026-08");
  await expect(page.locator("#trend-summary")).toContainText("尚不足");
  await expect(page.locator("#trend-summary")).toContainText("尚無前期資料");
  const trendText = await page.locator("#trend-summary").textContent();
  expect(trendText).not.toMatch(/上升|下降|成長最快/);
  await expectNoConsoleErrors(errors);
});

test("temporal provenance is explicit and does not mislabel sources", async ({ page }) => {
  const errors = await openDashboard(page);
  await expect(page.locator("#snapshot-date")).toContainText("2026-08");
  await expect(page.locator("#data-sanity")).toContainText("人口 2026-07");
  await expect(page.locator("#provenance")).toContainText("分析快照月份");
  await expect(page.locator("#provenance")).toContainText("2026-08");
  await expect(page.locator("#provenance")).toContainText("人口參考月份");
  await expect(page.locator("#provenance")).toContainText("2026-07");
  await expect(page.locator("#provenance")).toContainText(/職缺下載時間|職缺最新參考日/);
  await expect(page.locator("body")).not.toContainText("2026-08 官方統計資料");
  await expectNoConsoleErrors(errors);
});
