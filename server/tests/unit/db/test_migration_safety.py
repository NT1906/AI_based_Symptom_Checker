"""Migration safety review: backward compatibility and rollback drills.

Responsibilities:
    - Verify strict linear migration history without branches or multiple heads.
    - Validate step-by-step forward upgrade and backward downgrade across revisions.
    - Confirm zero-downtime backward compatibility (additive DDL, safe column defaults).
    - Test rollback with populated data ensuring zero corruption of unrelated records.
    - Validate offline PostgreSQL DDL generation for upgrades and downgrades.

Owner: Kavya (Database) · Task: S2-KAV-7 · Requirements: NFR-05, FR-01, FR-02, DR-06
"""

from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

SERVER = Path(__file__).resolve().parents[3]

EXPECTED_LINEAR_REVISIONS: list[str] = [
    "0001_database_foundation",
    "0002_hot_query_indexes",
    "0003_guest_sessions",
    "0004_symptom_structured_details",
    "0005_user_profile",
    "0006_audit_log",
    "0007_history_indexes_pgvector",
    "0008_query_perf_indexes",
    "0009_assessment_result",
]


class TestLinearRevisionChain:
    """Validate Alembic revision chain structure and integrity."""

    def test_strictly_linear_history_no_branches_or_forks(self) -> None:
        """Every revision has exactly one parent forming a single linear chain."""
        config = Config(str(SERVER / "alembic.ini"))
        script = ScriptDirectory.from_config(config)

        heads = script.get_heads()
        assert len(heads) == 1, f"Expected exactly 1 migration head, got: {heads}"
        assert heads[0] == "0009_assessment_result"

        revisions = list(script.walk_revisions("base", "head"))
        assert len(revisions) == len(EXPECTED_LINEAR_REVISIONS)

        forward_revisions = [rev.revision for rev in reversed(revisions)]
        assert forward_revisions == EXPECTED_LINEAR_REVISIONS

        # Verify parent-child links without forks
        for i, rev in enumerate(reversed(revisions)):
            expected_down = EXPECTED_LINEAR_REVISIONS[i - 1] if i > 0 else None
            assert rev.down_revision == expected_down, (
                f"Revision {rev.revision} should have down_revision "
                f"{expected_down}, but got {rev.down_revision}"
            )


class TestBidirectionalMigrationStepByStep:
    """Validate step-by-step forward upgrade and backward downgrade."""

    def test_step_by_step_forward_upgrade_and_backward_downgrade(self) -> None:
        """Step-by-step forward upgrade and backward downgrade execute cleanly."""
        engine = create_engine("sqlite://", hide_parameters=True)
        config = Config(str(SERVER / "alembic.ini"))
        script = ScriptDirectory.from_config(config)

        with engine.begin() as conn:
            config.attributes["connection"] = conn

            # 1. Forward upgrade step by step
            for rev in reversed(list(script.walk_revisions("base", "head"))):
                command.upgrade(config, rev.revision)
                inspector = inspect(conn)
                tables = set(inspector.get_table_names())

                if rev.revision == "0001_database_foundation":
                    assert {
                        "users",
                        "consents",
                        "assessments",
                        "messages",
                        "symptoms",
                    }.issubset(tables)
                elif rev.revision == "0003_guest_sessions":
                    assert "guest_sessions" in tables
                    cols = {c["name"] for c in inspector.get_columns("assessments")}
                    assert "guest_session_id" in cols
                elif rev.revision == "0004_symptom_structured_details":
                    cols = {c["name"] for c in inspector.get_columns("symptoms")}
                    assert "details" in cols
                elif rev.revision == "0005_user_profile":
                    assert "profiles" in tables
                elif rev.revision == "0006_audit_log":
                    assert "audit_logs" in tables
                elif rev.revision == "0007_history_indexes_pgvector":
                    assert "symptom_embeddings" in tables
                elif rev.revision == "0009_assessment_result":
                    cols = {c["name"] for c in inspector.get_columns("assessments")}
                    assert "result" in cols

            # 2. Backward downgrade step by step
            for rev in list(script.walk_revisions("base", "head")):
                target = rev.down_revision or "base"
                target_rev = (
                    target[0] if isinstance(target, (list, tuple)) else str(target)
                )
                command.downgrade(config, target_rev)
                inspector = inspect(conn)
                tables = set(inspector.get_table_names())

                if rev.revision == "0009_assessment_result":
                    cols = {c["name"] for c in inspector.get_columns("assessments")}
                    assert "result" not in cols
                elif rev.revision == "0007_history_indexes_pgvector":
                    assert "symptom_embeddings" not in tables
                elif rev.revision == "0006_audit_log":
                    assert "audit_logs" not in tables
                elif rev.revision == "0005_user_profile":
                    assert "profiles" not in tables
                elif rev.revision == "0003_guest_sessions":
                    assert "guest_sessions" not in tables
                elif rev.revision == "0001_database_foundation":
                    assert set(inspector.get_table_names()) == {"alembic_version"}


