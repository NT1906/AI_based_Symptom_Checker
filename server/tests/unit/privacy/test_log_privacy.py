"""Prevent personal values in authentication and error logging.

Owner: Harsh Â· Task: S2-HAR-7 Â· Issue: #210 Â· Requirements: NFR-10
"""

import ast
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_session_factory
from app.core.errors import ValidationError
from app.main import create_app
from app.models import Base


def test_auth_and_errors_omit_personal_values(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Capture the configured sink while real auth and error handlers execute."""
    engine = create_engine(f"sqlite:///{tmp_path / 'private-logs.db'}")
    sessions = sessionmaker(engine)
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sessions

    @app.get("/fixtures/{value}")
    def fail(value: str) -> None:
        raise ValidationError("fictional-private-error")

    credentials = {
        "email": "fictional-log-secret@example.com",
        "password": "FictionalPrivatePass123!",
    }
    original_handlers = logging.getLogger().handlers[:]
    try:
        Base.metadata.create_all(engine)
        with TestClient(app) as client:
            registration = client.post("/api/v1/auth/register", json=credentials)
            assert registration.status_code == 201
            client.post("/api/v1/auth/register", json=credentials)
            assert (
                client.post("/api/v1/auth/login", json=credentials).status_code == 200
            )
            client.post(
                "/api/v1/auth/login",
                json={**credentials, "password": "IncorrectPrivatePass123!"},
            )
            # httpx logs full URLs independently, so suppress that test-client
            # transport while checking the application sink for raw paths.
            transport_logger = logging.getLogger("httpx")
            previous_disabled = transport_logger.disabled
            transport_logger.disabled = True
            try:
                assert client.get("/fixtures/fictional-private-path").status_code == 422
            finally:
                transport_logger.disabled = previous_disabled
        output = capsys.readouterr().out
        for marker in (
            *credentials.values(),
            registration.json()["id"],
            "fictional-private-path",
            "fictional-private-error",
        ):
            assert marker not in output
        assert "auth_login_successful" in output
        assert "request_validation_failed" not in output
        assert "app_error_occurred" in output
        assert "/fixtures/{value}" in output
    finally:
        logging.getLogger().handlers[:] = original_handlers
        engine.dispose()


def test_log_calls_exclude_direct_identifiers_and_symptom_values() -> None:
    """Catch regressions that reintroduce removed personal logging fields."""
    root = Path(__file__).resolve().parents[3] / "app"
    prohibited = {
        "email",
        "user_id",
        "symptom_name",
        "age_band",
        "chronic_conditions_count",
        "expected_user_id",
        "provided_user_id",
        "jti",
    }
    for filename in (
        "api/v1/auth.py",
        "services/auth/service.py",
        "services/assessment/orchestrator.py",
        "services/assessment/state_machine.py",
        "services/ai/openai_provider.py",
    ):
        for node in ast.walk(ast.parse((root / filename).read_text())):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "logger"
            ):
                continue
            assert prohibited.isdisjoint(keyword.arg for keyword in node.keywords)
            assert all(
                ast.unparse(keyword.value) != "str(exc)" for keyword in node.keywords
            )
