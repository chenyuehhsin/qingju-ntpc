import { expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

export const projectRoot = process.cwd();
export const websiteData = path.join(projectRoot, "website", "data");

export function readJson(name) {
  return JSON.parse(fs.readFileSync(path.join(websiteData, name), "utf8"));
}

export function attachConsoleFailure(page) {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  return errors;
}

export async function openDashboard(page, url = "/") {
  const errors = attachConsoleFailure(page);
  await page.goto(url);
  await expect(page.locator("h1")).toContainText("新北市青年就業地圖");
  await expect(page.locator("#app-status")).toContainText("資料已載入", { timeout: 15000 });
  return errors;
}

export async function expectNoConsoleErrors(errors) {
  expect(errors, errors.join("\n")).toEqual([]);
}
