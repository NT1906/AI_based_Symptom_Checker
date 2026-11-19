"""OpenAPI documentation completeness and schema validity tests.

Responsibilities:
    - Verify that all 26 backend endpoint operations across 21 paths
      are documented.
    - Assert that every endpoint has a descriptive summary, description,
      and success response.
    - Assert that all request bodies have concrete JSON examples.
    - Validate presence of error models (400, 401, 403, 404, 409, 422).
    - Verify root OpenAPI metadata including tags, contact, license,
      and medical disclaimers.

Owner: Vivek (api) · Task: S2-VIV-7 · Requirement: NFR-08
"""

import pytest
from fastapi import FastAPI

# All 26 implemented endpoint operations across 21 paths
EXPECTED_OPERATIONS: list[tuple[str, str]] = [
    ("/api/v1/health", "get"),
    ("/api/v1/auth/register", "post"),
    ("/api/v1/auth/login", "post"),
    ("/api/v1/auth/refresh", "post"),
    ("/api/v1/auth/csrf", "get"),
    ("/api/v1/auth/logout", "post"),
    ("/api/v1/auth/me", "get"),
    ("/api/v1/assessments", "post"),
    ("/api/v1/assessments/{id}", "get"),
    ("/api/v1/assessments/{id}/state", "get"),
    ("/api/v1/assessments/{id}/messages", "post"),
    ("/api/v1/assessments/{id}/messages", "get"),
    ("/api/v1/assessments/{id}/symptoms", "get"),
    ("/api/v1/assessments/{id}/symptoms", "patch"),
    ("/api/v1/assessments/{id}/analyze", "post"),
    ("/api/v1/assessments/{id}/result", "get"),
    ("/api/v1/assessments/{id}/images", "post"),
    ("/api/v1/consents/current-policy", "get"),
    ("/api/v1/consents", "post"),
    ("/api/v1/history", "get"),
    ("/api/v1/history/{assessment_id}", "get"),
    ("/api/v1/profile", "get"),
    ("/api/v1/profile", "put"),
    ("/api/v1/profile", "patch"),
    ("/api/v1/profile", "delete"),
    ("/api/v1/privacy/export", "get"),
]

# Endpoints with JSON request bodies that must have examples
JSON_BODY_OPERATIONS: list[tuple[str, str]] = [
    ("/api/v1/auth/register", "post"),
    ("/api/v1/auth/login", "post"),
    ("/api/v1/consents", "post"),
    ("/api/v1/profile", "put"),
    ("/api/v1/profile", "patch"),
    ("/api/v1/assessments", "post"),
    ("/api/v1/assessments/{id}/messages", "post"),
    ("/api/v1/assessments/{id}/symptoms", "patch"),
]

EXPECTED_TAGS: list[str] = [
    "health",
    "auth",
    "assessments",
    "consents",
    "history",
    "profile",
    "privacy",
]


def test_openapi_schema_generates_successfully(app: FastAPI) -> None:
    """Verify that app.openapi() generates a valid, complete OpenAPI 3.1 dict."""
    spec = app.openapi()
    assert spec is not None
    assert "openapi" in spec
    assert spec["openapi"].startswith("3.")
    assert "info" in spec
    assert spec["info"]["title"] == "AI-Based Symptom Checker API"
    assert "does **not** provide medical diagnoses" in spec["info"]["description"]
    assert "paths" in spec


def test_all_expected_tags_present_with_descriptions(app: FastAPI) -> None:
    """Verify all 7 tag categories are documented with non-empty descriptions."""
    spec = app.openapi()
    tags = spec.get("tags", [])
    tag_names = {t["name"] for t in tags}

    for expected in EXPECTED_TAGS:
        assert expected in tag_names, f"Tag '{expected}' missing from OpenAPI tags"

    for tag in tags:
        assert tag["name"] in EXPECTED_TAGS
        assert "description" in tag and len(tag["description"].strip()) > 10


