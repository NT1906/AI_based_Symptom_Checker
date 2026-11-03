/**
 * @file E2E health-check spec: verifies the backend /health endpoint
 * returns the expected structure before running any assessment spec.
 *
 * Owner: Mohit (testing) · Task: S0-MOH-1 · Requirements: NFR-08
 */

import { test, expect } from "../fixtures";

test("GET /api/v1/health returns ok status and version", async ({
  page,
  request,
}) => {
  const response = await request.get("/api/v1/health");
  expect(response.status()).toBe(200);

  const body = (await response.json()) as { status: string; version: string };
  expect(body.status).toBe("ok");
  expect(typeof body.version).toBe("string");
  expect(body.version.length).toBeGreaterThan(0);
});
