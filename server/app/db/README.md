# Db

Owner: Harsh · Task: S0-HAR-1 · Issue: #9 · Requirement: FR-01

Injected engine/session factories and a temporary local maintenance runner.

`create_db_engine(url)`, `create_session_factory(engine)`, and `upgrade_database(engine)`. Run `python -m app.db.manage upgrade` or `seed` from `server/` for local setup.

Configuration is injected; these modules never read environment variables.
See [database setup and design](../../../docs/database.md) for integration,
constraints, commands, and the outstanding team handoff.

From `server/`, run `python -m pytest tests/unit/db -q`. SQLite is the default
fast test backend; it does not establish PostgreSQL compatibility. Run
`python -m pytest tests/unit/db --db-postgres -s -q` against the documented
local PostgreSQL 16 container before submitting the PR. Tests use temporary
schemas and leave application tables intact.
