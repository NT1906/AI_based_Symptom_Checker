/**
 * Cross-browser and responsive-device E2E matrix.
 * Uses mock providers; never uses real health data or external AI APIs.
 */

import { defineConfig, devices } from "@playwright/test";

const BASE_URL =
  process.env["PLAYWRIGHT_BASE_URL"] ?? "http://localhost:5173";

export default defineConfig({
  testDir: "./specs",
  fullyParallel: false,
  forbidOnly: !!process.env["CI"],
  retries: process.env["CI"] ? 1 : 0,
  workers: process.env["CI"] ? 2 : 1,

  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],

  use: {
    baseURL: BASE_URL,
    screenshot: "only-on-failure",
    trace: "on-first-retry",
    extraHTTPHeaders: {
      "X-Test-Run": "playwright-e2e",
    },
  },

  projects: [
    {
      name: "chromium-desktop",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox-desktop",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit-desktop",
      use: { ...devices["Desktop Safari"] },
    },
    {
      name: "pixel-5-chrome",
      use: { ...devices["Pixel 5"] },
    },
    {
      name: "iphone-12-safari",
      use: { ...devices["iPhone 12"] },
    },
    {
      name: "ipad-tablet",
      use: { ...devices["iPad (gen 7)"] },
    },
  ],
});
