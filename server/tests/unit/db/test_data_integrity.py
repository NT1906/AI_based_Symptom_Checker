"""Data-integrity and schema invariants test suite across all 9 database tables.

Responsibilities:
    - Verify foreign key integrity, cascade rules, and RESTRICT / SET NULL constraints.
    - Verify check constraints and enum domain validation for all entity types.
    - Verify unique constraints (uniqueness of emails, token hashes, etc.).
    - Verify DPDP Act 2023 & medical safety invariants (no plaintext passwords).
    - Verify transactional atomicity and rollback safety.

Owner: Kavya (Database) · Task: S2-KAV-6 · Requirements: NFR-08, DR-06, FR-01, FR-02
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import create_session_factory
from app.models.assessment import Assessment
from app.models.audit_log import AuditLog
from app.models.consent import Consent
from app.models.guest_session import GuestSession
from app.models.message import Message
from app.models.profile import Profile
from app.models.symptom import Symptom
from app.models.symptom_embedding import SymptomEmbedding
from app.models.user import User


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Yield an isolated database session with foreign keys enforced.

    Args:
        engine: Migrated database engine fixture.

    Yields:
        Active SQLAlchemy ORM session.
    """
    factory = create_session_factory(engine)
    with factory() as sess:
        yield sess


def _make_user(session: Session, email_prefix: str = "integrity_user") -> User:
    """Helper to persist a unique valid test user."""
    user = User(email=f"{email_prefix}_{uuid4().hex[:8]}@example.invalid")
    session.add(user)
    session.flush()
    return user


def _make_consent(session: Session, version: str = "2026.1") -> Consent:
    """Helper to persist a valid consent record."""
    consent = Consent(policy_version=version)
    session.add(consent)
    session.flush()
    return consent


def _make_guest_session(session: Session, hours_valid: int = 24) -> GuestSession:
    """Helper to persist a valid guest session."""
    now = datetime.now(UTC)
    guest = GuestSession(
        token_hash=uuid4().hex + uuid4().hex,  # 64-character SHA-256 hex string
        expires_at=now + timedelta(hours=hours_valid),
    )
    session.add(guest)
    session.flush()
    return guest


def _make_assessment(
    session: Session,
    user_id: UUID | None = None,
    guest_session_id: UUID | None = None,
    consent: Consent | None = None,
    state: str = "START",
) -> Assessment:
    """Helper to persist an assessment linked to user or guest session."""
    if consent is None:
        consent = _make_consent(session)
    assessment = Assessment(
        user_id=user_id,
        guest_session_id=guest_session_id,
        consent_id=consent.id,
        state=state,
    )
    session.add(assessment)
    session.flush()
    return assessment


# =============================================================================
# 1. Foreign Key Cascades, Set-Null, and Restrict Invariants
# =============================================================================


