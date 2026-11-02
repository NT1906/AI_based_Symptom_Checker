"""Unit tests for the OpenAPI schema export script.

Responsibilities:
    - Verify deterministic formatting and schema extraction.
    - Test CLI arguments and file writing functionality.
    - Validate presence of all registered assessment operations in the spec.

Owner: Vivek (tests) · Task: S1-VIV-1 · Requirements: —
"""

import json
from pathlib import Path

import pytest
from fastapi import FastAPI

from scripts.export_openapi import export_openapi, main


def test_export_openapi_returns_deterministic_valid_json(app: FastAPI) -> None:
    """Verify that export_openapi returns identical, deterministic JSON across runs."""
    run_one = export_openapi(app)
    run_two = export_openapi(app)

    # Determinism test
    assert run_one == run_two
    assert run_one.endswith("\n")

    # Valid JSON test
    parsed = json.loads(run_one)
    assert "openapi" in parsed
    assert "paths" in parsed
    assert "/api/v1/health" in parsed["paths"]
    assert "/api/v1/assessments" in parsed["paths"]


def test_export_openapi_matches_app_openapi_dict(app: FastAPI) -> None:
    """Verify exported JSON data matches app.openapi() dictionary exactly."""
    exported_str = export_openapi(app)
    exported_dict = json.loads(exported_str)

    direct_dict = app.openapi()
    assert exported_dict == direct_dict


def test_export_openapi_cli_writes_to_file(tmp_path: Path) -> None:
    """Verify CLI --output argument writes valid OpenAPI JSON to specified file."""
    output_file = tmp_path / "subfolder" / "openapi.json"
    exit_code = main(["--output", str(output_file)])

    assert exit_code == 0
    assert output_file.exists()

    content = output_file.read_text(encoding="utf-8")
    parsed = json.loads(content)
    assert parsed["info"]["title"] == "AI-Based Symptom Checker API"


def test_export_openapi_cli_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify CLI without --output writes JSON specification to stdout."""
    exit_code = main([])
    assert exit_code == 0

    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert "paths" in parsed


def test_openapi_contains_all_assessment_operations(app: FastAPI) -> None:
    """Verify OpenAPI spec includes all assessment operations with descriptions."""
    spec = app.openapi()
    paths = spec["paths"]

    expected_routes = [
        ("/api/v1/assessments", "post"),
        ("/api/v1/assessments/{id}", "get"),
        ("/api/v1/assessments/{id}/state", "get"),
        ("/api/v1/assessments/{id}/messages", "post"),
        ("/api/v1/assessments/{id}/messages", "get"),
        ("/api/v1/assessments/{id}/symptoms", "get"),
        ("/api/v1/assessments/{id}/symptoms", "patch"),
        ("/api/v1/assessments/{id}/analyze", "post"),
        ("/api/v1/assessments/{id}/result", "get"),
    ]

    for path, method in expected_routes:
        assert path in paths, f"Path {path} missing from OpenAPI schema"
        assert method in paths[path], f"Method {method.upper()} {path} missing"
        operation = paths[path][method]
        assert "summary" in operation and operation["summary"]
        assert (
            "responses" in operation
            and "200" in operation["responses"]
            or "201" in operation["responses"]
        )