class TestBackwardCompatibilityAndZeroDowntime:
    """Validate zero-downtime and non-destructive schema modification invariants."""

    def test_all_upgrades_are_strictly_additive(self) -> None:
        """No upgrade operation drops existing tables or columns."""
        versions_dir = SERVER / "alembic" / "versions"
        destructive_keywords = [
            "op.drop_table",
            "op.drop_column",
            "op.drop_constraint",
        ]

        for filepath in versions_dir.glob("*.py"):
            content = filepath.read_text(encoding="utf-8")
            upgrade_def = content.split("def upgrade()")[1].split("def downgrade()")[0]

            for keyword in destructive_keywords:
                assert keyword not in upgrade_def, (
                    f"Found destructive keyword '{keyword}' in upgrade() "
                    f"of {filepath.name}. Upgrades must be strictly additive."
                )

    def test_columns_added_to_existing_tables_are_safe_for_rolling_deploys(
        self,
    ) -> None:
        """Columns added to existing tables are nullable or have constant defaults."""
        # Check 0003: assessments.guest_session_id (nullable=True)
        # Check 0004: symptoms.details (server_default='{}')
        # Check 0009: assessments.result (nullable=True)
        file_0003 = (
            SERVER / "alembic" / "versions" / "0003_guest_sessions.py"
        ).read_text(encoding="utf-8")
        assert "nullable=True" in file_0003

        file_0004 = (
            SERVER / "alembic" / "versions" / "0004_symptom_structured_details.py"
        ).read_text(encoding="utf-8")
        assert "server_default=sa.text(\"'{}'\")" in file_0004

        file_0009 = (
            SERVER / "alembic" / "versions" / "0009_assessment_result.py"
        ).read_text(encoding="utf-8")
        assert "nullable=True" in file_0009


class TestRollbackWithDataPreservation:
    """Validate rollback drills with populated baseline clinical records."""

    def test_rollback_0009_preserves_assessments_and_related_records(
        self,
    ) -> None:
        """Rolling back 0009 preserves assessments and related entities."""
        engine = create_engine("sqlite://", hide_parameters=True)
        config = Config(str(SERVER / "alembic.ini"))

        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, "head")

            user_id = uuid4().hex
            consent_id = uuid4().hex
            assessment_id = uuid4().hex
            message_id = uuid4().hex
            symptom_id = uuid4().hex

            conn.execute(
                text("INSERT INTO users (id, email) VALUES (:id, :email)"),
                {"id": user_id, "email": "rollback-test@example.invalid"},
            )
            conn.execute(
                text("INSERT INTO consents (id, policy_version) VALUES (:id, :v)"),
                {"id": consent_id, "v": "v1.0"},
            )
            conn.execute(
                text(
                    "INSERT INTO assessments (id, user_id, consent_id, state, result) "
                    "VALUES (:id, :uid, :cid, :state, :result)"
                ),
                {
                    "id": assessment_id,
                    "uid": user_id,
                    "cid": consent_id,
                    "state": "COMPLETED",
                    "result": '{"risk_level": "URGENT"}',
                },
            )
            conn.execute(
                text(
                    "INSERT INTO messages (id, assessment_id, position, role, content) "
                    "VALUES (:id, :aid, :pos, :role, :content)"
                ),
                {
                    "id": message_id,
                    "aid": assessment_id,
                    "pos": 0,
                    "role": "user",
                    "content": "Severe chest pain",
                },
            )
            conn.execute(
                text(
                    "INSERT INTO symptoms (id, assessment_id, name, details) "
                    "VALUES (:id, :aid, :name, :details)"
                ),
                {
                    "id": symptom_id,
                    "aid": assessment_id,
                    "name": "chest_pain",
                    "details": '{"severity": "severe"}',
                },
            )

            # Roll back 0009 (result column removal)
            command.downgrade(config, "0008_query_perf_indexes")

            # Verify assessment and all children remain completely intact
            row = conn.execute(
                text(
                    "SELECT id, user_id, consent_id, state "
                    "FROM assessments WHERE id = :id"
                ),
                {"id": assessment_id},
            ).fetchone()
            assert row is not None
            assert row[0] == assessment_id
            assert row[3] == "COMPLETED"

            msg = conn.execute(
                text("SELECT id, content FROM messages WHERE id = :id"),
                {"id": message_id},
            ).fetchone()
            assert msg is not None
            assert msg[1] == "Severe chest pain"

            sym = conn.execute(
                text("SELECT id, name FROM symptoms WHERE id = :id"),
                {"id": symptom_id},
            ).fetchone()
            assert sym is not None
            assert sym[1] == "chest_pain"

            # Re-upgrade to head
            command.upgrade(config, "head")

            # Result column is available again, defaulting to None for existing record
            reloaded = conn.execute(
                text("SELECT id, state, result FROM assessments WHERE id = :id"),
                {"id": assessment_id},
            ).fetchone()
            assert reloaded is not None
            assert reloaded[0] == assessment_id
            assert reloaded[1] == "COMPLETED"
            assert reloaded[2] is None

    def test_rollback_indexes_0008_preserves_audit_and_guest_data(
        self,
    ) -> None:
        """Rolling back 0008 index additions leaves table rows intact."""
        engine = create_engine("sqlite://", hide_parameters=True)
        config = Config(str(SERVER / "alembic.ini"))

        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, "0008_query_perf_indexes")

            log_id = uuid4().hex
            session_id = uuid4().hex
            token_hash = "a" * 64
            future_expiry = datetime.now(UTC) + timedelta(hours=24)

            conn.execute(
                text(
                    "INSERT INTO guest_sessions (id, token_hash, expires_at) "
                    "VALUES (:id, :th, :exp)"
                ),
                {"id": session_id, "th": token_hash, "exp": future_expiry},
            )
            conn.execute(
                text(
                    "INSERT INTO audit_logs (id, action, details) "
                    "VALUES (:id, :act, :det)"
                ),
                {"id": log_id, "act": "TRIAGE", "det": "{}"},
            )

            # Downgrade 0008 -> 0007 (dropping composite indexes)
            command.downgrade(config, "0007_history_indexes_pgvector")

            # Check rows still exist
            sess_row = conn.execute(
                text("SELECT id FROM guest_sessions WHERE id = :id"),
                {"id": session_id},
            ).fetchone()
            assert sess_row is not None

            audit_row = conn.execute(
                text("SELECT id, action FROM audit_logs WHERE id = :id"),
                {"id": log_id},
            ).fetchone()
            assert audit_row is not None
            assert audit_row[1] == "TRIAGE"

            # Re-upgrade 0007 -> 0008 recreates indexes cleanly
            command.upgrade(config, "0008_query_perf_indexes")


