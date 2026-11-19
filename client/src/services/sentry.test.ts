/**
 * @file Tests for the client-side Sentry telemetry service.
 * Owner: Dimple · Task: S2-DIM-7 · Requirements: NFR-03, NFR-05, DR-06
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  addBreadcrumb,
  captureException,
  clearBreadcrumbs,
  getBreadcrumbs,
  initSentry,
  resetSentry,
  scrubObject,
  scrubPii,
} from "./sentry";

describe("Sentry Client Service", () => {
  beforeEach(() => {
    resetSentry();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    resetSentry();
    vi.restoreAllMocks();
  });

  describe("PII & Secrets Scrubbing (NFR-03, DPDP Act 2023)", () => {
    it("scrubs email addresses from strings", () => {
      const raw = "User email patient.doe@example.com reported an issue";
      expect(scrubPii(raw)).toBe(
        "User email [REDACTED_EMAIL] reported an issue",
      );
    });

    it("scrubs JWT and Bearer tokens from strings", () => {
      const raw =
        "Authorization: Bearer secret_token_1234567890abcdef and eyJhbGciOi.eyJzdWIiOi.signature";
      const scrubbed = scrubPii(raw);
      expect(scrubbed).not.toContain("secret_token_1234567890abcdef");
      expect(scrubbed).toContain("Bearer [REDACTED_TOKEN]");
      expect(scrubbed).toContain("[REDACTED_JWT]");
    });

    it("scrubs 64-character SHA-256 session token hashes", () => {
      const hash = "a".repeat(64);
      const raw = `Session token_hash=${hash} was evaluated`;
      expect(scrubPii(raw)).toBe(
        "Session token_hash=[REDACTED_HASH] was evaluated",
      );
    });

    it("scrubObject redacts sensitive keys entirely", () => {
      const sensitive = {
        email: "test@example.com",
        password: "secretpassword",
        symptoms: ["headache", "chest pain"],
        content: "I feel dizzy and weak",
        safeMeta: "navigation-click",
      };

      const result = scrubObject(sensitive);
      expect(result.email).toBe("[REDACTED_SENSITIVE]");
      expect(result.password).toBe("[REDACTED_SENSITIVE]");
      expect(result.symptoms).toBe("[REDACTED_SENSITIVE]");
      expect(result.content).toBe("[REDACTED_SENSITIVE]");
      expect(result.safeMeta).toBe("navigation-click");
    });
  });

  describe("Breadcrumbs Management", () => {
    it("records sanitized breadcrumbs up to the 50 cap", () => {
      initSentry({ enabled: true });

      for (let i = 0; i < 60; i++) {
        addBreadcrumb({
          category: "ui.click",
          message: `Button clicked user${i}@mail.com`,
        });
      }

      const breadcrumbs = getBreadcrumbs();
      expect(breadcrumbs.length).toBe(50);
      expect(breadcrumbs[0].message).toContain("[REDACTED_EMAIL]");
    });

    it("clears breadcrumbs on demand", () => {
      addBreadcrumb({ category: "navigation", message: "/chat" });
      expect(getBreadcrumbs().length).toBe(1);
      clearBreadcrumbs();
      expect(getBreadcrumbs().length).toBe(0);
    });
  });

  describe("Error Capture & Transmission", () => {
    it("does not transmit when DSN is absent or disabled", () => {
      const fetchSpy = vi.spyOn(globalThis, "fetch");
      initSentry({ enabled: false });

      captureException(new Error("Test error"));
      expect(fetchSpy).not.toHaveBeenCalled();
    });

    it("transmits scrubbed payload to Sentry endpoint when DSN is valid", async () => {
      const fetchSpy = vi
        .spyOn(globalThis, "fetch")
        .mockResolvedValue(new Response("ok", { status: 200 }));

      const fakeDsn = "https://public_key_abc@sentry.io/123456";
      initSentry({ dsn: fakeDsn, enabled: true, environment: "production" });

      const error = new Error("Failed to process payment for user@example.com");
      captureException(error, { route: "/profile" });

      expect(fetchSpy).toHaveBeenCalledOnce();
      const [url, requestInit] = fetchSpy.mock.calls[0];

      expect(url).toContain("sentry.io/api/123456/store/");
      expect(url).toContain("sentry_key=public_key_abc");

      const body = JSON.parse(requestInit?.body as string);
      expect(body.exception.values[0].value).toBe(
        "Failed to process payment for [REDACTED_EMAIL]",
      );
      expect(body.environment).toBe("production");
    });
  });
});
