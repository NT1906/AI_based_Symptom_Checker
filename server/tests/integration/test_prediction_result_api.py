"""S2-NIS-23: condition prediction and result content API tests.

Responsibilities:
    - Equivalence partitions: every confidence label is LIKELY, POSSIBLE or
      LESS_LIKELY and nothing else (FR-22).
    - Ranking: conditions come back ranked 1, 2, 3 (at most three), each with
      a "why" line and a recommended specialty (FR-05, FR-23).
    - Boundary values: 1 symptom, many symptoms, and symptoms the model does
      not know all end safely (General physician, no crash).
    - Repeatability: the same confirmed symptoms give the same result.
    - Doctor referral: a specialty the client turns into a map search query,
      and no doctor or personal data in the result (FR-08, idea §9).
    - Guidance by tier: self-care steps for SELF_CARE, "get care now" for
      URGENT (FR-06).

Each test is one test case (TC-SAF-A-xx) in docs/testing/safety/test-cases.md.
Only the mock AI provider is used; no real Groq/OpenAI key is ever read.

Owner: Nisarg · Task: S2-NIS-23 · Issue: #330
Requirements: FR-05, FR-06, FR-08, FR-22, FR-23, DR-01, DR-02
"""

from typing import Any

import pytest
from httpx import AsyncClient

from app.core.config import Settings
from tests.integration.safety_support import (
    BASE_URL,
    CONSENT_ID,
    USER_EMAIL,
    USER_ID,
    auth_header,
    completed_result,
    run_assessment,
)

LABELS = {"LIKELY", "POSSIBLE", "LESS_LIKELY"}
GENERAL_PHYSICIAN = "General physician"

#: Symptom sets covering the three risk tiers and several body systems.
SAMPLE_INPUTS: dict[str, list[tuple[str, str]]] = {
    "cold": [("runny nose", "MILD"), ("sneezing", "MILD"), ("sore throat", "MILD")],
    "dengue": [
        ("fever", "MODERATE"),
        ("pain behind the eyes", "MODERATE"),
        ("joint pain", "MODERATE"),
    ],
    "headache": [("headache", "MILD")],
    "cardiac": [("chest pain", "MODERATE"), ("shortness of breath", "MODERATE")],
    "skin": [("itchy skin", "MILD")],
}

#: Twelve everyday symptoms: the upper boundary used for "many symptoms".
MANY_SYMPTOMS = [
    (name, "MILD")
    for name in (
        "fever",
        "cough",
        "headache",
        "fatigue",
        "sore throat",
        "runny nose",
        "body ache",
        "sneezing",
        "nausea",
        "diarrhea",
        "rash",
        "itchy skin",
    )
]

#: Allowed keys of a result: anything else could carry stored personal data.
RESULT_KEYS = {
    "assessmentId",
    "riskLevel",
    "conditions",
    "guidance",
    "referral",
    "limitations",
    "modelVersion",
    "disclaimer",
    "createdAt",
}
REFERRAL_KEYS = {"required", "specialty", "reason", "emergencyNumber"}


def map_query(result: dict[str, Any]) -> str:
    """The map search the client builds from the referral (DoctorReferral.tsx)."""
    return f"{result['referral']['specialty']} near me"


# ===========================================================================
# Equivalence partitions and ranking (FR-05, FR-22, FR-23)
# ===========================================================================


