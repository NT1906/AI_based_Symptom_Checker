# AI Gateway & Mock Provider Tests

**Owner:** Nishith · **Task:** S0-NIT-1 · **Issue:** #18

This suite validates the `AiGateway` protocol, `MockAiProvider`, schemas, and versioned prompt files. All tests run completely offline without an external API key.

## Running Tests

From `server/`:

```powershell
py -3.11 -m pytest tests/unit/ai -v
```
