# Production Deployment & Client Telemetry Specification

> **Owner:** Dimple (Frontend + Deployment · Database)  
> **Task:** S2-DIM-7 · **Issue:** #222  
> **Requirements:** NFR-03 (Security & Zero-PII), NFR-05 (Reliability & Monitoring), DR-01 (Medical Disclaimer), DR-02 (Emergency Override), DR-06 (Data Minimization)  
> **Date:** November 2026  
> **Target Application:** AI-Based Symptom Checker Web Application & PWA (`client/`)  

---

## 1. Executive Summary

This document specifies the production hosting, security header configuration, and client-side error telemetry architecture implemented for the AI-Based Symptom Checker frontend on **Vercel** (`client/vercel.json`) with **Sentry client monitoring** (`client/src/services/sentry.ts` and `client/src/components/layout/ErrorBoundary.tsx`).

As a clinical decision-support Progressive Web App (PWA) operating under India's **DPDP Act 2023** and medical-safety invariants (DR-01, DR-02, DR-06), the deployment architecture guarantees:
1. **Strict Content-Security-Policy (CSP) & Security Headers (NFR-03):** Prevents cross-site scripting (XSS), clickjacking, MIME-confusion, and unauthorized third-party network egress.
2. **Deterministic SPA Routing & API Reverse Proxying (NFR-08):** Routes client navigation through `/index.html` while proxying `/api/*` requests to the staging backend.
3. **Resilient Error Boundaries with Graceful Degradation (NFR-05):** Traps unhandled React crashes, prevents blank screens, and offers one-click assessment restart with emergency 112 guidance.
4. **Zero-PII Client Telemetry (NFR-03, DR-06):** Redacts email addresses, passwords, auth bearer tokens, session token hashes, and health symptom text prior to Sentry transmission.

---

## 2. Vercel Production Configuration Audit (`client/vercel.json`)

The production configuration file at `client/vercel.json` enforces transport security, resource isolation, and routing.

### 2.1 Routing Architecture

```json
"rewrites": [
  {
    "source": "/api/(.*)",
    "destination": "STAGING_API_ORIGIN/api/$1"
  },
  {
    "source": "/(.*)",
    "destination": "/index.html"
  }
]
```

- **API Reverse Proxy (`/api/*`):** Proxies all API calls through the Vercel edge to the backend target (`STAGING_API_ORIGIN`). Avoids cross-origin browser credential restrictions and keeps API communication on the same domain origin.
- **SPA Fallback (`/(.*)`):** Rewrites deep client links (e.g., `/chat`, `/profile`, `/privacy`, `/history`) back to `/index.html`, allowing React Router (`client/src/app/router.tsx`) to manage route resolution without 404 errors.

### 2.2 Content-Security-Policy (CSP) Directives (NFR-03)

| Directive | Configured Value | Security Justification |
|---|---|---|
| `default-src` | `'self'` | Disallows loading external content by default. |
| `script-src` | `'self'` | Disallows inline scripts (`'unsafe-inline'`) and untrusted external CDNs. Only compiled application bundles execute. |
| `style-src` | `'self' 'unsafe-inline'` | Permits application CSS and Tailwind inline utility classes while restricting external fonts or style sheets. |
| `img-src` | `'self' data: blob:` | Permits application SVG icons, local assets, and in-memory object URLs created during visual symptom selection. |
| `connect-src` | `'self' https://*.sentry.io https://*.ingest.sentry.io https://api.symptomchecker.dev` | Restricts network requests strictly to application APIs, backend endpoints, and authorized Sentry telemetry ingests. |
| `font-src` | `'self'` | Disallows external web font downloads; relies on self-hosted Inter and system fonts. |
| `object-src` | `'none'` | Completely disables legacy plugins (Flash, Java, Silverlight). |
| `base-uri` | `'self'` | Restricts the `<base>` tag target to mitigate base-jacking attacks. |
| `form-action` | `'self'` | Prevents form submissions from targeting external endpoints. |
| `frame-ancestors` | `'none'` | Strictly disallows embedding the application inside `<iframe>` tags (prevents clickjacking). |

### 2.3 Additional Production Security Headers (NFR-03)

