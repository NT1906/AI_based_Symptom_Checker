/**
 * @file Playwright global configuration for the AI-Based Symptom Checker E2E suite.
 *
 * Runs all spec files in this directory against the locally running full stack
 * (client: http://localhost:5173, server: http://localhost:8000).
 *
 * To run:
 *   cd tests/e2e && npm ci && npx playwright install --with-deps chromium
 *   npx playwright test
 *
 * Owner: Mohit (testing) · Task: S0-MOH-1 · Requirements: NFR-07, NFR-08
 */

import { defineConfig, devices } from "@playwright/test";

/**
 * Base URL of the running React PWA dev server (Vite, proxied to :8000).
 * Override with the PLAYWRIGHT_BASE_URL env var to point at staging.
 */
const BASE_URL = process.env["PLAYWRIGHT_BASE_URL"] ?? "http://localhost:5173";

export default defineConfig({
  testDir: "./specs",

  /** Run each test file in isolation; never share state between specs. */
  fullyParallel: false,

  /** Fail the whole suite immediately if any spec file has a global error. */
  forbidOnly: !!process.env["CI"],

  /** Retry failed tests once on CI to reduce flakiness from race conditions. */
  retries: process.env["CI"] ? 1 : 0,

  /** Keep workers to 1 so tests run sequentially against the same server. */
  workers: 1,

  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],

  use: {
    baseURL: BASE_URL,

    /** Capture a screenshot on failure for debugging. */
    screenshot: "only-on-failure",

    /** Record a trace on first retry so failures are reproducible. */
    trace: "on-first-retry",

    /**
     * Why: The assessment API uses AI_PROVIDER=mock and CV_PROVIDER=mock
     * in test/local mode so no real LLM or CV API is ever called (AI_RULES §2).
     */
    extraHTTPHeaders: {
      "X-Test-Run": "playwright-e2e",
    },
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
