"""End-to-end HTTP tests for the orchestrator-backed assessment service.

Covers:
    - Happy path: real extraction, condition model and risk engine (mock AI and
      CV providers) give an input-dependent, repeatable result.
    - Safety: a red-flag message ends URGENT with the 112 step first; every
      result carries the disclaimer and no raw scores.
    - Clarifying questions work (regression: the symptom state sent to the
      privacy gateway must be JSON, or every question crashed with a 500).
    - The CV model being unavailable never stops a text assessment (S2-NIS-14).
    - Edge and failure cases: result before analysis (409), repeated analysis,
      a message after confirmation (409, not 500), unknown IDs (404).
    - The confirmed symptom list replaces the stored one: a symptom the user
      removed no longer counts, kept ones keep their ID and details (#351).

Owner: Nisarg (integration) · Task: S2-NIS-13 · Requirements: FR-01, FR-06, DR-01, DR-02
Symptom list replacement: Nisarg · S2-NIS-29 (#351)
"""

from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from app.api.deps import get_ai_gateway_dep, get_assessment_service, get_session_factory
from app.api.orchestrator_service import (
    UnavailableImageAnalyzer,
    _replacement_list,
    build_orchestrator_service,
)
from app.schemas.enums import DurationUnit, Severity, SymptomSource
from app.schemas.symptom import Duration, SymptomRead, SymptomUpdate
from app.services.image.analyzer import ImageAnalysisError
from app.services.image.mock_analyzer import MockImageAnalyzer
from app.core.config import Settings
from app.models.base import Base
from app.models.consent import Consent
from app.services.privacy.consent import CURRENT_POLICY_VERSION
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

CONSENT_ID = UUID("00000000-0000-4000-8000-0000000000c1")
BASE = "/api/v1/assessments"


