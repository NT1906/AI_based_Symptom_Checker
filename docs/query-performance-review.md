# Query Performance Review (`EXPLAIN ANALYZE`) & Index Fixes (S2-NIT-6)

**Owner:** Nishith (`@Nishith1130`, Database team) · **Issue:** #198 · **Requirement:** `NFR-01` (p95 response time ≤ 5 s)
**Migration:** [`0008_query_perf_indexes.py`](../server/alembic/versions/0008_query_perf_indexes.py) · **Runner:** [`server/app/db/query_perf.py`](../server/app/db/query_perf.py) · **Tests:** [`server/tests/unit/db/test_query_performance.py`](../server/tests/unit/db/test_query_performance.py)

---

## 1. Review Methodology

All 9 ORM tables (`users`, `profiles`, `consents`, `guest_sessions`, `assessments`, `messages`, `symptoms`, `audit_logs`, `symptom_embeddings`) and all repository read/delete queries (`assessment_repository`, `audit_log_repository`, `guest_session_repository`, `message_repository`, `symptom_repository`, `profile_repository`, `retention_repository`, `symptom_embedding_repository`) were audited across two layers:

1. **Automated Plan Verification (`server/app/db/query_perf.py`):** Compiles the 12 canonical hot-path read queries and runs:
   - **`EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)`** on PostgreSQL (Neon staging / local Docker / CI Postgres).
   - **`EXPLAIN QUERY PLAN`** on SQLite (fast hermetic regression assertions in `pytest`).
2. **Foreign-Key Cascade Audit:** Inspected every `ON DELETE SET NULL` and `ON DELETE RESTRICT` foreign key executed during DPDP account deletion (`delete_user_account`) and guest TTL purge (`purge_expired_guest_sessions`) to confirm PostgreSQL never falls back to a sequential scan while checking or updating child rows.

---

## 2. Findings & Index Fixes (`0008_query_perf_indexes`)

Five concrete query-plan bottlenecks were identified and resolved in additive, backward-compatible migration **`0008_query_perf_indexes`**:

| # | Table | Repository Operation | Plan Before `0008` | Index Added in `0008` | Plan After `0008` |
|---|---|---|---|---|---|
| 1 | `assessments` | `list_assessments_by_guest_session` (`WHERE guest_session_id = ? AND user_id IS NULL ORDER BY created_at DESC LIMIT 20`) | Index scan on `ix_assessments_guest_session_id` + explicit **`Sort (created_at DESC)`** | `ix_assessments_guest_session_id_created_at (guest_session_id, created_at)` | **Index Scan Backward** directly in `created_at DESC` order (zero Sort) |
| 2 | `guest_sessions` | `delete_user_account` (`DELETE FROM users WHERE id = ?` triggering `FK ON DELETE SET NULL` on `guest_sessions.claimed_by_user_id`) | Full **`Seq Scan`** on `guest_sessions` (unindexed FK) | `ix_guest_sessions_claimed_by_user_id (claimed_by_user_id)` | **Index Scan** on `claimed_by_user_id` (zero Seq Scan on DPDP account deletion) |
| 3 | `audit_logs` | `list_audit_logs_by_assessment` (`WHERE assessment_id = ? ORDER BY created_at DESC LIMIT 50`) | Index scan on `ix_audit_logs_assessment_id` + explicit **`Sort (created_at DESC)`** | `ix_audit_logs_assessment_id_created_at (assessment_id, created_at)` | **Index Scan Backward** directly in `created_at DESC` order (zero Sort) |
| 4 | `audit_logs` | `list_audit_logs_by_user` (`WHERE user_id = ? ORDER BY created_at DESC LIMIT 50`) | Index scan on `ix_audit_logs_user_id` + explicit **`Sort (created_at DESC)`** | `ix_audit_logs_user_id_created_at (user_id, created_at)` | **Index Scan Backward** directly in `created_at DESC` order (zero Sort) |
| 5 | `audit_logs` | `query_audit_logs` (`WHERE action = ? AND created_at >= ? ORDER BY created_at DESC LIMIT 50`) | Single-column scan + filter discard + explicit **`Sort (created_at DESC)`** | `ix_audit_logs_action_created_at (action, created_at)` | **Index Scan Backward** bounded by `(action, created_at)` range (zero Sort) |

