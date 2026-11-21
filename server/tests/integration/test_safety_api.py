"""S2-NIS-23: safety API tests (decision table on the risk engine, run via HTTP).

Responsibilities:
    - Red-flag scenarios (cardiac, stroke, serious bleeding, meningitis,
      self-harm) always give URGENT, 112 and the emergency department (DR-02).
    - Severity boundary on a red-flag symptom: mild chest pain is not urgent,
      severe or unstated-severity chest pain is.
    - Mild symptoms give SELF_CARE with no emergency referral.
    - Low confidence can raise the risk tier but never lowers it.
    - Every completed result carries the medical disclaimer (DR-01).
    - No response anywhere in the flow contains a raw percentage or
      probability (AI_RULES.md §2.3, FR-22).
    - A symptom removed on the confirmation card no longer counts, even a
      red flag; removing everything is still refused (#351, FR-16).

Each test is one test case (TC-SAF-A-xx) in docs/testing/safety/test-cases.md.
Only the mock AI provider is used; no real Groq/OpenAI key is ever read.

Owner: Nisarg · Task: S2-NIS-23 · Issue: #330
Requirements: DR-01, DR-02, FR-05, FR-06, FR-22
Regression tests TC-SAF-A-21/22 for #351: Nisarg · S2-NIS-29
"""

import json
import re
from typing import Any

import pytest
from httpx import AsyncClient

from app.schemas.result import DEFAULT_DISCLAIMER
from tests.integration.safety_support import (
    BASE_URL,
    completed_result,
    run_assessment,
    run_card_edit,
)

URGENT_GUIDANCE = "Call 112 now, or go to the nearest emergency department."
HOME_CARE_GUIDANCE = (
    "Your symptoms may be manageable at home with rest and plenty of fluids."
)
UNCERTAINTY_LIMITATION = (
    "Because the match was uncertain, this result was raised to the safer level."
)
ASSUMED_SEVERITY_STEP = (
    "You did not say how severe a symptom is, so to be safe this is treated as urgent."
)
TELE_MANAS_HELPLINE = "14416"

TIER_ORDER = {"SELF_CARE": 0, "CONSULT_DOCTOR": 1, "URGENT": 2}

#: A percentage ("80%", "12.5 %"), or a word that exposes a number as a chance.
PERCENT_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*%")
PROBABILITY_WORDS = re.compile(r"probabilit|percent|\bscore\b", re.IGNORECASE)


def assert_urgent(result: dict[str, Any]) -> None:
    """The red-flag override: URGENT, 112 first, emergency department."""
    assert result["riskLevel"] == "URGENT"
    assert result["referral"]["required"] is True
    assert result["referral"]["emergencyNumber"] == "112"
    assert result["referral"]["specialty"] == "Emergency department"
    assert result["referral"]["reason"].startswith("Warning sign reported:")
    assert result["guidance"][0] == URGENT_GUIDANCE


# ===========================================================================
# Decision table: red-flag conditions -> URGENT (DR-02)
# ===========================================================================


