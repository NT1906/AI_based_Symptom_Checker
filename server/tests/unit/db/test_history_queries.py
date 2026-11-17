"""Unit tests for assessment history queries, pagination, and ownership filters.

Responsibilities:
    - Validate query_assessment_history pagination and order direction.
    - Validate state filtering (single state, multiple states) and date windows.
    - Validate count_assessments_by_user matching active filters.
    - Validate eager loading of messages, symptoms, and consent (N+1 avoidance).
    - Validate query-level ownership filters for users and guest sessions.
    - Validate safe individual and bulk deletion enforcing user boundaries.
    - Verify input validation (negative limit/offset, missing ownership identifier).

Owner: Kavya · Task: S2-KAV-4 · Requirements: FR-02
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.db.session import create_session_factory
from app.models.assessment import Assessment
from app.models.consent import Consent
from app.models.message import Message
from app.models.symptom import Symptom
from app.models.user import User
from app.repositories.assessment_repository import (
    count_assessments_by_user,
    delete_assessment_for_user,
    delete_assessments_for_user,
    get_assessment_by_id_and_guest_session,
    get_assessment_by_id_and_user,
    get_assessment_by_ownership,
    get_assessment_with_details_for_user,
    list_assessments_by_guest_session,
    list_assessments_by_user,
    query_assessment_history,
)
from app.repositories.guest_session_repository import create_guest_session


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Yield an isolated test session that rolls back after each test."""
    factory = create_session_factory(engine)
    with factory.begin() as sess:
        yield sess
        sess.rollback()


def _make_user(session: Session, email_prefix: str = "test-user") -> User:
    """Helper to create and persist a test user."""
    user = User(email=f"{email_prefix}-{uuid4().hex[:8]}@example.invalid")
    session.add(user)
    session.flush()
    return user


def _make_consent(session: Session) -> Consent:
    """Helper to create and persist a test consent record."""
    consent = Consent(policy_version="1.0.0")
    session.add(consent)
    session.flush()
    return consent


def _make_assessment(
    session: Session,
    user_id: UUID | None = None,
    guest_session_id: UUID | None = None,
    state: str = "START",
    created_at: datetime | None = None,
) -> Assessment:
    """Helper to create and persist an assessment with explicit metadata."""
    consent = _make_consent(session)
    assessment = Assessment(
        consent_id=consent.id,
        user_id=user_id,
        guest_session_id=guest_session_id,
        state=state,
    )
    if created_at is not None:
        assessment.created_at = created_at
    session.add(assessment)
    session.flush()
    return assessment


def test_history_query_pagination_order_and_lookahead(session: Session) -> None:
    """Assessments paginate correctly with newest-first and oldest-first ordering."""
    user = _make_user(session)
    base_time = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)

    # Create 5 assessments with staggered created_at timestamps
    created = [
        _make_assessment(
            session,
            user_id=user.id,
            created_at=base_time + timedelta(hours=i),
        )
        for i in range(5)
    ]

    # Page 1: newest 2 (created[4], created[3])
    page_1 = query_assessment_history(session, user.id, limit=2, offset=0)
    assert len(page_1) == 2
    assert [a.id for a in page_1] == [created[4].id, created[3].id]

    # Page 2: next 2 (created[2], created[1])
    page_2 = query_assessment_history(session, user.id, limit=2, offset=2)
    assert len(page_2) == 2
    assert [a.id for a in page_2] == [created[2].id, created[1].id]

    # Page 3: last 1 (created[0])
    page_3 = query_assessment_history(session, user.id, limit=2, offset=4)
    assert len(page_3) == 1
    assert page_3[0].id == created[0].id

    # Page 4: beyond end -> empty list
    empty_page = query_assessment_history(session, user.id, limit=2, offset=6)
    assert len(empty_page) == 0

    # Oldest-first ordering (ASC)
    asc_page = query_assessment_history(
        session, user.id, limit=3, offset=0, order_desc=False
    )
    assert len(asc_page) == 3
    assert [a.id for a in asc_page] == [created[0].id, created[1].id, created[2].id]


def test_history_query_state_filtering(session: Session) -> None:
    """Assessments filter by single state and multiple state values."""
    user = _make_user(session)
    _make_assessment(session, user_id=user.id, state="START")
    _make_assessment(session, user_id=user.id, state="READY")
    comp1 = _make_assessment(session, user_id=user.id, state="COMPLETED")
    comp2 = _make_assessment(session, user_id=user.id, state="COMPLETED")

    # Filter single state 'COMPLETED'
    completed = query_assessment_history(session, user.id, state="COMPLETED")
    assert len(completed) == 2
    assert {a.id for a in completed} == {comp1.id, comp2.id}

    # Filter multiple states ['READY', 'COMPLETED']
    ready_and_comp = query_assessment_history(
        session, user.id, states=["READY", "COMPLETED"]
    )
    assert len(ready_and_comp) == 3

    # Filter state with no matches
    empty = query_assessment_history(session, user.id, state="CLARIFYING")
    assert len(empty) == 0