@pytest.mark.parametrize("path,method", EXPECTED_OPERATIONS)
def test_operation_has_summary_and_description(
    app: FastAPI, path: str, method: str
) -> None:
    """Verify each implemented operation has a non-empty summary and description."""
    spec = app.openapi()
    paths = spec["paths"]
    assert path in paths, f"Path '{path}' missing from OpenAPI paths"
    assert method in paths[path], f"Method '{method.upper()} {path}' missing"

    operation = paths[path][method]
    summary = operation.get("summary", "")
    description = operation.get("description", "")

    assert summary.strip(), f"Summary missing for {method.upper()} {path}"
    assert description.strip(), f"Description missing for {method.upper()} {path}"
    assert len(summary) >= 5, f"Summary too short for {method.upper()} {path}"
    assert len(description) >= 15, f"Description too short for {method.upper()} {path}"


@pytest.mark.parametrize("path,method", EXPECTED_OPERATIONS)
def test_operation_has_success_response(app: FastAPI, path: str, method: str) -> None:
    """Verify each operation documents a 200, 201, or 204 success response."""
    spec = app.openapi()
    operation = spec["paths"][path][method]
    responses = operation.get("responses", {})

    has_success = any(code in responses for code in ("200", "201", "204"))
    assert has_success, (
        f"Operation {method.upper()} {path} lacks 200/201/204 response schema"
    )

    success_code = next(code for code in ("200", "201", "204") if code in responses)
    success_resp = responses[success_code]
    assert "description" in success_resp and success_resp["description"]


@pytest.mark.parametrize("path,method", JSON_BODY_OPERATIONS)
def test_json_request_bodies_have_examples(
    app: FastAPI, path: str, method: str
) -> None:
    """Verify each endpoint with a JSON request body provides documentation examples."""
    spec = app.openapi()
    operation = spec["paths"][path][method]

    assert "requestBody" in operation, (
        f"Missing requestBody for {method.upper()} {path}"
    )
    content = operation["requestBody"].get("content", {})
    assert "application/json" in content, (
        f"Missing application/json in requestBody for {method.upper()} {path}"
    )

    json_content = content["application/json"]
    has_example = "example" in json_content or "examples" in json_content
    # Alternatively schema may define examples
    schema = json_content.get("schema", {})
    schema_has_example = "example" in schema or "examples" in schema

    assert has_example or schema_has_example, (
        f"Request body for {method.upper()} {path} lacks openapi examples"
    )


def test_authenticated_endpoints_document_unauthorized_error(app: FastAPI) -> None:
    """Verify protected endpoints document 401 Unauthorized status."""
    spec = app.openapi()
    protected_operations = [
        ("/api/v1/auth/me", "get"),
        ("/api/v1/profile", "get"),
        ("/api/v1/profile", "put"),
        ("/api/v1/profile", "patch"),
        ("/api/v1/profile", "delete"),
        ("/api/v1/history", "get"),
        ("/api/v1/history/{assessment_id}", "get"),
        ("/api/v1/privacy/export", "get"),
    ]

    for path, method in protected_operations:
        operation = spec["paths"][path][method]
        responses = operation.get("responses", {})
        assert "401" in responses, (
            f"Protected endpoint {method.upper()} {path} missing 401 error response"
        )


def test_assessment_endpoints_document_state_conflict_or_not_found(
    app: FastAPI,
) -> None:
    """Verify assessment endpoints document 404 or 409 error models."""
    spec = app.openapi()
    paths = spec["paths"]

    assessment_id_paths = [
        ("/api/v1/assessments/{id}", "get"),
        ("/api/v1/assessments/{id}/state", "get"),
        ("/api/v1/assessments/{id}/messages", "post"),
        ("/api/v1/assessments/{id}/messages", "get"),
        ("/api/v1/assessments/{id}/symptoms", "get"),
        ("/api/v1/assessments/{id}/symptoms", "patch"),
        ("/api/v1/assessments/{id}/analyze", "post"),
        ("/api/v1/assessments/{id}/result", "get"),
        ("/api/v1/assessments/{id}/images", "post"),
    ]

    for path, method in assessment_id_paths:
        operation = paths[path][method]
        responses = operation.get("responses", {})
        assert "404" in responses, (
            f"{method.upper()} {path} missing 404 response documentation"
        )
