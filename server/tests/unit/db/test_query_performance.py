"""Unit tests for S2-NIT-6 query performance review and 0008 index fixes.

Responsibilities:
    - Verify all 12 hot-path queries use indexes with zero sequential scans
      and zero explicit sort / temp B-tree nodes after migration 0008.
    - Verify migration 0008_query_perf_indexes downgrade and upgrade roundtrip
      and offline PostgreSQL SQL generation.
    - Verify PostgreSQL EXPLAIN (ANALYZE, BUFFERS) output parsing across
      Index Scan Backward, Seq Scan, Sort, and timing lines.
    - Verify defensive failure cases: non-SELECT SQL rejection and invalid
      query-name filtering.

Owner: Nishith (Database) · Task: S2-NIT-6 · Requirements: NFR-01
"""

from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.db.query_perf import (
    explain_query,
    format_markdown_report,
    parse_postgres_explain_plan,
    run_query_performance_review,
    validate_read_only_sql,
)
from app.db.session import create_session_factory
from app.models.assessment import Assessment
from app.models.audit_log import AuditLog
from app.models.consent import Consent
from app.models.guest_session import GuestSession
from app.models.message import Message
from app.models.symptom import Symptom
from app.models.symptom_embedding import SymptomEmbedding
from app.models.user import User

SERVER = Path(__file__).resolve().parents[3]


def _seed_synthetic_dataset(engine: Engine) -> dict[str, object]:
    """Insert synthetic multi-table rows for realistic query plan verification."""
    factory = create_session_factory(engine)
    now = datetime.now(UTC)
    token_hash = "b" * 64
    model_revision = "1110a24"

    with factory.begin() as session:
        user = User(email="perf.synthetic@example.invalid")
        session.add(user)
        session.flush()

        guest = GuestSession(
            token_hash=token_hash,
            expires_at=now + timedelta(hours=12),
            claimed_by_user_id=user.id,
        )
        expired_guest = GuestSession(
            token_hash="c" * 64,
            created_at=now - timedelta(hours=48),
            expires_at=now - timedelta(hours=1),
        )
        session.add_all([guest, expired_guest])
        session.flush()

        consent_user = Consent(policy_version="v1.0")
        consent_guest = Consent(policy_version="v1.0")
        session.add_all([consent_user, consent_guest])
        session.flush()

        user_assessment = Assessment(
            user_id=user.id,
            consent_id=consent_user.id,
            state="COMPLETED",
        )
        guest_assessment = Assessment(
            user_id=None,
            guest_session_id=guest.id,
            consent_id=consent_guest.id,
            state="SYMPTOM_COLLECTION",
        )
        session.add_all([user_assessment, guest_assessment])
        session.flush()

        session.add_all(
            [
                Message(
                    assessment_id=user_assessment.id,
                    position=0,
                    role="user",
                    content="Synthetic fever description",
                ),
                Message(
                    assessment_id=user_assessment.id,
                    position=1,
                    role="assistant",
                    content="Synthetic clarification reply",
                ),
                Symptom(
                    assessment_id=user_assessment.id,
                    name="fever",
                    details={"severity": "moderate"},
                ),
                AuditLog(
                    action="ANALYSIS",
                    assessment_id=user_assessment.id,
                    user_id=user.id,
                    risk_level="CONSULT_DOCTOR",
                    risk_engine_version="v1.0",
                ),
                SymptomEmbedding(
                    symptom_id="fever",
                    phrase="high temperature",
                    model_revision=model_revision,
                    embedding=[0.0] * 384,
                ),
            ]
        )
        ids: dict[str, object] = {
            "user_id": user.id,
            "guest_session_id": guest.id,
            "assessment_id": user_assessment.id,
            "token_hash": token_hash,
            "model_revision": model_revision,
        }
    return ids


def test_all_hot_queries_use_indexes_without_seq_scan_or_sort(engine: Engine) -> None:
    """All 12 hot queries hit their indexes with zero table scans and zero sorts."""
    ids = _seed_synthetic_dataset(engine)
    factory = create_session_factory(engine)

    with factory() as session:
        reports = run_query_performance_review(
            session,
            user_id=ids["user_id"],  # type: ignore[arg-type]
            guest_session_id=ids["guest_session_id"],  # type: ignore[arg-type]
            assessment_id=ids["assessment_id"],  # type: ignore[arg-type]
            token_hash=str(ids["token_hash"]),
            model_revision=str(ids["model_revision"]),
        )

    assert len(reports) == 12
    for rep in reports:
        assert rep.uses_index is True, f"{rep.name} did not use an index: {rep}"
        assert rep.has_seq_scan is False, f"{rep.name} triggered seq scan: {rep}"
        assert rep.has_sort is False, f"{rep.name} triggered explicit sort: {rep}"

    markdown = format_markdown_report(reports)
    assert "| Query | Table | Dialect |" in markdown
    for rep in reports:
        assert f"`{rep.name}`" in markdown


def test_query_performance_review_on_empty_tables_and_subset_filter(
    engine: Engine,
) -> None:
    """Empty tables still produce valid indexed plans and support subset filtering."""
    factory = create_session_factory(engine)
    with factory() as session:
        subset = run_query_performance_review(
            session,
            only=["guest_history_unclaimed", "audit_logs_by_assessment"],
        )

    assert [r.name for r in subset] == [
        "guest_history_unclaimed",
        "audit_logs_by_assessment",
    ]
    for rep in subset:
        assert rep.uses_index is True
        assert rep.has_seq_scan is False
        assert rep.has_sort is False


