import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 30000,
  fullyParallel: false,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:8080",
    trace: "retain-on-failure"
  },
  webServer: {
    command: "python -m http.server 8080 --directory website",
    url: "http://127.0.0.1:8080",
    reuseExistingServer: true,
    timeout: 15000
  }
});
