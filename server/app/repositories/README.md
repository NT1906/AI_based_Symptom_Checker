# Repositories

Owner: Harsh, Kavya, Nishith · Tasks: S0-HAR-1, S1-KAV-4, S1-NIT-4 · Issues: #9, #36, #37 · Requirements: FR-01, FR-17, idea § 10

Database access layer providing typed CRUD persistence for assessments, dialogue messages, structured symptoms, and guest sessions.

## Key Functions

- `seed_fictional_data(session)`: Seeds fictional test graph. Flushes but does not commit. The caller owns the transaction.
- `create_guest_session(session, ttl_hours=24)`: Creates anonymous session, hashes token, returns `(GuestSession, raw_token)`.
- `get_guest_session_by_token(session, raw_token, include_expired=False)`: Resolves active session via SHA-256 token hash lookup.
- `get_guest_session_by_id(session, guest_session_id)`: Fetches session by UUID.
- `link_assessment_to_session(session, assessment_id, guest_session_id)`: Associates assessment with guest session.
- `claim_guest_session(session, guest_session_id, user_id)`: Claims guest session and transfers assessment ownership to registered account (idea § 10).

## Architectural Invariants

1. **Transaction Ownership:** Repositories accept an active SQLAlchemy `Session` and call `session.flush()` to populate generated attributes and defaults. **The caller owns the transaction boundary** (`session.commit()` or rollback).
2. **Environment Isolation:** Configuration is injected; repository modules never read environment variables or instantiate database engines directly.
3. **Engine Portability:** Symptoms use `JSON().with_variant(JSONB, "postgresql")` to provide native binary JSONB storage in PostgreSQL while remaining fully operational in SQLite test environments.

## Modules

* **`assessment_repository.py`**: Typed CRUD for assessments, atomic state updates, eager loading of relations (`selectinload`), and user-scoped pagination.
* **`guest_session_repository.py`**: Anonymous session lifecycle, SHA-256 token hashing, expiration checks, and claiming.
* **`message_repository.py`**: Ordered conversation turn management with automatic position numbering and message counting.
* **`symptom_repository.py`**: Canonical symptom persistence storing clinical attributes (severity, duration, body site, onset) as structured JSONB with upsert and bulk-replacement capabilities.

## Running Tests

From `server/`:

```powershell
pytest tests/unit/db -v
```
