"""Verify saved results in history, their saving rules and their export.

Owner: Nisarg · Task: S2-NIS-16 · Issue: #313 · Requirements: FR-02, DR-06
"""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.orchestrator_service import OrchestratorAssessmentService
from app.api.v1.history import create_history_router
from app.core.errors import register_error_handlers
from app.models import Assessment, Base, Consent, User
from app.schemas.condition import Condition
from app.schemas.enums import ConfidenceLabel, RiskLevel
from app.schemas.result import AssessmentResult
from app.services.privacy.account_export import AccountExport
from app.services.privacy.history import HistoryService, stored_result

AUTH = {"Authorization": "Bearer fixture-owner"}
PATH = "/api/v1/history"


def _result(assessment_id: UUID) -> AssessmentResult:
    """A fictional finished result with conditions listed out of rank order."""
    return AssessmentResult(
        assessment_id=assessment_id,
        risk_level=RiskLevel.CONSULT_DOCTOR,
        conditions=[
            Condition(
                name="Influenza (flu)", confidence=ConfidenceLabel.POSSIBLE, rank=2
            ),
            Condition(
                name="Sore throat (pharyngitis)",
                confidence=ConfidenceLabel.LIKELY,
                rank=1,
            ),
        ],
        guidance=["Rest and drink fluids."],
    )


@pytest.fixture
def sessions(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    """A SQLite database with the full schema."""
    engine = create_engine(f"sqlite:///{tmp_path / 'history-results.db'}")
    Base.metadata.create_all(engine)
    try:
        yield sessionmaker(engine)
    finally:
        engine.dispose()


@pytest.fixture
def owner_id(sessions: sessionmaker[Session]) -> UUID:
    """A registered account that owns the assessments in these tests."""
    with sessions.begin() as session:
        owner = User(email="results-owner@example.test")
        session.add(owner)
        session.flush()
        return owner.id


def _add_assessment(
    sessions: sessionmaker[Session],
    user_id: UUID | None,
    result: dict[str, object] | None = None,
) -> UUID:
    """Insert one assessment row and return its id."""
    with sessions.begin() as session:
        row = Assessment(
            user_id=user_id,
            state="COMPLETED",
            consent=Consent(policy_version="1.0.0"),
            result=result,
        )
        session.add(row)
        session.flush()
        return row.id


def _client(sessions: sessionmaker[Session], owner_id: UUID) -> TestClient:
    """History API authenticated as ``owner_id``."""

    def get_user_id(request: Request) -> UUID:
        assert request.headers.get("Authorization") == AUTH["Authorization"]
        return owner_id

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(
        create_history_router(get_user_id, lambda: HistoryService(sessions)),
        prefix="/api/v1",
    )
    return TestClient(app)


def test_history_shows_top_condition_and_detail_returns_saved_result(
    sessions: sessionmaker[Session], owner_id: UUID
) -> None:
    """The list names the rank-1 condition; the detail returns the whole result."""
    assessment_id = uuid4()
    saved = _result(assessment_id).model_dump(mode="json", by_alias=True)
    row_id = _add_assessment(sessions, owner_id, saved)

    with _client(sessions, owner_id) as client:
        items = client.get(PATH, headers=AUTH).json()["items"]
        detail = client.get(f"{PATH}/{row_id}", headers=AUTH).json()

    assert items[0]["topCondition"] == "Sore throat (pharyngitis)"
    assert detail["topCondition"] == "Sore throat (pharyngitis)"
    assert detail["result"]["riskLevel"] == "CONSULT_DOCTOR"
    assert [c["name"] for c in detail["result"]["conditions"]] == [
        "Influenza (flu)",
        "Sore throat (pharyngitis)",
    ]
    assert detail["result"]["guidance"] == ["Rest and drink fluids."]
    assert detail["result"]["disclaimer"]


def test_history_without_saved_result_has_no_result(
    sessions: sessionmaker[Session], owner_id: UUID
) -> None:
    """Assessments finished before results were saved still list normally."""
    row_id = _add_assessment(sessions, owner_id)
    with _client(sessions, owner_id) as client:
        items = client.get(PATH, headers=AUTH).json()["items"]
        detail = client.get(f"{PATH}/{row_id}", headers=AUTH).json()
    assert items[0]["topCondition"] is None
    assert detail["result"] is None


def test_unreadable_saved_result_is_ignored(
    sessions: sessionmaker[Session], owner_id: UUID
) -> None:
    """A damaged saved result never breaks the history page."""
    row_id = _add_assessment(sessions, owner_id, {"riskLevel": "NOT_A_LEVEL"})
    with _client(sessions, owner_id) as client:
        response = client.get(f"{PATH}/{row_id}", headers=AUTH)
    assert response.status_code == 200
    assert response.json()["result"] is None
    assert stored_result(None) is None


def test_result_is_saved_only_for_account_owned_assessments(
    sessions: sessionmaker[Session], owner_id: UUID
) -> None:
    """Results are kept for accounts and never for guests (DR-06)."""
    owned = _add_assessment(sessions, owner_id)
    guest = _add_assessment(sessions, None)
    service = OrchestratorAssessmentService(MagicMock(), session_factory=sessions)

    service._save_result_for_account(owned, _result(owned))
    service._save_result_for_account(guest, _result(guest))
    service._save_result_for_account(uuid4(), _result(uuid4()))  # unknown: no-op

    with sessions() as session:
        owned_row = session.get(Assessment, owned)
        guest_row = session.get(Assessment, guest)
        assert owned_row is not None and guest_row is not None
        assert owned_row.result is not None
        assert owned_row.result["riskLevel"] == "CONSULT_DOCTOR"
        assert guest_row.result is None


def test_result_save_failure_is_logged_not_raised(
    sessions: sessionmaker[Session], owner_id: UUID
) -> None:
    """A database error while saving never reaches the user."""
    broken = MagicMock(side_effect=RuntimeError("database down"))
    service = OrchestratorAssessmentService(MagicMock(), session_factory=broken)
    assessment_id = uuid4()
    service._save_result_for_account(assessment_id, _result(assessment_id))


def test_account_export_includes_saved_result(
    sessions: sessionmaker[Session], owner_id: UUID
) -> None:
    """The DPDP data export carries the saved result (right of access)."""
    assessment_id = uuid4()
    saved = _result(assessment_id).model_dump(mode="json", by_alias=True)
    _add_assessment(sessions, owner_id, saved)
    exported = AccountExport(sessions).export(owner_id)
    assessments = exported["assessments"]
    assert isinstance(assessments, list)
    first = assessments[0]
    assert isinstance(first, dict)
    assert first["result"] == saved
