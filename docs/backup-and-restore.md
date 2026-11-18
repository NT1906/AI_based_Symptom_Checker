# Neon PostgreSQL Backup & Restore Procedure (S2-NIT-7)

**Owner:** Nishith (`@Nishith1130`, Database team) · **Issue:** #199 · **Requirements:** `NFR-05`, `DR-06`
**Tooling:** [`server/app/db/backup_restore.py`](../server/app/db/backup_restore.py) · **Tests:** [`server/tests/unit/db/test_backup_restore.py`](../server/tests/unit/db/test_backup_restore.py) · **Schema Reference:** [`docs/database.md`](database.md)

---

## 1. Recovery Objectives & Neon Branch Layout

Our database runs on **Neon PostgreSQL 16** (with `pgvector` enabled) using two long-lived branches:
- `main` → production API (`DATABASE_URL` in production environment).
- `staging` → staging API (`DATABASE_URL` in staging environment, auto-deployed from `develop`).

| Mechanism | Scope | RPO | RTO | Retention / Cadence |
|---|---|---|---|---|
| **Neon PITR (WAL history)** | Instant branch restore to any timestamp/LSN | ~Seconds | < 5 min | 24 h on Neon Free Tier (7–30 days on Launch/Scale plans) |
| **Neon Pre-Migration Snapshot Branch** | Copy-on-write snapshot before every production Alembic migration | 0 (exact pre-migration state) | < 2 min | Retained 48 h after successful release, then pruned |
| **Encrypted `pg_dump` Custom Archive** | Portable off-Neon logical backup (schema + all 9 tables) | ≤ 24 h (weekly / pre-release) | < 15 min | Encrypted at rest (`age` / `gpg`), never committed to git |

---

## 2. Strategy 1 — Neon Native PITR & Pre-Migration Branch Snapshots (Primary)

### 2.1 Mandatory Pre-Migration Snapshot (Before Every Production Release)
Before running `alembic upgrade head` against `main`:

```bash
# 1. Authenticate neonctl (one-time per operator machine)
neonctl auth

# 2. Record pre-migration integrity baseline (Alembic revision + row counts + SHA-256 digests, zero PII)
python -m app.db.backup_restore verify --database-url "$DATABASE_URL"

# 3. Create an instant copy-on-write snapshot branch from main
neonctl branches create \
  --project-id "$NEON_PROJECT_ID" \
  --parent main \
  --name "pre-mig-$(date -u +%Y%m%d-%H%M)"
```

### 2.2 Point-in-Time Restore (PITR) Drill / Incident Recovery
Never overwrite `main` blindly. Always restore into an **isolated recovery branch**, verify integrity, and only then promote or swap:

```bash
# 1. Create an isolated recovery branch at the last known-good UTC timestamp
neonctl branches create \
  --project-id "$NEON_PROJECT_ID" \
  --parent main \
  --point-in-time "2026-11-18T12:00:00Z" \
  --name "restore-verify-$(date -u +%Y%m%d-%H%M)"

# 2. Retrieve the recovery branch connection string
RECOVERY_URL=$(neonctl connection-string "restore-verify-YYYYMMDD-HHMM" --project-id "$NEON_PROJECT_ID")

# 3. Verify Alembic revision, row counts, and SHA-256 table digests on recovery branch
python -m app.db.backup_restore verify --database-url "postgresql+psycopg://${RECOVERY_URL#postgresql://}"

# 4. Verify pgvector extension and embeddings table
psql "$RECOVERY_URL" -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
psql "$RECOVERY_URL" -c "SELECT version_num FROM alembic_version;"

# 5. Cutover (leader-approved):
#    Option A: Reset `main` to the recovery branch timestamp via Neon Console ("Restore branch").
#    Option B: Point Render/VPS `DATABASE_URL` to the promoted branch and restart the API container.
```

---

## 3. Strategy 2 — Portable Logical Backup (`pg_dump` / `pg_restore`)

Use PostgreSQL 16 client tools (`pg_dump` / `pg_restore` 16.x) so backups remain portable even outside Neon.

### 3.1 Taking an Encrypted Logical Backup
> **Security Rule (`AI_RULES.md §2.12`, `DR-06`):** Always use a libpq `postgresql://` URL with `sslmode=require` (never `postgresql+psycopg://`), never log credentials, and **never** place `.dump`, `.sql`, or `.json` backups inside the git repository.

