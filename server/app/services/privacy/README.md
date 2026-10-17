# Privacy text scrubber

Owner: Harsh · Task: S1-HAR-2 · Issue #48 · NFR-04, DR-06

## Text interface

`from app.services.privacy.pii import scrub_pii`

`scrub_pii(text, known_names=()) -> str` runs locally, with no new dependency,
network calls, logging, file writes or retained name mapping. It replaces common
email addresses, 10–15 digit phone formats, PAN-shaped strings, Aadhaar-shaped
strings, UUIDs and explicitly labelled IDs with category placeholders.
Names introduced by `My name is`, `Name:` or `Patient name:` are supported,
as are exact names supplied through the optional trusted `known_names` tuple.
It normalizes compatibility characters and strips zero-width format controls.

Rejects non-string input, input over 20,000 characters (before or after
normalization), and invalid known-name configuration. Never fall back to raw
text when validation fails. This limit is local to this service; it does not
change an API schema or environment setting.

## Limits and remaining integration

This is a bounded rule-based baseline, not guaranteed anonymization. Arbitrary
unlabelled names, other languages, addresses, obfuscated emails and identifiers
outside the documented formats can remain. Name context can also over-redact;
known names can collide with clinical words. No guarantee of precision or recall
is made. Do not enable external LLM transmission solely because this function
returned a string. More representative evaluation and an agreed residual-risk
policy are needed before real-provider release.

## AI gateway boundary

`PrivacyAiGateway(provider, known_names=())` in `gateway.py` implements the
existing `AiGateway` interface. It scrubs the current message and history for
extraction, and copies/scrubs all nested JSON strings (including keys) plus
already-asked questions for clarification. Clinical scalar values are preserved.
Key collisions after redaction are rejected instead of silently losing data.

Each call is bounded to depth 12, 2,048 traversal nodes and 40,000 text characters
across all inputs. Strings and keys consume an extra traversal node for text
accounting. Each string also has the scrubber's 20,000-character limit.
Invalid values, cycles, non-finite floats and excessive payloads raise a generic
`AiValidationError` BEFORE the provider is called. No raw-input retry occurs.
Provider output and exceptions pass through unchanged; safe wording is #49.
This wrapper does not log or persist data. Optional known names remain in memory
for that wrapper's lifetime; use per-assessment instances for personal names,
not a globally cached wrapper. Serialize Pydantic state with
`model_dump(mode="json")`; models, bytes, tuples and arbitrary objects are rejected.

## Wiring request for Nishith and Darshil

The wrapper is tested but application wiring is NOT included. Ownership rules
reserve `services/ai/` for Nishith and assessment orchestration for Darshil.
Nishith should wrap each selected provider before returning it from the factory:

```python
from app.services.privacy.gateway import PrivacyAiGateway

# Return this from the factory's provider-selection branch.
return PrivacyAiGateway(MockAiProvider())
```

Use the same boundary around real providers when they are implemented. Darshil's
callers must use that returned gateway for BOTH extraction and clarification,
and handle `AiValidationError` as a safe input failure without raw-text fallback.
Do not add a second direct provider path. Factory wiring and a test of the actual
factory return value are required before claiming #48 is integrated/completed.
The concrete review request is to wrap the current MockAiProvider return sites
in `server/app/services/ai/factory.py` and add factory-level coverage in the AI
owner's tests. No provider selection, configuration or prompts need changing.

Do not collect names just to populate `known_names`.

Temperature, age, symptom duration, blood pressure, negation and short emergency
numbers have preservation tests. Tests use synthetic values only. Database
retention and consent are separate tasks and are not changed here.

## Verification

From `server/`: `python -m pytest tests/unit/privacy -q`, then the shared
`ruff check .`, `ruff format --check .`, `mypy app` and `pytest -q` gates.