class TestAlembicVersionTrackingAndIdempotency:
    """Validate Alembic version tracking and idempotent execution."""

    def test_version_table_tracks_exact_single_head_revision(self) -> None:
        """The alembic_version table contains exactly one current revision number."""
        engine = create_engine("sqlite://", hide_parameters=True)
        config = Config(str(SERVER / "alembic.ini"))

        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, "head")

            rows = conn.execute(
                text("SELECT version_num FROM alembic_version")
            ).fetchall()
            assert len(rows) == 1
            assert rows[0][0] == "0009_assessment_result"

    def test_repeated_upgrade_at_head_is_idempotent(self) -> None:
        """Calling upgrade at head executes cleanly without errors or schema changes."""
        engine = create_engine("sqlite://", hide_parameters=True)
        config = Config(str(SERVER / "alembic.ini"))

        with engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            tables_before = set(inspect(conn).get_table_names())

            # Repeated upgrade call
            command.upgrade(config, "head")
            tables_after = set(inspect(conn).get_table_names())

            assert tables_before == tables_after


class TestOfflineSqlCompilation:
    """Validate offline PostgreSQL SQL script compilation for production deployments."""

    def test_offline_upgrade_generates_valid_postgres_ddl(self) -> None:
        """Alembic generates offline SQL script containing all revisions."""
        output = StringIO()
        config = Config(str(SERVER / "alembic.ini"), output_buffer=output)
        command.upgrade(config, "head", sql=True)
        sql = output.getvalue()

        # Must include all tables and key indexes
        for table in [
            "users",
            "consents",
            "assessments",
            "guest_sessions",
            "messages",
            "profiles",
            "symptoms",
            "audit_logs",
            "symptom_embeddings",
        ]:
            assert (
                f"CREATE TABLE {table}" in sql or f"create table {table}" in sql.lower()
            )

        # Must contain revisions 0001 through 0009
        for rev in EXPECTED_LINEAR_REVISIONS:
            assert rev in sql

    def test_offline_downgrade_generates_valid_postgres_ddl(self) -> None:
        """Alembic generates offline SQL downgrade script without errors."""
        output = StringIO()
        config = Config(str(SERVER / "alembic.ini"), output_buffer=output)
        command.downgrade(config, "0001_database_foundation:base", sql=True)
        sql = output.getvalue()

        assert "DROP TABLE" in sql or "drop table" in sql.lower()
        assert "symptoms" in sql
        assert "messages" in sql