---

## 3. Complete 12-Query Hot-Path Index Matrix (Post-`0008`)

Every hot-path query is verified to use an index with **zero sequential table scans** and **zero explicit sort / temp B-tree nodes**:

| Query Name | Table | Expected Index | Seq Scan | Explicit Sort |
|---|---|---|---|---|
| `user_history_paginated` | `assessments` | `ix_assessments_user_id_created_at` | no | no |
| `user_history_by_state` | `assessments` | `ix_assessments_user_id_state_created_at` | no | no |
| `guest_history_unclaimed` | `assessments` | `ix_assessments_guest_session_id_created_at` | no | no |
| `assessment_messages_ordered` | `messages` | `uq_messages_assessment_id_position` | no | no |
| `assessment_symptoms_lookup` | `symptoms` | `ix_symptoms_assessment_id` / `uq_symptoms_assessment_id_name` | no | no |
| `guest_session_token_lookup` | `guest_sessions` | `uq_guest_sessions_token_hash` | no | no |
| `expired_guest_sessions_purge` | `guest_sessions` | `ix_guest_sessions_expires_at` | no | no |
| `guest_sessions_by_claimed_user` | `guest_sessions` | `ix_guest_sessions_claimed_by_user_id` | no | no |
| `audit_logs_by_assessment` | `audit_logs` | `ix_audit_logs_assessment_id_created_at` | no | no |
| `audit_logs_by_user` | `audit_logs` | `ix_audit_logs_user_id_created_at` | no | no |
| `audit_logs_by_action_window` | `audit_logs` | `ix_audit_logs_action_created_at` | no | no |
| `symptom_embeddings_by_revision` | `symptom_embeddings` | `ix_symptom_embeddings_model_revision` | no | no |

---

## 4. Intentional Non-Changes & Trade-Offs

1. **No HNSW / IVFFlat Approximate Index on `symptom_embeddings` (`DR-02`):**
   - `ix_symptom_embeddings_model_revision` scopes the query to the pinned revision (~700 rows), followed by an exact distance scan. Approximate vector indexes are intentionally omitted so nearest-neighbor symptom resolution remains 100% deterministic.
2. **Preserving Sprint 1 Single-Column Indexes (`S2-KAV-7` Migration Safety):**
   - Single-column indexes `ix_assessments_user_id`, `ix_messages_assessment_id`, `ix_symptoms_assessment_id`, `ix_assessments_guest_session_id`, `ix_audit_logs_assessment_id`, `ix_audit_logs_user_id`, and `ix_audit_logs_action` are leftmost prefixes of composite/unique indexes.
   - Because write throughput on this triage workload is low and dropping existing indexes could impact backward compatibility during rolling deployments (`S2-KAV-7`) or existing schema tests, `0008_query_perf_indexes` is strictly additive. Any future cleanup of redundant single-column indexes can be scheduled as a dedicated post-v1.0 migration with `DROP INDEX CONCURRENTLY`.

---

## 5. Reproducing `EXPLAIN (ANALYZE, BUFFERS)` on Neon Staging or Local PostgreSQL

From `server/`:

```powershell
# Apply migration 0008 first
alembic upgrade head

# Run EXPLAIN (ANALYZE, BUFFERS) across all 12 hot queries
python -m app.db.query_perf --database-url "$env:DATABASE_URL"
```

Safety guarantees of `app.db.query_perf`:
- Strictly rejects any non-`SELECT` SQL before issuing `EXPLAIN` (`validate_read_only_sql`).
- Uses synthetic UUID parameters only; never queries or prints real user health text or PII (`AI_RULES.md §2.12`).