| Header Name | Configured Value | Compliance Purpose |
|---|---|---|
| **Strict-Transport-Security** | `max-age=63072000; includeSubDomains; preload` | Enforces HTTPS for 2 years with preloading support across all subdomains. |
| **X-Content-Type-Options** | `nosniff` | Disables browser MIME-type sniffing. |
| **X-Frame-Options** | `DENY` | Anti-clickjacking defense alongside CSP `frame-ancestors`. |
| **Referrer-Policy** | `strict-origin-when-cross-origin` | Protects privacy by omitting path/query data across cross-origin requests. |
| **Permissions-Policy** | `camera=(), microphone=(), geolocation=()` | Hardware isolation: explicitly turns off camera, microphone, and geolocation APIs. |
| **Cross-Origin-Opener-Policy** | `same-origin` | Isolates top-level browsing context from malicious cross-origin popups. |
| **Cross-Origin-Resource-Policy** | `same-origin` | Disallows external sites from reading static assets directly. |

### 2.4 Git Deployment Guardrails

```json
"git": {
  "deploymentEnabled": {
    "main": false,
    "develop": false
  }
}
```
Automatic pushes from GitHub branches are disabled in Vercel to guarantee that deployments occur **only after GitHub Actions CI verification passes** (PR Policy + Automated Test Suite).

---

## 3. Client Telemetry & Error Boundary Architecture

### 3.1 DPDP Act 2023 & Zero-PII Compliance Pipeline (`sentry.ts`)

Medical-safety and data protection rules mandate that personal health information is never transmitted to third-party loggers or error monitoring platforms.

The client telemetry pipeline enforces a two-tier redaction algorithm before any error event leaves the browser:

```
[ Uncaught Error / React Crash ]
               │
               ▼
   1. String PII Scrubber (Regex)
      ├── Emails → [REDACTED_EMAIL]
      ├── JWT Tokens → [REDACTED_JWT]
      ├── Bearer Tokens → Bearer [REDACTED_TOKEN]
      └── 64-char Hashes → [REDACTED_HASH]
               │
               ▼
   2. Object Metadata Scrubber
      ├── Strip health keys: symptoms, message, content, chronic_conditions
      └── Strip credential keys: password, password_hash, token, user_id
               │
               ▼
   3. Sentry Envelope Constructor (sentry.ts)
      ├── Ingests scrubbed message & stack frames
      ├── Ingests last 50 sanitized UI breadcrumbs
      └── Transmits via fetch() with keepalive: true
```

### 3.2 React Error Boundary (`ErrorBoundary.tsx`)

To prevent the application from crashing to a blank screen during runtime errors (NFR-05 Graceful Degradation):
1. `<ErrorBoundary>` wraps the top-level provider tree in `client/src/app/providers.tsx`.
2. Catches unhandled lifecycle and render errors via `componentDidCatch`.
3. Reports the incident to Sentry with scrubbed component stack metadata.
4. Renders an accessible, reassuring fallback card with:
   - "Something went wrong" header.
   - Non-technical explanation assuring the user that health data remains secure.
   - "Start New Assessment" button (safely navigates back to `/`).
   - "Try Again" state reset button.
   - Prominent **112 (Unified Emergency)** escalation guidance (DR-02).
   - Mandatory medical disclaimer (DR-01).

---

## 4. Automated Test Verification Matrix

| Test Suite | File Path | Assertions Verified | Status |
|---|---|---|---|
| **Sentry Telemetry** | `client/src/services/sentry.test.ts` | PII regex scrubbing, object key redaction, breadcrumb capping (50), Sentry store URL generation, fetch transmission. | **PASS** (8 tests) |
| **Error Boundary** | `client/src/components/layout/ErrorBoundary.test.tsx` | Clean child rendering, crash interception, fallback UI display, Sentry capture trigger, state recovery. | **PASS** (3 tests) |
| **Vercel Config** | `client/src/test/vercelConfig.test.ts` | `/api` rewrite presence, SPA fallback, CSP directives, HSTS headers, clickjacking protection, Git deploy flags. | **PASS** (10 tests) |

---

## 5. Conclusion

With these implementations, the AI-Based Symptom Checker frontend satisfies **NFR-03 (Security)** and **NFR-05 (Reliability & Monitoring)**. The production deployment is locked down with strict security headers, protected by an automated error recovery boundary, and instrumented with zero-PII Sentry error telemetry.
