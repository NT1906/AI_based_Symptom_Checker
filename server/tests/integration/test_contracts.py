"""S1-MOH-3 — Contract tests: every endpoint response matches published schemas.

Responsibilities:
    - Validate every assessment and consent endpoint response can be parsed by
      the corresponding published Pydantic schema (AssessmentRead, MessageRead,
      SymptomRead, AssessmentResult, AssessmentStateResponse, ConsentResponse).
    - Validate camelCase wire format on all JSON responses.
    - Validate OpenAPI-documented error shape (ErrorResponse) on 4xx routes.
    - Ensure the disclaimer field in AssessmentResult is always the exact
      DEFAULT_DISCLAIMER constant (AI_RULES §2 rule 8).

Owner: Mohit (testing) · Task: S1-MOH-3 · Requirements: DR-01
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.deps import get_db_engine, get_session_factory
from app.api.v1._assessment_stubs import STUB_ASSESSMENT_ID
from app.api.v1.consents import ConsentRequest, ConsentResponse
from app.core.errors import ErrorResponse
from app.models.base import Base
from app.models.consent import Consent
from app.schemas.assessment import AssessmentRead, AssessmentStateResponse
from app.schemas.enums import AssessmentState, RiskLevel
from app.schemas.message import MessageRead
from app.schemas.result import DEFAULT_DISCLAIMER, AssessmentResult
from app.schemas.symptom import SymptomRead
from app.services.privacy.consent import CURRENT_POLICY_VERSION
from tests.conftest import FAKE_CONSENT_ID

SAMPLE_CONSENT_ID = "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"
SAMPLE_UUID = str(STUB_ASSESSMENT_ID)


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------


def _parse_or_fail[T: BaseModel](
    schema_cls: type[T], data: dict[str, Any], endpoint: str
) -> T:
    """Parse *data* with *schema_cls*; raise AssertionError with context on failure."""
    try:
        return schema_cls.model_validate(data)
    except Exception as exc:
        raise AssertionError(
            f"Response from {endpoint} failed {schema_cls.__name__} validation: {exc}"
        ) from exc


@pytest.fixture(autouse=True)
def setup_test_database(app: FastAPI, tmp_path: Path) -> Iterator[None]:
    """Provide an isolated database with verified consents for contract tests."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'contract-test.db'}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory.begin() as session:
        session.add(
            Consent(
                id=FAKE_CONSENT_ID,
                policy_version=CURRENT_POLICY_VERSION,
            )
        )
        session.add(
            Consent(
                id=UUID(SAMPLE_CONSENT_ID),
                policy_version=CURRENT_POLICY_VERSION,
            )
        )

    app.state.db_engine = engine
    app.state.session_factory = session_factory
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    app.dependency_overrides[get_db_engine] = lambda: engine
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_session_factory, None)
        app.dependency_overrides.pop(get_db_engine, None)
        engine.dispose()


# ---------------------------------------------------------------------------
# 1. POST /api/v1/assessments -> AssessmentRead
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_create_assessment(async_client: AsyncClient) -> None:
    """POST /assessments response must satisfy AssessmentRead schema."""
    resp = await async_client.post(
        "/api/v1/assessments",
        json={"consentId": SAMPLE_CONSENT_ID},
    )
    assert resp.status_code == status.HTTP_201_CREATED

    parsed = _parse_or_fail(AssessmentRead, resp.json(), "POST /api/v1/assessments")
    assert isinstance(parsed.id, UUID)
    assert parsed.state is not None

    raw = resp.json()
    assert "id" in raw
    assert "state" in raw
    assert "consent_id" not in raw, "Wire must use consentId not consent_id"


# ---------------------------------------------------------------------------
# 2. GET /api/v1/assessments/{id} -> AssessmentRead
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_get_assessment(async_client: AsyncClient) -> None:
    """GET /assessments/{id} response must satisfy AssessmentRead schema."""
    resp = await async_client.get(f"/api/v1/assessments/{SAMPLE_UUID}")
    assert resp.status_code == status.HTTP_200_OK

    parsed = _parse_or_fail(AssessmentRead, resp.json(), "GET /api/v1/assessments/{id}")
    assert str(parsed.id) == SAMPLE_UUID


# ---------------------------------------------------------------------------
# 3. GET /api/v1/assessments/{id}/state -> AssessmentStateResponse
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_get_assessment_state(async_client: AsyncClient) -> None:
    """GET /assessments/{id}/state response satisfies AssessmentStateResponse schema."""
    resp = await async_client.get(f"/api/v1/assessments/{SAMPLE_UUID}/state")
    assert resp.status_code == status.HTTP_200_OK

    parsed = _parse_or_fail(
        AssessmentStateResponse,
        resp.json(),
        "GET /api/v1/assessments/{id}/state",
    )
    assert str(parsed.assessment_id) == SAMPLE_UUID
    assert parsed.clarification_count >= 0
    assert parsed.max_clarifications > 0

    raw = resp.json()
    assert "assessmentId" in raw, "Wire format must use assessmentId"
    assert "clarificationCount" in raw, "Wire format must use clarificationCount"
    assert "maxClarifications" in raw, "Wire format must use maxClarifications"


