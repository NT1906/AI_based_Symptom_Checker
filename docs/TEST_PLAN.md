# Test Plan — AI-Based Symptom Checker (Group 14)

**Owner:** Mohit (Backend, Testing lead) · **Task:** S0-MOH-1 · **Requirements:** NFR-07, NFR-08

---

## 1. Purpose and Scope

This document defines the testing strategy, tooling, coverage targets, and responsibilities for the
AI-Based Symptom Checker project across all sprints. It applies to every layer of the stack:
backend (FastAPI), frontend (React PWA), and ML pipelines.

**In scope:** unit tests, integration tests, contract tests, E2E tests, safety tests, load tests,
and QA sign-off.

**Out of scope:** testing anything listed as out of scope in `docs/idea.md` (appointment booking,
doctor accounts, voice input, prescriptions, general chatbot).

---

## 2. Test Levels

### 2.1 Unit Tests

| Attribute | Value |
|---|---|
| **What** | One module, all external deps mocked |
| **Who** | Module owner (same PR as the feature code) |
| **Location** | `server/tests/unit/<module>/` · `client/src/**/<Component>.test.tsx` · `ml/*/tests/` |
| **Tools** | pytest + unittest.mock (server) · Vitest + RTL (client) · pytest (ML) |
| **Target** | ≥ 70% line coverage per module (CI gate from Sprint 2) |

Each public function, route, component, and hook must have at minimum:
- A happy-path case
- At least one edge/boundary case
- At least one failure/error case

### 2.2 Integration Tests

| Attribute | Value |
|---|---|
| **What** | Multiple real layers wired together (router → service → repository), external services mocked |
| **Who** | Mohit |
| **Location** | `server/tests/integration/` |
| **Tools** | pytest + httpx `AsyncClient` + SQLite in-memory (or test Postgres) |
| **Target** | Every assessment API endpoint and all state transitions must have integration coverage |

Integration tests never call real LLM, CV, map, or Hugging Face APIs.
Use `AI_PROVIDER=mock`, `CV_PROVIDER=mock`, and dependency overrides.

### 2.3 Contract Tests

| Attribute | Value |
|---|---|
| **What** | Every API endpoint's response schema is validated against the published Pydantic models and OpenAPI spec |
| **Who** | Mohit |
| **Location** | `server/tests/integration/test_contracts.py` |
| **Tools** | pytest + httpx + `openapi-spec-validator` |
| **Target** | 100% of published endpoints have a contract test |

### 2.4 End-to-End (E2E) Tests

| Attribute | Value |
|---|---|
| **What** | Full user journeys through the browser against the locally running full stack |
| **Who** | Mohit (core flows) · Rutva (CD smoke tests) · Mann (regression matrix) |
| **Location** | `tests/e2e/` |
| **Tools** | Playwright (TypeScript) |
| **Target** | Happy path, urgent path, and restart flow must pass before every sprint review |

### 2.5 Safety and Security Tests

| Attribute | Value |
|---|---|
| **What** | Red-flag → URGENT path, disclaimer presence, no raw percentages in responses; auth, cross-user access, oversized input |
| **Who** | Mohit |
| **Location** | `server/tests/integration/test_safety.py`, `server/tests/integration/test_auth.py` |
| **Tools** | pytest + httpx |
| **Target** | Every medical-safety rule in `AI_RULES.md §2` has at least one test |

### 2.6 Load Tests

| Attribute | Value |
|---|---|
| **What** | Concurrent requests to staging (Sprint 3) |
| **Who** | Mohit |
| **Location** | `tests/load/` (Sprint 3) |
| **Tools** | Locust (preferred) or Artillery |
| **NFR** | NFR-02: p95 result time ≤ 5 s at target concurrency |

---

## 3. Tooling Summary