@pytest.mark.anyio
async def test_tc_saf_a_01_chest_pain_with_breathlessness_is_urgent(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-01: chest pain + shortness of breath -> URGENT with 112.

    Decision table rule rf_cardiac_chest_pain. Even though every predicted
    condition is only "Possible", the red flag wins (DR-02).
    """
    result = await completed_result(
        safety_client,
        [("chest pain", "MODERATE"), ("shortness of breath", "MODERATE")],
    )
    assert_urgent(result)
    assert "chest pain" in result["referral"]["reason"].lower()
    assert all(c["confidence"] != "LIKELY" for c in result["conditions"])


@pytest.mark.anyio
async def test_tc_saf_a_02_stroke_sign_is_urgent(safety_client: AsyncClient) -> None:
    """TC-SAF-A-02: a single stroke sign (face drooping) -> URGENT with 112.

    Decision table rule rf_stroke_signs: one sign alone is enough.
    """
    result = await completed_result(safety_client, [("facial droop", "MODERATE")])
    assert_urgent(result)
    assert "face drooping" in result["referral"]["reason"].lower()


@pytest.mark.anyio
async def test_tc_saf_a_03_serious_bleeding_is_urgent_without_condition(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-03: vomiting blood -> URGENT even when no condition matches.

    Decision table rule rf_serious_bleeding. The condition list is empty,
    yet the result is still URGENT: red flags do not depend on predictions.
    """
    result = await completed_result(safety_client, [("vomiting blood", "MILD")])
    assert_urgent(result)
    assert result["conditions"] == []
    assert "vomiting blood" in result["referral"]["reason"].lower()


@pytest.mark.anyio
async def test_tc_saf_a_04_meningitis_signs_are_urgent(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-04: fever + stiff neck -> URGENT (rule rf_meningitis_signs).

    Each symptom alone is not a red flag; the combination is (all_of rule).
    """
    result = await completed_result(
        safety_client, [("fever", "MILD"), ("stiff neck", "MILD")]
    )
    assert_urgent(result)

    fever_only = await completed_result(safety_client, [("fever", "MILD")])
    assert fever_only["riskLevel"] != "URGENT"


@pytest.mark.anyio
async def test_tc_saf_a_05_self_harm_is_urgent_with_helpline(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-05: thoughts of self-harm -> URGENT, 112 and Tele-MANAS 14416."""
    result = await completed_result(
        safety_client, [("thoughts of self harm", "MODERATE")]
    )
    assert_urgent(result)
    assert any(TELE_MANAS_HELPLINE in step for step in result["guidance"])


# ===========================================================================
# Boundary values on a red-flag severity threshold
# ===========================================================================


@pytest.mark.anyio
async def test_tc_saf_a_06_chest_pain_severity_boundary(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-06: chest pain alone: MILD/MODERATE not urgent, SEVERE urgent.

    rf_cardiac_chest_pain fires on chest pain alone only at min_severity
    SEVERE. Values just below (MODERATE) and at (SEVERE) the threshold.
    """
    tiers = {}
    for severity in ("MILD", "MODERATE", "SEVERE"):
        result = await completed_result(safety_client, [("chest pain", severity)])
        tiers[severity] = result["riskLevel"]
        if severity != "SEVERE":
            assert result["referral"]["emergencyNumber"] is None
    assert tiers == {
        "MILD": "CONSULT_DOCTOR",
        "MODERATE": "CONSULT_DOCTOR",
        "SEVERE": "URGENT",
    }


@pytest.mark.anyio
async def test_tc_saf_a_07_unknown_severity_never_lowers_risk(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-07: chest pain with unstated severity is treated as SEVERE.

    Not knowing the severity must never lower the risk (AI_RULES.md §2.6):
    the severity minimum counts as met and the user is told why.
    """
    result = await completed_result(safety_client, [("chest pain", "UNKNOWN")])
    assert_urgent(result)
    assert ASSUMED_SEVERITY_STEP in result["guidance"]


# ===========================================================================
# Mild symptoms and the uncertainty rule
# ===========================================================================


@pytest.mark.anyio
async def test_tc_saf_a_08_mild_symptoms_are_not_urgent(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-08: common-cold symptoms -> SELF_CARE, no emergency referral."""
    result = await completed_result(
        safety_client,
        [("runny nose", "MILD"), ("sneezing", "MILD"), ("sore throat", "MILD")],
    )
    assert result["riskLevel"] == "SELF_CARE"
    assert result["referral"]["required"] is False
    assert result["referral"]["emergencyNumber"] is None
    assert URGENT_GUIDANCE not in result["guidance"]
    assert result["conditions"][0]["confidence"] == "LIKELY"


@pytest.mark.anyio
async def test_tc_saf_a_09_low_confidence_raises_self_care(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-09: low confidence raises SELF_CARE to CONSULT_DOCTOR.

    "Sneezing" alone matches only self-care conditions, none of them
    "Likely". Without the uncertainty rule it would be SELF_CARE; with it,
    the result is raised one tier and the limitation says so.
    """
    result = await completed_result(safety_client, [("sneezing", "MILD")])
    assert all(c["confidence"] != "LIKELY" for c in result["conditions"])
    assert result["riskLevel"] == "CONSULT_DOCTOR"
    assert result["referral"]["required"] is True
    assert UNCERTAINTY_LIMITATION in result["limitations"]


@pytest.mark.anyio
async def test_tc_saf_a_10_low_confidence_never_lowers_a_tier(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-10: low confidence never lowers URGENT or CONSULT_DOCTOR.

    Pairs with the same confidence situation (no "Likely" condition) but a
    higher starting tier: the tier is kept, never reduced.
    """
    cases = {
        # red flag, conditions only "Possible" -> stays URGENT
        "URGENT": [("chest pain", "SEVERE")],
        # condition-driven CONSULT_DOCTOR, no "Likely" -> stays CONSULT_DOCTOR
        "CONSULT_DOCTOR": [("chest pain", "MILD")],
    }
    for expected, symptoms in cases.items():
        result = await completed_result(safety_client, symptoms)
        assert all(c["confidence"] != "LIKELY" for c in result["conditions"])
        assert result["riskLevel"] == expected
        assert TIER_ORDER[result["riskLevel"]] >= TIER_ORDER["CONSULT_DOCTOR"]


# ===========================================================================
# Disclaimer and "no raw numbers" on every result
# ===========================================================================


@pytest.mark.anyio
async def test_tc_saf_a_11_every_result_has_disclaimer_and_no_percentages(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-11: disclaimer on every tier; no percentage anywhere in the flow.

    One run per risk tier. Every response body of each run (create, chat,
    symptoms, analyze, result) is scanned for a percentage or a probability
    word, and the result JSON must hold no decimal number at all.
    """
    runs = {
        "SELF_CARE": [("runny nose", "MILD"), ("sneezing", "MILD")],
        "CONSULT_DOCTOR": [
            ("fever", "MODERATE"),
            ("pain behind the eyes", "MODERATE"),
            ("joint pain", "MODERATE"),
        ],
        "URGENT": [("chest pain", "MODERATE"), ("shortness of breath", "MODERATE")],
    }
    for expected_tier, symptoms in runs.items():
        run = await run_assessment(safety_client, symptoms)
        assert run.result_status == 200, run.result
        assert run.result["riskLevel"] == expected_tier
        assert run.result["disclaimer"] == DEFAULT_DISCLAIMER

        for body in run.bodies:
            assert not PERCENT_PATTERN.search(body), body
            assert not PROBABILITY_WORDS.search(body), body

        floats = [
            v for v in _walk_values(json.loads(run.bodies[-1])) if isinstance(v, float)
        ]
        assert floats == [], floats


# ===========================================================================
# Confirmation card edits (regression for #351)
# ===========================================================================


@pytest.mark.anyio
async def test_tc_saf_a_21_removed_red_flag_no_longer_counts(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-21: chest pain removed on the card does not make the result urgent.

    The AI extracts chest pain and headache; the user removes chest pain and
    keeps headache. Before #351 the removed chest pain was still analysed and
    the result was URGENT ("Because you reported chest pain").
    """
    run = await run_card_edit(
        safety_client,
        "I have chest pain and a mild headache since yesterday",
        keep=["headache"],
    )
    assert "chest_pain" in run.extracted
    assert run.confirmed == ["headache"]
    assert run.result_status == 200, run.result
    assert run.result["riskLevel"] != "URGENT"
    whys = " ".join(c["why"] for c in run.result["conditions"])
    assert "chest pain" not in whys
    assert "headache" in whys


@pytest.mark.anyio
async def test_tc_saf_a_22_card_edit_replaces_the_list(
    safety_client: AsyncClient,
) -> None:
    """TC-SAF-A-22: the edited list replaces the stored one; empty is refused.

    Removing headache and adding fever leaves only fever (stored and in the
    result). Sending an empty list clears it, and analysis then refuses to
    run on nothing (400), as before.
    """
    run = await run_card_edit(
        safety_client,
        "I have a mild headache since yesterday",
        keep=[],
        add=[("fever", "MILD")],
    )
    assert run.extracted == ["headache"]
    assert run.confirmed == ["fever"]
    whys = " ".join(c["why"] for c in run.result["conditions"])
    assert "fever" in whys and "headache" not in whys

    run = await run_card_edit(
        safety_client, "I have a mild headache since yesterday", keep=[]
    )
    assert run.confirmed == []
    assert run.analyze_status == 400
    assert run.result_status == 409
    stored = await safety_client.get(f"{BASE_URL}/{run.assessment_id}/symptoms")
    assert stored.json() == []


def _walk_values(node: Any) -> list[Any]:
    """Every leaf value in a JSON document."""
    if isinstance(node, dict):
        return [v for child in node.values() for v in _walk_values(child)]
    if isinstance(node, list):
        return [v for child in node for v in _walk_values(child)]
    return [node]