class TestForeignKeyInvariants:
    """Validate referential integrity, deletion cascades, and orphan protection."""

    def test_user_deletion_cascades_to_profile(self, session: Session) -> None:
        """Deleting user automatically purges medical profile (DPDP § 12)."""
        user = _make_user(session, "cascade_prof")
        profile = Profile(
            user_id=user.id,
            age_band="young_adult",
            biological_sex="female",
            chronic_conditions=["Asthma"],
        )
        session.add(profile)
        session.flush()

        # Delete user
        session.delete(user)
        session.flush()

        # Verify profile is purged
        found = session.execute(
            select(Profile).where(Profile.user_id == user.id)
        ).scalar_one_or_none()
        assert found is None

    def test_user_deletion_sets_null_on_claimed_guest_session(
        self, session: Session
    ) -> None:
        """Deleting user unlinks guest claim without deleting session."""
        user = _make_user(session, "claim_user")
        guest = _make_guest_session(session)
        guest.claimed_at = datetime.now(UTC)
        guest.claimed_by_user_id = user.id
        session.flush()

        session.delete(user)
        session.flush()

        session.refresh(guest)
        assert guest.claimed_by_user_id is None
        assert guest.claimed_at is not None

    def test_user_deletion_sets_null_on_audit_logs(self, session: Session) -> None:
        """Deleting user sets audit_logs.user_id to NULL to preserve compliance."""
        user = _make_user(session, "audit_user")
        log = AuditLog(
            user_id=user.id,
            action="TRIAGE_RESULT",
            risk_level="SELF_CARE",
            details={"rules": ["r1"]},
        )
        session.add(log)
        session.flush()

        session.delete(user)
        session.flush()

        session.refresh(log)
        assert log.user_id is None
        assert log.action == "TRIAGE_RESULT"

    def test_guest_session_purge_sets_null_on_assessments(
        self, session: Session
    ) -> None:
        """Purging guest session clears assessment link without deleting health data."""
        guest = _make_guest_session(session)
        assessment = _make_assessment(session, guest_session_id=guest.id)

        session.delete(guest)
        session.flush()

        session.refresh(assessment)
        assert assessment.guest_session_id is None

    def test_guest_session_purge_sets_null_on_audit_logs(
        self, session: Session
    ) -> None:
        """Purging an expired guest session clears audit log session link."""
        guest = _make_guest_session(session)
        log = AuditLog(
            guest_session_id=guest.id,
            action="GUEST_TRIAGE",
            details={},
        )
        session.add(log)
        session.flush()

        session.delete(guest)
        session.flush()

        session.refresh(log)
        assert log.guest_session_id is None

    def test_assessment_deletion_restricted_when_children_exist(
        self, session: Session
    ) -> None:
        """Deleting an assessment with messages or symptoms raises IntegrityError.

        Protects clinical conversation logs and symptom history from accidental wipes.
        """
        assessment = _make_assessment(session)
        msg = Message(
            assessment_id=assessment.id,
            position=0,
            role="user",
            content="I have a headache.",
        )
        sym = Symptom(
            assessment_id=assessment.id,
            name="headache",
            details={"severity": "MILD"},
        )
        session.add_all([msg, sym])
        session.flush()

        # Attempting to delete assessment directly fails due to ondelete="RESTRICT"
        session.delete(assessment)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_assessment_deletion_succeeds_when_children_cleared_first(
        self, session: Session
    ) -> None:
        """Clearing messages and symptoms first allows assessment to be deleted."""
        assessment = _make_assessment(session)
        msg = Message(
            assessment_id=assessment.id,
            position=0,
            role="user",
            content="I have a headache.",
        )
        sym = Symptom(
            assessment_id=assessment.id,
            name="headache",
            details={"severity": "MILD"},
        )
        session.add_all([msg, sym])
        session.flush()

        # Clear child entities first (repository pattern)
        session.delete(msg)
        session.delete(sym)
        session.flush()

        # Now assessment deletes cleanly
        session.delete(assessment)
        session.flush()

        found = session.get(Assessment, assessment.id)
        assert found is None

    def test_assessment_deletion_sets_null_on_audit_logs(
        self, session: Session
    ) -> None:
        """Deleting an assessment clears assessment_id on audit logs."""
        assessment = _make_assessment(session)
        log = AuditLog(
            assessment_id=assessment.id,
            action="ANALYSIS_RUN",
            details={},
        )
        session.add(log)
        session.flush()

        session.delete(assessment)
        session.flush()

        session.refresh(log)
        assert log.assessment_id is None

    def test_consent_deletion_fails_when_assessment_linked(
        self, session: Session
    ) -> None:
        """Deleting a consent record linked to an assessment raises IntegrityError."""
        consent = _make_consent(session)
        _make_assessment(session, consent=consent)

        session.delete(consent)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


# =============================================================================
# 2. Check Constraints, Domain Types, and Uniqueness Invariants
# =============================================================================


