import { test, expect } from "@playwright/test";
import { openDashboard, expectNoConsoleErrors } from "./helpers.js";

async function ask(page, query) {
  await page.locator("#assistant-query").fill(query);
  await page.locator("#assistant-submit").click();
  await expect(page.locator("#assistant-output .assistant-answer")).toBeVisible();
}

test("assistant salary filter does not show visibly lower salary jobs", async ({ page }) => {
  const errors = await openDashboard(page);
  await ask(page, "月薪至少40000");
  await expect(page.locator("#assistant-output")).toContainText(/依目前職缺資料|目前沒有找到/);
  const cards = await page.locator("#assistant-output .job-card").allTextContents();
  for (const text of cards) {
    const salaryMatch = text.replaceAll(",", "").match(/月薪\s*(\d+)/);
    if (salaryMatch) expect(Number(salaryMatch[1])).toBeGreaterThanOrEqual(40000);
  }
  await expectNoConsoleErrors(errors);
});

test("assistant full-time filter shows full-time jobs when results exist", async ({ page }) => {
  const errors = await openDashboard(page);
  await ask(page, "我想找全職工作");
  await expect(page.locator("#assistant-output")).toContainText(/依目前職缺資料|目前沒有找到/);
  const cards = await page.locator("#assistant-output .job-card").allTextContents();
  for (const text of cards) expect(text).toContain("全職");
  await expectNoConsoleErrors(errors);
});

test("assistant explains reliability limits and refuses fabricated jobs", async ({ page }) => {
  const errors = await openDashboard(page);
  await ask(page, "平溪為什麼 Index 高？");
  await expect(page.locator("#assistant-output")).toContainText(/可靠度|資料量|謹慎/);

  await ask(page, "火星採礦工程師月薪999萬");
  await expect(page.locator("#assistant-output")).toContainText("目前沒有找到符合條件的職缺");
  await expect(page.locator("#assistant-output .job-card")).toHaveCount(0);
  await expectNoConsoleErrors(errors);
});

test("backend failure with assistantApi=1 falls back locally", async ({ page }) => {
  await page.route("http://localhost:8000/**", (route) => route.fulfill({ status: 200, contentType: "text/plain", body: "backend unavailable" }));
  const errors = await openDashboard(page, "/?assistantApi=1");
  await ask(page, "月薪至少40000");
  await expect(page.locator("#assistant-status")).toContainText("已改用資料分析結果");
  await expect(page.locator("#assistant-output")).not.toContainText("traceback");
  await expectNoConsoleErrors(errors);
});
