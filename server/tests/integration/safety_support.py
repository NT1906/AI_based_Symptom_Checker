"""Shared fixtures and helpers for the safety and prediction API tests.

Responsibilities:
    - Drive one assessment end to end through the public HTTP API:
      create -> chat -> confirm an exact symptom list -> analyze -> result.
    - Keep every response body of that run, so tests can scan the whole flow
      (for example for raw percentages).
    - Edit the extracted list the way the confirmation card does (one PATCH
      with only the kept and added symptoms), so removals are tested (#351).

Used by ``test_safety_api.py`` and ``test_prediction_result_api.py``; the
isolated app and client fixtures live in ``conftest.py``.

Owner: Nisarg · Task: S2-NIS-23 · Issue: #330
Card-style edit helper (``run_card_edit``): Nisarg · S2-NIS-29 (#351)
Requirements: DR-01, DR-02, FR-05, FR-06, FR-08, FR-22, FR-23
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from collections.abc import Sequence
from typing import Any
from uuid import UUID

import jwt
from httpx import AsyncClient, Response

from app.core.config import Settings

BASE_URL = "/api/v1/assessments"
CONSENT_ID = UUID("00000000-0000-4000-8000-000000005a01")
USER_ID = UUID("00000000-0000-4000-8000-000000005a02")
USER_EMAIL = "safety_tester@example.com"

#: Opening chat message. The mock AI extracts a symptom from it, which moves
#: the assessment to CONFIRMING; the test then replaces the list exactly.
OPENING_MESSAGE = "I have had a mild headache since yesterday"

#: A symptom as the user confirms it on the confirmation card: (name, severity).
SymptomInput = tuple[str, str]


@dataclass
class FlowRun:
    """Everything one end-to-end assessment run returned.

    Attributes:
        assessment_id: The assessment created for this run.
        analyze_status: HTTP status of ``POST /analyze``.
        result_status: HTTP status of ``GET /result``.
        result: JSON body of ``GET /result`` (an error body when it failed).
        bodies: Raw text of every response in the run, in call order.
        extracted: Symptom names the AI extracted (``run_card_edit`` only).
        confirmed: Symptom names stored after the edit (``run_card_edit`` only).
    """

    assessment_id: str
    analyze_status: int
    result_status: int
    result: dict[str, Any]
    bodies: list[str] = field(default_factory=list)
    extracted: list[str] = field(default_factory=list)
    confirmed: list[str] = field(default_factory=list)


def auth_header(settings: Settings) -> dict[str, str]:
    """Bearer header for the preloaded test user."""
    payload = {
        "sub": str(USER_ID),
        "email": USER_EMAIL,
        "role": "USER",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def _reset_rate_limits(client: AsyncClient) -> None:
    """Start each run with a fresh rate-limit budget.

    A run makes six requests; tests that run several assessments would
    otherwise reach the per-minute limit, which is not what they test.
    """
    transport = client._transport
    app = getattr(transport, "app", None)
    limiter = getattr(getattr(app, "state", None), "limiter", None)
    if limiter is not None:
        limiter.reset()


async def run_assessment(
    client: AsyncClient,
    symptoms: Sequence[SymptomInput],
    headers: dict[str, str] | None = None,
) -> FlowRun:
    """Run one assessment through the API with an exact confirmed symptom list.

    Steps: create, send ``OPENING_MESSAGE``, clear the extracted list, confirm
    ``symptoms`` (as the confirmation card does), analyze, fetch the result.

    Args:
        client: HTTP client bound to the isolated app.
        symptoms: The confirmed symptoms, as (name, severity) pairs.
        headers: Optional extra headers, e.g. a signed-in user's token.

    Returns:
        The run's statuses, result body and every response body.
    """
    _reset_rate_limits(client)
    headers = headers or {}
    bodies: list[str] = []

    def keep(response: Response) -> Response:
        bodies.append(response.text)
        return response

    created = keep(
        await client.post(
            BASE_URL, json={"consentId": str(CONSENT_ID)}, headers=headers
        )
    )
    assert created.status_code == 201, created.text
    aid = created.json()["id"]

    message = keep(
        await client.post(
            f"{BASE_URL}/{aid}/messages",
            json={"content": OPENING_MESSAGE},
            headers=headers,
        )
    )
    assert message.status_code == 200, message.text

    cleared = keep(
        await client.patch(
            f"{BASE_URL}/{aid}/symptoms", json={"symptoms": []}, headers=headers
        )
    )
    assert cleared.status_code == 200, cleared.text

    confirmed = keep(
        await client.patch(
            f"{BASE_URL}/{aid}/symptoms",
            json={
                "symptoms": [
                    {"name": name, "severity": severity} for name, severity in symptoms
                ]
            },
            headers=headers,
        )
    )
    assert confirmed.status_code == 200, confirmed.text

    analyzed = keep(await client.post(f"{BASE_URL}/{aid}/analyze", headers=headers))
    result = keep(await client.get(f"{BASE_URL}/{aid}/result", headers=headers))
    return FlowRun(
        assessment_id=aid,
        analyze_status=analyzed.status_code,
        result_status=result.status_code,
        result=result.json(),
        bodies=bodies,
    )


async def completed_result(
    client: AsyncClient,
    symptoms: Sequence[SymptomInput],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run an assessment and return its result, asserting it completed."""
    run = await run_assessment(client, symptoms, headers)
    assert run.analyze_status == 200, run.result
    assert run.result_status == 200, run.result
    return run.result


async def run_card_edit(
    client: AsyncClient,
    message: str,
    keep: Sequence[str],
    add: Sequence[SymptomInput] = (),
) -> FlowRun:
    """Chat once, then edit the extracted list as the confirmation card does.

    The card sends one PATCH holding only the symptoms the user kept (by ID)
    and any they added; everything else was removed by the user.

    Args:
        client: HTTP client bound to the isolated app.
        message: The user's chat message.
        keep: Names of extracted symptoms to keep (substring match).
        add: New symptoms to add, as (name, severity) pairs.

    Returns:
        The run, with the extracted and the stored (confirmed) symptom names.
    """
    _reset_rate_limits(client)
    bodies: list[str] = []

    def keep_body(response: Response) -> Response:
        bodies.append(response.text)
        return response

    created = keep_body(
        await client.post(BASE_URL, json={"consentId": str(CONSENT_ID)})
    )
    aid = created.json()["id"]
    reply = keep_body(
        await client.post(f"{BASE_URL}/{aid}/messages", json={"content": message})
    )
    assert reply.status_code == 200, reply.text
    extracted = keep_body(await client.get(f"{BASE_URL}/{aid}/symptoms")).json()

    edits: list[dict[str, Any]] = [
        {"id": s["id"], "name": s["name"], "severity": s["severity"]}
        for s in extracted
        if any(k in s["name"] for k in keep)
    ]
    edits += [{"name": name, "severity": severity} for name, severity in add]
    edited = keep_body(
        await client.patch(f"{BASE_URL}/{aid}/symptoms", json={"symptoms": edits})
    )
    assert edited.status_code == 200, edited.text

    analyzed = keep_body(await client.post(f"{BASE_URL}/{aid}/analyze"))
    result = keep_body(await client.get(f"{BASE_URL}/{aid}/result"))
    return FlowRun(
        assessment_id=aid,
        analyze_status=analyzed.status_code,
        result_status=result.status_code,
        result=result.json(),
        bodies=bodies,
        extracted=[s["name"] for s in extracted],
        confirmed=[s["name"] for s in edited.json()],
    )
