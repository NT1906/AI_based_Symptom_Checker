# Database foundation tests

Owner: Harsh · Task: S0-HAR-1 · Issue: #9

The suite checks migrations, relationships, constraints, transactions, seed
idempotency, and the local CLI. All fixtures are explicitly fictional.

From `server/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/unit/db -q
..\.venv\Scripts\python.exe -m pytest tests/unit/db --db-postgres -s -q
```

Default tests use an in-memory SQLite database with foreign keys enabled.
PostgreSQL mode prompts once for the local Docker password and uses
`127.0.0.1:5433`, `symptom_dev`, `symptom_checker`. Each test creates and drops
its own `test_db_<random UUID>` schema. It does not drop the public schema or
application database. The local role must be able to create schemas.
Never substitute production credentials. A forcibly interrupted run may leave
an empty/test-only schema behind; normal cleanup removes it.

The fixtures are deliberately scoped to this module; shared test infrastructure
in `tests/conftest.py` remains Mohit's responsibility.
