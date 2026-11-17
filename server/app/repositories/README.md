# Repositories

Owner: Harsh, Kavya, Nishith · Tasks: S0-HAR-1, S1-KAV-4, S1-NIT-4, S2-KAV-3, S2-KAV-4 · Issues: #9, #36, #37, #161, #162 · Requirements: FR-01, FR-02, FR-17, idea § 10

Database access layer providing typed CRUD persistence for assessments, dialogue messages, structured symptoms, user profiles, and guest sessions.

## Key Functions

### Assessments & History (FR-02, FR-17)
- `create_assessment(session, consent_id, user_id=None, state='START')`: Persists a new assessment.
- `get_assessment_by_id(session, assessment_id)`: Fetches an assessment by ID.
- `get_assessment_with_details(session, assessment_id)`: Eagerly loads messages, symptoms, and consent.
- `query_assessment_history(session, user_id, ...)`: Paginated history query with state filtering, timestamp bounds, ordering, and optional relation eager-loading.
- `count_assessments_by_user(session, user_id, ...)`: Counts matching assessments for total page calculation.
- `list_assessments_by_user(session, user_id, limit=20, offset=0, ...)`: Lightweight paginated list.
- `get_assessment_by_id_and_user(session, assessment_id, user_id)`: Query-level IDOR ownership guard.
- `get_assessment_with_details_for_user(session, assessment_id, user_id)`: Query-level ownership guard with relations.
- `get_assessment_by_id_and_guest_session(session, assessment_id, guest_session_id)`: Guest session ownership guard.
- `get_assessment_by_ownership(session, assessment_id, user_id=None, guest_session_id=None)`: Unified ownership resolver.
- `delete_assessment_for_user(session, assessment_id, user_id)`: Deletes an assessment only if owned by user.
- `delete_assessments_for_user(session, user_id)`: Purges all assessments for a user account (data erasure).

### Guest Sessions (idea § 10)
- `create_guest_session(session, ttl_hours=24)`: Creates anonymous session, hashes token, returns `(GuestSession, raw_token)`.
- `get_guest_session_by_token(session, raw_token, include_expired=False)`: Resolves active session via SHA-256 token hash lookup.
- `get_guest_session_by_id(session, guest_session_id)`: Fetches session by UUID.
- `link_assessment_to_session(session, assessment_id, guest_session_id)`: Associates assessment with guest session.
- `claim_guest_session(session, guest_session_id, user_id)`: Claims guest session and transfers assessment ownership to registered account.

### User Profiles (FR-02)
- `get_profile_by_user_id(session, user_id)`: Fetches user profile.
- `upsert_profile(session, user_id, ...)`: Creates or updates profile fields with sanitization.
- `delete_profile_by_user_id(session, user_id)`: Deletes user profile.
- `clear_profile_by_user_id(session, user_id)`: Resets profile fields without deleting row.

### Seeding
- `seed_fictional_data(session)`: Seeds fictional test graph. Flushes but does not commit. The caller owns the transaction.

## Architectural Invariants

1. **Transaction Ownership:** Repositories accept an active SQLAlchemy `Session` and call `session.flush()` to populate generated attributes and defaults. **The caller owns the transaction boundary** (`session.commit()` or rollback).
2. **Environment Isolation:** Configuration is injected; repository modules never read environment variables or instantiate database engines directly.
3. **Engine Portability:** Symptoms use `JSON().with_variant(JSONB, "postgresql")` to provide native binary JSONB storage in PostgreSQL while remaining fully operational in SQLite test environments.
4. **Query-Level IDOR Protection:** Ownership filters operate directly in SQL `WHERE` clauses rather than relying solely on application-level filtering.

## Modules

* **`assessment_repository.py`**: Typed CRUD for assessments, history queries, pagination, eager loading (`selectinload`), and ownership filtering.
* **`guest_session_repository.py`**: Anonymous session lifecycle, SHA-256 token hashing, expiration checks, and claiming.
* **`message_repository.py`**: Ordered conversation turn management with automatic position numbering and message counting.
* **`profile_repository.py`**: User profile CRUD, coarse age band & biological sex validation, chronic conditions normalization.
* **`symptom_repository.py`**: Canonical symptom persistence storing clinical attributes (severity, duration, body site, onset) as structured JSONB with upsert and bulk-replacement capabilities.

## Running Tests

From `server/`:

```powershell
pytest tests/unit/db -v
```
