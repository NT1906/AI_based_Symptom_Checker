# Testing and Quality Assurance Documentation

This directory centralizes formal test plans, automated API test specifications, manual browser acceptance matrices, and execution evidence across sprints.

---

## Active Test Suites & Evidence Directories

| Suite / Feature Area | Task ID & Issue | Author | Coverage Scope | Evidence & Specifications |
|---|---|---|---|---|
| **Security API Suite** | `S2-NIT-8` ([#336](https://github.com/NT1906/AI_based_Symptom_Checker/issues/336)) | Nishith Tandel (`@NT1906`) | Authorization/IDOR, CSRF tokens, prompt injection & jailbreaks, AI upstream failure modes (502/503/504), exception shielding | [Security API Test Cases](security-api/test-cases.md)<br>• [Evidence Screenshots](security-api/screenshots/)<br>• [Pytest Execution Log](security-api/pytest-output.txt) |
| **Assessment Flow Suite** | `S2-DAR-12` ([#332](https://github.com/NT1906/AI_based_Symptom_Checker/issues/332))<br>`S2-DAR-13` ([#333](https://github.com/NT1906/AI_based_Symptom_Checker/issues/333)) | Darshil Kanani (`@darshil2501`) | State transitions (`START → CLARIFYING → CONFIRMING → READY → ANALYZING → COMPLETED`), clarification limits, symptom correction, disclaimer enforcement | [Assessment Flow Test Cases](assessment-flow/test-cases.md)<br>• [Evidence Screenshots](assessment-flow/screenshots/)<br>• [Pytest Execution Log](assessment-flow/pytest-output.txt) |

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
pytest server/tests/integration/test_assessment_flow.py -v --tb=short
```
* **Coverage:** 17 automated tests covering full lifecycle state transitions, guard conditions, and disclaimer presence.
* **Test Report & Traceability:** [`docs/testing/assessment-flow/test-cases.md`](assessment-flow/test-cases.md)

---

## Quality Metrics Summary

| Area | Automated Tests | Manual Scenarios | Pass Rate | Evidence Captures |
|---|---|---|---|---|
| **Security API (S2-NIT-8)** | 16 | N/A (Automated) | 100 % (16/16) | 17 PNG screenshots |
| **Assessment Flow (S2-DAR-12/13)** | 17 | 14 | 100 % (31/31) | 31 PNG screenshots |
| **Combined Quality Assurance** | **33** | **14** | **100 %** | **48 verification artifacts** |