def test_history_query_date_range_filtering(session: Session) -> None:
    """Assessments filter within specific created_at timestamp bounds."""
    user = _make_user(session)
    t0 = datetime(2026, 11, 10, 10, 0, tzinfo=UTC)
    t1 = t0 + timedelta(days=1)
    t2 = t0 + timedelta(days=2)
    t3 = t0 + timedelta(days=3)

    a0 = _make_assessment(session, user_id=user.id, created_at=t0)
    a1 = _make_assessment(session, user_id=user.id, created_at=t1)
    a2 = _make_assessment(session, user_id=user.id, created_at=t2)
    a3 = _make_assessment(session, user_id=user.id, created_at=t3)

    # created_after (>= t1 + 12h) -> should return a3 and a2
    after = query_assessment_history(
        session, user.id, created_after=t1 + timedelta(hours=12)
    )
    assert [a.id for a in after] == [a3.id, a2.id]

    # created_before (<= t1 + 12h) -> should return a1 and a0
    before = query_assessment_history(
        session, user.id, created_before=t1 + timedelta(hours=12)
    )
    assert [a.id for a in before] == [a1.id, a0.id]

    # Window between t1 and t2 (inclusive)
    window = query_assessment_history(
        session, user.id, created_after=t1, created_before=t2
    )
    assert [a.id for a in window] == [a2.id, a1.id]


def test_history_query_eager_loading_details(session: Session) -> None:
    """Eager loading populates messages, symptoms, and consent without N+1 queries."""
    user = _make_user(session)
    assessment = _make_assessment(session, user_id=user.id)

    # Add messages
    m1 = Message(
        assessment_id=assessment.id,
        role="user",
        content="Headache since yesterday",
        position=0,
    )
    m2 = Message(
        assessment_id=assessment.id,
        role="assistant",
        content="Is the headache throbbing?",
        position=1,
    )
    session.add_all([m1, m2])

    # Add symptom
    sym = Symptom(
        assessment_id=assessment.id,
        name="headache",
    )
    session.add(sym)
    session.flush()

    # Query with include_details=True
    results = query_assessment_history(session, user.id, limit=1, include_details=True)
    assert len(results) == 1
    item = results[0]
    assert len(item.messages) == 2
    assert item.messages[0].content == "Headache since yesterday"
    assert len(item.symptoms) == 1
    assert item.symptoms[0].name == "headache"
    assert item.consent is not None
    assert item.consent.policy_version == "1.0.0"


def test_count_assessments_by_user(session: Session) -> None:
    """count_assessments_by_user counts records matching user and optional filters."""
    user1 = _make_user(session, "user1")
    user2 = _make_user(session, "user2")

    _make_assessment(session, user_id=user1.id, state="START")
    _make_assessment(session, user_id=user1.id, state="READY")
    _make_assessment(session, user_id=user1.id, state="COMPLETED")
    _make_assessment(session, user_id=user2.id, state="COMPLETED")

    # user1 total count
    assert count_assessments_by_user(session, user1.id) == 3
    # user2 total count
    assert count_assessments_by_user(session, user2.id) == 1
    # user1 count with state filter
    assert count_assessments_by_user(session, user1.id, state="COMPLETED") == 1
    # user1 count with states filter
    assert count_assessments_by_user(session, user1.id, states=["START", "READY"]) == 2


def test_list_assessments_by_user_backwards_compatibility(
    session: Session,
) -> None:
    """list_assessments_by_user preserves default behavior while supporting filters."""
    user = _make_user(session)
    _make_assessment(session, user_id=user.id, state="START")
    _make_assessment(session, user_id=user.id, state="COMPLETED")

    # Default signature
    all_rows = list_assessments_by_user(session, user.id)
    assert len(all_rows) == 2

    # Filtered by state
    completed = list_assessments_by_user(session, user.id, state="COMPLETED")
    assert len(completed) == 1
    assert completed[0].state == "COMPLETED"


def test_ownership_filter_get_assessment_by_id_and_user(session: Session) -> None:
    """get_assessment_by_id_and_user prevents cross-user access at query level."""
    owner = _make_user(session, "owner")
    other_user = _make_user(session, "other")
    assessment = _make_assessment(session, user_id=owner.id)

    # Owner can retrieve
    retrieved = get_assessment_by_id_and_user(session, assessment.id, owner.id)
    assert retrieved is not None
    assert retrieved.id == assessment.id

    # Other user receives None (blocked at SQL query level)
    denied = get_assessment_by_id_and_user(session, assessment.id, other_user.id)
    assert denied is None

    # Unknown assessment receives None
    missing = get_assessment_by_id_and_user(session, uuid4(), owner.id)
    assert missing is None