| Layer | Framework | Assertion | Mocking | Coverage |
|---|---|---|---|---|
| Backend unit | pytest | pytest assert | `unittest.mock`, `dependency_overrides` | pytest-cov |
| Backend integration | pytest + httpx | pytest assert | Mock providers, SQLite/test Postgres | pytest-cov |
| Frontend | Vitest + RTL | expect (Vitest) | MSW (fetch mocks) | Vitest coverage (v8) |
| E2E | Playwright (TS) | `expect` (Playwright) | Full stack running locally | — |
| ML | pytest | pytest assert | Tiny fixtures, no training in CI | pytest-cov |

---

## 4. Coverage Targets

| Layer | Minimum Line Coverage | Gate Enforced |
|---|---|---|
| `server/app/` | **70%** | Sprint 2 CI (pytest-cov, `--cov-fail-under=70`) |
| `client/src/` | **70%** | Sprint 2 CI (Vitest coverage with `--coverage`) |
| `ml/` | **60%** (light CI only) | Sprint 2 CI |

Coverage reports are uploaded as CI artifacts on every PR. Failures below the threshold block merge.

---

## 5. Test Data and Fixtures

- All test fixtures use **obviously fake data** (never real patient data).
- Example names: `"Alice Test"`, emails: `"test@example.invalid"`.
- Fake symptoms: `"test headache"`, `"test rash"`.
- Fake UUIDs: generated deterministically via `uuid.UUID(int=N)` for reproducibility.
- No real health data, images, or LLM responses are ever stored in the repository.

---

## 6. CI / CD Integration

```text
PR opened
  └── CI: ruff + mypy + pytest (with --cov) + docker build       [server]
  └── CI: lint + typecheck + vitest --coverage + build            [client]
  └── CI: ruff + pytest                                           [ml]
  └── PR policy: branch name, commit format, header check
Merge to develop
  └── Auto-deploy to staging
  └── Post-deploy smoke test (Playwright, owned by Rutva — S2-RUT-4)
Sprint 3
  └── Full E2E regression matrix (Rutva — S3-RUT-2)
  └── Load test run (Mohit — S3-MOH-1)
```

Coverage reports are published as **GitHub Actions artifacts** on every run (S2-MOH-4).

---

## 7. Safety-Critical Test Rules

These are non-negotiable (from `AI_RULES.md §2`):

1. **Red-flag symptoms always produce `URGENT`** — verified by `test_red_flag_always_urgent`.
2. **Disclaimer present in every result response** — contract test checks the `disclaimer` field.
3. **No raw percentages in any user-facing response** — integration test asserts the absence of
   `score`, `probability`, `percent` fields in result JSON.
4. **Uncertainty escalates risk** — integration test verifies low-confidence mock returns a
   higher tier, never `SELF_CARE`.
5. **Images are never written to disk or logged** — upload tests assert no temp files and no
   filename in log output.

---

## 8. Responsibilities by Sprint

| Sprint | Task ID | Deliverable |
|---|---|---|
| S0 | S0-MOH-1 | This document + `conftest.py` + Playwright scaffold |
| S1 | S1-MOH-1 | State machine unit tests (every valid/invalid transition) |
| S1 | S1-MOH-2 | Integration tests for the full assessment API flow |
| S1 | S1-MOH-3 | Contract tests: every endpoint vs published schemas / OpenAPI |
| S1 | S1-MOH-4 | Playwright E2E happy path |
| S2 | S2-MOH-1 | Auth, privacy, and deletion integration tests |
| S2 | S2-MOH-2 | Image upload API tests |
| S2 | S2-MOH-3 | Safety integration tests |
| S2 | S2-MOH-4 | 70% coverage gate in CI |
| S3 | S3-MOH-1 | Load test against staging |
| S3 | S3-MOH-2 | Authorization and abuse tests |
| S3 | S3-MOH-3 | Bug triage + release QA sign-off report |

---

## 9. Definition of Done (Tests)

A test task is done when:
1. All new test functions follow the naming convention `test_<behaviour>` (e.g., `test_escalates_to_urgent_on_severe_chest_pain`).
2. No real API keys, LLM calls, or patient data appear in any test.
3. CI passes on the PR (green `CI passed` check).
4. Coverage does not drop below the module target.
5. The change works on staging after the automatic deploy.