# ---------------------------------------------------------------------------
# 4. POST /api/v1/assessments/{id}/messages -> SendMessageResponse shape
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_send_message(async_client: AsyncClient) -> None:
    """POST /messages response has message, assistantMessage, nextState."""
    resp = await async_client.post(
        f"/api/v1/assessments/{SAMPLE_UUID}/messages",
        json={"content": "I have a test headache since yesterday"},
    )
    assert resp.status_code == status.HTTP_200_OK

    raw = resp.json()
    assert "message" in raw, "message field missing"
    assert "assistantMessage" in raw, "assistantMessage field missing"
    assert "nextState" in raw, "nextState field missing"

    user_msg = _parse_or_fail(MessageRead, raw["message"], "message field")
    asst_msg = _parse_or_fail(
        MessageRead, raw["assistantMessage"], "assistantMessage field"
    )
    assert user_msg.role.value == "user"
    assert asst_msg.role.value == "assistant"

    valid_states = {s.value for s in AssessmentState}
    assert raw["nextState"] in valid_states


# ---------------------------------------------------------------------------
# 5. GET /api/v1/assessments/{id}/messages -> list[MessageRead]
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_get_messages(async_client: AsyncClient) -> None:
    """GET /messages response is a list where each item satisfies MessageRead."""
    resp = await async_client.get(f"/api/v1/assessments/{SAMPLE_UUID}/messages")
    assert resp.status_code == status.HTTP_200_OK

    raw_list = resp.json()
    assert isinstance(raw_list, list)
    for item in raw_list:
        _parse_or_fail(MessageRead, item, "GET /messages item")


# ---------------------------------------------------------------------------
# 6. GET /api/v1/assessments/{id}/symptoms -> list[SymptomRead]
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_get_symptoms(async_client: AsyncClient) -> None:
    """GET /symptoms response is a list where each item satisfies SymptomRead."""
    resp = await async_client.get(f"/api/v1/assessments/{SAMPLE_UUID}/symptoms")
    assert resp.status_code == status.HTTP_200_OK

    raw_list = resp.json()
    assert isinstance(raw_list, list)
    for item in raw_list:
        _parse_or_fail(SymptomRead, item, "GET /symptoms item")


# ---------------------------------------------------------------------------
# 7. PATCH /api/v1/assessments/{id}/symptoms -> list[SymptomRead]
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_update_symptoms(async_client: AsyncClient) -> None:
    """PATCH /symptoms response is a list where each item satisfies SymptomRead."""
    payload = {
        "symptoms": [
            {
                "name": "headache",
                "severity": "MILD",
                "source": "USER_CONFIRMED",
            }
        ]
    }
    resp = await async_client.patch(
        f"/api/v1/assessments/{SAMPLE_UUID}/symptoms",
        json=payload,
    )
    assert resp.status_code == status.HTTP_200_OK

    raw_list = resp.json()
    assert isinstance(raw_list, list)
    for item in raw_list:
        _parse_or_fail(SymptomRead, item, "PATCH /symptoms item")
        assert item.get("source") == "USER_CONFIRMED"


# ---------------------------------------------------------------------------
# 8. POST /api/v1/assessments/{id}/analyze -> AnalyzeResponse shape
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_analyze_assessment(async_client: AsyncClient) -> None:
    """POST /analyze response satisfies AnalyzeResponse shape contract."""
    resp = await async_client.post(f"/api/v1/assessments/{SAMPLE_UUID}/analyze")
    assert resp.status_code == status.HTTP_200_OK

    raw = resp.json()
    assert "assessmentId" in raw, "assessmentId missing from AnalyzeResponse"
    assert "state" in raw, "state missing from AnalyzeResponse"
    assert "resultAvailable" in raw, "resultAvailable missing from AnalyzeResponse"
    assert isinstance(raw["resultAvailable"], bool)
    UUID(raw["assessmentId"])


