# Server Scripts

Utility scripts for backend development, schema generation, and CI automation.

## Available Scripts

### `export_openapi.py`

Exports the deterministic OpenAPI 3.1 JSON specification from the FastAPI application.

- **No external dependencies:** Runs completely offline without a database connection, network access, or populated `.env` secrets.
- **Deterministic output:** Serialized with `indent=2`, `sort_keys=True`, and a trailing newline for clean git diffs.

#### Usage

From the `server/` directory:

```bash
# Print OpenAPI JSON to stdout
python scripts/export_openapi.py

# Write OpenAPI JSON to a target file
python scripts/export_openapi.py --output ../docs/openapi.json
```

From the repository root:

```bash
python server/scripts/export_openapi.py -o docs/openapi.json
```

## Testing

The script is tested in `tests/unit/api/test_export_openapi.py`:
- Determinism check (consecutive runs produce byte-for-byte identical output).
- Output matches `app.openapi()` directly.
- File export creates directories and writes valid UTF-8 JSON.