@pytest.mark.anyio
async def test_tc_saf_a_12_confidence_labels_are_only_three_partitions(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-12: every confidence label is LIKELY / POSSIBLE / LESS_LIKELY.

    Valid partition: the three labels. Invalid partition: anything else,
    such as a number or another word. All three labels must occur across
    the sample inputs, so each valid partition is exercised.
    """
    seen: set[str] = set()
    for symptoms in SAMPLE_INPUTS.values():
        result = await completed_result(safety_client, symptoms)
        for condition in result["conditions"]:
            assert isinstance(condition["confidence"], str)
            assert condition["confidence"] in LABELS
            seen.add(condition["confidence"])
    assert seen == LABELS


@pytest.mark.anyio
async def test_tc_saf_a_13_conditions_are_ranked_with_why_and_specialty(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-13: ranks 1..n (n <= 3), each with a "why" and a specialty."""
    for symptoms in SAMPLE_INPUTS.values():
        result = await completed_result(safety_client, symptoms)
        conditions = result["conditions"]
        assert 1 <= len(conditions) <= 3
        assert [c["rank"] for c in conditions] == list(range(1, len(conditions) + 1))
        for condition in conditions:
            assert condition["why"].startswith("Because you reported ")
            assert condition["specialty"]


# ===========================================================================
# Boundary values: number and kind of symptoms
# ===========================================================================


@pytest.mark.anyio
async def test_tc_saf_a_14_single_symptom_lower_boundary(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-14: exactly one confirmed symptom gives a complete result."""
    result = await completed_result(safety_client, [("headache", "MILD")])
    assert result["conditions"][0]["rank"] == 1
    assert result["conditions"][0]["why"] == "Because you reported headache."
    assert result["riskLevel"] in {"SELF_CARE", "CONSULT_DOCTOR", "URGENT"}


@pytest.mark.anyio
async def test_tc_saf_a_15_many_symptoms_upper_boundary(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-15: twelve symptoms: still at most 3 ranked conditions.

    The "why" line stays short ("... and N other symptoms").
    """
    result = await completed_result(safety_client, MANY_SYMPTOMS)
    assert 1 <= len(result["conditions"]) <= 3
    assert any("other symptoms" in c["why"] for c in result["conditions"])


@pytest.mark.anyio
async def test_tc_saf_a_16_unknown_symptoms_mixed_with_known_fall_back_safely(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-16: unknown symptoms next to a known one are ignored safely.

    The two made-up symptoms are skipped; the known one ("fatigue") drives a
    CONSULT_DOCTOR result with a General physician referral.
    """
    result = await completed_result(
        safety_client,
        [
            ("glorbitis of the zibble", "MILD"),
            ("tingling in my left little toe", "MILD"),
            ("fatigue", "MILD"),
        ],
    )
    assert result["riskLevel"] == "CONSULT_DOCTOR"
    assert result["referral"]["specialty"] == GENERAL_PHYSICIAN
    for condition in result["conditions"]:
        assert "glorbitis" not in condition["why"]


@pytest.mark.anyio
@pytest.mark.xfail(
    strict=True,
    reason="Defect #348: only unknown symptoms -> 422 and stuck in ANALYZING",
)
async def test_tc_saf_a_17_only_unknown_symptoms_fall_back_to_general_physician(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-17: only symptoms the model does not know -> safe fallback.

    Expected: the result completes as CONSULT_DOCTOR with a General physician
    referral (not knowing is never "probably nothing", idea §7).
    Actual: POST /analyze returns 422 "At least one confirmed symptom is
    required." and the assessment stays in ANALYZING, so it can be neither
    edited nor analysed again. Marked xfail (strict) until #348 is fixed.
    """
    run = await run_assessment(safety_client, [("glorbitis of the zibble", "MILD")])
    assert run.analyze_status == 200, run.result
    assert run.result["riskLevel"] == "CONSULT_DOCTOR"
    assert run.result["referral"]["specialty"] == GENERAL_PHYSICIAN


# ===========================================================================
# Repeatability (deterministic condition model)
# ===========================================================================


@pytest.mark.anyio
async def test_tc_saf_a_18_same_symptoms_give_the_same_result(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-18: three runs of the same symptoms give identical results.

    Compared: risk tier, every condition (name, rank, label, why, specialty),
    guidance and referral. Only the IDs and timestamps differ.
    """
    for symptoms in (
        SAMPLE_INPUTS["cold"],
        SAMPLE_INPUTS["dengue"],
        SAMPLE_INPUTS["cardiac"],
    ):
        outcomes = []
        for _ in range(3):
            result = await completed_result(safety_client, symptoms)
            outcomes.append(
                (
                    result["riskLevel"],
                    result["conditions"],
                    result["guidance"],
                    result["referral"],
                    result["limitations"],
                )
            )
        assert outcomes[0] == outcomes[1] == outcomes[2]


# ===========================================================================
# Doctor referral and guidance content (FR-06, FR-08)
# ===========================================================================


@pytest.mark.anyio
async def test_tc_saf_a_19_referral_has_specialty_and_no_personal_data(
    safety_client: AsyncClient,
    test_settings: Settings,
) -> None:
    """TC-SAF-A-19: referral gives a specialty for the map search; no PII.

    Run as a signed-in user. The referral names a specialty (the client
    searches "<specialty> near me"); the result has only the published keys
    and contains no email, user ID, consent ID or doctor details.
    """
    headers = auth_header(test_settings)
    run = await run_assessment(safety_client, SAMPLE_INPUTS["dengue"], headers)
    assert run.result_status == 200, run.result
    result = run.result

    assert result["referral"]["required"] is True
    assert result["referral"]["specialty"] == GENERAL_PHYSICIAN
    assert map_query(result) == "General physician near me"

    assert set(result) == RESULT_KEYS
    assert set(result["referral"]) == REFERRAL_KEYS
    body = run.bodies[-1].lower()
    for private in (USER_EMAIL, str(USER_ID), str(CONSENT_ID)):
        assert private.lower() not in body
    for doctor_word in ("dr.", "doctor name", "phone", "address", "clinic"):
        assert doctor_word not in body

    # The referral is not tied to the account: the history copy has no PII.
    stored = await safety_client.get(
        f"{BASE_URL}/{run.assessment_id}/result", headers=headers
    )
    assert USER_EMAIL not in stored.text


@pytest.mark.anyio
async def test_tc_saf_a_20_guidance_matches_the_risk_tier(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-20: self-care steps when non-urgent; "get care now" when urgent."""
    self_care = await completed_result(safety_client, SAMPLE_INPUTS["cold"])
    assert self_care["riskLevel"] == "SELF_CARE"
    assert any("at home with rest" in step for step in self_care["guidance"])
    assert not any(step.startswith("Call 112 now") for step in self_care["guidance"])

    consult = await completed_result(safety_client, SAMPLE_INPUTS["dengue"])
    assert consult["riskLevel"] == "CONSULT_DOCTOR"
    assert consult["guidance"][0].startswith("Book a visit with")
    assert not any("at home with rest" in step for step in consult["guidance"])

    urgent = await completed_result(safety_client, SAMPLE_INPUTS["cardiac"])
    assert urgent["riskLevel"] == "URGENT"
    assert urgent["guidance"][0].startswith("Call 112 now")
    assert not any("at home with rest" in step for step in urgent["guidance"])
