# Testing and Quality Assurance Documentation

This directory centralizes formal test plans, automated API test specifications, manual browser acceptance matrices, and execution evidence across sprints.

---

## Active Test Suites & Evidence Directories

| Suite / Feature Area | Task ID & Issue | Author | Coverage Scope | Evidence & Specifications |
|---|---|---|---|---|
| **Security API Suite** | `S2-NIT-8` ([#336](https://github.com/NT1906/AI_based_Symptom_Checker/issues/336)) | Nishith Tandel (`@NT1906`) | Authorization/IDOR, CSRF tokens, prompt injection & jailbreaks, AI upstream failure modes (502/503/504), exception shielding | [Security API Test Cases](security-api/test-cases.md)<br>• [Evidence Screenshots](security-api/screenshots/)<br>• [Pytest Execution Log](security-api/pytest-output.txt) |
| **Assessment Flow Suite** | `S2-DAR-12` ([#332](https://github.com/NT1906/AI_based_Symptom_Checker/issues/332))<br>`S2-DAR-13` ([#333](https://github.com/NT1906/AI_based_Symptom_Checker/issues/333)) | Darshil Kanani (`@darshil2501`) | State transitions (`START → CLARIFYING → CONFIRMING → READY → ANALYZING → COMPLETED`), clarification limits, symptom correction, disclaimer enforcement | [Assessment Flow Test Cases](assessment-flow/test-cases.md)<br>• [Evidence Screenshots](assessment-flow/screenshots/)<br>• [Pytest Execution Log](assessment-flow/pytest-output.txt) |
| **Accounts, Profile, History & Deletion Suite** | `S2-KAV-8` ([#334](https://github.com/NT1906/AI_based_Symptom_Checker/issues/334)) | Kavya Nakrani (`@KAVY-OP`) | Registration/login lifecycle, password change, profile demographic context, history pagination & IDOR isolation, DPDP data export & cascading erasure | [Accounts & Deletion Test Cases](accounts-profile-history-deletion/test-cases.md)<br>• [Evidence Screenshots](accounts-profile-history-deletion/screenshots/)<br>• [Pytest Execution Log](accounts-profile-history-deletion/pytest-output.txt) |
| **Safety & Condition-Prediction Result Suite** | `S2-NIS-23` ([#330](https://github.com/NT1906/AI_based_Symptom_Checker/issues/330)) | Nisarg (`@NT1906`) | Red-flag decision table (URGENT + 112), severity boundaries, uncertainty only raises risk, disclaimer and no raw percentages, confidence labels, ranking and "why" lines, 1 / 12 / unknown symptoms, repeatability, referral without personal data | [Safety Test Cases](safety/test-cases.md)<br>• [Evidence Screenshots](safety/screenshots/)<br>• [Pytest Execution Log](safety/pytest-output.txt) |

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
* **Test Report & Traceability:** [`docs/testing/safety/test-cases.md`](safety/test-cases.md)

---

## Quality Metrics Summary

| Area | Automated Tests | Manual Scenarios | Pass Rate | Evidence Captures |
|---|---|---|---|---|
| **Security API (S2-NIT-8)** | 16 | N/A (Automated) | 100 % (16/16) | 17 PNG screenshots |
| **Assessment Flow (S2-DAR-12/13)** | 17 | 14 | 100 % (31/31) | 31 PNG screenshots |
| **Accounts & Data Rights (S2-KAV-8)** | 18 | N/A (Automated) | 100 % (18/18) | 19 PNG screenshots |
| **Safety & Prediction API (S2-NIS-23)** | 20 | N/A (Automated) | 95 % (19/20, 1 defect: #348) | 22 PNG screenshots |
| **Combined Quality Assurance** | **71** | **14** | **98.8 % (84/85)** | **89 verification artifacts** |
