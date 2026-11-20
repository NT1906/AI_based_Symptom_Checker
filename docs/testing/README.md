# Testing and Quality Assurance Documentation

This directory centralizes formal test plans, automated API test specifications, manual browser acceptance matrices, and execution evidence across sprints.

---

## Active Test Suites & Evidence Directories

| Suite / Feature Area | Task ID & Issue | Author | Coverage Scope | Evidence & Specifications |
|---|---|---|---|---|
| **Security API Suite** | `S2-NIT-8` ([#336](https://github.com/NT1906/AI_based_Symptom_Checker/issues/336)) | Nishith Tandel (`@NT1906`) | Authorization/IDOR, CSRF tokens, prompt injection & jailbreaks, AI upstream failure modes (502/503/504), exception shielding | [Security API Test Cases](security-api/test-cases.md)<br>• [Evidence Screenshots](security-api/screenshots/)<br>• [Pytest Execution Log](security-api/pytest-output.txt) |
| **Assessment Flow Suite** | `S2-DAR-12` ([#332](https://github.com/NT1906/AI_based_Symptom_Checker/issues/332))<br>`S2-DAR-13` ([#333](https://github.com/NT1906/AI_based_Symptom_Checker/issues/333)) | Darshil Kanani (`@darshil2501`) | State transitions (`START → CLARIFYING → CONFIRMING → READY → ANALYZING → COMPLETED`), clarification limits, symptom correction, disclaimer enforcement | [Assessment Flow Test Cases](assessment-flow/test-cases.md)<br>• [Evidence Screenshots](assessment-flow/screenshots/)<br>• [Pytest Execution Log](assessment-flow/pytest-output.txt) |
| **Accounts, Profile, History & Deletion Suite** | `S2-KAV-8` ([#334](https://github.com/NT1906/AI_based_Symptom_Checker/issues/334)) | Kavya Nakrani (`@KAVY-OP`) | Registration/login lifecycle, password change, profile demographic context, history pagination & IDOR isolation, DPDP data export & cascading erasure | [Accounts & Deletion Test Cases](accounts-profile-history-deletion/test-cases.md)<br>• [Evidence Screenshots](accounts-profile-history-deletion/screenshots/)<br>• [Pytest Execution Log](accounts-profile-history-deletion/pytest-output.txt) |
| **Safety & Condition-Prediction Result Suite** | `S2-NIS-23` ([#330](https://github.com/NT1906/AI_based_Symptom_Checker/issues/330))<br>`S2-NIS-24` ([#331](https://github.com/NT1906/AI_based_Symptom_Checker/issues/331)) | Nisarg (`@NT1906`) | Red-flag decision table (URGENT + 112), severity boundaries, uncertainty only raises risk, disclaimer and no raw percentages, confidence labels, ranking and "why" lines, 1 / 12 / unknown symptoms, repeatability, referral without personal data; manual result-page checks (urgent alert, disclaimer on screen and PDF, map referral, light / dark / mobile) | [Safety Test Cases](safety/test-cases.md)<br>• [Evidence Screenshots](safety/screenshots/)<br>• [Pytest Execution Log](safety/pytest-output.txt) |

---

## Quick Execution Reference

### 1. Security API Integration Tests (`S2-NIT-8`)
```bash
# From repository root or server/ directory:
pytest server/tests/integration/test_security_api.py -v --tb=short
```
* **Coverage:** 16 automated tests covering Authorization (4), CSRF (4), Prompt Injection (4), and AI Gateway Degradation (4).
* **Test Report & Traceability:** [`docs/testing/security-api/test-cases.md`](security-api/test-cases.md)

### 2. Assessment Flow Integration Tests (`S2-DAR-12`)
```bash
# From repository root or server/ directory:
pytest server/tests/integration/test_assessment_flow_api.py -v --tb=short
```
* **Coverage:** 17 automated tests covering full lifecycle state transitions, guard conditions, and disclaimer presence.
* **Test Report & Traceability:** [`docs/testing/assessment-flow/test-cases.md`](assessment-flow/test-cases.md)

### 3. Accounts, Profile, History & Deletion Integration Tests (`S2-KAV-8`)
```bash
# From repository root or server/ directory:
pytest server/tests/integration/test_accounts_profile_history_deletion_api.py -v --tb=short
```
* **Coverage:** 18 automated tests covering Authentication Lifecycle & Password Change (6), Clinical Profile (5), History Pagination & IDOR (4), and DPDP Data Export & Erasure (3).
* **Test Report & Traceability:** [`docs/testing/accounts-profile-history-deletion/test-cases.md`](accounts-profile-history-deletion/test-cases.md)

### 4. Safety & Condition-Prediction Result Integration Tests (`S2-NIS-23`)
```bash
# From the server/ directory:
pytest tests/integration/test_safety_api.py tests/integration/test_prediction_result_api.py -v
```
* **Coverage:** 20 automated tests: safety decision table and boundaries (11) and condition prediction / result content (9). 19 pass; TC-SAF-A-17 is a known defect ([#348](https://github.com/NT1906/AI_based_Symptom_Checker/issues/348)) kept as a strict `xfail`.
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
| Accounts, profile, history & deletion | Kavya | 18 | manual: [#335](https://github.com/NT1906/AI_based_Symptom_Checker/issues/335) in progress | 18 | 18 | 0 | 100 % | FR-01, FR-02, NFR-03, NFR-04, DR-02, DR-06 | [accounts-profile-history-deletion/](accounts-profile-history-deletion/test-cases.md) · 19 PNG |
| Security | Nishith | 16 | manual: [#337](https://github.com/NT1906/AI_based_Symptom_Checker/issues/337) in progress | 16 | 16 | 0 | 100 % | NFR-03, NFR-05, NFR-10, DR-01, DR-02, DR-05 | [security-api/](security-api/test-cases.md) · 17 PNG |
| Safety & condition-prediction result | Nisarg | 20 | 12 | 32 | 31 | 1 ([#348](https://github.com/NT1906/AI_based_Symptom_Checker/issues/348)) | 96.9 % | DR-01, DR-02, FR-05, FR-06, FR-07, FR-08, FR-22, FR-23, NFR-07 | [safety/](safety/test-cases.md) · 36 PNG |
| **Total** | 4 testers | **71** | **26** | **97** | **96** | **1** | **99.0 %** | 24 requirement IDs (see below) | **104 PNG** + 4 pytest logs |

When Kavya's and Nishith's manual suites (#335, #337) merge, their authors add their manual counts to this table, as each area has done so far.

**Requirements covered (all areas):** FR-01, FR-02, FR-03, FR-04, FR-05, FR-06, FR-07, FR-08, FR-16, FR-19, FR-20, FR-21, FR-22, FR-23, FR-25, NFR-03, NFR-04, NFR-05, NFR-07, NFR-10, DR-01, DR-02, DR-05, DR-06 and idea §7 / §9 / §10 rules.

**Defects found:** 1, [#348](https://github.com/NT1906/AI_based_Symptom_Checker/issues/348): analysis fails (422) and the assessment stays in `ANALYZING` when none of the confirmed symptoms is known to the model (found by TC-SAF-A-17; open).

### Testing methods used

No new software was installed: automated tests use pytest + httpx (already in the server's dev dependencies), manual tests use the browser.

| Method | Where it is used |
|---|---|
| Black-box API integration testing (pytest + httpx, mock AI provider) | all four areas: `server/tests/integration/test_*_api.py` |
| Manual system / acceptance testing in the browser | assessment flow (TC-FLOW-M), safety result page (TC-SAF-M) |

### Test-design techniques used

| Technique | Examples |
|---|---|
| State transition testing | assessment states START → CLARIFYING → CONFIRMING → READY → ANALYZING → COMPLETED, invalid transitions rejected (assessment flow) |
| Decision table | red-flag rules × expected risk tier (safety, TC-SAF-A-01 to 10) |
| Boundary value analysis | clarification cap of 3 questions (flow); chest-pain severity threshold, 1 and 12 symptoms (safety); pagination limits (accounts) |
| Equivalence partitioning | confidence labels Likely / Possible / Less likely; one result per risk tier; valid vs invalid inputs (accounts) |
| Error guessing / negative testing | unknown symptoms, unstated severity, personal data in results (safety); IDOR, CSRF, prompt injection, AI failures (security) |
| Repeatability | same symptoms give the same result (safety, automated and manual) |
| Compatibility | light / dark theme, mobile width, print to PDF (safety manual) |

### Where everything is

- [assessment-flow/](assessment-flow/test-cases.md): Darshil, S2-DAR-12 / S2-DAR-13
- [accounts-profile-history-deletion/](accounts-profile-history-deletion/test-cases.md): Kavya, S2-KAV-8 (S2-KAV-9 manual in progress)
- [security-api/](security-api/test-cases.md): Nishith, S2-NIT-8 (S2-NIT-9 manual in progress)
- [safety/](safety/test-cases.md): Nisarg, S2-NIS-23 / S2-NIS-24

Each folder has `test-cases.md` (metrics, test-case table), `screenshots/` and, for automated suites, `pytest-output.txt`.
