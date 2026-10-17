# Privacy text scrubber

Owner: Harsh · Task: S1-HAR-2 · Issue #48 · NFR-04, DR-06

## Step 1 interface

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

This first patch does NOT wire the application or mark #48 complete. The next
step is an AiGateway-compatible privacy wrapper covering the message, history,
and strings nested in clarification state and already-asked questions, tested
with a recording fake provider. Nishith must coordinate wiring his factory to
the wrapper. All paths to any real provider must use the privacy boundary.
Do not collect names just to populate `known_names`.

Temperature, age, symptom duration, blood pressure, negation and short emergency
numbers have preservation tests. Tests use synthetic values only. Database
retention and consent are separate tasks and are not changed here.

## Verification

From `server/`: `python -m pytest tests/unit/privacy -q`, then the shared
`ruff check .`, `ruff format --check .`, `mypy app` and `pytest -q` gates.