def test_ownership_filter_get_assessment_with_details_for_user(
    session: Session,
) -> None:
    """get_assessment_with_details_for_user loads relations only for owner."""
    owner = _make_user(session, "owner")
    other_user = _make_user(session, "other")
    assessment = _make_assessment(session, user_id=owner.id)

    m = Message(
        assessment_id=assessment.id,
        role="user",
        content="Chest pain",
        position=0,
    )
    session.add(m)
    session.flush()

    # Owner retrieves with relations
    res = get_assessment_with_details_for_user(session, assessment.id, owner.id)
    assert res is not None
    assert len(res.messages) == 1
    assert res.messages[0].content == "Chest pain"

    # Other user receives None
    denied = get_assessment_with_details_for_user(session, assessment.id, other_user.id)
    assert denied is None


def test_ownership_filter_guest_session(session: Session) -> None:
    """Guest session assessment retrieval verifies guest session ownership."""
    guest_session, _ = create_guest_session(session)
    other_guest, _ = create_guest_session(session)

    assessment = _make_assessment(
        session, guest_session_id=guest_session.id, user_id=None
    )

    # Matching guest session retrieves unclaimed assessment
    found = get_assessment_by_id_and_guest_session(
        session, assessment.id, guest_session.id
    )
    assert found is not None
    assert found.id == assessment.id

    # Other guest session receives None
    denied = get_assessment_by_id_and_guest_session(
        session, assessment.id, other_guest.id
    )
    assert denied is None

    # If claimed by user, unclaimed_only=True returns None
    user = _make_user(session)
    assessment.user_id = user.id
    session.flush()

    claimed_check = get_assessment_by_id_and_guest_session(
        session, assessment.id, guest_session.id, unclaimed_only=True
    )
    assert claimed_check is None

    # unclaimed_only=False still resolves
    claimed_check_all = get_assessment_by_id_and_guest_session(
        session, assessment.id, guest_session.id, unclaimed_only=False
    )
    assert claimed_check_all is not None


def test_get_assessment_by_ownership_resolver(session: Session) -> None:
    """Unified get_assessment_by_ownership enforces user or guest parameters."""
    user = _make_user(session)
    guest, _ = create_guest_session(session)

    user_assessment = _make_assessment(session, user_id=user.id)
    guest_assessment = _make_assessment(session, guest_session_id=guest.id)

    # Resolves user assessment
    assert (
        get_assessment_by_ownership(session, user_assessment.id, user_id=user.id)
        is not None
    )

    # Resolves guest assessment
    assert (
        get_assessment_by_ownership(
            session, guest_assessment.id, guest_session_id=guest.id
        )
        is not None
    )

    # Raises ValueError when neither identifier is supplied
    with pytest.raises(ValueError, match="Either user_id or guest_session_id"):
        get_assessment_by_ownership(session, user_assessment.id)


def test_delete_assessment_for_user_safety(session: Session) -> None:
    """delete_assessment_for_user only deletes if owned by specified user."""
    owner = _make_user(session, "owner")
    other_user = _make_user(session, "other")
    assessment = _make_assessment(session, user_id=owner.id)
    aid = assessment.id

    # Other user cannot delete owner's assessment
    assert delete_assessment_for_user(session, aid, other_user.id) is False
    assert session.get(Assessment, aid) is not None

    # Owner deletes assessment successfully
    assert delete_assessment_for_user(session, aid, owner.id) is True
    assert session.get(Assessment, aid) is None

    # Repeat delete returns False
    assert delete_assessment_for_user(session, aid, owner.id) is False


def test_delete_assessments_for_user_bulk(session: Session) -> None:
    """delete_assessments_for_user purges only target user's records."""
    user1 = _make_user(session, "u1")
    user2 = _make_user(session, "u2")

    for _ in range(3):
        _make_assessment(session, user_id=user1.id)
    for _ in range(2):
        _make_assessment(session, user_id=user2.id)

    deleted_count = delete_assessments_for_user(session, user1.id)
    assert deleted_count == 3
    assert count_assessments_by_user(session, user1.id) == 0
    assert count_assessments_by_user(session, user2.id) == 2


def test_list_assessments_by_guest_session(session: Session) -> None:
    """list_assessments_by_guest_session paginates guest assessments."""
    guest, _ = create_guest_session(session)

    _make_assessment(session, guest_session_id=guest.id, user_id=None)
    _make_assessment(session, guest_session_id=guest.id, user_id=None)

    items = list_assessments_by_guest_session(session, guest.id, limit=10)
    assert len(items) == 2


def test_history_queries_input_validation(session: Session) -> None:
    """Invalid limit or offset raises ValueError."""
    user = _make_user(session)

    with pytest.raises(ValueError, match="Limit must be at least 1"):
        query_assessment_history(session, user.id, limit=0)

    with pytest.raises(ValueError, match="Offset must be non-negative"):
        query_assessment_history(session, user.id, offset=-1)

    with pytest.raises(ValueError, match="Limit must be at least 1"):
        list_assessments_by_user(session, user.id, limit=0)

    with pytest.raises(ValueError, match="Offset must be non-negative"):
        list_assessments_by_user(session, user.id, offset=-1)

    with pytest.raises(ValueError, match="Limit must be at least 1"):
        list_assessments_by_guest_session(session, uuid4(), limit=-5)
