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

## Rules

- Never import or call real LLM or CV providers — use `AI_PROVIDER=mock`, `CV_PROVIDER=mock`.
- Use fixtures from `server/tests/conftest.py` (`async_client`, `assessment_create_payload`, etc.).
- Test names: `test_<behaviour_under_test>` (e.g., `test_result_contains_mandatory_disclaimer`).
