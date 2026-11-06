"""Unit tests for the database repository layer (S1-NIT-4).

Responsibilities:
    - Validate typed CRUD operations on assessment, message, and symptom repositories.
    - Test sequential message position tracking and role-filtered counting.
    - Verify structured JSONB symptom attributes (severity, duration, body site, onset).
    - Validate upsert attribute merging and atomic bulk symptom replacement.
    - Ensure caller-owned transaction isolation and foreign key cascade rules.

Owner: Nishith · Task: S1-NIT-4 · Requirements: FR-01, FR-17, NFR-01
"""

from uuid import uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError

from app.db.session import create_session_factory
from app.models.consent import Consent
from app.models.user import User
from app.repositories.assessment_repository import (
    create_assessment,
    delete_assessment,
    get_assessment_by_id,
    get_assessment_with_details,
    list_assessments_by_user,
    update_assessment_state,
)
from app.repositories.message_repository import (
    count_messages,
    create_message,
    delete_messages_by_assessment,
    get_message_by_id,
    list_messages_by_assessment,
)
from app.repositories.symptom_repository import (
    create_symptom,
    delete_symptom,
    delete_symptoms_by_assessment,
    get_symptom,
    list_symptoms_by_assessment,
    replace_symptoms_for_assessment,
    upsert_symptom,
)


def _create_test_consent(session) -> Consent:
    """Helper to persist a valid consent record for assessment foreign key."""
    consent = Consent(policy_version="test-consent-v1.0")
    session.add(consent)
    session.flush()
    return consent


def test_assessment_crud_lifecycle(engine: Engine) -> None:
    """Assessments support creation, retrieval, state updates, and deletion."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        consent = _create_test_consent(session)
        assessment = create_assessment(
            session=session,
            consent_id=consent.id,
            user_id=None,
            state="START",
        )
        assert assessment.id is not None
        assert assessment.state == "START"
        assert assessment.user_id is None
        assert assessment.created_at is not None
        assessment_id = assessment.id

    with factory() as session:
        retrieved = get_assessment_by_id(session, assessment_id)
        assert retrieved is not None
        assert retrieved.id == assessment_id
        assert retrieved.state == "START"

    with factory.begin() as session:
        updated = update_assessment_state(
            session=session,
            assessment_id=assessment_id,
            new_state="SYMPTOM_COLLECTION",
        )
        assert updated is not None
        assert updated.state == "SYMPTOM_COLLECTION"

    with factory.begin() as session:
        missing = update_assessment_state(
            session=session,
            assessment_id=uuid4(),
            new_state="CLARIFYING",
        )
        assert missing is None

    with factory.begin() as session:
        deleted = delete_assessment(session, assessment_id)
        assert deleted is True

    with factory() as session:
        assert get_assessment_by_id(session, assessment_id) is None


def test_assessment_eager_loading_with_details(engine: Engine) -> None:
    """get_assessment_with_details loads messages and symptoms in one query."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        consent = _create_test_consent(session)
        assessment = create_assessment(session, consent.id)
        create_message(session, assessment.id, "user", "I have a headache")
        create_message(session, assessment.id, "assistant", "How long has it lasted?")
        create_symptom(
            session,
            assessment.id,
            "headache",
            severity="MILD",
            body_site="temples",
        )
        assessment_id = assessment.id

    with factory() as session:
        detailed = get_assessment_with_details(session, assessment_id)
        assert detailed is not None
        assert len(detailed.messages) == 2
        assert detailed.messages[0].role == "user"
        assert detailed.messages[1].role == "assistant"
        assert len(detailed.symptoms) == 1
        assert detailed.symptoms[0].name == "headache"
        assert detailed.symptoms[0].severity == "MILD"
        assert detailed.consent.policy_version == "test-consent-v1.0"


def test_list_assessments_by_user_pagination(engine: Engine) -> None:
    """Registered user assessments are retrieved with limit and offset pagination."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        user = User(email="patient.nishith@example.invalid")
        session.add(user)
        session.flush()
        user_id = user.id

        for _ in range(3):
            c = _create_test_consent(session)
            create_assessment(session, c.id, user_id=user_id)

        # Create one guest assessment that should not appear
        c_guest = _create_test_consent(session)
        create_assessment(session, c_guest.id, user_id=None)

    with factory() as session:
        page_1 = list_assessments_by_user(session, user_id, limit=2, offset=0)
        assert len(page_1) == 2

        page_2 = list_assessments_by_user(session, user_id, limit=2, offset=2)
        assert len(page_2) == 1

        all_user_items = list_assessments_by_user(session, user_id, limit=10)
        assert len(all_user_items) == 3


def test_message_sequential_positions(engine: Engine) -> None:
    """Messages auto-increment positions (0, 1, 2) when position is None."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        consent = _create_test_consent(session)
        assessment = create_assessment(session, consent.id)
        aid = assessment.id

        m0 = create_message(session, aid, "user", "Message 0")
        assert m0.position == 0
        m0_id = m0.id

        m1 = create_message(session, aid, "assistant", "Message 1")
        assert m1.position == 1

        m2 = create_message(session, aid, "user", "Message 2")
        assert m2.position == 2

    with factory() as session:
        retrieved_msg = get_message_by_id(session, m0_id)
        assert retrieved_msg is not None
        assert retrieved_msg.content == "Message 0"

        messages = list_messages_by_assessment(session, aid)
        assert len(messages) == 3
        assert [m.position for m in messages] == [0, 1, 2]

        total = count_messages(session, aid)
        assert total == 3

        user_count = count_messages(session, aid, role="user")
        assert user_count == 2

        asst_count = count_messages(session, aid, role="assistant")
        assert asst_count == 1


