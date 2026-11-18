"""Neon PostgreSQL backup, restore, and integrity verification tooling.

Responsibilities:
    - Translate SQLAlchemy URLs into TLS-enforced libpq URLs for pg_dump and
      pg_restore while masking passwords from logs and dry-run output.
    - Build injection-safe argv lists for Neon logical pg_dump / pg_restore.
    - Capture per-table row counts and deterministic SHA-256 integrity digests
      across all 9 application tables plus alembic_version (zero PII logged).
    - Export and atomically restore FK-ordered logical snapshots with SHA-256
      tamper detection for reproducible restore drills (NFR-05).

Owner: Nishith (Database) · Task: S2-NIT-7 · Requirements: NFR-05, DR-06
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Table, Uuid, delete, func, insert, select, text
from sqlalchemy.engine import Connection, make_url

from app.models import Base

SNAPSHOT_FORMAT_VERSION: int = 1

# Strict FK topological insertion order across all 9 application tables.
# Deletions run in the exact reverse order to satisfy RESTRICT constraints.
TABLE_ORDER: tuple[str, ...] = (
    "consents",
    "users",
    "profiles",
    "guest_sessions",
    "assessments",
    "messages",
    "symptoms",
    "audit_logs",
    "symptom_embeddings",
)

_ALLOWED_PG_DRIVERS: frozenset[str] = frozenset(
    {"postgresql", "postgres", "postgresql+psycopg"}
)
_LOCAL_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1", "::1"})


@dataclass(frozen=True)
class TableIntegrity:
    """Aggregate row count and deterministic SHA-256 digest for one table."""

    table: str
    row_count: int
    sha256: str


@dataclass(frozen=True)
class IntegritySnapshot:
    """Schema revision and aggregate integrity metrics across all 9 tables."""

    alembic_revision: str | None
    tables: dict[str, TableIntegrity]


@dataclass(frozen=True)
class IntegrityDiff:
    """Comparison result between pre-backup and post-restore snapshots."""

    is_match: bool
    mismatches: tuple[str, ...]


def to_libpq_url(database_url: str) -> str:
    """Convert a SQLAlchemy PostgreSQL URL to a libpq URI for pg_dump/pg_restore.

    Enforces ``sslmode=require`` automatically for non-localhost hosts (such as
    Neon ``*.neon.tech`` endpoints) unless ``sslmode`` is already configured.

    Args:
        database_url: PostgreSQL or ``postgresql+psycopg`` connection URL.

    Returns:
        libpq-compatible ``postgresql://...`` URI string.

    Raises:
        ValueError: If the URL is blank, malformed, or not a PostgreSQL scheme.
    """
    cleaned = database_url.strip()
    if not cleaned:
        raise ValueError("Database URL must not be blank.")
    try:
        parsed = make_url(cleaned)
    except Exception as exc:
        raise ValueError("Malformed PostgreSQL database URL.") from exc

    if parsed.drivername not in _ALLOWED_PG_DRIVERS:
        raise ValueError(
            f"Unsupported driver '{parsed.drivername}'. "
            "Expected postgresql or postgresql+psycopg."
        )
    if not parsed.host or not parsed.database:
        raise ValueError("PostgreSQL URL must specify both host and database name.")

    query = dict(parsed.query)
    if parsed.host.lower() not in _LOCAL_HOSTS and "sslmode" not in query:
        query["sslmode"] = "require"

    normalized = parsed.set(drivername="postgresql", query=query)
    return normalized.render_as_string(hide_password=False)


def mask_database_url(database_url: str) -> str:
    """Return a log-safe PostgreSQL URL with password replaced by ``***``."""
    cleaned = database_url.strip()
    if not cleaned:
        raise ValueError("Database URL must not be blank.")
    try:
        parsed = make_url(cleaned)
    except Exception as exc:
        raise ValueError("Malformed PostgreSQL database URL.") from exc
    return parsed.render_as_string(hide_password=True)


def build_pg_dump_command(
    database_url: str,
    output_path: str | Path,
    *,
    compression_level: int = 6,
) -> list[str]:
    """Build an injection-safe ``pg_dump`` argv list for Neon logical backups.

    Args:
        database_url: Target Neon or PostgreSQL connection URL.
        output_path: Destination ``.dump`` file path (custom format).
        compression_level: Zlib compression level in ``[0, 9]``.

    Returns:
        Argv list suitable for ``subprocess.run(..., shell=False)``.

    Raises:
        ValueError: If the URL, output path, or compression level is invalid.
    """
    if not 0 <= compression_level <= 9:
        raise ValueError("compression_level must be between 0 and 9.")
    out_str = str(output_path).strip()
    if not out_str:
        raise ValueError("output_path must not be blank.")

    libpq_url = to_libpq_url(database_url)
    return [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        f"--compress={compression_level}",
        f"--file={out_str}",
        f"--dbname={libpq_url}",
    ]


def build_pg_restore_command(
    database_url: str,
    input_path: str | Path,
    *,
    clean: bool = True,
) -> list[str]:
    """Build an injection-safe ``pg_restore`` argv list for Neon recovery.

    Uses ``--single-transaction`` and ``--exit-on-error`` so partial restores
    roll back atomically if any statement fails.

    Args:
        database_url: Target Neon recovery branch or PostgreSQL URL.
        input_path: Source custom-format ``.dump`` archive path.
        clean: Include ``--clean --if-exists`` to replace existing objects.

    Returns:
        Argv list suitable for ``subprocess.run(..., shell=False)``.

    Raises:
        ValueError: If the URL or input path is invalid.
    """
    in_str = str(input_path).strip()
    if not in_str:
        raise ValueError("input_path must not be blank.")

    libpq_url = to_libpq_url(database_url)
    cmd = [
        "pg_restore",
        "--no-owner",
        "--no-privileges",
        "--single-transaction",
        "--exit-on-error",
    ]
    if clean:
        cmd.extend(["--clean", "--if-exists"])
    cmd.extend([f"--dbname={libpq_url}", in_str])
    return cmd


def _get_alembic_revision(connection: Connection) -> str | None:
    """Read current Alembic revision from ``alembic_version``, if present."""
    try:
        row = connection.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        ).fetchone()
    except Exception:
        return None
    return str(row[0]) if row is not None and row[0] is not None else None


def _serialize_value(value: Any) -> Any:
    """Convert SQLAlchemy row values into deterministic JSON-safe primitives."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return round(value, 8)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return dt.astimezone(UTC).isoformat()
    if isinstance(value, Mapping):
        return {str(k): _serialize_value(v) for k, v in sorted(value.items())}
    if hasattr(value, "tolist"):
        return [_serialize_value(float(item)) for item in value.tolist()]
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    return str(value)


