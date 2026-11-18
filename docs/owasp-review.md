# OWASP Top 10 Security Review & Verification Report

Owner: Vivek (Backend: API Foundation, Auth, Security) · Task: S2-VIV-5 · Issue: #205 · Requirement: NFR-03

---

## 1. Executive Summary

This document presents the comprehensive security review of the **AI-Based Symptom Checker** application against the **OWASP Top 10 (2021)** security risks and API Security standards.

The product operates as an **informational triage aid** and adheres to strict medical-safety and data protection invariants (`AI_RULES.md §2`, `docs/rules.md`, DPDP Act 2023, and `docs/api-contract.md`). The review demonstrates that the application's layered architecture systematically enforces defense-in-depth across authentication, authorization, cryptography, input validation, output sanitization, and audit logging.

| OWASP Category | Risk Level | Status | Architectural Defense & Mitigation |
|---|---|---|---|
| **A01: Broken Access Control** | High | **Passed** | Explicit ownership checks (`assert_ownership`), IDOR prevention, double-submit CSRF cookies, strict user isolation on `/profile` and `/assessments`. |
| **A02: Cryptographic Failures** | High | **Passed** | Argon2id password hashing with OWASP parameters (64 MB, 3 iterations, 4 parallelism); JWT HS256 with ≥ 32-character secret enforcement; HttpOnly, Secure, SameSite=Lax cookies. |
| **A03: Injection** | High | **Passed** | 100% parameterized queries via SQLAlchemy 2.0 ORM; prompt injection defense via `intent.py`; PII scrubbing before any LLM provider invocation. |
| **A04: Insecure Design** | High | **Passed** | 100% deterministic risk engine (zero LLM/random influence on risk tier); emergency helpline (112) for URGENT tier; non-negotiable medical disclaimer; uncertainty escalation. |
| **A05: Security Misconfiguration** | Medium | **Passed** | Security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, HSTS); CORS policy with exact origin validation; generic 500 error masking. |
| **A06: Vulnerable Components** | Medium | **Passed** | Pinned dependencies in `requirements.txt`; regular dependency audits; minimal Docker runtime image without dev/build dependencies. |
| **A07: Identification & Auth Failures** | High | **Passed** | Token family rotation with reuse detection; constant-time password & CSRF comparisons; rate limiting via `slowapi` on auth routes. |
| **A08: Software & Data Integrity** | Medium | **Passed** | Strict Pydantic v2 schemas with `extra="forbid"`; upload verification enforcing MIME and image magic bytes; images kept strictly in volatile memory. |
| **A09: Security Logging Failures** | Medium | **Passed** | Centralized structured logging with `X-Request-ID` correlation; zero-PII in application logs; immutable audit trail for clinical analysis and recommendations (`AuditService`, NFR-10). |
| **A10: Server-Side Request Forgery** | Low | **Passed** | Zero user-supplied outbound network requests; external LLM communication restricted to pre-configured provider endpoints. |

---

## 2. Detailed OWASP Top 10 Analysis

### A01: Broken Access Control
- **IDOR and Object-Level Authorization:**
  - Every assessment endpoint enforces ownership validation (`assert_ownership` in `server/app/services/assessment/orchestrator.py`).
  - Accessing an assessment owned by another user or another guest session returns `403 Forbidden` (`ASSESSMENT_ACCESS_DENIED` or `GUEST_SESSION_MISMATCH`).
  - User profiles (`/api/v1/profile`) are accessed exclusively via the authenticated user's ID (`current_user.id`), preventing horizontal privilege escalation.
- **CSRF Defense:**
  - State-changing HTTP endpoints require matching double-submit CSRF tokens via `X-CSRF-Token` header and `csrf_token` cookie, verified in constant time (`server/app/services/auth/security.py`).
- **CORS Controls:**
  - `server/app/middleware/cors.py` validates exact origins without wildcards or embedded credentials. Configured via `Settings.cors_allowed_origins`.

### A02: Cryptographic Failures
- **Password Storage:**
  - Passwords hashed using Argon2id (`argon2_cffi`) with OWASP-recommended parameters:
    - Memory cost: 65,536 KiB (64 MB)
    - Time cost: 3 iterations
    - Parallelism: 4 threads
    - Salt length: 16 bytes
- **Token Signing & Secret Hygiene:**
  - JWT tokens signed with HMAC-SHA256 (`HS256`).
  - `Settings` enforces `jwt_secret` length validation (minimum 32 characters in staging and production).
  - Short-lived access tokens (15 minutes) and 7-day refresh tokens.
- **Transport & Cookie Security:**
  - Cookies configured with `HttpOnly=True`, `SameSite="Lax"`, and `Secure=True` in production/staging.

### A03: Injection
- **SQL Injection:**
  - All database queries utilize SQLAlchemy 2.0 ORM expressions and parameterized statements (`server/app/repositories/`).
  - No raw SQL strings or user string interpolation are used anywhere in the codebase.
- **Prompt Injection:**
  - User inputs pass through the AI Gateway intent defense (`server/app/services/ai/intent.py` using `intent_defence.v1.txt`).
  - Prompt injections and adversarial overrides are flagged before reaching clinical models.
- **Log Injection:**
  - Structured logging via `structlog` emits serialized JSON logs, preventing CRLF/log-forgery injection attacks.

