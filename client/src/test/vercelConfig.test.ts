/**
 * @file Automated configuration test verifying production Vercel deployment rules and security headers.
 * Owner: Dimple · Task: S2-DIM-7 · Requirements: NFR-03, NFR-05
 */

import { describe, expect, it } from "vitest";
import vercelConfig from "../../vercel.json";

interface VercelConfig {
  rewrites?: Array<{ source: string; destination: string }>;
  headers?: Array<{
    source: string;
    headers: Array<{ key: string; value: string }>;
  }>;
  git?: {
    deploymentEnabled?: {
      main?: boolean;
      develop?: boolean;
    };
  };
}

describe("Vercel Production Configuration (vercel.json)", () => {
  const config = vercelConfig as unknown as VercelConfig;

  describe("Routing & Rewrites (SPA Fallback and API Proxy)", () => {
    it("proxies /api requests to staging backend origin", () => {
      const apiRewrite = config.rewrites?.find((r) =>
        r.source.includes("/api/"),
      );
      expect(apiRewrite).toBeDefined();
      expect(apiRewrite?.destination).toContain("/api/$1");
    });

    it("includes SPA catch-all rewrite to /index.html", () => {
      const spaRewrite = config.rewrites?.find((r) => r.source === "/(.*)");
      expect(spaRewrite).toBeDefined();
      expect(spaRewrite?.destination).toBe("/index.html");
    });
  });

  describe("Security Headers & CSP (NFR-03)", () => {
    const globalHeaders =
      config.headers?.find((h) => h.source === "/(.*)")?.headers || [];

    const getHeader = (name: string) =>
      globalHeaders.find(
        (h) => h.key.toLowerCase() === name.toLowerCase(),
      )?.value;

    it("enforces Content-Security-Policy (CSP) restricting scripts and connections", () => {
      const csp = getHeader("Content-Security-Policy");
      expect(csp).toBeDefined();
      expect(csp).toContain("default-src 'self'");
      expect(csp).toContain("script-src 'self'");
      expect(csp).toContain("connect-src");
      expect(csp).toContain("sentry.io");
      expect(csp).toContain("frame-ancestors 'none'");
    });

    it("enforces Strict-Transport-Security (HSTS)", () => {
      const hsts = getHeader("Strict-Transport-Security");
      expect(hsts).toBeDefined();
      expect(hsts).toContain("max-age=63072000");
      expect(hsts).toContain("includeSubDomains");
      expect(hsts).toContain("preload");
    });

    it("enforces X-Content-Type-Options: nosniff", () => {
      expect(getHeader("X-Content-Type-Options")).toBe("nosniff");
    });

    it("enforces X-Frame-Options: DENY to prevent clickjacking", () => {
      expect(getHeader("X-Frame-Options")).toBe("DENY");
    });

    it("enforces strict Referrer-Policy", () => {
      expect(getHeader("Referrer-Policy")).toBe("strict-origin-when-cross-origin");
    });

    it("enforces Permissions-Policy disabling camera, mic, and geolocation", () => {
      const permissions = getHeader("Permissions-Policy");
      expect(permissions).toBeDefined();
      expect(permissions).toContain("camera=()");
      expect(permissions).toContain("microphone=()");
      expect(permissions).toContain("geolocation=()");
    });

    it("enforces Cross-Origin policies for resource isolation", () => {
      expect(getHeader("Cross-Origin-Opener-Policy")).toBe("same-origin");
      expect(getHeader("Cross-Origin-Resource-Policy")).toBe("same-origin");
    });
  });

  describe("Git Deployment Safeguards", () => {
    it("disables automatic Vercel deploys of main and develop branches (managed via GitHub Actions)", () => {
      expect(config.git?.deploymentEnabled?.main).toBe(false);
      expect(config.git?.deploymentEnabled?.develop).toBe(false);
    });
  });
});