def _deserialize_row(table: Table, raw_row: Mapping[str, Any]) -> dict[str, Any]:
    """Convert serialized JSON row fields back into SQLAlchemy-bound Python types."""
    restored: dict[str, Any] = {}
    for col in table.columns:
        if col.name not in raw_row:
            continue
        val = raw_row[col.name]
        if val is None:
            restored[col.name] = None
        elif isinstance(col.type, Uuid):
            restored[col.name] = UUID(str(val))
        elif isinstance(col.type, DateTime):
            dt = datetime.fromisoformat(str(val))
            restored[col.name] = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
        else:
            restored[col.name] = val
    return restored


def _serialize_table_rows(
    connection: Connection,
    table: Table,
) -> list[dict[str, Any]]:
    """Fetch all rows from a table ordered deterministically by primary key."""
    pk_cols = list(table.primary_key.columns)
    stmt = select(table).order_by(*pk_cols) if pk_cols else select(table)
    rows = connection.execute(stmt).mappings().all()
    return [
        {col.name: _serialize_value(row[col.name]) for col in table.columns}
        for row in rows
    ]


def _hash_canonical(obj: Any) -> str:
    """Compute a deterministic SHA-256 hex digest of a JSON-serializable object."""
    encoded = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def capture_integrity_snapshot(connection: Connection) -> IntegritySnapshot:
    """Capture Alembic revision, row counts, and SHA-256 digests for all 9 tables.

    Produces aggregate metadata only — zero row contents or PII are emitted.
    """
    revision = _get_alembic_revision(connection)
    tables: dict[str, TableIntegrity] = {}
    for table_name in TABLE_ORDER:
        table = Base.metadata.tables[table_name]
        serialized = _serialize_table_rows(connection, table)
        tables[table_name] = TableIntegrity(
            table=table_name,
            row_count=len(serialized),
            sha256=_hash_canonical(serialized),
        )
    return IntegritySnapshot(alembic_revision=revision, tables=tables)


