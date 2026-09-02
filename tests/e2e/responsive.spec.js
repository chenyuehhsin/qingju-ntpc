import { test, expect } from "@playwright/test";
import { openDashboard, expectNoConsoleErrors } from "./helpers.js";

for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "laptop", width: 1280, height: 720 },
  { name: "mobile", width: 390, height: 844 }
]) {
  test(`responsive layout works on ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    const errors = await openDashboard(page);
    await expect(page.locator("#kpi-youth")).toBeVisible();
    await expect(page.locator("#map")).toBeVisible();
    await expect(page.locator("#assistant-query")).toBeVisible();
    await expect(page.locator(".job-card").first()).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2);
    expect(overflow).toBe(false);
    await expectNoConsoleErrors(errors);
  });
}