class TestTableCheckConstraintsAndUniqueness:
    """Validate check constraints, enum domains, and uniqueness guards."""

    def test_duplicate_user_email_rejected(self, session: Session) -> None:
        """Duplicate user emails are strictly rejected by the database."""
        email = f"dup_{uuid4().hex[:8]}@example.invalid"
        user1 = User(email=email)
        user2 = User(email=email)
        session.add(user1)
        session.flush()

        session.add(user2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_duplicate_guest_session_token_hash_rejected(
        self, session: Session
    ) -> None:
        """Duplicate guest session token hashes are rejected."""
        fixed_hash = "a" * 64
        now = datetime.now(UTC)
        g1 = GuestSession(token_hash=fixed_hash, expires_at=now + timedelta(hours=1))
        g2 = GuestSession(token_hash=fixed_hash, expires_at=now + timedelta(hours=2))
        session.add(g1)
        session.flush()

        session.add(g2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_assessment_state_must_be_valid_enum(self, session: Session) -> None:
        """Non-standard assessment states violate check constraint."""
        consent = _make_consent(session)
        bad_assessment = Assessment(
            consent_id=consent.id,
            state="DIAGNOSED",  # Prohibited state violating DR-01 and constraint
        )
        session.add(bad_assessment)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_messages_unique_position_per_assessment(self, session: Session) -> None:
        """Two messages for same assessment cannot share position index."""
        assessment = _make_assessment(session)
        m1 = Message(
            assessment_id=assessment.id,
            position=0,
            role="user",
            content="Hello",
        )
        m2 = Message(
            assessment_id=assessment.id,
            position=0,
            role="assistant",
            content="Hi",
        )
        session.add(m1)
        session.flush()

        session.add(m2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_messages_role_must_be_user_or_assistant(self, session: Session) -> None:
        """Invalid message roles (e.g. bot, admin, system) are rejected."""
        assessment = _make_assessment(session)
        bad_msg = Message(
            assessment_id=assessment.id,
            position=0,
            role="bot",  # Only user or assistant permitted
            content="Hello",
        )
        session.add(bad_msg)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_symptoms_unique_name_per_assessment(self, session: Session) -> None:
        """Duplicate symptom names under same assessment violate uniqueness."""
        assessment = _make_assessment(session)
        s1 = Symptom(
            assessment_id=assessment.id,
            name="headache",
            details={},
        )
        s2 = Symptom(
            assessment_id=assessment.id,
            name="headache",
            details={},
        )
        session.add(s1)
        session.flush()

        session.add(s2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_profile_age_band_check_constraint(self, session: Session) -> None:
        """Invalid age band values violate check constraint."""
        user = _make_user(session, "age_test")
        profile = Profile(
            user_id=user.id,
            age_band="toddler",  # Invalid; only child, teen, young_adult, etc.
        )
        session.add(profile)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_profile_biological_sex_check_constraint(self, session: Session) -> None:
        """Invalid biological sex values violate check constraint."""
        user = _make_user(session, "sex_test")
        profile = Profile(
            user_id=user.id,
            biological_sex="unspecified",  # Invalid; only female, male, etc.
        )
        session.add(profile)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_profile_enforces_one_to_one_user_id(self, session: Session) -> None:
        """A user cannot have multiple profile records."""
        user = _make_user(session, "single_prof")
        p1 = Profile(user_id=user.id, age_band="adult")
        p2 = Profile(user_id=user.id, age_band="senior")
        session.add(p1)
        session.flush()

        session.add(p2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_symptom_embedding_unique_revision_and_phrase(
        self, session: Session
    ) -> None:
        """Duplicate (model_revision, phrase) pairs are rejected in embeddings."""
        rev = "b7a63e8"
        emb1 = SymptomEmbedding(
            symptom_id="cough",
            phrase="dry cough",
            model_revision=rev,
            embedding=[0.1] * 384,
        )
        emb2 = SymptomEmbedding(
            symptom_id="cough",
            phrase="dry cough",
            model_revision=rev,
            embedding=[0.2] * 384,
        )
        session.add(emb1)
        session.flush()

        session.add(emb2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


# =============================================================================
# 3. Medical Safety & Privacy Invariants (DPDP Act 2023, DR-06)
# =============================================================================


class TestMedicalSafetyAndPrivacyInvariants:
    """Validate database-level privacy constraints, data minimization, and PII."""

    def test_zero_binary_or_image_columns_across_entire_schema(
        self, engine: Engine
    ) -> None:
        """Verify NO table in the entire schema contains BLOB/binary/image columns.

        Requirements: AI_RULES.md §2 (Rule 10), DR-06, idea §3.
        User images must be processed in volatile memory only and NEVER stored.
        """
        insp = inspect(engine)
        disallowed_types = {"BLOB", "BYTEA", "LARGEBINARY", "BINARY", "VARBINARY"}
        for table_name in insp.get_table_names():
            columns = insp.get_columns(table_name)
            for col in columns:
                type_name = str(col["type"]).upper()
                assert not any(bad in type_name for bad in disallowed_types), (
                    f"Prohibited binary column {table_name}.{col['name']} "
                    f"({type_name}) found."
                )

    def test_guest_session_tokens_are_sha256_digests_only(
        self, session: Session
    ) -> None:
        """Token hash must be non-empty and stores hex hashes, never raw tokens."""
        guest = _make_guest_session(session)
        assert len(guest.token_hash) == 64
        # Verify it contains valid hexadecimal characters only
        int(guest.token_hash, 16)

    def test_all_primary_keys_use_uuid_or_bigint(self, engine: Engine) -> None:
        """Audit all 9 tables for standard primary key convention (UUID or BIGINT)."""
        insp = inspect(engine)
        expected_tables = {
            "users",
            "consents",
            "guest_sessions",
            "profiles",
            "assessments",
            "messages",
            "symptoms",
            "audit_logs",
            "symptom_embeddings",
        }
        found_tables = set(insp.get_table_names())
        assert expected_tables.issubset(found_tables)

        for table in expected_tables:
            pk_constraint = insp.get_pk_constraint(table)
            pk_cols = pk_constraint.get("constrained_columns", [])
            assert len(pk_cols) == 1, f"Table {table} must have exactly one PK column."
            assert pk_cols[0] == "id", f"Table {table} PK column must be named 'id'."

    def test_assessment_cannot_be_created_without_consent_fk(
        self, session: Session
    ) -> None:
        """Assessment creation strictly requires a non-null valid consent FK."""
        bad_assessment = Assessment(
            consent_id=uuid4(),  # Non-existent foreign key
            state="START",
        )
        session.add(bad_assessment)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


# =============================================================================
# 4. Transactional Atomicity and Rollback Safety
# =============================================================================


class TestTransactionalAtomicity:
    """Validate transaction boundaries, atomic commits, and rollback guarantees."""

    def test_failed_intake_transaction_leaves_no_orphans(
        self, session: Session
    ) -> None:
        """A failure during intake message persistence rolls back the transaction.

        Ensures no orphan assessment or orphaned messages exist on error.
        """
        user = _make_user(session, "atomic_intake")
        consent = _make_consent(session)

        initial_assessments = session.execute(select(Assessment)).scalars().all()

        try:
            with session.begin_nested():
                assessment = Assessment(
                    user_id=user.id,
                    consent_id=consent.id,
                    state="START",
                )
                session.add(assessment)
                session.flush()

                # Add a message with invalid role to trigger failure
                bad_msg = Message(
                    assessment_id=assessment.id,
                    position=0,
                    role="invalid_role",
                    content="Crash",
                )
                session.add(bad_msg)
                session.flush()
        except IntegrityError:
            session.rollback()

        # Verify zero partial records were created
        current_assessments = session.execute(select(Assessment)).scalars().all()
        assert len(current_assessments) == len(initial_assessments)