def _install_service(app: FastAPI, settings: Settings, tmp_path: Path) -> Engine:
    """Serve the app from a fresh orchestrator service and a consent DB."""
    engine = create_engine(f"sqlite:///{tmp_path / 'e2e.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions.begin() as session:
        session.add(Consent(id=CONSENT_ID, policy_version=CURRENT_POLICY_VERSION))
    service = build_orchestrator_service(settings, get_ai_gateway_dep(settings), None)
    app.dependency_overrides[get_assessment_service] = lambda: service
    app.dependency_overrides[get_session_factory] = lambda: sessions
    return engine


@pytest.fixture
def real_service(
    app: FastAPI, test_settings: Settings, tmp_path: Path
) -> Iterator[None]:
    """Serve the test app from a fresh orchestrator service and a consent DB."""
    engine = _install_service(app, test_settings, tmp_path)
    yield
    app.dependency_overrides.pop(get_session_factory, None)
    engine.dispose()


@pytest.fixture
async def http(app: FastAPI, real_service: None) -> AsyncIterator[AsyncClient]:
    """Async client bound to the test app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def _assess(http: AsyncClient, *messages: str) -> dict[str, Any]:
    """Create an assessment, send messages, analyze, and return the result."""
    created = await http.post(BASE, json={"consentId": str(CONSENT_ID)})
    assert created.status_code == status.HTTP_201_CREATED
    aid = created.json()["id"]
    for text in messages:
        sent = await http.post(f"{BASE}/{aid}/messages", json={"content": text})
        assert sent.status_code == status.HTTP_200_OK
    analyzed = await http.post(f"{BASE}/{aid}/analyze")
    assert analyzed.status_code == status.HTTP_200_OK
    assert analyzed.json() == {
        "assessmentId": aid,
        "state": "COMPLETED",
        "resultAvailable": True,
    }
    result = await http.get(f"{BASE}/{aid}/result")
    assert result.status_code == status.HTTP_200_OK
    body: dict[str, Any] = result.json()
    return body


@pytest.mark.anyio
async def test_result_depends_on_what_the_user_reported(http: AsyncClient) -> None:
    throat = await _assess(http, "I have a sore throat and fever since 2 days")
    tired = await _assess(http, "I feel a bit tired")

    assert throat["riskLevel"] == "SELF_CARE"
    assert throat["conditions"][0]["name"] != tired["conditions"][0]["name"]
    assert throat["conditions"][0]["why"].startswith("Because you reported")


@pytest.mark.anyio
async def test_same_input_gives_the_same_result(http: AsyncClient) -> None:
    first = await _assess(http, "I have a sore throat and fever since 2 days")
    second = await _assess(http, "I have a sore throat and fever since 2 days")

    for key in ("riskLevel", "conditions", "guidance", "limitations"):
        assert first[key] == second[key]


@pytest.mark.anyio
async def test_red_flag_ends_urgent_with_112_first(http: AsyncClient) -> None:
    result = await _assess(
        http, "I have severe chest pain and I can't breathe properly"
    )

    assert result["riskLevel"] == "URGENT"
    assert "112" in result["guidance"][0]
    assert result["referral"]["emergencyNumber"] == "112"


@pytest.mark.anyio
async def test_every_result_has_disclaimer_and_no_scores(http: AsyncClient) -> None:
    result = await _assess(http, "I feel a bit tired")

    assert result["disclaimer"].startswith("This is not a medical diagnosis.")
    for condition in result["conditions"]:
        assert set(condition).isdisjoint({"score", "probability"})
        assert condition["confidence"] in {"LIKELY", "POSSIBLE", "LESS_LIKELY"}


@pytest.mark.anyio
async def test_clarifying_question_is_returned_not_a_server_error(
    http: AsyncClient,
) -> None:
    created = await http.post(BASE, json={"consentId": str(CONSENT_ID)})
    aid = created.json()["id"]

    sent = await http.post(
        f"{BASE}/{aid}/messages", json={"content": "I feel a bit tired"}
    )

    assert sent.status_code == status.HTTP_200_OK
    assert sent.json()["nextState"] == "CLARIFYING"
    assert sent.json()["assistantMessage"]["messageType"] == "CLARIFICATION"


@pytest.mark.anyio
async def test_result_before_analysis_is_a_conflict(http: AsyncClient) -> None:
    created = await http.post(BASE, json={"consentId": str(CONSENT_ID)})

    resp = await http.get(f"{BASE}/{created.json()['id']}/result")

    assert resp.status_code == status.HTTP_409_CONFLICT


@pytest.mark.anyio
async def test_analysing_twice_returns_the_same_result(http: AsyncClient) -> None:
    created = await http.post(BASE, json={"consentId": str(CONSENT_ID)})
    aid = created.json()["id"]
    await http.post(f"{BASE}/{aid}/messages", json={"content": "I have a sore throat"})
    await http.post(f"{BASE}/{aid}/analyze")
    first = (await http.get(f"{BASE}/{aid}/result")).json()

    again = await http.post(f"{BASE}/{aid}/analyze")

    assert again.status_code == status.HTTP_200_OK
    assert (await http.get(f"{BASE}/{aid}/result")).json() == first


@pytest.mark.anyio
async def test_message_after_confirmation_is_a_conflict(http: AsyncClient) -> None:
    created = await http.post(BASE, json={"consentId": str(CONSENT_ID)})
    aid = created.json()["id"]
    first = await http.post(
        f"{BASE}/{aid}/messages",
        json={"content": "I have a sore throat and fever since 2 days"},
    )
    assert first.json()["nextState"] == "CONFIRMING"

    resp = await http.post(f"{BASE}/{aid}/messages", json={"content": "it is moderate"})

    assert resp.status_code == status.HTTP_409_CONFLICT


@pytest.mark.anyio
@pytest.mark.parametrize("suffix", ["", "/state", "/result"])
async def test_unknown_assessment_is_not_found(http: AsyncClient, suffix: str) -> None:
    resp = await http.get(f"{BASE}/{uuid4()}{suffix}")

    assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.anyio
async def test_analysing_an_unknown_assessment_is_not_found(http: AsyncClient) -> None:
    resp = await http.post(f"{BASE}/{uuid4()}/analyze")

    assert resp.status_code == status.HTTP_404_NOT_FOUND


# --- S2-NIS-14: the optional photo step must never stop a text assessment ---


@pytest.mark.anyio
async def test_text_assessment_completes_when_the_cv_model_is_missing(
    app: FastAPI, test_settings: Settings, tmp_path: Path
) -> None:
    """``CV_PROVIDER=onnx`` before the model exists (as on Render) runs text-only."""
    settings = test_settings.model_copy(update={"cv_provider": "onnx"})
    engine = _install_service(app, settings, tmp_path)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as client:
            result = await _assess(
                client, "I have a sore throat and fever since 2 days"
            )
    finally:
        app.dependency_overrides.pop(get_session_factory, None)
        engine.dispose()

    assert result["riskLevel"] == "SELF_CARE"


@pytest.mark.parametrize(
    ("provider", "expected"),
    [
        ("mock", MockImageAnalyzer),
        ("onnx", UnavailableImageAnalyzer),
        ("nope", UnavailableImageAnalyzer),
    ],
)
def test_unavailable_provider_gets_a_text_only_stand_in(
    test_settings: Settings, provider: str, expected: type
) -> None:
    from app.api import orchestrator_service

    analyzer = orchestrator_service._image_analyzer_or_unavailable(provider)

    assert isinstance(analyzer, expected)


@pytest.mark.anyio
async def test_stand_in_never_invents_a_finding() -> None:
    with pytest.raises(ImageAnalysisError):
        await UnavailableImageAnalyzer("onnx").analyze(b"\xff\xd8 fake jpeg")


# --- confirmed list replaces the stored one (S2-NIS-29, #351) --------------------

HEADACHE = SymptomRead(
    name="headache",
    severity=Severity.MILD,
    duration=Duration(value=2, unit=DurationUnit.DAY),
    source=SymptomSource.AI_EXTRACTED,
)
CHEST_PAIN = SymptomRead(name="chest_pain", source=SymptomSource.AI_EXTRACTED)


def test_symptom_left_out_of_the_update_is_removed() -> None:
    kept = _replacement_list(
        [CHEST_PAIN, HEADACHE], [SymptomUpdate(id=HEADACHE.id, name="headache")]
    )

    assert [s.name for s in kept] == ["headache"]


def test_kept_symptom_keeps_its_id_and_unedited_details() -> None:
    kept = _replacement_list(
        [HEADACHE], [SymptomUpdate(id=HEADACHE.id, severity=Severity.MODERATE)]
    )

    assert kept[0].id == HEADACHE.id
    assert kept[0].name == "headache"
    assert kept[0].severity is Severity.MODERATE
    assert kept[0].duration == HEADACHE.duration
    assert kept[0].source is SymptomSource.USER_CORRECTED


def test_update_without_id_matches_by_name() -> None:
    kept = _replacement_list([HEADACHE], [SymptomUpdate(name="Headache")])

    assert [s.id for s in kept] == [HEADACHE.id]


def test_new_symptom_is_added_in_the_users_order() -> None:
    kept = _replacement_list(
        [HEADACHE],
        [
            SymptomUpdate(name="fever", severity=Severity.MILD),
            SymptomUpdate(id=HEADACHE.id, name="headache"),
        ],
    )

    assert [s.name for s in kept] == ["fever", "headache"]
    assert kept[0].source is SymptomSource.USER
    assert kept[0].severity is Severity.MILD


def test_new_symptom_without_a_name_is_skipped() -> None:
    assert _replacement_list([HEADACHE], [SymptomUpdate(id=uuid4())]) == []


def test_empty_update_removes_everything() -> None:
    assert _replacement_list([CHEST_PAIN, HEADACHE], []) == []