```bash
# 1. Convert SQLAlchemy URL to libpq URI with TLS enforced
LIBPQ_URL="${DATABASE_URL/postgresql+psycopg:/postgresql:}"
[[ "$LIBPQ_URL" != *"sslmode="* ]] && LIBPQ_URL="${LIBPQ_URL}?sslmode=require"

BACKUP_DIR="/tmp/neon-backups"
mkdir -p "$BACKUP_DIR"
DUMP_FILE="${BACKUP_DIR}/symptom_checker_$(date -u +%Y%m%dT%H%M%SZ).dump"

# 2. Create custom-format compressed backup (schema + all 9 tables + alembic_version)
pg_dump \
  --format=custom \
  --no-owner \
  --no-privileges \
  --compress=6 \
  --file="$DUMP_FILE" \
  --dbname="$LIBPQ_URL"

# 3. Generate SHA-256 checksum sidecar
sha256sum "$DUMP_FILE" > "${DUMP_FILE}.sha256"

# 4. Encrypt at rest before off-host storage (remove plaintext dump afterward)
age -r "$BACKUP_AGE_PUBLIC_KEY" -o "${DUMP_FILE}.age" "$DUMP_FILE"
rm -f "$DUMP_FILE"
```

### 3.2 Restoring a Logical Backup onto a Fresh Neon Branch
```bash
# 1. Decrypt and verify integrity checksum before touching any database
age -d -i "$BACKUP_AGE_PRIVATE_KEY" -o "$DUMP_FILE" "${DUMP_FILE}.age"
sha256sum -c "${DUMP_FILE}.sha256"

# 2. Create a clean target branch on Neon and ensure pgvector extension is enabled
psql "$TARGET_LIBPQ_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 3. Restore atomically inside a single transaction
pg_restore \
  --no-owner \
  --no-privileges \
  --single-transaction \
  --exit-on-error \
  --clean \
  --if-exists \
  --dbname="$TARGET_LIBPQ_URL" \
  "$DUMP_FILE"

# 4. Verify schema revision, row counts, and SHA-256 digests match baseline
python -m app.db.backup_restore verify --database-url "postgresql+psycopg://${TARGET_LIBPQ_URL#postgresql://}"

# 5. Clean up local plaintext dump immediately
rm -f "$DUMP_FILE"
```

---

## 4. Mandatory DPDP Act 2023 Post-Restore Hygiene (`DR-06`)

Restoring a database from an earlier point in time can temporarily **resurrect** records deleted between the backup timestamp and the incident:

1. **Re-run Guest TTL Purge (`S2-DIM-4` / `S2-HAR-4`):** Immediately execute the scheduled guest purge runner (`purge_expired_guest_sessions`) before reopening user traffic so expired anonymous sessions and assessments are wiped.
2. **Replay Account Deletion Requests (`S2-HAR-2`):** Cross-check the immutable deletion audit entries (from the audit log / operational incident log) for any user IDs that invoked `"Delete my data"` after the backup timestamp and re-run `delete_user_account(session, user_id)` before unpausing traffic.
3. **Verify `symptom_embeddings`:** Confirm `SELECT COUNT(*) FROM symptom_embeddings;` matches the pinned `all-MiniLM-L6-v2` revision (~700 rows); if empty, startup self-healing in `retrieval` automatically rebuilds it in one transaction.

---

## 5. Restore Verification Drill Log ("Tested Once")

### Automated End-to-End Round-Trip Drill (`test_backup_restore.py`)
- **Date Executed:** 2026-11-18
- **Schema Revision Tested:** `0008_query_perf_indexes` (all 9 tables: `consents`, `users`, `profiles`, `guest_sessions`, `assessments`, `messages`, `symptoms`, `audit_logs`, `symptom_embeddings`)
- **Procedure Executed:**
  1. Seeded synthetic multi-table dataset with foreign-key graphs, JSONB details, timestamps, and 384-dim `Vector(384)` embeddings.
  2. Exported SHA-256-sealed logical snapshot (`export_logical_snapshot`) and captured pre-backup `IntegritySnapshot`.
  3. Executed destructive full-table wipe across all 9 tables in reverse FK order and confirmed `0` rows remaining across the schema.
  4. Restored snapshot atomically (`restore_logical_snapshot(..., truncate_target=True)`) in forward FK topological order.
  5. Executed `verify_restore_integrity(before, after)` — **100% parity confirmed** across `alembic_version` (`0008_query_perf_indexes`), exact row counts for all 9 tables, and deterministic SHA-256 table digests.
  6. Verified negative safety controls: tampered SHA-256 digest rejected before touching target DB; Alembic revision mismatch rejected; non-empty target refused without explicit `truncate_target=True`; atomic savepoint rollback verified on mid-restore constraint error.
- **Neon Staging Checklist (for operator with `NEON_PROJECT_ID` credentials):**
  - [ ] Run `neonctl branches create --parent staging --name restore-drill-YYYYMMDD`.
  - [ ] Execute §3.1 `pg_dump` → §3.2 `pg_restore` onto the disposable drill branch.
  - [ ] Compare `python -m app.db.backup_restore verify` outputs between `staging` and `restore-drill-YYYYMMDD`.
  - [ ] Delete disposable drill branch (`neonctl branches delete restore-drill-YYYYMMDD`) and remove local `.dump` file.
