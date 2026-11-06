# Models

Owner: Harsh, Kavya · Tasks: S0-HAR-1, S1-KAV-4 · Issues: #9, #37 · Requirements: FR-01, idea § 10

The SQLAlchemy models and shared metadata.

Import `Base`, `User`, `Consent`, `Assessment`, `Message`, `Symptom`, and `GuestSession` from `app.models`.

`GuestSession` stores cryptographic token hashes (SHA-256, 64 hex characters) with expiration timestamps for frictionless anonymous triage (idea § 10). It supports ownership linking to `Assessment` and account transfer (`claimed_by_user_id`).

Configuration is injected; these modules never read environment variables.
See [database setup and design](../../../docs/database.md) for integration,
constraints, commands, and the outstanding team handoff.

From `server/`, run `python -m pytest tests/unit/db -q`. SQLite is the default
fast test backend; it does not establish PostgreSQL compatibility. Run
`python -m pytest tests/unit/db --db-postgres -s -q` against the documented
local PostgreSQL 16 container before submitting the PR. Tests use temporary
schemas and leave application tables intact.
