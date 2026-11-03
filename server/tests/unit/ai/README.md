# AI Gateway, Missing-Information & Clarification Tests

**Owner:** Nishith · **Task:** S1-NIT-3 · **Issue:** #32 · **Requirements:** FR-04, FR-19, FR-20, NFR-05

This suite validates the `AiGateway` protocol, `MockAiProvider`, `OpenAiProvider`, missing-information detection engine, clarification question generation, and versioned prompt files. All tests run completely offline with hermetic mocking (never calling real OpenAI endpoints or consuming tokens).

## Coverage Areas

* **`test_openai_provider.py`**: Validates `OpenAiProvider` conformance to `AiGateway`, Structured Outputs parsing, 2 automatic retries on transient errors (`429`, `5xx`, connection failure), timeout handling, fail-fast terminal errors (`401`, `400`), defensive clarification triggers, and 3-turn clarification ceiling.
* **`test_missing_info.py`**: Validates deterministic detection of missing duration, unknown severity, absent anatomical body site, and missing onset for safety-critical symptoms. Verifies clinical triage priority ordering (red flags first).
* **`test_clarification.py`**: Enforces the strict 3-question maximum turn cap (FR-20), question deduplication (`already_asked`), safe non-diagnostic medical phrasing, and question type classification.
* **`test_mock_provider.py`**: Comprehensive coverage of extraction heuristics, duration parsing, body site mapping, negation exclusions, and testing hooks.
* **`test_gateway.py`**: Validates the `AiGateway` protocol interface, default and openai factory provider resolution wrapped in `PrivacyAiGateway`, and presence/formatting of versioned prompts (`extraction.v1.txt`, `clarification.v1.txt`, `clarification.v2.txt`).

## Running Tests

From `server/`:

```powershell
pytest tests/unit/ai -v
```
