# Repositories

Owner: Harsh, Kavya, Nishith · Tasks: S0-HAR-1, S1-KAV-4, S1-NIT-4, S2-KAV-3, S2-KAV-4, S2-NIT-3, S2-NIT-4, S2-KAV-6, S2-KAV-7 · Issues: #9, #36, #37, #159, #160, #161, #162, #200, #201 · Requirements: FR-01, FR-02, FR-03, FR-17, FR-18, DR-02, NFR-01, NFR-05, NFR-08, NFR-10, idea § 10

Database access layer providing typed CRUD persistence for assessments, dialogue messages, structured symptoms, user profiles, guest sessions, audit logging, and symptom vector embeddings.

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
- `claim_guest_session(session, guest_session_id, user_id)`: Claims guest session and transfers assessment ownership to registered account (idea § 10).

### User Profiles (FR-02)
- `get_profile_by_user_id(session, user_id)`: Fetches user profile.
- `upsert_profile(session, user_id, ...)`: Creates or updates profile fields with sanitization.
- `delete_profile_by_user_id(session, user_id)`: Deletes user profile.
- `clear_profile_by_user_id(session, user_id)`: Resets profile fields without deleting row.

### Audit Logging (NFR-10, S2-NIT-3)
- `create_audit_log(session, action, ...)`: Persists clinical decision audit telemetry (who, when, engines/models, risk tier). Caller owns transaction.
- `list_audit_logs_by_assessment(session, assessment_id, limit, offset)`: Retrieves audit records for an assessment, ordered newest first.
- `list_audit_logs(session, action, risk_level, ...)`: Multi-criteria filtering for compliance auditing and system observability.

### Symptom Embeddings & Vector Retrieval (S2-NIT-4, S2-NIS-7, DR-02)
- `insert_symptom_embeddings(session, embeddings)`: Bulk persists dense 384-dimensional sentence vectors (`all-MiniLM-L6-v2`).
- `get_symptom_embedding_by_phrase(session, model_revision, phrase)`: Resolves cached embedding by exact phrase and revision.
- `list_symptom_embeddings_by_revision(session, model_revision)`: Retrieves embeddings scoped to a pinned model revision for linear scan matching.
- `count_symptom_embeddings(session, model_revision)`: Returns count of indexed vectors.

### Seeding
- `seed_fictional_data(session)`: Seeds fictional test graph. Flushes but does not commit. The caller owns the transaction.

## Architectural Invariants

1. **Transaction Ownership:** Repositories accept an active SQLAlchemy `Session` and call `session.flush()` to populate generated attributes and defaults. **The caller owns the transaction boundary** (`session.commit()` or rollback).
2. **Environment Isolation:** Configuration is injected; repository modules never read environment variables or instantiate database engines directly.
3. **Engine Portability:** Symptoms and audit logs use `JSON().with_variant(JSONB, "postgresql")` to provide native binary JSONB storage in PostgreSQL while remaining fully operational in SQLite test environments. Embeddings use `Numeric(384).with_variant(Vector(384), "postgresql")` to guarantee portability across SQLite and PostgreSQL.
4. **Query-Level IDOR Protection:** Ownership filters operate directly in SQL `WHERE` clauses rather than relying solely on application-level filtering.
5. **Zero-PII Audit Privacy (NFR-10, DR-06):** Audit log operations strictly reject or omit personal identifiers, conversation dialogue, and raw message text, recording only operational telemetry, rule decisions, and model version identifiers.
6. **Deterministic Vector Scans (DR-02):** Embeddings are retrieved via plain table scans over ~700 rows (< 2 ms) without approximate indexes (no HNSW or IVFFlat), guaranteeing identical nearest neighbors on repeat queries.

## Modules

* **`assessment_repository.py`**: Typed CRUD for assessments, history queries, pagination, eager loading (`selectinload`), and ownership filtering.
* **`audit_log_repository.py`**: Audit log persistence, compliance queries, time-range filtering, and model version lineage tracking (S2-NIT-3).
* **`guest_session_repository.py`**: Anonymous session lifecycle, SHA-256 token hashing, expiration checks, and claiming.
* **`message_repository.py`**: Ordered conversation turn management with automatic position numbering and message counting.
* **`profile_repository.py`**: User profile CRUD, coarse age band & biological sex validation, chronic conditions normalization.
* **`symptom_embedding_repository.py`**: Symptom vector embedding persistence, model revision scoping, and exact linear scan retrieval (S2-NIT-4).
* **`symptom_repository.py`**: Canonical symptom persistence storing clinical attributes (severity, duration, body site, onset) as structured JSONB with upsert and bulk-replacement capabilities.

## Running Tests

From `server/`:

```powershell
# Run repository and database tests
python -m pytest tests/unit/db -v

# Run schema data integrity and invariant tests
python -m pytest tests/unit/db/test_data_integrity.py -v

# Run migration safety and rollback drill tests
python -m pytest tests/unit/db/test_migration_safety.py -v
```

See [database setup and design](../../../docs/database.md), [data integrity report](../../../docs/data-integrity.md), and [migration safety review](../../../docs/migration-safety-review.md) for full relational specifications, constraint verification, and rollback procedures.
