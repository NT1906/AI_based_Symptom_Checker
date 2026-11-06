# Repositories

Owner: Harsh, Kavya · Tasks: S0-HAR-1, S1-KAV-4 · Issues: #9, #37 · Requirements: FR-01, idea § 10

Database access layer.

- `seed_fictional_data(session)`: Seeds fictional test graph. Flushes but does not commit. The caller owns the transaction.
- `create_guest_session(session, ttl_hours=24)`: Creates anonymous session, hashes token, returns `(GuestSession, raw_token)`.
- `get_guest_session_by_token(session, raw_token, include_expired=False)`: Resolves active session via SHA-256 token hash lookup.
- `get_guest_session_by_id(session, guest_session_id)`: Fetches session by UUID.
- `link_assessment_to_session(session, assessment_id, guest_session_id)`: Associates assessment with guest session.
- `claim_guest_session(session, guest_session_id, user_id)`: Claims guest session and transfers assessment ownership to registered account (idea § 10).

Configuration is injected; these modules never read environment variables.
See [database setup and design](../../../docs/database.md) for integration,
constraints, commands, and the outstanding team handoff.

From `server/`, run `python -m pytest tests/unit/db -q`. SQLite is the default
fast test backend; it does not establish PostgreSQL compatibility. Run
`python -m pytest tests/unit/db --db-postgres -s -q` against the documented
local PostgreSQL 16 container before submitting the PR. Tests use temporary
schemas and leave application tables intact.
