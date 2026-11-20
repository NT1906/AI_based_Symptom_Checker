# Integration Tests

**Owner:** Mohit (testing) · **Task:** S1-MOH-2 onwards

This folder contains pytest integration tests that wire the full server
stack (router → service → mock providers) using `httpx.AsyncClient`.

## Planned test files (Sprint 1)

| File | Task | Coverage |
|---|---|---|
| `test_assessment_flow.py` | S1-MOH-2 | Full API flow: create → message → confirm → analyze → result |
| `test_contracts.py` | S1-MOH-3 | Every endpoint response matches published Pydantic schema / OpenAPI |

## Planned test files (Sprint 2)

| File | Task | Coverage |
|---|---|---|
| `test_auth.py` | S2-MOH-1 | Auth, privacy, and deletion endpoints |
| `test_image_upload.py` | S2-MOH-2 | Image size, MIME, magic bytes, never-written-to-disk |
| `test_safety.py` | S2-MOH-3 | Urgent path, disclaimer, no raw percentages |

## Sprint 2 testing (S2-NIS-23, #330)

| File | Task | Coverage |
|---|---|---|
| `test_safety_api.py` | S2-NIS-23 | Red-flag decision table, severity boundary, uncertainty only raises risk, disclaimer, no raw percentages |
| `test_prediction_result_api.py` | S2-NIS-23 | Confidence labels, ranking and "why", 1 / 12 / unknown symptoms, repeatability, referral without personal data, guidance per tier |
| `safety_support.py`, `conftest.py` | S2-NIS-23 | `run_assessment()` helper and the isolated `safety_client` fixture used by the two files above |

Test cases and evidence: [`docs/testing/safety/test-cases.md`](../../../docs/testing/safety/test-cases.md).

## Rules

- Never import or call real LLM or CV providers — use `AI_PROVIDER=mock`, `CV_PROVIDER=mock`.
- Use fixtures from `server/tests/conftest.py` (`async_client`, `assessment_create_payload`, etc.).
- Test names: `test_<behaviour_under_test>` (e.g., `test_result_contains_mandatory_disclaimer`).
