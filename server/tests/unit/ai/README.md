# AI Gateway, Extraction Schemas & Mock Provider Tests

**Owner:** Nishith · **Task:** S1-NIT-1 · **Issue:** #30 · **Requirements:** FR-03, FR-17, NFR-05

This suite validates the `AiGateway` protocol, `MockAiProvider`, extraction Pydantic schemas (symptom, severity, duration, onset, body site), and versioned prompt files. All tests run completely offline without an external API key.


## Running Tests

From `server/`:

```powershell
py -3.11 -m pytest tests/unit/ai -v
```
