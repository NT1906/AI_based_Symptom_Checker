# Testing and Quality Assurance Documentation

This directory centralizes formal test plans, automated API test specifications, manual browser acceptance matrices, and execution evidence across sprints.

---

## Active Test Suites & Evidence Directories

| Suite / Feature Area | Task ID & Issue | Author | Coverage Scope | Evidence & Specifications |
|---|---|---|---|---|
| **Security Suite (API & DevTools)** | `S2-NIT-8` ([#336](https://github.com/NT1906/AI_based_Symptom_Checker/issues/336))<br>`S2-NIT-9` ([#337](https://github.com/NT1906/AI_based_Symptom_Checker/issues/337)) | Nishith Tandel (`@NT1906`) | Authorization/IDOR, CSRF tokens, prompt injection & jailbreaks, AI upstream failure modes (502/503/504), exception shielding, DevTools cookie/storage audits, HTTP security headers, DOM XSS sanitization, rate limiting UI feedback, and TLS certificate verification | [Security Test Cases](security-api/test-cases.md)<br>• [Evidence Screenshots (31 captures)](security-api/screenshots/)<br>• [Pytest Execution Log](security-api/pytest-output.txt)<br>• [Manual Evidence Script](security-api/generate_manual_evidence.py) |
| **Assessment Flow Suite** | `S2-DAR-12` ([#332](https://github.com/NT1906/AI_based_Symptom_Checker/issues/332))<br>`S2-DAR-13` ([#333](https://github.com/NT1906/AI_based_Symptom_Checker/issues/333)) | Darshil Kanani (`@darshil2501`) | State transitions (`START → CLARIFYING → CONFIRMING → READY → ANALYZING → COMPLETED`), clarification limits, symptom correction, disclaimer enforcement, and mobile viewports | [Assessment Flow Test Cases](assessment-flow/test-cases.md)<br>• [Evidence Screenshots (32 captures)](assessment-flow/screenshots/)<br>• [Pytest Execution Log](assessment-flow/pytest-output.txt)<br>• [Manual Evidence Script](assessment-flow/generate_manual_evidence.py) |
| **Accounts, Profile, History & Deletion Suite** | `S2-KAV-8` ([#334](https://github.com/NT1906/AI_based_Symptom_Checker/issues/334))<br>`S2-KAV-9` ([#335](https://github.com/NT1906/AI_based_Symptom_Checker/issues/335)) | Kavya Nakrani (`@KAVY-OP`) | Registration/login lifecycle, password change, profile demographic context, history pagination & IDOR isolation, DPDP data export & cascading erasure, manual browser acceptance across routes | [Accounts & Deletion Test Cases](accounts-profile-history-deletion/test-cases.md)<br>• [Evidence Screenshots (31 captures)](accounts-profile-history-deletion/screenshots/)<br>• [Pytest Execution Log](accounts-profile-history-deletion/pytest-output.txt) |
| **Safety & Condition-Prediction Result Suite** | `S2-NIS-23` ([#330](https://github.com/NT1906/AI_based_Symptom_Checker/issues/330))<br>`S2-NIS-24` ([#331](https://github.com/NT1906/AI_based_Symptom_Checker/issues/331)) | Nisarg (`@NT1906`) | Red-flag decision table (URGENT + 112), severity boundaries, uncertainty only raises risk, disclaimer and no raw percentages, confidence labels, ranking and "why" lines, 1 / 12 / unknown symptoms, repeatability, referral without personal data; manual result-page checks (urgent alert, disclaimer on screen and PDF, map referral, light / dark / mobile) | [Safety Test Cases](safety/test-cases.md)<br>• [Evidence Screenshots (36 captures)](safety/screenshots/)<br>• [Pytest Execution Log](safety/pytest-output.txt) |

---

## Quick Execution Reference

### 1. Security API Integration Tests (`S2-NIT-8`)
```bash
# From repository root or server/ directory:
pytest server/tests/integration/test_security_api.py -v --tb=short
```
* **Coverage:** 16 automated tests covering Authorization (4), CSRF (4), Prompt Injection (4), and AI Gateway Degradation (4).
* **Execution Log:** [`docs/testing/security-api/pytest-output.txt`](security-api/pytest-output.txt)

### 2. Security Browser & DevTools Evidence Captures (`S2-NIT-9`)
```bash
# From repository root:
python docs/testing/security-api/generate_manual_evidence.py
```
* **Coverage:** 14 Chrome DevTools manual security tests covering Cookies (`HttpOnly`/`Secure`/`SameSite`), Local/SessionStorage hygiene, HTTP Security Headers, In-Flight CSRF Header, CORS whitelisting, Console zero-leakage, DOM XSS sanitization, 500 error exception shielding, `/history` route guard, 112 emergency banner, rate-limiting feedback, multi-tab logout, and TLS 1.3 certificate validation.
* **Test Report & Traceability:** [`docs/testing/security-api/test-cases.md`](security-api/test-cases.md)

### 3. Assessment Flow Integration Tests (`S2-DAR-12`)
```bash
# From repository root or server/ directory:
pytest server/tests/integration/test_assessment_flow_api.py -v --tb=short
```
* **Coverage:** 17 automated tests covering full lifecycle state transitions, guard conditions, and disclaimer presence.
* **Test Report & Traceability:** [`docs/testing/assessment-flow/test-cases.md`](assessment-flow/test-cases.md)

### 4. Accounts, Profile, History & Deletion Integration & Manual Tests (`S2-KAV-8`, `S2-KAV-9`)
```bash
# From repository root or server/ directory:
pytest server/tests/integration/test_accounts_profile_history_deletion_api.py -v --tb=short
```
* **Coverage:** 18 automated tests covering Authentication Lifecycle & Password Change (6), Clinical Profile (5), History Pagination & IDOR (4), and DPDP Data Export & Erasure (3).
* **Manual Acceptance Suite (`S2-KAV-9`):** 12 browser acceptance test cases covering registration, login, session logout, password change, clinical profile form, persistence across reloads, profile reset, history listing, history detail with medical disclaimer, DPDP data export, permanent cascading erasure, and responsive/dark mode (TC-ACC-M-01 to 12), all 12 passed.
* **Test Report & Traceability:** [`docs/testing/accounts-profile-history-deletion/test-cases.md`](accounts-profile-history-deletion/test-cases.md)

### 5. Safety & Condition-Prediction Result Integration Tests (`S2-NIS-23`)
```bash
# From the server/ directory:
pytest tests/integration/test_safety_api.py tests/integration/test_prediction_result_api.py -v
```
* **Coverage:** 22 automated tests: safety decision table and boundaries (11), condition prediction / result content (9) and confirmation-card edits (2). All 22 pass. TC-SAF-A-17 found defect [#348](https://github.com/NT1906/AI_based_Symptom_Checker/issues/348) on the first run; it is fixed and the test passes. TC-SAF-A-21 and 22 are regression tests for [#351](https://github.com/NT1906/AI_based_Symptom_Checker/issues/351).
* **Manual (`S2-NIS-24`):** 12 browser test cases on the result page (TC-SAF-M-01 to 12), all passed.
* **Test Report & Traceability:** [`docs/testing/safety/test-cases.md`](safety/test-cases.md)

---

## Overall Testing Summary (for evaluation)

Owner of this summary: Nisarg · Task: S2-NIS-24 · Issue: [#331](https://github.com/NT1906/AI_based_Symptom_Checker/issues/331).
Numbers are taken from each area's `test-cases.md` metrics table.

### Combined metrics

| Area | Owner | Automated TC | Manual TC | Total TC | Passed | Failed | Pass rate | Requirements covered | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Assessment flow | Darshil | 17 | 14 | 31 | 31 | 0 | 100 % | FR-03, FR-04, FR-16, FR-19, FR-20, FR-21, FR-25, NFR-05, DR-01, DR-02 | [assessment-flow/](assessment-flow/test-cases.md) · 32 PNG |
| Accounts, profile, history & deletion | Kavya | 18 | 12 | 30 | 30 | 0 | 100 % | FR-01, FR-02, NFR-03, NFR-04, NFR-06, NFR-07, DR-01, DR-02, DR-06, idea §10 | [accounts-profile-history-deletion/](accounts-profile-history-deletion/test-cases.md) · 31 PNG |
| Security | Nishith | 16 | 14 | 30 | 30 | 0 | 100 % | NFR-03, NFR-05, NFR-10, DR-01, DR-02, DR-05 | [security-api/](security-api/test-cases.md) · 31 PNG |
| Safety & condition-prediction result | Nisarg | 22 | 12 | 34 | 34 | 0 (2 found and fixed: [#348](https://github.com/NT1906/AI_based_Symptom_Checker/issues/348), [#351](https://github.com/NT1906/AI_based_Symptom_Checker/issues/351)) | 100 % | DR-01, DR-02, FR-03, FR-05, FR-06, FR-07, FR-08, FR-16, FR-22, FR-23, NFR-07 | [safety/](safety/test-cases.md) · 41 PNG |
| **Total** | 4 testers | **73** | **52** | **125** | **125** | **0** | **100 %** | 25 requirement IDs (see below) | **135 PNG** + 4 pytest logs |

All four testing areas across automated API and manual browser / DevTools acceptance suites are complete.

**Requirements covered (all areas):** FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-08, FR-16, FR-19, FR-20, FR-21, FR-22, FR-23, FR-25, NFR-03, NFR-04, NFR-05, NFR-06, NFR-07, NFR-10, DR-01, DR-02, DR-05, DR-06 and idea §7 / §9 / §10 rules.

**Defects found:** 2, both fixed and re-tested. [#348](https://github.com/NT1906/AI_based_Symptom_Checker/issues/348): analysis failed (422) and the assessment stayed in `ANALYZING` when none of the confirmed symptoms was known to the model (found by TC-SAF-A-17). [#351](https://github.com/NT1906/AI_based_Symptom_Checker/issues/351): a symptom removed on the confirmation card was still analysed (found while re-testing #348 on the local app; now covered by TC-SAF-A-21 and 22).

### Testing methods used

No new software was installed: automated tests use pytest + httpx (already in the server's dev dependencies), manual tests use the browser.

| Method | Where it is used |
|---|---|
| Black-box API integration testing (pytest + httpx, mock AI provider) | all four areas: `server/tests/integration/test_*_api.py` |
| Manual system / acceptance testing in the browser & DevTools | assessment flow (TC-FLOW-M), safety result page (TC-SAF-M), accounts/profile (TC-ACC-M), security DevTools (TC-SEC-M) |

### Test-design techniques used

| Technique | Examples |
|---|---|
| State transition testing | assessment states START → CLARIFYING → CONFIRMING → READY → ANALYZING → COMPLETED, invalid transitions rejected (assessment flow) |
| Decision table | red-flag rules × expected risk tier (safety, TC-SAF-A-01 to 10) |
| Boundary value analysis | clarification cap of 3 questions (flow); chest-pain severity threshold, 1 and 12 symptoms (safety); pagination limits (accounts) |
| Equivalence partitioning | confidence labels Likely / Possible / Less likely; one result per risk tier; valid vs invalid inputs (accounts) |
| Error guessing / negative testing | unknown symptoms, unstated severity, personal data in results (safety); IDOR, CSRF, prompt injection, AI failures, DevTools security audits (security) |
| Repeatability | same symptoms give the same result (safety, automated and manual) |
| Compatibility | light / dark theme, mobile width, print to PDF (safety manual) |

### Where everything is

- [assessment-flow/](assessment-flow/test-cases.md): Darshil, S2-DAR-12 / S2-DAR-13
- [accounts-profile-history-deletion/](accounts-profile-history-deletion/test-cases.md): Kavya, S2-KAV-8 / S2-KAV-9
- [security-api/](security-api/test-cases.md): Nishith, S2-NIT-8 / S2-NIT-9
- [safety/](safety/test-cases.md): Nisarg, S2-NIS-23 / S2-NIS-24

Each folder has `test-cases.md` (metrics, test-case table), `screenshots/` and, for automated suites, `pytest-output.txt`.
