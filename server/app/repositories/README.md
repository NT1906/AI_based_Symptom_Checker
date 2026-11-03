# Repositories

**Owner:** Harsh (S0-HAR-1), Nishith (S1-NIT-4) · **Requirement:** FR-01, FR-17

Database repository layer providing typed CRUD persistence for assessments, dialogue messages, and structured symptoms.

## Architectural Invariants

1. **Transaction Ownership:** Repositories accept an active SQLAlchemy `Session` and call `session.flush()` to populate generated attributes and defaults. **The caller owns the transaction boundary** (`session.commit()` or rollback).
2. **Environment Isolation:** Configuration is injected; repository modules never read environment variables or instantiate database engines directly.
3. **Engine Portability:** Symptoms use `JSON().with_variant(JSONB, "postgresql")` to provide native binary JSONB storage in PostgreSQL while remaining fully operational in SQLite test environments.

## Modules

* **`assessment_repository.py`**: Typed CRUD for assessments, atomic state updates, eager loading of relations (`selectinload`), and user-scoped pagination.
* **`message_repository.py`**: Ordered conversation turn management with automatic position numbering and message counting.
* **`symptom_repository.py`**: Canonical symptom persistence storing clinical attributes (severity, duration, body site, onset) as structured JSONB with upsert and bulk-replacement capabilities.

## Running Tests

From `server/`:

```powershell
pytest tests/unit/db -v
```
