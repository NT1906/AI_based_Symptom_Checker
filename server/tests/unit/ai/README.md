# AI Gateway, Missing-Information & Clarification Tests

**Owner:** Nishith · **Task:** S1-NIT-2 · **Issue:** #31 · **Requirements:** FR-04, FR-19, FR-20, NFR-05

This suite validates the `AiGateway` protocol, `MockAiProvider`, missing-information detection engine, clarification question generation, and versioned prompt files. All tests run completely offline without an external API key.

## Coverage Areas

* **`test_missing_info.py`**: Validates deterministic detection of missing duration, unknown severity, absent anatomical body site, and missing onset for safety-critical symptoms. Verifies clinical triage priority ordering (red flags first).
* **`test_clarification.py`**: Enforces the strict 3-question maximum turn cap (FR-20), question deduplication (`already_asked`), safe non-diagnostic medical phrasing, and question type classification.
* **`test_mock_provider.py`**: Comprehensive coverage of extraction heuristics, duration parsing, body site mapping, negation exclusions, and testing hooks.
* **`test_gateway.py`**: Validates the `AiGateway` protocol interface, default factory provider resolution, and presence/formatting of versioned prompts (`extraction.v1.txt`, `clarification.v1.txt`, `clarification.v2.txt`).

## Running Tests

From `server/`:

```powershell
pytest tests/unit/ai -v
```