def verify_restore_integrity(
    expected: IntegritySnapshot,
    actual: IntegritySnapshot,
) -> IntegrityDiff:
    """Compare pre-backup and post-restore snapshots across schema and all tables."""
    mismatches: list[str] = []
    if expected.alembic_revision != actual.alembic_revision:
        mismatches.append(
            f"alembic_version mismatch: expected '{expected.alembic_revision}', "
            f"got '{actual.alembic_revision}'"
        )

    for table_name in TABLE_ORDER:
        exp = expected.tables.get(table_name)
        act = actual.tables.get(table_name)
        if exp is None or act is None:
            mismatches.append(f"table '{table_name}' missing from snapshot comparison")
            continue
        if exp.row_count != act.row_count:
            mismatches.append(
                f"table '{table_name}' row_count mismatch: "
                f"expected {exp.row_count}, got {act.row_count}"
            )
        elif exp.sha256 != act.sha256:
            mismatches.append(f"table '{table_name}' SHA-256 digest mismatch")

    return IntegrityDiff(is_match=not mismatches, mismatches=tuple(mismatches))


def export_logical_snapshot(
    connection: Connection,
    output_path: str | Path,
) -> IntegritySnapshot:
    """Export all 9 tables + Alembic revision to a SHA-256-verified JSON snapshot.

    Args:
        connection: Active SQLAlchemy Connection.
        output_path: Destination file path for the snapshot archive.

    Returns:
        IntegritySnapshot captured at export time.
    """
    revision = _get_alembic_revision(connection)
    tables_payload: dict[str, list[dict[str, Any]]] = {}
    table_stats: dict[str, TableIntegrity] = {}

    for table_name in TABLE_ORDER:
        table = Base.metadata.tables[table_name]
        rows = _serialize_table_rows(connection, table)
        tables_payload[table_name] = rows
        table_stats[table_name] = TableIntegrity(
            table=table_name,
            row_count=len(rows),
            sha256=_hash_canonical(rows),
        )

    body = {
        "alembic_revision": revision,
        "tables": tables_payload,
    }
    envelope = {
        "format_version": SNAPSHOT_FORMAT_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "alembic_revision": revision,
        "tables": tables_payload,
        "payload_sha256": _hash_canonical(body),
    }

    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(envelope, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return IntegritySnapshot(alembic_revision=revision, tables=table_stats)


def restore_logical_snapshot(
    connection: Connection,
    snapshot_path: str | Path,
    *,
    truncate_target: bool = False,
) -> IntegritySnapshot:
    """Validate and atomically restore a logical snapshot in FK topological order.

    Verifies format version, SHA-256 tamper digest, and Alembic schema revision
    before modifying any rows. Runs inside a nested savepoint so any failure
    leaves the target database completely unchanged.

    Args:
        connection: Active SQLAlchemy Connection inside an open transaction.
        snapshot_path: Path to snapshot file created by ``export_logical_snapshot``.
        truncate_target: If True, clears all 9 tables in reverse FK order before
            restoring. If False, refuses to overwrite non-empty tables.

    Returns:
        Post-restore IntegritySnapshot.

    Raises:
        ValueError: On missing/corrupt file, SHA-256 mismatch, version/revision
            mismatch, or non-empty target when ``truncate_target=False``.
    """
    src = Path(snapshot_path)
    if not src.exists():
        raise ValueError(f"Snapshot file not found: {src}")

    try:
        envelope = json.loads(src.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError("Snapshot file is not valid JSON.") from exc

    if not isinstance(envelope, dict):
        raise ValueError("Snapshot root payload must be a JSON object.")

    if envelope.get("format_version") != SNAPSHOT_FORMAT_VERSION:
        raise ValueError(
            f"Unsupported snapshot format_version: {envelope.get('format_version')}."
        )

    expected_sha = envelope.get("payload_sha256")
    tables_payload = envelope.get("tables")
    snap_revision = envelope.get("alembic_revision")
    if not isinstance(expected_sha, str) or not isinstance(tables_payload, dict):
        raise ValueError("Snapshot payload is missing required integrity fields.")

    recomputed_sha = _hash_canonical(
        {"alembic_revision": snap_revision, "tables": tables_payload}
    )
    if not hmac.compare_digest(expected_sha, recomputed_sha):
        raise ValueError("Snapshot integrity check failed: SHA-256 mismatch.")

    current_revision = _get_alembic_revision(connection)
    if snap_revision is not None and current_revision != snap_revision:
        raise ValueError(
            f"Alembic revision mismatch: snapshot is '{snap_revision}', "
            f"target database is '{current_revision}'."
        )

    for table_name in TABLE_ORDER:
        if table_name not in tables_payload or not isinstance(
            tables_payload[table_name], list
        ):
            raise ValueError(f"Snapshot is missing table data for '{table_name}'.")

    if not truncate_target:
        for table_name in TABLE_ORDER:
            table = Base.metadata.tables[table_name]
            count = connection.execute(select(func.count()).select_from(table)).scalar()
            if count and count > 0:
                raise ValueError(
                    f"Target table '{table_name}' is not empty ({count} rows); "
                    "pass truncate_target=True to overwrite."
                )

    with connection.begin_nested():
        if truncate_target:
            for table_name in reversed(TABLE_ORDER):
                connection.execute(delete(Base.metadata.tables[table_name]))

        for table_name in TABLE_ORDER:
            table = Base.metadata.tables[table_name]
            raw_rows = tables_payload[table_name]
            if not raw_rows:
                continue
            rows_to_insert = [_deserialize_row(table, r) for r in raw_rows]
            connection.execute(insert(table), rows_to_insert)

    return capture_integrity_snapshot(connection)


def format_integrity_report(snapshot: IntegritySnapshot) -> str:
    """Format an IntegritySnapshot as a PII-free Markdown verification table."""
    lines = [
        f"Alembic revision: `{snapshot.alembic_revision or 'none'}`",
        "",
        "| Table | Row Count | SHA-256 (prefix) |",
        "|---|---|---|",
    ]
    for table_name in TABLE_ORDER:
        info = snapshot.tables[table_name]
        lines.append(f"| `{info.table}` | {info.row_count} | `{info.sha256[:16]}` |")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for Neon backup/restore command generation and verification."""
    parser = argparse.ArgumentParser(
        description="Neon PostgreSQL backup, restore, and integrity verification."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_verify = sub.add_parser(
        "verify",
        help="Print Alembic revision, row counts, and SHA-256 digests (PII-free).",
    )
    p_verify.add_argument("--database-url", required=True)

    p_dump = sub.add_parser(
        "pg-dump-cmd",
        help="Print masked Neon pg_dump command for runbook execution.",
    )
    p_dump.add_argument("--database-url", required=True)
    p_dump.add_argument("--output", required=True)

    p_restore = sub.add_parser(
        "pg-restore-cmd",
        help="Print masked Neon pg_restore command for runbook execution.",
    )
    p_restore.add_argument("--database-url", required=True)
    p_restore.add_argument("--input", required=True)

    args = parser.parse_args(argv)

    if args.command == "pg-dump-cmd":
        cmd = build_pg_dump_command(args.database_url, args.output)
        masked_cmd = [
            f"--dbname={mask_database_url(args.database_url)}"
            if part.startswith("--dbname=")
            else part
            for part in cmd
        ]
        print(" ".join(masked_cmd))
        return 0

    if args.command == "pg-restore-cmd":
        cmd = build_pg_restore_command(args.database_url, args.input)
        masked_cmd = [
            f"--dbname={mask_database_url(args.database_url)}"
            if part.startswith("--dbname=")
            else part
            for part in cmd
        ]
        print(" ".join(masked_cmd))
        return 0

    from app.db.session import create_db_engine

    engine = create_db_engine(args.database_url)
    try:
        with engine.connect() as conn:
            snap = capture_integrity_snapshot(conn)
        print(format_integrity_report(snap))
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
