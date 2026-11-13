"""Verify history pagination, authentication, and ownership with fictional data.

Owner: Harsh · Task: S2-HAR-1 · Issue: #172 · Requirements: FR-02
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.history import create_history_router
from app.core.errors import UnauthorizedError, register_error_handlers
from app.models import Assessment, Base, Consent, User
from app.services.privacy.history import HistoryService


@pytest.fixture
def history_api(tmp_path: Path) -> Iterator[tuple[TestClient, list[UUID]]]:
    """Mount the history router with real SQLite queries and a test identity."""
    engine = create_engine(f"sqlite:///{tmp_path / 'history.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    with sessions.begin() as session:
        owner = User(email="history-owner@example.test")
        other = User(email="history-other@example.test")
        session.add_all((owner, other))
        session.flush()
        owner_id = owner.id
        now = datetime(2026, 11, 13, tzinfo=UTC)
        rows = [
            Assessment(
                user_id=account,
                consent=Consent(policy_version="1.0.0"),
                created_at=now - timedelta(minutes=index),
            )
            for index, account in enumerate((owner_id, owner_id, other.id, None))
        ]
        session.add_all(rows)
        session.flush()
        ids = [row.id for row in rows]

    def get_user_id(request: Request) -> UUID:
        if request.headers.get("Authorization") != "Bearer fixture-owner":
            raise UnauthorizedError()
        return owner_id

    def get_service() -> HistoryService:
        return HistoryService(sessions)

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(
        create_history_router(get_user_id, get_service), prefix="/api/v1"
    )
    try:
        with TestClient(app) as client:
            yield client, ids
    finally:
        engine.dispose()


AUTH = {"Authorization": "Bearer fixture-owner"}
PATH = "/api/v1/history"


def test_history_paginates_only_owned_assessments(
    history_api: tuple[TestClient, list[UUID]],
) -> None:
    client, ids = history_api
    first = client.get(PATH, params={"limit": 1}, headers=AUTH)
    assert first.status_code == 200
    assert first.headers["cache-control"] == "no-store"
    assert [item["id"] for item in first.json()["items"]] == [str(ids[0])]
    assert first.json()["nextOffset"] == 1
    second = client.get(PATH, params={"limit": 1, "offset": 1}, headers=AUTH)
    assert [item["id"] for item in second.json()["items"]] == [str(ids[1])]
    assert second.json()["nextOffset"] is None
    empty = client.get(PATH, params={"offset": 2}, headers=AUTH)
    assert empty.json() == {"items": [], "nextOffset": None}


def test_history_detail_hides_guest_and_other_accounts(
    history_api: tuple[TestClient, list[UUID]],
) -> None:
    client, ids = history_api
    owned = client.get(f"{PATH}/{ids[0]}", headers=AUTH)
    assert owned.status_code == 200
    assert owned.json()["id"] == str(ids[0])
    for assessment_id in (ids[2], ids[3], UUID(int=0)):
        hidden = client.get(f"{PATH}/{assessment_id}", headers=AUTH)
        assert hidden.status_code == 404
        assert hidden.json()["code"] == "NOT_FOUND"


@pytest.mark.parametrize("path", [PATH, f"{PATH}/{UUID(int=0)}"])
def test_history_requires_authentication(
    history_api: tuple[TestClient, list[UUID]],
    path: str,
) -> None:
    client, _ = history_api
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_history_rejects_invalid_pagination(
    history_api: tuple[TestClient, list[UUID]],
    params: dict[str, int],
) -> None:
    client, _ = history_api
    assert client.get(PATH, params=params, headers=AUTH).status_code == 422