### A04: Insecure Design
- **Deterministic Medical Triage Guard:**
  - Per `AI_RULES.md §2`, the Risk Engine (`server/app/services/prediction/`) is 100% deterministic. LLMs and randomness cannot lower a risk tier or assign diagnoses.
  - Red-flag symptoms unconditionally trigger `URGENT` triage and display the emergency helpline (112).
  - Uncertainty (such as low model confidence or unparseable inputs) escalates to a safer (higher) tier.
  - Every clinical outcome enforces the mandatory disclaimer: *"This is not a medical diagnosis. Always consult a qualified healthcare professional."*

### A05: Security Misconfiguration
- **HTTP Security Headers:**
  - Applied via `SecurityHeadersMiddleware` (`server/app/middleware/security_headers.py`) on every response:
    - `X-Content-Type-Options: nosniff`
    - `X-Frame-Options: DENY`
    - `Referrer-Policy: no-referrer`
    - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
    - `Strict-Transport-Security: max-age=31536000` (in staging and production)
- **Error Information Leakage:**
  - Exception handlers in `server/app/core/errors.py` mask stack traces, database schemas, and internals, returning safe, uniform `ErrorResponse` envelopes.
  - Interactive documentation (`/docs`, `/redoc`) is disabled when `APP_ENV=production`.

### A06: Vulnerable and Outdated Components
- **Dependency Management:**
  - All direct dependencies are pinned in `server/requirements.txt` with locked versions.
  - Automated security scans in CI verify package integrity and detect known vulnerabilities (`pip-audit`, GitHub Dependabot).
  - Production Docker image uses multi-stage builds (`python:3.12-slim`), discarding build tools and dev dependencies.

### A07: Identification and Authentication Failures
- **Brute Force Protection:**
  - Rate limiting via `slowapi` restricts request rates on `/api/v1/auth/login`, `/api/v1/auth/register`, and `/api/v1/auth/refresh`.
- **Token Reuse Detection:**
  - Refresh tokens follow strict single-use rotation. If a previously consumed refresh token is presented, the entire token family is revoked to prevent session hijacking.
- **Timing Attack Resistance:**
  - Password and CSRF comparisons utilize constant-time comparison algorithms (`secrets.compare_digest`).

### A08: Software and Data Integrity Failures
- **Strict Input Validation:**
  - All incoming payloads validate against Pydantic v2 schemas with `extra="forbid"`.
  - Disallowed types, out-of-range values, and overlength strings are rejected with `422 Unprocessable Content`.
- **Upload Integrity:**
  - Image uploads (`POST /api/v1/assessments/{id}/images`) validate magic bytes against allowed MIME types (JPEG, PNG, WebP) up to 5 MB. Disguised executables (.exe, .html, .js) are rejected.
  - Uploaded images are processed strictly in volatile memory and never saved to disk or database (DR-06).

### A09: Security Logging and Monitoring Failures
- **Audit Logging (NFR-10):**
  - Dedicated `AuditService` (`server/app/services/audit/`) records every clinical analysis and recommendation event with pinned rule versions (`2026.1`), model versions, and triage outcomes.
  - Zero PII invariant: Audit logs and structured application logs strictly forbid and strip passwords, email addresses, names, tokens, and freeform symptom messages (`docs/logging-review.md`).
  - Correlation tracking via `X-Request-ID` header on all requests and log records.

### A10: Server-Side Request Forgery (SSRF)
- **External Network Access:**
  - The backend never initiates outbound HTTP requests to user-supplied URLs.
  - External network communication is restricted exclusively to pre-configured AI Gateway endpoints (e.g., OpenAI API, Google Cloud Vertex).
  - Image processing accepts raw uploaded bytes directly; no remote image URL fetching is implemented.

---

## 3. Verification & Automated Test Coverage

The automated OWASP security test suite resides in `server/tests/unit/core/test_owasp_security.py` and exercises:
1. `test_owasp_a01_idor_access_control`: Verifies 403 Forbidden on cross-user assessment access.
2. `test_owasp_a02_cryptographic_secret_strength`: Validates rejection of weak JWT secrets (< 32 chars).
3. `test_owasp_a02_cookie_security_flags`: Verifies `HttpOnly` and `SameSite` flags on authentication cookies.
4. `test_owasp_a03_sql_injection_defense`: Verifies SQL injection strings are safely escaped.
5. `test_owasp_a04_insecure_design_medical_disclaimer`: Verifies disclaimer and emergency number 112 cannot be bypassed.
6. `test_owasp_a05_security_headers_present`: Verifies presence of nosniff, DENY, and referrer-policy headers.
7. `test_owasp_a05_error_masking_no_stack_trace`: Verifies 500 errors never leak tracebacks or file paths.
8. `test_owasp_a07_auth_failure_expired_token`: Verifies expired tokens are rejected with 401.
9. `test_owasp_a07_csrf_protection_enforced`: Verifies missing or mismatched CSRF tokens return 401.
10. `test_owasp_a08_upload_magic_bytes_validation`: Verifies disguised executable uploads are rejected with 400.
11. `test_owasp_a09_zero_pii_in_audit_logs`: Verifies audit schema rejects forbidden PII keys.
12. `test_owasp_a10_no_arbitrary_outbound_requests`: Verifies absence of arbitrary URL fetching endpoints.

Run the test suite:
```bash
python -m pytest tests/unit/core/test_owasp_security.py -v
```
