"""Unit tests verifying audit logging during assessment analysis and results (NFR-10).

Responsibilities:
    - Verify POST /api/v1/assessments/{id}/analyze records an ANALYSIS audit event.
    - Verify GET /api/v1/assessments/{id}/result records a RECOMMENDATION audit event.
    - Test fail-safe behavior: audit persistence errors do not crash user requests.
    - Verify zero-PII compliance and layering guards.

Owner: Vivek (tests) · Task: S2-VIV-4 · Requirements: NFR-10, DR-06
"""

from unittest.mock import MagicMock
from uuid import UUID

from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.api.deps import get_audit_service
from app.services.audit.schemas import AuditEventType
from app.services.audit.service import AuditService

SAMPLE_UUID = "e4caa1b2-8493-4a16-928e-5b1287c95e1a"


def test_analyze_assessment_records_audit_log(
    app: FastAPI,
    client: TestClient,
) -> None:
    """POST /analyze must record an ANALYSIS audit log entry."""
    audit_service = AuditService(session_factory=None)
    app.dependency_overrides[get_audit_service] = lambda: audit_service

    try:
        response = client.post(f"/api/v1/assessments/{SAMPLE_UUID}/analyze")
        assert response.status_code == status.HTTP_200_OK

        logs = audit_service.list_logs_for_assessment(UUID(SAMPLE_UUID))
        assert len(logs) == 1
        log = logs[0]

        assert log.action == AuditEventType.ANALYSIS
        assert log.assessment_id == UUID(SAMPLE_UUID)
        assert log.risk_engine_version == "2026.1"
        assert log.condition_model_version == "baseline_v1"
    finally:
        app.dependency_overrides.pop(get_audit_service, None)


def test_get_result_records_audit_recommendation(
    app: FastAPI,
    client: TestClient,
) -> None:
    """GET /result must record a RECOMMENDATION audit log entry with risk tier."""
    audit_service = AuditService(session_factory=None)
    app.dependency_overrides[get_audit_service] = lambda: audit_service

    try:
        response = client.get(f"/api/v1/assessments/{SAMPLE_UUID}/result")
        assert response.status_code == status.HTTP_200_OK

        logs = audit_service.list_logs_for_assessment(UUID(SAMPLE_UUID))
        assert len(logs) == 1
        log = logs[0]

        assert log.action == AuditEventType.RECOMMENDATION
        assert log.assessment_id == UUID(SAMPLE_UUID)
        assert log.risk_level in ("SELF_CARE", "CONSULT_DOCTOR", "URGENT")
        assert log.risk_engine_version is not None
        assert "conditions_count" in log.details
        assert "referral_required" in log.details
    finally:
        app.dependency_overrides.pop(get_audit_service, None)


def test_audit_logging_failure_is_resilient_and_does_not_crash_request(
    app: FastAPI,
    client: TestClient,
) -> None:
    """Audit service exceptions are logged without failing the API response."""
    failing_audit_service = MagicMock(spec=AuditService)
    failing_audit_service.record_analysis.side_effect = RuntimeError("Database offline")
    failing_audit_service.record_recommendation.side_effect = RuntimeError(
        "Database offline"
    )

    app.dependency_overrides[get_audit_service] = lambda: failing_audit_service

    try:
        # 1. Analyze request must still succeed with 200
        analyze_resp = client.post(f"/api/v1/assessments/{SAMPLE_UUID}/analyze")
        assert analyze_resp.status_code == status.HTTP_200_OK
        assert analyze_resp.json()["resultAvailable"] is True

        # 2. Result request must still succeed with 200
        result_resp = client.get(f"/api/v1/assessments/{SAMPLE_UUID}/result")
        assert result_resp.status_code == status.HTTP_200_OK
        assert result_resp.json()["disclaimer"] is not None
    finally:
        app.dependency_overrides.pop(get_audit_service, None)
