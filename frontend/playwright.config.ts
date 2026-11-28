import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://localhost:3100",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { browserName: "chromium", viewport: { width: 1440, height: 1000 } } },
    { name: "tablet", use: { browserName: "chromium", viewport: { width: 768, height: 1024 }, isMobile: true, hasTouch: true } },
    { name: "mobile", use: { browserName: "chromium", viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
  webServer: {
    command: "npx next dev -p 3100",
    url: "http://localhost:3100",
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
    env: {
      NEXT_PUBLIC_API_URL: "http://api.test",
      NEXT_PUBLIC_PARTY_0_URL: "http://party0.test",
      NEXT_PUBLIC_PARTY_1_URL: "http://party1.test",
      NEXT_PUBLIC_PARTY_2_URL: "http://party2.test",
    },
  },
});