def test_migration_0008_downgrade_and_upgrade_roundtrip(engine: Engine) -> None:
    """Revision 0008 cleanly drops its 5 indexes on downgrade and restores them."""
    config = Config(str(SERVER / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0007_history_indexes_pgvector")

    with engine.connect() as connection:
        inspector = inspect(connection)
        assert "ix_assessments_guest_session_id_created_at" not in {
            ix["name"] for ix in inspector.get_indexes("assessments")
        }
        assert "ix_guest_sessions_claimed_by_user_id" not in {
            ix["name"] for ix in inspector.get_indexes("guest_sessions")
        }
        audit_indexes = {ix["name"] for ix in inspector.get_indexes("audit_logs")}
        assert "ix_audit_logs_assessment_id_created_at" not in audit_indexes
        assert "ix_audit_logs_user_id_created_at" not in audit_indexes
        assert "ix_audit_logs_action_created_at" not in audit_indexes

    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    with engine.connect() as connection:
        inspector = inspect(connection)
        assert "ix_assessments_guest_session_id_created_at" in {
            ix["name"] for ix in inspector.get_indexes("assessments")
        }
        assert "ix_guest_sessions_claimed_by_user_id" in {
            ix["name"] for ix in inspector.get_indexes("guest_sessions")
        }
        audit_indexes = {ix["name"] for ix in inspector.get_indexes("audit_logs")}
        assert "ix_audit_logs_assessment_id_created_at" in audit_indexes
        assert "ix_audit_logs_user_id_created_at" in audit_indexes
        assert "ix_audit_logs_action_created_at" in audit_indexes


def test_offline_postgres_sql_includes_0008_indexes_and_valid_rev_len() -> None:
    """Offline PostgreSQL migration emits all 5 indexes and fits VARCHAR(32)."""
    output = StringIO()
    command.upgrade(
        Config(str(SERVER / "alembic.ini"), output_buffer=output), "head", sql=True
    )
    sql = output.getvalue()
    assert len("0008_query_perf_indexes") <= 32
    assert "0008_query_perf_indexes" in sql
    for expected_idx in (
        "ix_assessments_guest_session_id_created_at",
        "ix_guest_sessions_claimed_by_user_id",
        "ix_audit_logs_assessment_id_created_at",
        "ix_audit_logs_user_id_created_at",
        "ix_audit_logs_action_created_at",
    ):
        assert f"CREATE INDEX {expected_idx}" in sql


def test_parse_postgres_explain_plan_indexed_vs_degraded() -> None:
    """PostgreSQL EXPLAIN ANALYZE parser detects Index Scan Backward, Sort, Seq Scan."""
    indexed_lines = [
        "Limit  (cost=0.15..8.17 rows=20 width=96) "
        "(actual time=0.021..0.028 rows=2 loops=1)",
        "  Buffers: shared hit=3",
        "  ->  Index Scan Backward using ix_audit_logs_assessment_id_created_at "
        "on audit_logs  (cost=0.15..8.17 rows=20 width=96) "
        "(actual time=0.019..0.025 rows=2 loops=1)",
        "        Index Cond: (assessment_id = '00000000-0000-0000-0000-000000000001')",
        "Planning Time: 0.142 ms",
        "Execution Time: 0.056 ms",
    ]
    good = parse_postgres_explain_plan(
        "audit_logs_by_assessment",
        "audit_logs",
        "ix_audit_logs_assessment_id_created_at",
        indexed_lines,
    )
    assert good.uses_index is True
    assert good.indexes_used == ("ix_audit_logs_assessment_id_created_at",)
    assert good.has_seq_scan is False
    assert good.has_sort is False
    assert good.planning_time_ms == pytest.approx(0.142)
    assert good.execution_time_ms == pytest.approx(0.056)

    degraded_lines = [
        "Sort  (cost=25.40..25.90 rows=200 width=96) "
        "(actual time=1.420..1.450 rows=50 loops=1)",
        "  Sort Key: created_at DESC",
        "  ->  Seq Scan on guest_sessions  (cost=0.00..18.00 rows=200 width=96)",
        "Planning Time: 0.210 ms",
        "Execution Time: 1.512 ms",
    ]
    bad = parse_postgres_explain_plan(
        "guest_sessions_by_claimed_user",
        "guest_sessions",
        "ix_guest_sessions_claimed_by_user_id",
        degraded_lines,
    )
    assert bad.uses_index is False
    assert bad.has_seq_scan is True
    assert bad.has_sort is True
    assert bad.execution_time_ms == pytest.approx(1.512)


@pytest.mark.parametrize(
    "unsafe_sql",
    [
        "",
        "   ",
        "DELETE FROM users WHERE id = :id",
        "UPDATE assessments SET state = 'COMPLETED'",
        "DROP TABLE audit_logs",
        "SELECT id FROM users; DELETE FROM users",
    ],
)
def test_validate_and_explain_reject_non_select_sql(
    engine: Engine,
    unsafe_sql: str,
) -> None:
    """Mutating, blank, or multi-statement SQL is rejected before EXPLAIN."""
    with pytest.raises(ValueError):
        validate_read_only_sql(unsafe_sql)

    with engine.connect() as conn:
        with pytest.raises(ValueError):
            explain_query(conn, unsafe_sql, params={"id": str(uuid4())})


def test_run_query_performance_review_rejects_unknown_query_name(
    engine: Engine,
) -> None:
    """Requesting an unknown hot-query name raises ValueError."""
    factory = create_session_factory(engine)
    with factory() as session:
        with pytest.raises(ValueError, match="Unknown query name"):
            run_query_performance_review(session, only=["does_not_exist"])
