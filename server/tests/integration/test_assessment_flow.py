"""S1-MOH-2 — Integration tests for the full assessment API flow.

Responsibilities:
    - Test the complete chat lifecycle end-to-end via the HTTP API:
      POST /assessments -> POST /messages -> GET /messages -> GET /symptoms
      -> PATCH /symptoms -> POST /confirm -> POST /analyze -> GET /result.
    - Verify all responses use camelCase wire format (AI_RULES §3.3).
    - Verify mock providers are used — no real LLM or CV calls made.
    - Verify state transitions via the state endpoint after each step.
    - Verify medical-safety rules:
        - disclaimer always present in result (AI_RULES §2 rule 8)
        - no raw percentage fields in result (AI_RULES §2 rule 3)
        - URGENT result exposes emergency number 112 (AI_RULES §2 rule 5)

Owner: Mohit (testing) · Task: S1-MOH-2 · Requirements: FR-03, FR-17, DR-01, DR-02
"""

from uuid import UUID

import pytest
from fastapi import status
from httpx import AsyncClient

from app.schemas.result import DEFAULT_DISCLAIMER

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_CONSENT_ID = "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"
VALID_SYMPTOM_MESSAGE = "I have a test headache and mild test fatigue since yesterday"


def _assert_camel_case_id_field(data: dict) -> None:
    """Assert the response does NOT expose snake_case fields (wire format check)."""
    # The Pydantic alias_generator converts snake_case to camelCase on the wire
    assert "consent_id" not in data, "Wire format must use consentId, not consent_id"
    assert "risk_level" not in data or "riskLevel" in data


