# Db

Owner: Harsh, Nishith, Kavya · Tasks: S0-HAR-1, S2-NIT-6, S2-NIT-7, S2-KAV-6 · Issues: #9, #198, #199, #200 · Requirements: FR-01, NFR-01, NFR-05, NFR-08

Injected engine/session factories and a temporary local maintenance runner.

`create_db_engine(url)`, `create_session_factory(engine)`, and `upgrade_database(engine)`. Run `python -m app.db.manage upgrade` or `seed` from `server/` for local setup.
Run `python -m app.db.query_perf --database-url <url>` to execute the S2-NIT-6 `EXPLAIN (ANALYZE, BUFFERS)` query performance review across all 12 hot-path queries (see [query-performance-review.md](../../../docs/query-performance-review.md)).
Run `python -m app.db.backup_restore verify --database-url <url>` to capture PII-free Alembic revision, row counts, and SHA-256 table digests before and after Neon backup/restore drills (see [backup-and-restore.md](../../../docs/backup-and-restore.md)).

Configuration is injected; these modules never read environment variables.
See [database setup and design](../../../docs/database.md) for full 9-table schema architecture, data dictionary, and index catalog.
See [data integrity report](../../../docs/data-integrity.md) for the complete constraint matrix and invariant verification.

From `server/`, run `python -m pytest tests/unit/db -q`. SQLite is the default
fast test backend; it does not establish PostgreSQL compatibility. Run
`python -m pytest tests/unit/db/test_data_integrity.py -v` to verify foreign key actions,
constraints, and atomicity invariants across all 9 schema tables. Run
`python -m pytest tests/unit/db --db-postgres -s -q` against the documented
local PostgreSQL 16 container before submitting the PR. Tests use temporary
schemas and leave application tables intact.
