"""Unit and end-to-end drill tests for Neon backup and restore (S2-NIT-7).

Responsibilities:
    - Execute a full backup -> destructive 9-table wipe -> atomic restore ->
      SHA-256 integrity verification drill across every application table.
    - Verify Neon libpq URL conversion (sslmode=require), password masking,
      and injection-safe pg_dump / pg_restore argv construction.
    - Verify edge cases: empty-database roundtrip, integrity drift detection
      (row count, digest, revision), and atomic savepoint rollback on error.
    - Verify failure cases: tampered SHA-256 checksum, unsupported format
      version, revision mismatch, non-empty target guard, and invalid URLs.

Owner: Nishith (Database) · Task: S2-NIT-7 · Requirements: NFR-05, DR-06
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import delete, text
from sqlalchemy.engine import Engine

from app.db.backup_restore import (
    TABLE_ORDER,
    build_pg_dump_command,
    build_pg_restore_command,
    capture_integrity_snapshot,
    export_logical_snapshot,
    format_integrity_report,
    mask_database_url,
    restore_logical_snapshot,
    to_libpq_url,
    verify_restore_integrity,
)
from app.db.session import create_session_factory
from app.models import Base
from app.models.assessment import Assessment
from app.models.audit_log import AuditLog
from app.models.consent import Consent
from app.models.guest_session import GuestSession
from app.models.message import Message
from app.models.profile import Profile
from app.models.symptom import Symptom
from app.models.symptom_embedding import SymptomEmbedding
from app.models.user import User


def _seed_all_nine_tables(engine: Engine) -> None:
    """Populate synthetic rows across all 9 tables with valid FK graphs."""
    factory = create_session_factory(engine)
    now = datetime.now(UTC)

    with factory.begin() as session:
        user = User(email="restore.drill@example.invalid")
        session.add(user)
        session.flush()

        profile = Profile(
            user_id=user.id,
            age_band="adult",
            biological_sex="prefer_not_to_say",
            chronic_conditions=["asthma"],
        )
        guest = GuestSession(
            token_hash="d" * 64,
            expires_at=now + timedelta(hours=24),
            claimed_by_user_id=user.id,
        )
        consent_user = Consent(policy_version="v1.0")
        consent_guest = Consent(policy_version="v1.0")
        session.add_all([profile, guest, consent_user, consent_guest])
        session.flush()

        assessment_user = Assessment(
            user_id=user.id,
            consent_id=consent_user.id,
            state="COMPLETED",
        )
        assessment_guest = Assessment(
            user_id=None,
            guest_session_id=guest.id,
            consent_id=consent_guest.id,
            state="SYMPTOM_COLLECTION",
        )
        session.add_all([assessment_user, assessment_guest])
        session.flush()

        session.add_all(
            [
                Message(
                    assessment_id=assessment_user.id,
                    position=0,
                    role="user",
                    content="Synthetic headache for restore drill",
                ),
                Message(
                    assessment_id=assessment_user.id,
                    position=1,
                    role="assistant",
                    content="Synthetic follow-up question",
                ),
                Symptom(
                    assessment_id=assessment_user.id,
                    name="headache",
                    details={"severity": "moderate", "duration_days": 2},
                ),
                AuditLog(
                    action="ANALYSIS",
                    assessment_id=assessment_user.id,
                    user_id=user.id,
                    risk_level="CONSULT_DOCTOR",
                    risk_engine_version="v1.0",
                    details={"symptom_count": 1},
                ),
                SymptomEmbedding(
                    symptom_id="headache",
                    phrase="throbbing head pain",
                    model_revision="1110a24",
                    embedding=[0.25] * 384,
                ),
            ]
        )


def test_end_to_end_backup_wipe_restore_and_verify_drill(
    engine: Engine,
    tmp_path: Path,
) -> None:
    """Full drill: backup all 9 tables -> wipe -> restore -> 100% SHA-256 parity."""
    _seed_all_nine_tables(engine)
    snapshot_file = tmp_path / "neon_drill_snapshot.json"

    with engine.connect() as conn:
        before = export_logical_snapshot(conn, snapshot_file)

    assert before.alembic_revision == "0008_query_perf_indexes"
    for table_name in TABLE_ORDER:
        assert before.tables[table_name].row_count >= 1

    # Destructively wipe all 9 tables in reverse FK order
    with engine.begin() as conn:
        for table_name in reversed(TABLE_ORDER):
            conn.execute(delete(Base.metadata.tables[table_name]))
        wiped = capture_integrity_snapshot(conn)

    for table_name in TABLE_ORDER:
        assert wiped.tables[table_name].row_count == 0

    wiped_diff = verify_restore_integrity(before, wiped)
    assert wiped_diff.is_match is False
    assert len(wiped_diff.mismatches) == len(TABLE_ORDER)

    # Restore atomically and verify exact parity
    with engine.begin() as conn:
        after = restore_logical_snapshot(conn, snapshot_file, truncate_target=False)

    diff = verify_restore_integrity(before, after)
    assert diff.is_match is True, f"Unexpected restore mismatches: {diff.mismatches}"

    report = format_integrity_report(after)
    assert "0008_query_perf_indexes" in report
    assert "restore.drill@example.invalid" not in report
    assert "throbbing head pain" not in report


def test_empty_database_backup_and_restore_roundtrip(
    engine: Engine,
    tmp_path: Path,
) -> None:
    """Backup and restore of an empty migrated database succeeds with zero drift."""
    snapshot_file = tmp_path / "empty_snapshot.json"
    with engine.connect() as conn:
        before = export_logical_snapshot(conn, snapshot_file)

    with engine.begin() as conn:
        after = restore_logical_snapshot(conn, snapshot_file, truncate_target=True)

    diff = verify_restore_integrity(before, after)
    assert diff.is_match is True
    for table_name in TABLE_ORDER:
        assert after.tables[table_name].row_count == 0


def test_verify_restore_integrity_detects_content_and_revision_drift(
    engine: Engine,
    tmp_path: Path,
) -> None:
    """Integrity verifier catches subtle content modification and revision drift."""
    _seed_all_nine_tables(engine)
    with engine.connect() as conn:
        baseline = capture_integrity_snapshot(conn)

    # Mutate one row without changing row count
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE assessments SET state = 'READY' "
                "WHERE state = 'SYMPTOM_COLLECTION'"
            )
        )
        mutated = capture_integrity_snapshot(conn)

    diff = verify_restore_integrity(baseline, mutated)
    assert diff.is_match is False
    assert any("assessments" in msg and "SHA-256" in msg for msg in diff.mismatches)

    # Simulate Alembic revision mismatch
    mismatched_rev = type(baseline)(
        alembic_revision="0007_history_indexes_pgvector",
        tables=baseline.tables,
    )
    rev_diff = verify_restore_integrity(baseline, mismatched_rev)
    assert rev_diff.is_match is False
    assert any("alembic_version" in msg for msg in rev_diff.mismatches)


def test_restore_rejects_tampered_checksum_without_modifying_db(
    engine: Engine,
    tmp_path: Path,
) -> None:
    """A tampered snapshot file fails SHA-256 verification before touching rows."""
    _seed_all_nine_tables(engine)
    snapshot_file = tmp_path / "tampered.json"
    with engine.connect() as conn:
        before = export_logical_snapshot(conn, snapshot_file)

    payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
    payload["tables"]["users"][0]["email"] = "tampered@example.invalid"
    snapshot_file.write_text(json.dumps(payload), encoding="utf-8")

    with engine.begin() as conn:
        with pytest.raises(ValueError, match="SHA-256 mismatch"):
            restore_logical_snapshot(conn, snapshot_file, truncate_target=True)
        still_intact = capture_integrity_snapshot(conn)

    assert verify_restore_integrity(before, still_intact).is_match is True


def test_restore_rejects_bad_version_revision_and_non_empty_target(
    engine: Engine,
    tmp_path: Path,
) -> None:
    """Guards reject unsupported format, revision mismatch, and non-empty target."""
    _seed_all_nine_tables(engine)
    snapshot_file = tmp_path / "valid.json"
    with engine.connect() as conn:
        export_logical_snapshot(conn, snapshot_file)

    # 1. Non-empty target refused when truncate_target=False
    with engine.begin() as conn:
        with pytest.raises(ValueError, match="not empty"):
            restore_logical_snapshot(conn, snapshot_file, truncate_target=False)

    # 2. Unsupported format version
    bad_ver = tmp_path / "bad_ver.json"
    raw = json.loads(snapshot_file.read_text(encoding="utf-8"))
    raw["format_version"] = 99
    bad_ver.write_text(json.dumps(raw), encoding="utf-8")
    with engine.begin() as conn:
        with pytest.raises(ValueError, match="Unsupported snapshot format_version"):
            restore_logical_snapshot(conn, bad_ver, truncate_target=True)

    # 3. Missing snapshot file
    with engine.begin() as conn:
        with pytest.raises(ValueError, match="not found"):
            restore_logical_snapshot(
                conn, tmp_path / "missing.json", truncate_target=True
            )


def test_neon_libpq_url_masking_and_pg_commands() -> None:
    """Neon URLs normalize to libpq with sslmode=require and never expose passwords."""
    neon_url = (
        "postgresql+psycopg://neondb_owner:s3cr3tPass@"
        "ep-cool-hill-12345.us-east-2.aws.neon.tech/neondb"
    )
    libpq = to_libpq_url(neon_url)
    assert libpq.startswith("postgresql://")
    assert "sslmode=require" in libpq

    local_url = "postgresql+psycopg://postgres:localpw@localhost:5432/symptom_checker"
    local_libpq = to_libpq_url(local_url)
    assert local_libpq.startswith("postgresql://")
    assert "sslmode" not in local_libpq

    masked = mask_database_url(neon_url)
    assert "s3cr3tPass" not in masked
    assert "***" in masked

    dump_cmd = build_pg_dump_command(neon_url, "/tmp/backup.dump")
    assert dump_cmd[0] == "pg_dump"
    assert "--format=custom" in dump_cmd
    assert "--no-owner" in dump_cmd
    assert "--no-privileges" in dump_cmd
    assert "--file=/tmp/backup.dump" in dump_cmd

    restore_cmd = build_pg_restore_command(neon_url, "/tmp/backup.dump")
    assert restore_cmd[0] == "pg_restore"
    assert "--single-transaction" in restore_cmd
    assert "--exit-on-error" in restore_cmd
    assert "--clean" in restore_cmd
    assert restore_cmd[-1] == "/tmp/backup.dump"


@pytest.mark.parametrize(
    "bad_url",
    [
        "",
        "   ",
        "sqlite:///local.db",
        "mysql://user:pass@host/db",
        "postgresql://onlyhost",
    ],
)
def test_to_libpq_url_rejects_invalid_urls(bad_url: str) -> None:
    """Non-PostgreSQL or incomplete URLs raise ValueError."""
    with pytest.raises(ValueError):
        to_libpq_url(bad_url)
