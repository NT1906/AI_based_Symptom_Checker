"""Verify account deletion and password change through the live app routes.

Owner: Nisarg · Task: S2-NIS-18 · Issue: #315 · Requirements: DR-06, NFR-04, FR-01
"""

from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_session_factory
from app.main import create_app
from app.models import Assessment, Base, Consent, Message, Profile, Symptom, User
from app.models.audit_log import AuditLog
from app.services.privacy.account_deletion import AccountDataRepository

DELETE = "/api/v1/privacy/data"
CHANGE = "/api/v1/auth/change-password"
CREDENTIALS = {"email": "settings-owner@example.com", "password": "FixturePassword123!"}


@pytest.fixture
def sessions(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    """A SQLite database with the full schema."""
    engine = create_engine(f"sqlite:///{tmp_path / 'account-settings.db'}")
    Base.metadata.create_all(engine)
    try:
        yield sessionmaker(engine)
    finally:
        engine.dispose()


@pytest.fixture
def client(sessions: sessionmaker[Session]) -> Iterator[TestClient]:
    """The real app wired to the test database."""
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sessions
    with TestClient(app) as test_client:
        yield test_client


def _register_and_login(client: TestClient) -> tuple[UUID, dict[str, str]]:
    """Create the fixture account, log in, and return its id and CSRF header."""
    registration = client.post("/api/v1/auth/register", json=CREDENTIALS)
    assert registration.status_code == 201
    login = client.post("/api/v1/auth/login", json=CREDENTIALS)
    assert login.status_code == 200
    return UUID(registration.json()["id"]), {
        "X-CSRF-Token": login.headers["X-CSRF-Token"]
    }


def _count(session: Session, model: type, *where: object) -> int:
    """Number of rows of ``model`` matching ``where``."""
    return session.scalar(select(func.count()).select_from(model).where(*where)) or 0


def test_delete_account_erases_owned_data_and_ends_session(
    client: TestClient, sessions: sessionmaker[Session]
) -> None:
    """Deletion removes the account's rows, keeps others, unlinks audit rows."""
    owner_id, csrf = _register_and_login(client)
    with sessions.begin() as session:
        owned = Assessment(
            user_id=owner_id,
            consent=Consent(policy_version="1.0.0"),
            messages=[Message(role="user", position=0, content="Example text")],
            symptoms=[Symptom(name="example symptom", details={})],
            result={"riskLevel": "SELF_CARE"},
        )
        other = Assessment(
            user=User(email="other-owner@example.com"),
            consent=Consent(policy_version="1.0.0"),
        )
        session.add_all(
            [owned, other, Profile(user_id=owner_id, chronic_conditions=["asthma"])]
        )
        session.flush()
        session.add(
            AuditLog(
                user_id=owner_id,
                assessment_id=owned.id,
                action="ANALYSIS",
                risk_level="SELF_CARE",
            )
        )
        owned_id, other_id = owned.id, other.id

    response = client.delete(DELETE, headers=csrf)

    assert response.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    with sessions() as session:
        assert session.get(User, owner_id) is None
        assert session.get(Assessment, owned_id) is None
        assert _count(session, Message, Message.assessment_id == owned_id) == 0
        assert _count(session, Symptom, Symptom.assessment_id == owned_id) == 0
        assert _count(session, Profile, Profile.user_id == owner_id) == 0
        assert session.get(Assessment, other_id) is not None
        audit = session.scalars(select(AuditLog)).one()
        assert audit.user_id is None
        assert audit.assessment_id is None
        assert audit.risk_level == "SELF_CARE"
    assert _consents(sessions) == 1  # only the other account's consent remains


def _consents(sessions: sessionmaker[Session]) -> int:
    """Number of consent rows left."""
    with sessions() as session:
        return _count(session, Consent)


def test_delete_requires_csrf_and_repeat_is_noop(
    client: TestClient, sessions: sessionmaker[Session]
) -> None:
    """Without the CSRF header nothing is deleted; deleting twice is harmless."""
    owner_id, csrf = _register_and_login(client)
    assert client.delete(DELETE).status_code == 401
    with sessions() as session:
        assert session.get(User, owner_id) is not None
    assert client.delete(DELETE, headers=csrf).status_code == 204
    AccountDataRepository(sessions).delete_user_data(owner_id)


def test_change_password_then_log_in_with_the_new_one(client: TestClient) -> None:
    """The new password works, the old one stops working."""
    _, csrf = _register_and_login(client)
    body = {
        "currentPassword": CREDENTIALS["password"],
        "newPassword": "BrandNew-Pass-42",
    }

    response = client.post(CHANGE, json=body, headers=csrf)

    assert response.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 200  # still signed in
    old = client.post("/api/v1/auth/login", json=CREDENTIALS)
    assert old.status_code == 401
    new = client.post(
        "/api/v1/auth/login",
        json={"email": CREDENTIALS["email"], "password": "BrandNew-Pass-42"},
    )
    assert new.status_code == 200


@pytest.mark.parametrize(
    ("body", "field"),
    [
        (
            {"currentPassword": "wrong-password", "newPassword": "BrandNew-Pass-42"},
            "currentPassword",
        ),
        (
            {
                "currentPassword": CREDENTIALS["password"],
                "newPassword": CREDENTIALS["password"],
            },
            "newPassword",
        ),
    ],
)
def test_change_password_rejects_wrong_or_unchanged_password(
    client: TestClient, body: dict[str, str], field: str
) -> None:
    """A wrong current password, or no change, is refused with 422."""
    _, csrf = _register_and_login(client)
    response = client.post(CHANGE, json=body, headers=csrf)
    assert response.status_code == 422
    assert response.json()["details"] == {"field": field}


def test_change_password_validates_input_and_needs_csrf(client: TestClient) -> None:
    """Short passwords are refused and the CSRF header is required."""
    _, csrf = _register_and_login(client)
    short = {"currentPassword": CREDENTIALS["password"], "newPassword": "short"}
    assert client.post(CHANGE, json=short, headers=csrf).status_code == 422
    good = {"currentPassword": CREDENTIALS["password"], "newPassword": "BrandNew-42"}
    assert client.post(CHANGE, json=good).status_code == 401
    client.cookies.clear()
    assert client.post(CHANGE, json=good, headers=csrf).status_code == 401
