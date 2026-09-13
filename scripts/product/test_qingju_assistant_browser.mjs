// Optional UI smoke check: npm install --no-save playwright
// Start Streamlit first, then node scripts/product/test_qingju_assistant_browser.mjs
import { chromium } from "playwright";
import assert from "node:assert/strict";
import { tmpdir } from "node:os";
import path from "node:path";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
page.setDefaultTimeout(60000);
try {
  await page.goto(process.env.QINGJU_URL || "http://127.0.0.1:8501");
  await page.getByText("青聚新北｜青年安居 × 就業 × 交通", { exact: true }).waitFor();
  await page.getByRole("button", { name: "青年職涯探索", exact: true }).waitFor();
  await page.locator(".qj-page-hero img").waitFor();
  const pet = page.locator('.st-key-qingju_assistant [data-testid="stPopoverButton"]');
  const panel = page.locator('[data-testid="stPopoverBody"]');
  await pet.waitFor();
  let box = await pet.boundingBox();
  assert.match(await pet.evaluate(el => getComputedStyle(el, "::before").backgroundImage), /data:image\/svg\+xml/);
  await page.screenshot({ path: path.join(tmpdir(), "qingju-real-site-pet.png") });
  assert(box.x > 1200 && box.y > 800, `Pet must be fixed bottom-right on the actual Qingju website: ${JSON.stringify(box)}`);
  await pet.click();
  await panel.waitFor();
  await panel.getByLabel("想問青聚什麼？", { exact: true }).fill("板橋目前青年人口有多少？");
  await panel.getByRole("button", { name: "詢問小幫手", exact: true }).click();
  await panel.getByText(/依目前青聚資料，板橋區/).waitFor();
  assert.equal(await page.locator('[data-testid="stException"]').count(), 0);
  await page.screenshot({ path: path.join(tmpdir(), "qingju-real-site-answer.png") });
  await page.keyboard.press("Escape");
  await panel.waitFor({ state: "hidden" });
  for (const name of ["青年安居推薦", "青年局 Policy Lens", "青年職涯探索"]) {
    await page.getByRole("button", { name, exact: true }).click();
    await pet.click();
    await panel.getByText(new RegExp(`目前頁面：${name}`)).waitFor();
    await panel.getByText(/依目前青聚資料，板橋區/).waitFor();
    assert.equal(await page.locator('[data-testid="stException"]').count(), 0);
    await page.keyboard.press("Escape");
    await panel.waitFor({ state: "hidden" });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await pet.click();
  await panel.waitFor();
  box = await panel.boundingBox();
  assert(box.x >= 0 && box.x + box.width <= 391, "Mobile panel must fit horizontally");
  assert(box.y >= 0 && box.y + box.height <= 845, "Mobile panel must fit vertically");
  await page.screenshot({ path: path.join(tmpdir(), "qingju-real-site-mobile.png") });
  console.log("PASS: Qingju brand, fixed pet, native question/answer, Escape, three pages, retained answer, mobile bounds, no app exceptions");
} finally {
  await browser.close();
}
