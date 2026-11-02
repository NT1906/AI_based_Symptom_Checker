"""Unit tests for the assessment endpoints and stub payloads.

Responsibilities:
    - Verify happy path status codes and response models for all assessment routes.
    - Test edge cases (e.g. 4000 character message length).
    - Validate failure scenarios (422 validation, 405 method not allowed).
    - Enforce medical-safety rules (AI_RULES.md §2).

Owner: Vivek (tests) · Task: S1-VIV-1 · Requirements: —
"""

from fastapi import status
from fastapi.testclient import TestClient

from app.api.v1._assessment_stubs import (
    STUB_ASSESSMENT_ID,
    STUB_URGENT_ASSESSMENT_ID,
)
from app.schemas.enums import ConfidenceLabel
from app.schemas.result import DEFAULT_DISCLAIMER

SAMPLE_UUID = "e4caa1b2-8493-4a16-928e-5b1287c95e1a"
SAMPLE_CONSENT_ID = "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"


def test_create_assessment_returns_201_and_start_state(
    client: TestClient,
) -> None:
    """Verify POST /api/v1/assessments initializes session in START state."""
    payload = {"consentId": SAMPLE_CONSENT_ID}
    response = client.post("/api/v1/assessments", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["state"] == "START"
    assert data["consentId"] == SAMPLE_CONSENT_ID
    assert "id" in data
    assert "createdAt" in data
    # Verify camelCase wire formatting
    assert "consent_id" not in data


def test_get_assessment_by_id_returns_200(client: TestClient) -> None:
    """Verify GET /api/v1/assessments/{id} returns assessment summary."""
    response = client.get(f"/api/v1/assessments/{SAMPLE_UUID}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == SAMPLE_UUID
    assert data["state"] == "START"


def test_get_assessment_state_returns_200_and_snapshot(
    client: TestClient,
) -> None:
    """Verify GET /api/v1/assessments/{id}/state returns state snapshot."""
    response = client.get(f"/api/v1/assessments/{SAMPLE_UUID}/state")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["assessmentId"] == SAMPLE_UUID
    assert data["state"] == "START"
    assert "clarificationCount" in data
    assert data["maxClarifications"] == 3


def test_send_message_returns_200_and_assistant_reply(
    client: TestClient,
) -> None:
    """Verify POST /api/v1/assessments/{id}/messages accepts text and clarifies."""
    payload = {"content": "I have had a throbbing headache for two days."}
    response = client.post(
        f"/api/v1/assessments/{SAMPLE_UUID}/messages",
        json=payload,
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "message" in data
    assert "assistantMessage" in data
    assert data["nextState"] == "CLARIFYING"
    assert data["message"]["content"] == payload["content"]
    assert data["assistantMessage"]["role"] == "assistant"


def test_get_messages_returns_200_and_dialogue_history(
    client: TestClient,
) -> None:
    """Verify GET /api/v1/assessments/{id}/messages returns message list."""
    response = client.get(f"/api/v1/assessments/{SAMPLE_UUID}/messages")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert data[0]["role"] == "user"
    assert data[1]["role"] == "assistant"


def test_get_symptoms_returns_200_and_extracted_list(
    client: TestClient,
) -> None:
    """Verify GET /api/v1/assessments/{id}/symptoms returns recognized symptoms."""
    response = client.get(f"/api/v1/assessments/{SAMPLE_UUID}/symptoms")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    symptom_names = [s["name"] for s in data]
    assert "headache" in symptom_names


def test_update_symptoms_returns_200_and_confirmed_list(
    client: TestClient,
) -> None:
    """Verify PATCH /api/v1/assessments/{id}/symptoms returns confirmed symptoms."""
    payload = {
        "symptoms": [
            {
                "name": "headache",
                "severity": "SEVERE",
                "source": "USER_CONFIRMED",
            },
            {
                "name": "photophobia",
                "severity": "MODERATE",
                "source": "USER_CONFIRMED",
            },
        ]
    }
    response = client.patch(
        f"/api/v1/assessments/{SAMPLE_UUID}/symptoms",
        json=payload,
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    for symptom in data:
        assert symptom["source"] == "USER_CONFIRMED"


def test_analyze_assessment_returns_200_and_completed_state(
    client: TestClient,
) -> None:
    """Verify POST /api/v1/assessments/{id}/analyze triggers analysis."""
    response = client.post(f"/api/v1/assessments/{SAMPLE_UUID}/analyze")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["assessmentId"] == SAMPLE_UUID
    assert data["state"] == "COMPLETED"
    assert data["resultAvailable"] is True


def test_get_result_returns_200_and_valid_assessment_result(
    client: TestClient,
) -> None:
    """Verify GET /api/v1/assessments/{id}/result returns valid triage result."""
    response = client.get(f"/api/v1/assessments/{SAMPLE_UUID}/result")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["assessmentId"] == SAMPLE_UUID
    assert data["riskLevel"] in ("SELF_CARE", "CONSULT_DOCTOR", "URGENT")
    assert len(data["conditions"]) > 0
    assert len(data["guidance"]) > 0
    assert "referral" in data


def test_send_message_edge_case_accepts_exactly_4000_chars(
    client: TestClient,
) -> None:
    """Verify messages of exactly 4000 characters are accepted."""
    long_content = "a" * 4000
    response = client.post(
        f"/api/v1/assessments/{SAMPLE_UUID}/messages",
        json={"content": long_content},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"]["content"] == long_content


def test_invalid_uuid_returns_422(client: TestClient) -> None:
    """Verify invalid UUID in path parameter returns HTTP 422 with ErrorResponse."""
    response = client.get("/api/v1/assessments/not-a-valid-uuid")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert "message" in data


def test_empty_message_returns_422(client: TestClient) -> None:
    """Verify empty message content returns HTTP 422."""
    response = client.post(
        f"/api/v1/assessments/{SAMPLE_UUID}/messages",
        json={"content": ""},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"


def test_overlength_message_returns_422(client: TestClient) -> None:
    """Verify message content exceeding 4000 characters returns HTTP 422."""
    too_long = "a" * 4001
    response = client.post(
        f"/api/v1/assessments/{SAMPLE_UUID}/messages",
        json={"content": too_long},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"


def test_create_assessment_missing_consent_returns_422(
    client: TestClient,
) -> None:
    """Verify POST /api/v1/assessments without consentId returns HTTP 422."""
    response = client.post("/api/v1/assessments", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"


def test_invalid_http_method_returns_405(client: TestClient) -> None:
    """Verify unsupported HTTP method on assessment router returns HTTP 405."""
    response = client.delete(f"/api/v1/assessments/{SAMPLE_UUID}")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_medical_safety_disclaimer_and_no_diagnostic_wording(
    client: TestClient,
) -> None:
    """Verify result payload adheres strictly to AI_RULES §2 medical safety."""
    response = client.get(f"/api/v1/assessments/{STUB_ASSESSMENT_ID}/result")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    # 1. Exact mandatory disclaimer
    assert data["disclaimer"] == DEFAULT_DISCLAIMER

    # 2. Confidence restricted to allowed categorical enums
    allowed_confidences = {c.value for c in ConfidenceLabel}
    for condition in data["conditions"]:
        assert condition["confidence"] in allowed_confidences
        # 3. No raw percentage scores or probability metrics on conditions
        assert "score" not in condition
        assert "probability" not in condition
        # 4. No diagnostic phrasing
        desc = condition["description"].lower()
        assert not desc.startswith("you have")
        assert not desc.startswith("diagnosis:")

    # 5. Guidance must not contain prescription or drug dosage instructions
    for line in data["guidance"]:
        lowered = line.lower()
        assert "take " not in lowered or "mg" not in lowered


def test_urgent_result_stub_includes_emergency_number_112(
    client: TestClient,
) -> None:
    """Verify URGENT result stub prioritizes emergency number 112."""
    response = client.get(f"/api/v1/assessments/{STUB_URGENT_ASSESSMENT_ID}/result")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["riskLevel"] == "URGENT"
    assert data["referral"]["required"] is True
    assert data["referral"]["emergencyNumber"] == "112"