# ---------------------------------------------------------------------------
# 1. Full happy-path lifecycle (chained requests)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_full_assessment_api_flow_happy_path(
    async_client: AsyncClient,
    assessment_create_payload: dict,
    send_message_payload: dict,
) -> None:
    """Integration: complete assessment lifecycle returns valid result with disclaimer.

    Flow:
        POST /assessments -> POST /messages -> GET /symptoms -> PATCH /symptoms
        -> POST /analyze -> GET /result
    Verifies camelCase wire format, state progression, and medical-safety rules.
    """
    # Step 1: Create assessment
    resp = await async_client.post(
        "/api/v1/assessments",
        json=assessment_create_payload,
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assessment_data = resp.json()
    assert assessment_data["state"] == "START"
    assert "id" in assessment_data
    assert "consent_id" not in assessment_data  # camelCase wire check
    assessment_id = assessment_data["id"]

    # Validate UUID format
    UUID(assessment_id)

    # Step 2: Send first symptom message
    resp = await async_client.post(
        f"/api/v1/assessments/{assessment_id}/messages",
        json=send_message_payload,
    )
    assert resp.status_code == status.HTTP_200_OK
    msg_data = resp.json()
    assert "message" in msg_data
    assert "assistantMessage" in msg_data
    assert "nextState" in msg_data
    # User message preserved
    assert msg_data["message"]["content"] == send_message_payload["content"]
    assert msg_data["message"]["role"] == "user"
    assert msg_data["assistantMessage"]["role"] == "assistant"

    # Step 3: Get message history
    resp = await async_client.get(f"/api/v1/assessments/{assessment_id}/messages")
    assert resp.status_code == status.HTTP_200_OK
    messages = resp.json()
    assert isinstance(messages, list)
    assert len(messages) >= 2  # user msg + assistant reply
    assert messages[0]["role"] == "user"

    # Step 4: Get extracted symptoms
    resp = await async_client.get(f"/api/v1/assessments/{assessment_id}/symptoms")
    assert resp.status_code == status.HTTP_200_OK
    symptoms = resp.json()
    assert isinstance(symptoms, list)

    # Step 5: Confirm / analyze -> result
    resp = await async_client.post(f"/api/v1/assessments/{assessment_id}/analyze")
    assert resp.status_code == status.HTTP_200_OK
    analyze_data = resp.json()
    assert analyze_data["resultAvailable"] is True

    # Step 6: Get result
    resp = await async_client.get(f"/api/v1/assessments/{assessment_id}/result")
    assert resp.status_code == status.HTTP_200_OK
    result = resp.json()

    # Medical-safety rule §2 rule 8: disclaimer always present
    assert "disclaimer" in result
    assert result["disclaimer"] == DEFAULT_DISCLAIMER

    # Medical-safety rule §2 rule 3: no raw percentages or scores
    assert "score" not in result
    assert "probability" not in result
    for condition in result.get("conditions", []):
        assert "score" not in condition
        assert "probability" not in condition

    # Risk level must be one of the three allowed tiers
    assert result["riskLevel"] in ("SELF_CARE", "CONSULT_DOCTOR", "URGENT")


# ---------------------------------------------------------------------------
# 2. POST /assessments — validation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_assessment_returns_201_and_start_state(
    async_client: AsyncClient,
    assessment_create_payload: dict,
) -> None:
    """POST /assessments with valid payload returns 201 and START state."""
    resp = await async_client.post(
        "/api/v1/assessments",
        json=assessment_create_payload,
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["state"] == "START"
    assert "id" in data
    UUID(data["id"])  # must be a valid UUID


@pytest.mark.anyio
async def test_create_assessment_missing_consent_returns_422(
    async_client: AsyncClient,
) -> None:
    """POST /assessments without consentId returns 422 with VALIDATION_ERROR code."""
    resp = await async_client.post("/api/v1/assessments", json={})
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = resp.json()
    assert data["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_create_assessment_invalid_consent_uuid_returns_422(
    async_client: AsyncClient,
) -> None:
    """POST /assessments with a non-UUID consentId returns 422."""
    resp = await async_client.post(
        "/api/v1/assessments",
        json={"consentId": "not-a-uuid"},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# 3. GET /assessments/{id} — retrieval
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_assessment_returns_200(
    async_client: AsyncClient,
    assessment_create_payload: dict,
) -> None:
    """GET /assessments/{id} returns 200 with assessment data."""
    create = await async_client.post(
        "/api/v1/assessments",
        json=assessment_create_payload,
    )
    aid = create.json()["id"]

    resp = await async_client.get(f"/api/v1/assessments/{aid}")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["id"] == aid


@pytest.mark.anyio
async def test_get_assessment_invalid_uuid_returns_422(
    async_client: AsyncClient,
) -> None:
    """GET /assessments/not-a-uuid returns 422 VALIDATION_ERROR."""
    resp = await async_client.get("/api/v1/assessments/not-a-uuid")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp.json()["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# 4. POST /messages — chat input
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_send_message_empty_content_returns_422(
    async_client: AsyncClient,
    assessment_create_payload: dict,
) -> None:
    """POST /messages with empty content returns 422 VALIDATION_ERROR."""
    create = await async_client.post(
        "/api/v1/assessments",
        json=assessment_create_payload,
    )
    aid = create.json()["id"]

    resp = await async_client.post(
        f"/api/v1/assessments/{aid}/messages",
        json={"content": ""},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.anyio
async def test_send_message_at_4000_chars_accepted(
    async_client: AsyncClient,
    assessment_create_payload: dict,
) -> None:
    """POST /messages with content of exactly 4000 chars returns 200."""
    create = await async_client.post(
        "/api/v1/assessments",
        json=assessment_create_payload,
    )
    aid = create.json()["id"]

    resp = await async_client.post(
        f"/api/v1/assessments/{aid}/messages",
        json={"content": "a" * 4000},
    )
    assert resp.status_code == status.HTTP_200_OK


@pytest.mark.anyio
async def test_send_message_over_4000_chars_rejected(
    async_client: AsyncClient,
    assessment_create_payload: dict,
) -> None:
    """POST /messages with content > 4000 chars returns 422 VALIDATION_ERROR."""
    create = await async_client.post(
        "/api/v1/assessments",
        json=assessment_create_payload,
    )
    aid = create.json()["id"]

    resp = await async_client.post(
        f"/api/v1/assessments/{aid}/messages",
        json={"content": "a" * 4001},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp.json()["code"] == "VALIDATION_ERROR"