# ---------------------------------------------------------------------------
# 9. GET /api/v1/assessments/{id}/result -> AssessmentResult
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_get_result(async_client: AsyncClient) -> None:
    """GET /result response must satisfy AssessmentResult schema."""
    resp = await async_client.get(f"/api/v1/assessments/{SAMPLE_UUID}/result")
    assert resp.status_code == status.HTTP_200_OK

    parsed = _parse_or_fail(
        AssessmentResult, resp.json(), "GET /api/v1/assessments/{id}/result"
    )

    assert parsed.disclaimer == DEFAULT_DISCLAIMER, (
        "Disclaimer in result does not match DEFAULT_DISCLAIMER constant"
    )
    assert parsed.risk_level in (
        RiskLevel.SELF_CARE,
        RiskLevel.CONSULT_DOCTOR,
        RiskLevel.URGENT,
    )

    raw = resp.json()
    assert "riskLevel" in raw, "Wire format must use riskLevel"
    assert "assessmentId" in raw, "Wire format must use assessmentId"
    assert "risk_level" not in raw, "snake_case must not appear on wire"


# ---------------------------------------------------------------------------
# 10. GET /api/v1/consents/current-policy -> ConsentRequest
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_get_current_policy(async_client: AsyncClient) -> None:
    """GET /consents/current-policy satisfies ConsentRequest schema."""
    resp = await async_client.get("/api/v1/consents/current-policy")
    assert resp.status_code == status.HTTP_200_OK

    parsed = _parse_or_fail(
        ConsentRequest, resp.json(), "GET /api/v1/consents/current-policy"
    )
    assert parsed.policy_version == CURRENT_POLICY_VERSION
    assert "policyVersion" in resp.json()


# ---------------------------------------------------------------------------
# 11. POST /api/v1/consents -> ConsentResponse
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_create_consent(async_client: AsyncClient) -> None:
    """POST /consents satisfies ConsentResponse schema."""
    resp = await async_client.post(
        "/api/v1/consents",
        json={"policyVersion": CURRENT_POLICY_VERSION},
    )
    assert resp.status_code == status.HTTP_201_CREATED

    raw = resp.json()
    assert "consentId" in raw
    UUID(raw["consentId"])
    parsed = ConsentResponse.model_validate({"consent_id": raw["consentId"]})
    assert str(parsed.consent_id) == raw["consentId"]


# ---------------------------------------------------------------------------
# 12. Error response shape: 422 VALIDATION_ERROR
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_error_response_shape_on_422(
    async_client: AsyncClient,
) -> None:
    """422 error response must satisfy ErrorResponse schema with VALIDATION_ERROR."""
    resp = await async_client.post(
        "/api/v1/assessments",
        json={},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    parsed = _parse_or_fail(ErrorResponse, resp.json(), "POST /api/v1/assessments 422")
    assert parsed.code == "VALIDATION_ERROR"
    assert len(parsed.message) > 0
    assert len(parsed.request_id) > 0


# ---------------------------------------------------------------------------
# 13. Error response shape: invalid UUID path -> 422
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_invalid_uuid_path_error_shape(
    async_client: AsyncClient,
) -> None:
    """Path parameter validation error must satisfy ErrorResponse schema."""
    resp = await async_client.get("/api/v1/assessments/not-a-valid-uuid")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    parsed = _parse_or_fail(
        ErrorResponse, resp.json(), "GET /assessments/invalid-uuid 422"
    )
    assert parsed.code == "VALIDATION_ERROR"
    assert len(parsed.message) > 0


# ---------------------------------------------------------------------------
# 14. Error response shape: 404 NOT_FOUND
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_not_found_error_shape(
    async_client: AsyncClient,
) -> None:
    """404 error response for unmatched route satisfies ErrorResponse schema."""
    resp = await async_client.get("/api/v1/nonexistent-route")
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    parsed = _parse_or_fail(ErrorResponse, resp.json(), "GET /nonexistent-route 404")
    assert parsed.code == "NOT_FOUND"
    assert len(parsed.message) > 0
    assert len(parsed.request_id) > 0


# ---------------------------------------------------------------------------
# 15. Error response shape: 409 CONFLICT (unregistered consent)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_conflict_error_shape(
    async_client: AsyncClient,
) -> None:
    """409 error response for unconsented assessment satisfies ErrorResponse."""
    unregistered_consent = "99999999-9999-9999-9999-999999999999"
    resp = await async_client.post(
        "/api/v1/assessments",
        json={"consentId": unregistered_consent},
    )
    assert resp.status_code == status.HTTP_409_CONFLICT

    parsed = _parse_or_fail(ErrorResponse, resp.json(), "POST /api/v1/assessments 409")
    assert parsed.code == "CONSENT_REQUIRED"
    assert len(parsed.message) > 0
    assert parsed.details == {"policyVersion": CURRENT_POLICY_VERSION}


# ---------------------------------------------------------------------------
# 16. GET /api/v1/health -> {status, version}
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_contract_health_endpoint(async_client: AsyncClient) -> None:
    """GET /api/v1/health must return {status: 'ok', version: <str>}."""
    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == status.HTTP_200_OK

    raw = resp.json()
    assert raw.get("status") == "ok"
    assert isinstance(raw.get("version"), str)
    assert len(raw["version"]) > 0
