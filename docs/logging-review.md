# Logging review

Owner: Harsh · Task S2-HAR-7 · Issue #210 · Requirement NFR-10

## Changes

Authentication events omit email addresses, direct account IDs and refresh-token
identifiers. Assessment events omit symptom names, age bands, chronic-condition
counts and account/guest ownership identifiers. State-machine guard events omit
free-text failure reasons. Provider errors record the exception class. Error
handlers record the route template instead of caller-supplied path segments.
Event names, status codes, approved assessment/request correlation and aggregate
operational counts remain available.

## Verification

The logging privacy regression captures the configured output sink while real
registration, duplicate registration, successful/failed login and an application
error execute with fictional data. It verifies that account values, symptom-like
path values and private errors are absent while event names and route templates
remain visible. A source regression check covers prohibited logging fields.

Run from server:
python -m pytest tests/unit/privacy/test_log_privacy.py tests/unit/core tests/unit/auth tests/unit/ai tests/unit/assessment -q

Result: 425 passed on the inspected develop base 4e0b628.

## Remaining verification

The audit-log storage work is on Nishith's unmerged nishith/159-audit-log branch.
Review its final persisted fields and retention after integration. Verify platform
log sinks and server exception handling on the actual staging environment. The
application changes span the auth, API, assessment and AI modules, so their owners
should review the logging-only edits before merge.