def test_message_rejects_blank_content_or_invalid_role(engine: Engine) -> None:
    """Database constraints reject empty content and unauthorized roles."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        consent = _create_test_consent(session)
        assessment = create_assessment(session, consent.id)
        aid = assessment.id

    with pytest.raises(IntegrityError), factory.begin() as session:
        create_message(session, aid, "user", "   ")

    with pytest.raises(IntegrityError), factory.begin() as session:
        create_message(session, aid, "system", "Unauthorized system role")


def test_symptom_persistence_structured_jsonb(engine: Engine) -> None:
    """Symptoms persist structured details (severity, duration) as JSONB."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        consent = _create_test_consent(session)
        assessment = create_assessment(session, consent.id)
        aid = assessment.id

        symptom = create_symptom(
            session=session,
            assessment_id=aid,
            name="Abdominal Pain",  # Will be normalized to 'abdominal pain'
            severity="SEVERE",
            duration={"value": 3.0, "unit": "DAY"},
            body_site="lower right abdomen",
            onset="started suddenly 3 days ago",
        )
        assert symptom.name == "abdominal pain"
        assert symptom.severity == "SEVERE"
        assert symptom.duration == {"value": 3.0, "unit": "DAY"}
        assert symptom.body_site == "lower right abdomen"

    with factory() as session:
        retrieved = get_symptom(session, aid, "abdominal pain")
        assert retrieved is not None
        assert retrieved.name == "abdominal pain"
        assert retrieved.details["severity"] == "SEVERE"
        assert retrieved.details["duration"]["value"] == 3.0
        assert retrieved.details["body_site"] == "lower right abdomen"
        assert retrieved.details["onset"] == "started suddenly 3 days ago"


def test_symptom_upsert_merges_attributes(engine: Engine) -> None:
    """upsert_symptom merges newly extracted details without duplicating rows or IDs."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        consent = _create_test_consent(session)
        assessment = create_assessment(session, consent.id)
        aid = assessment.id

        # Step 1: Initial extraction with unknown severity
        s1 = upsert_symptom(
            session=session,
            assessment_id=aid,
            name="cough",
            severity="UNKNOWN",
        )
        initial_id = s1.id
        assert s1.severity == "UNKNOWN"
        assert s1.duration is None

        # Step 2: Clarification provides specific severity and duration
        s2 = upsert_symptom(
            session=session,
            assessment_id=aid,
            name="cough",
            severity="MODERATE",
            duration={"value": 5.0, "unit": "DAY"},
            body_site="chest",
        )
        assert s2.id == initial_id  # Same row preserved!
        assert s2.severity == "MODERATE"
        assert s2.duration == {"value": 5.0, "unit": "DAY"}
        assert s2.body_site == "chest"

        # Step 3: Follow-up message mentions cough again with unknown severity;
        # previous moderate severity and duration must be preserved
        s3 = upsert_symptom(
            session=session,
            assessment_id=aid,
            name="cough",
            severity="UNKNOWN",
        )
        assert s3.id == initial_id
        assert s3.severity == "MODERATE"
        assert s3.duration == {"value": 5.0, "unit": "DAY"}

    with factory() as session:
        all_symptoms = list_symptoms_by_assessment(session, aid)
        assert len(all_symptoms) == 1
        assert all_symptoms[0].id == initial_id


def test_replace_symptoms_for_assessment(engine: Engine) -> None:
    """replace_symptoms_for_assessment adds, updates, and deletes symptoms."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        consent = _create_test_consent(session)
        assessment = create_assessment(session, consent.id)
        aid = assessment.id

        create_symptom(session, aid, "fever", severity="MILD")
        create_symptom(session, aid, "headache", severity="SEVERE")

    # Replace with fever (updated) and chills (new); headache should be deleted
    with factory.begin() as session:
        replaced = replace_symptoms_for_assessment(
            session=session,
            assessment_id=aid,
            symptoms_data=[
                {
                    "name": "fever",
                    "severity": "MODERATE",
                    "duration": {"value": 2, "unit": "DAY"},
                },
                {"name": "chills", "severity": "MILD"},
            ],
        )
        assert len(replaced) == 2
        names = {s.name for s in replaced}
        assert names == {"fever", "chills"}

    with factory() as session:
        current = list_symptoms_by_assessment(session, aid)
        assert len(current) == 2
        symptom_map = {s.name: s for s in current}
        assert "headache" not in symptom_map
        assert symptom_map["fever"].severity == "MODERATE"
        assert symptom_map["chills"].severity == "MILD"

    # Test single symptom deletion
    with factory.begin() as session:
        assert delete_symptom(session, aid, "chills") is True
        assert delete_symptom(session, aid, "non_existent") is False


def test_delete_symptoms_and_messages_by_assessment(engine: Engine) -> None:
    """Messages and symptoms can be bulk-deleted before deleting assessment."""
    factory = create_session_factory(engine)
    with factory.begin() as session:
        consent = _create_test_consent(session)
        assessment = create_assessment(session, consent.id)
        aid = assessment.id

        create_message(session, aid, "user", "Help")
        create_symptom(session, aid, "dizziness")

    with factory.begin() as session:
        deleted_msgs = delete_messages_by_assessment(session, aid)
        assert deleted_msgs == 1

        deleted_syms = delete_symptoms_by_assessment(session, aid)
        assert deleted_syms == 1

        # Now parent assessment can be safely deleted without RESTRICT foreign key error
        deleted_assessment = delete_assessment(session, aid)
        assert deleted_assessment is True

    with factory() as session:
        assert get_assessment_by_id(session, aid) is None
        assert list_messages_by_assessment(session, aid) == []
        assert list_symptoms_by_assessment(session, aid) == []
