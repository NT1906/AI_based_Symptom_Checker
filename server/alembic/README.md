# Database migrations

Owner: Harsh · Task: S0-HAR-1 · Issue: #9

`0001_database_foundation` creates the initial five tables. Revisions contain
explicit schema operations; they never import live models to create tables.
`script.py.mako` is the template for future revisions; replace its task header.

From `server/`, use `python -m app.db.manage upgrade` for the local database.
`alembic upgrade head --sql` emits PostgreSQL SQL without credentials.
Online Alembic requires a live connection in `Config.attributes["connection"]`.
The deployment configuration adapter is pending Rutva's settings contract.
See [database.md](../../docs/database.md) for exact integration requirements.

Tests: `python -m pytest tests/unit/db -q`; PostgreSQL mode is documented there.
Downgrade deletes tables and their data; use only disposable databases.
