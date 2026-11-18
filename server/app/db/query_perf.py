"""Query performance review runner using EXPLAIN ANALYZE / EXPLAIN QUERY PLAN.

Responsibilities:
    - Catalog the 12 hot-path read queries across assessments, messages,
      symptoms, guest sessions, audit logs, and symptom embeddings.
    - Execute read-only EXPLAIN (ANALYZE, BUFFERS) on PostgreSQL (Neon staging
      or local Docker) and EXPLAIN QUERY PLAN on SQLite (offline unit tests).
    - Parse execution plans to detect sequential table scans, explicit sort
      nodes, index usage, and timing metrics (NFR-01).
    - Reject non-SELECT statements defensively and never log PII.

Owner: Nishith (Database) · Task: S2-NIT-6 · Requirements: NFR-01
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Select, desc, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.sql.base import Executable
from sqlalchemy.sql.elements import ClauseElement

from app.models.assessment import Assessment
from app.models.audit_log import AuditLog
from app.models.guest_session import GuestSession
from app.models.message import Message
from app.models.symptom import Symptom
from app.models.symptom_embedding import SymptomEmbedding

_POSTGRES_INDEX_RE = re.compile(
    r"(?:Index Only Scan|Index Scan|Bitmap Index Scan)"
    r"(?: Backward)? using\s+([a-zA-Z0-9_]+)"
)
_POSTGRES_SEQ_SCAN_RE = re.compile(r"\bSeq Scan on\s+[a-zA-Z0-9_]+")
_POSTGRES_SORT_RE = re.compile(r"(?:^|\s|->\s*)Sort\s+\(cost=")
_POSTGRES_PLANNING_MS_RE = re.compile(r"Planning Time:\s*([0-9]+(?:\.[0-9]+)?)\s*ms")
_POSTGRES_EXECUTION_MS_RE = re.compile(r"Execution Time:\s*([0-9]+(?:\.[0-9]+)?)\s*ms")

_SQLITE_INDEX_RE = re.compile(r"USING (?:COVERING )?INDEX\s+([a-zA-Z0-9_]+)")
_SQLITE_SEQ_SCAN_RE = re.compile(
    r"^SCAN\s+[a-zA-Z0-9_]+(?!.*USING (?:COVERING )?INDEX)"
)
_SQLITE_SORT_RE = re.compile(r"USE TEMP B-TREE FOR ORDER BY")

_READ_ONLY_PREFIX_RE = re.compile(r"^\s*(?:WITH\b.*\bSELECT\b|SELECT\b)", re.I | re.S)
_MUTATING_SQL_RE = re.compile(
    r"\b(?:INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
    re.I,
)


@dataclass(frozen=True)
class QuerySpec:
    """Definition of a cataloged hot-path read query for plan inspection."""

    name: str
    table: str
    description: str
    expected_index_hint: str
    statement: Select[Any]


@dataclass(frozen=True)
class QueryPlanReport:
    """Structured result of running EXPLAIN / EXPLAIN ANALYZE on one query."""

    name: str
    table: str
    dialect: str
    expected_index_hint: str
    uses_index: bool
    indexes_used: tuple[str, ...]
    has_seq_scan: bool
    has_sort: bool
    planning_time_ms: float | None
    execution_time_ms: float | None
    plan_lines: tuple[str, ...]


def validate_read_only_sql(sql: str) -> str:
    """Ensure raw SQL passed to EXPLAIN is strictly a read-only SELECT query.

    Args:
        sql: Candidate SQL string.

    Returns:
        Stripped SQL string.

    Raises:
        ValueError: If SQL is empty, contains multiple statements, or is not
            a read-only SELECT query.
    """
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise ValueError("SQL statement for EXPLAIN must not be blank.")
    if ";" in cleaned:
        raise ValueError("EXPLAIN only accepts a single SQL statement.")
    if not _READ_ONLY_PREFIX_RE.match(cleaned) or _MUTATING_SQL_RE.search(cleaned):
        raise ValueError("EXPLAIN only permits read-only SELECT statements.")
    return cleaned


def parse_postgres_explain_plan(
    name: str,
    table: str,
    expected_index_hint: str,
    plan_lines: Sequence[str],
) -> QueryPlanReport:
    """Parse PostgreSQL EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) output.

    Args:
        name: Logical name of the benchmarked query.
        table: Primary target table name.
        expected_index_hint: Expected index name (or prefix) for documentation.
        plan_lines: Lines returned by PostgreSQL EXPLAIN output.

    Returns:
        Structured QueryPlanReport with scan, sort, and timing indicators.
    """
    lines = tuple(line.rstrip() for line in plan_lines)
    indexes: list[str] = []
    has_seq_scan = False
    has_sort = False
    planning_ms: float | None = None
    execution_ms: float | None = None

    for line in lines:
        for match in _POSTGRES_INDEX_RE.finditer(line):
            idx = match.group(1)
            if idx not in indexes:
                indexes.append(idx)
        if _POSTGRES_SEQ_SCAN_RE.search(line):
            has_seq_scan = True
        if _POSTGRES_SORT_RE.search(line):
            has_sort = True
        plan_match = _POSTGRES_PLANNING_MS_RE.search(line)
        if plan_match:
            planning_ms = float(plan_match.group(1))
        exec_match = _POSTGRES_EXECUTION_MS_RE.search(line)
        if exec_match:
            execution_ms = float(exec_match.group(1))

    return QueryPlanReport(
        name=name,
        table=table,
        dialect="postgresql",
        expected_index_hint=expected_index_hint,
        uses_index=bool(indexes),
        indexes_used=tuple(indexes),
        has_seq_scan=has_seq_scan,
        has_sort=has_sort,
        planning_time_ms=planning_ms,
        execution_time_ms=execution_ms,
        plan_lines=lines,
    )


def parse_sqlite_explain_plan(
    name: str,
    table: str,
    expected_index_hint: str,
    plan_lines: Sequence[str],
) -> QueryPlanReport:
    """Parse SQLite EXPLAIN QUERY PLAN detail lines.

    Args:
        name: Logical name of the benchmarked query.
        table: Primary target table name.
        expected_index_hint: Expected index name (or prefix) for documentation.
        plan_lines: Detail strings from SQLite EXPLAIN QUERY PLAN rows.

    Returns:
        Structured QueryPlanReport with scan and temp B-tree sort indicators.
    """
    lines = tuple(line.strip() for line in plan_lines)
    indexes: list[str] = []
    has_seq_scan = False
    has_sort = False

    for line in lines:
        for match in _SQLITE_INDEX_RE.finditer(line):
            idx = match.group(1)
            if idx not in indexes:
                indexes.append(idx)
        if "USING PRIMARY KEY" in line and "PRIMARY_KEY" not in indexes:
            indexes.append("PRIMARY_KEY")
        if _SQLITE_SEQ_SCAN_RE.match(line):
            has_seq_scan = True
        if _SQLITE_SORT_RE.search(line):
            has_sort = True

    return QueryPlanReport(
        name=name,
        table=table,
        dialect="sqlite",
        expected_index_hint=expected_index_hint,
        uses_index=bool(indexes),
        indexes_used=tuple(indexes),
        has_seq_scan=has_seq_scan,
        has_sort=has_sort,
        planning_time_ms=None,
        execution_time_ms=None,
        plan_lines=lines,
    )


def build_hot_query_catalog(
    *,
    user_id: UUID | None = None,
    guest_session_id: UUID | None = None,
    assessment_id: UUID | None = None,
    token_hash: str | None = None,
    model_revision: str = "1110a24",
    action: str = "ANALYSIS",
    reference_time: datetime | None = None,
) -> list[QuerySpec]:
    """Build the 12 canonical hot-path read queries across the schema.

    Uses caller-provided synthetic IDs or random UUIDs so plans can be
    inspected without touching real user data (AI_RULES.md §2.12).
    """
    uid = user_id or uuid4()
    gs_id = guest_session_id or uuid4()
    aid = assessment_id or uuid4()
    tok = token_hash or ("a" * 64)
    now = reference_time or datetime.now(UTC)
    since = now - timedelta(days=7)

    return [
        QuerySpec(
            name="user_history_paginated",
            table="assessments",
            description="Paginated assessment history for a registered user",
            expected_index_hint="ix_assessments_user_id_created_at",
            statement=(
                select(Assessment)
                .where(Assessment.user_id == uid)
                .order_by(desc(Assessment.created_at))
                .limit(20)
            ),
        ),
        QuerySpec(
            name="user_history_by_state",
            table="assessments",
            description="State-filtered assessment history for a registered user",
            expected_index_hint="ix_assessments_user_id_state_created_at",
            statement=(
                select(Assessment)
                .where(Assessment.user_id == uid, Assessment.state == "COMPLETED")
                .order_by(desc(Assessment.created_at))
                .limit(20)
            ),
        ),
        QuerySpec(
            name="guest_history_unclaimed",
            table="assessments",
            description="Paginated unclaimed assessment history for a guest session",
            expected_index_hint="ix_assessments_guest_session_id_created_at",
            statement=(
                select(Assessment)
                .where(
                    Assessment.guest_session_id == gs_id,
                    Assessment.user_id.is_(None),
                )
                .order_by(desc(Assessment.created_at))
                .limit(20)
            ),
        ),
        QuerySpec(
            name="assessment_messages_ordered",
            table="messages",
            description="Ordered message transcript load for an assessment",
            expected_index_hint="uq_messages_assessment_id_position",
            statement=(
                select(Message)
                .where(Message.assessment_id == aid)
                .order_by(Message.position.asc())
            ),
        ),
        QuerySpec(
            name="assessment_symptoms_lookup",
            table="symptoms",
            description="Structured symptom fetch for an assessment",
            expected_index_hint="ix_symptoms_assessment_id",
            statement=select(Symptom).where(Symptom.assessment_id == aid),
        ),
        QuerySpec(
            name="guest_session_token_lookup",
            table="guest_sessions",
            description="Bearer token SHA-256 lookup for anonymous guest session",
            expected_index_hint="uq_guest_sessions_token_hash",
            statement=select(GuestSession).where(GuestSession.token_hash == tok),
        ),
        QuerySpec(
            name="expired_guest_sessions_purge",
            table="guest_sessions",
            description="Scheduled TTL purge scan for expired guest sessions",
            expected_index_hint="ix_guest_sessions_expires_at",
            statement=select(GuestSession.id).where(GuestSession.expires_at < now),
        ),
        QuerySpec(
            name="guest_sessions_by_claimed_user",
            table="guest_sessions",
            description="FK SET NULL lookup on guest_sessions during user deletion",
            expected_index_hint="ix_guest_sessions_claimed_by_user_id",
            statement=select(GuestSession.id).where(
                GuestSession.claimed_by_user_id == uid
            ),
        ),
        QuerySpec(
            name="audit_logs_by_assessment",
            table="audit_logs",
            description="Newest-first audit entries for a single assessment",
            expected_index_hint="ix_audit_logs_assessment_id_created_at",
            statement=(
                select(AuditLog)
                .where(AuditLog.assessment_id == aid)
                .order_by(desc(AuditLog.created_at))
                .limit(50)
            ),
        ),
        QuerySpec(
            name="audit_logs_by_user",
            table="audit_logs",
            description="Newest-first audit entries for a registered user",
            expected_index_hint="ix_audit_logs_user_id_created_at",
            statement=(
                select(AuditLog)
                .where(AuditLog.user_id == uid)
                .order_by(desc(AuditLog.created_at))
                .limit(50)
            ),
        ),
        QuerySpec(
            name="audit_logs_by_action_window",
            table="audit_logs",
            description="Time-windowed compliance query filtered by action",
            expected_index_hint="ix_audit_logs_action_created_at",
            statement=(
                select(AuditLog)
                .where(AuditLog.action == action, AuditLog.created_at >= since)
                .order_by(desc(AuditLog.created_at))
                .limit(50)
            ),
        ),
        QuerySpec(
            name="symptom_embeddings_by_revision",
            table="symptom_embeddings",
            description="Exact scan of ~700 embeddings for pinned revision (DR-02)",
            expected_index_hint="ix_symptom_embeddings_model_revision",
            statement=select(SymptomEmbedding.id).where(
                SymptomEmbedding.model_revision == model_revision
            ),
        ),
    ]


def explain_query(
    connection: Connection,
    sql: str,
    params: Mapping[str, Any] | None = None,
    *,
    name: str = "custom_query",
    table: str = "unknown",
    expected_index_hint: str = "",
    analyze: bool = True,
) -> QueryPlanReport:
    """Run EXPLAIN / EXPLAIN ANALYZE for a validated read-only SELECT query.

    Args:
        connection: Active SQLAlchemy Connection (PostgreSQL or SQLite).
        sql: Read-only SELECT SQL string.
        params: Optional bound parameters mapping.
        name: Logical query identifier for reporting.
        table: Primary table name for reporting.
        expected_index_hint: Expected index name hint.
        analyze: On PostgreSQL, run ``EXPLAIN (ANALYZE, BUFFERS)`` when True,
            otherwise ``EXPLAIN (FORMAT TEXT)``.

    Returns:
        Parsed QueryPlanReport.

    Raises:
        ValueError: If SQL is not a safe read-only SELECT or dialect is
            unsupported.
    """
    cleaned = validate_read_only_sql(sql)
    dialect_name = connection.dialect.name
    bound_params = dict(params or {})

    if dialect_name == "postgresql":
        prefix = (
            "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) "
            if analyze
            else "EXPLAIN (FORMAT TEXT) "
        )
        rows = connection.execute(text(prefix + cleaned), bound_params).fetchall()
        plan_lines = [str(row[0]) for row in rows]
        return parse_postgres_explain_plan(name, table, expected_index_hint, plan_lines)

    if dialect_name == "sqlite":
        rows = connection.execute(
            text("EXPLAIN QUERY PLAN " + cleaned), bound_params
        ).fetchall()
        # SQLite EXPLAIN QUERY PLAN returns (id, parent, notused, detail)
        plan_lines = [str(row[-1]) for row in rows]
        return parse_sqlite_explain_plan(name, table, expected_index_hint, plan_lines)

    raise ValueError(
        f"Unsupported dialect for query performance review: {dialect_name}"
    )


class _Explain(Executable, ClauseElement):
    """Dialect-aware SQLAlchemy EXPLAIN clause preserving bound parameter types."""

    inherit_cache = False

    def __init__(self, statement: Select[Any], *, analyze: bool = True) -> None:
        self.statement = statement
        self.analyze = analyze


@compiles(_Explain, "postgresql")
def _compile_pg_explain(element: _Explain, compiler: Any, **kw: Any) -> str:
    prefix = (
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) "
        if element.analyze
        else "EXPLAIN (FORMAT TEXT) "
    )
    return prefix + str(compiler.process(element.statement, **kw))


@compiles(_Explain, "sqlite")
def _compile_sqlite_explain(element: _Explain, compiler: Any, **kw: Any) -> str:
    return "EXPLAIN QUERY PLAN " + str(compiler.process(element.statement, **kw))


def explain_select(
    connection: Connection,
    spec: QuerySpec,
    *,
    analyze: bool = True,
) -> QueryPlanReport:
    """Execute a dialect-aware EXPLAIN / EXPLAIN ANALYZE on a Select QuerySpec."""
    dialect_name = connection.dialect.name
    if dialect_name not in {"postgresql", "sqlite"}:
        raise ValueError(
            f"Unsupported dialect for query performance review: {dialect_name}"
        )

    result = connection.execute(_Explain(spec.statement, analyze=analyze))
    # Fetch raw DBAPI tuples so EXPLAIN rows bypass the inner SELECT's column processors
    rows = result.cursor.fetchall() if result.cursor is not None else result.fetchall()
    result.close()
    if dialect_name == "postgresql":
        plan_lines = [str(row[0]) for row in rows]
        return parse_postgres_explain_plan(
            spec.name, spec.table, spec.expected_index_hint, plan_lines
        )

    plan_lines = [str(row[-1]) for row in rows]
    return parse_sqlite_explain_plan(
        spec.name, spec.table, spec.expected_index_hint, plan_lines
    )


def run_query_performance_review(
    session_or_conn: Session | Connection,
    *,
    only: Sequence[str] | None = None,
    user_id: UUID | None = None,
    guest_session_id: UUID | None = None,
    assessment_id: UUID | None = None,
    token_hash: str | None = None,
    model_revision: str = "1110a24",
    action: str = "ANALYSIS",
    analyze: bool = True,
) -> list[QueryPlanReport]:
    """Execute EXPLAIN review across all (or selected) cataloged hot queries.

    Args:
        session_or_conn: Active SQLAlchemy Session or Connection.
        only: Optional subset of query names to execute.
        user_id: Optional synthetic user UUID present in the database.
        guest_session_id: Optional synthetic guest session UUID.
        assessment_id: Optional synthetic assessment UUID.
        token_hash: Optional synthetic 64-hex token hash.
        model_revision: Pinned embedding revision string.
        action: Audit log action string.
        analyze: Whether to run ANALYZE on PostgreSQL.

    Returns:
        List of QueryPlanReport results in catalog order.

    Raises:
        ValueError: If ``only`` contains an unknown query name.
    """
    catalog = build_hot_query_catalog(
        user_id=user_id,
        guest_session_id=guest_session_id,
        assessment_id=assessment_id,
        token_hash=token_hash,
        model_revision=model_revision,
        action=action,
    )

    if only is not None:
        known = {spec.name for spec in catalog}
        unknown = [q for q in only if q not in known]
        if unknown:
            raise ValueError(
                f"Unknown query name(s): {', '.join(unknown)}. "
                f"Available: {', '.join(sorted(known))}."
            )
        selected_set = set(only)
        catalog = [spec for spec in catalog if spec.name in selected_set]

    conn = (
        session_or_conn.connection()
        if isinstance(session_or_conn, Session)
        else session_or_conn
    )
    return [explain_select(conn, spec, analyze=analyze) for spec in catalog]


def format_markdown_report(reports: Sequence[QueryPlanReport]) -> str:
    """Format QueryPlanReport entries as a Markdown summary table."""
    header = (
        "| Query | Table | Dialect | Index Used "
        "| Seq Scan | Explicit Sort | Exec (ms) |"
    )
    lines = [
        header,
        "|---|---|---|---|---|---|---|",
    ]
    for rep in reports:
        idx_text = ", ".join(rep.indexes_used) if rep.indexes_used else "*(none)*"
        exec_text = (
            f"{rep.execution_time_ms:.2f}"
            if rep.execution_time_ms is not None
            else "n/a"
        )
        lines.append(
            f"| `{rep.name}` | `{rep.table}` | {rep.dialect} | `{idx_text}` "
            f"| {'YES' if rep.has_seq_scan else 'no'} "
            f"| {'YES' if rep.has_sort else 'no'} | {exec_text} |"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: run EXPLAIN ANALYZE review against a target database."""
    parser = argparse.ArgumentParser(
        description="Run S2-NIT-6 EXPLAIN ANALYZE query performance review."
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="SQLAlchemy database URL (defaults to Settings.database_url).",
    )
    parser.add_argument(
        "--no-analyze",
        action="store_true",
        help="Run EXPLAIN without ANALYZE on PostgreSQL.",
    )
    args = parser.parse_args(argv)

    from app.core.config import get_settings
    from app.db.session import create_db_engine

    url = args.database_url or get_settings().database_url
    engine = create_db_engine(url)
    try:
        with engine.connect() as conn:
            reports = run_query_performance_review(
                conn,
                analyze=not args.no_analyze,
            )
        print(format_markdown_report(reports))
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
