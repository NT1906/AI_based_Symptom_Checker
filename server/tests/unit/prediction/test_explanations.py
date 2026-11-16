"""Unit tests for the contributing-factor explanations.

Covers:
    - One, two, three and more than three matched symptoms (the rest counted).
    - Display names from the knowledge service, lowercased inside the sentence
      unless they start with an acronym; unknown IDs fall back readably.
    - Every condition in the dataset gets a guard-safe line with no raw IDs.
    - ``join_names`` rejects an empty list.

Owner: Nisarg (prediction) · Task: S2-NIS-2 · Requirements: FR-24, DR-05
"""

import pytest
from app.schemas.enums import ConfidenceLabel, RiskLevel
from app.services.prediction import result_text as text
from app.services.prediction.condition_catalog import get_catalog
from app.services.prediction.explanations import (
    MAX_LISTED,
    ConditionExplainer,
    join_names,
    knowledge_symptom_name,
)
from app.services.prediction.schemas import ConditionPrediction
from app.services.privacy.safety_guard import assert_safe_wording

NAMES = {
    "fever": "Fever",
    "joint_pain": "Joint pain",
    "pain_behind_eyes": "Pain behind the eyes",
    "headache": "Headache",
    "rash": "Skin rash",
    "uti_ache": "UTI-type ache",
}


def _prediction(*matched: str) -> ConditionPrediction:
    """A hand-made prediction whose matched symptoms are ``matched``."""
    return ConditionPrediction(
        condition_id="dengue",
        name="Dengue",
        icd10_code="A90",
        specialty="general_physician",
        base_risk=RiskLevel.CONSULT_DOCTOR,
        confidence=ConfidenceLabel.LIKELY,
        rank=1,
        matched_symptom_ids=matched,
    )


def _explain(*matched: str) -> str:
    """Explain a prediction with the fixed test names."""
    return ConditionExplainer(NAMES.get).explain(_prediction(*matched))


@pytest.mark.parametrize(
    ("matched", "expected"),
    [
        (("fever",), "Because you reported fever."),
        (("fever", "joint_pain"), "Because you reported fever and joint pain."),
        (
            ("fever", "joint_pain", "pain_behind_eyes"),
            "Because you reported fever, joint pain and pain behind the eyes.",
        ),
        (
            ("fever", "joint_pain", "pain_behind_eyes", "headache"),
            "Because you reported fever, joint pain, pain behind the eyes "
            "and 1 other symptom.",
        ),
        (
            ("fever", "joint_pain", "pain_behind_eyes", "headache", "rash"),
            "Because you reported fever, joint pain, pain behind the eyes "
            "and 2 other symptoms.",
        ),
    ],
)
def test_lists_up_to_three_symptoms_and_counts_the_rest(
    matched: tuple[str, ...], expected: str
) -> None:
    assert _explain(*matched) == expected


def test_keeps_matched_order_heaviest_first() -> None:
    assert _explain("joint_pain", "fever") == (
        "Because you reported joint pain and fever."
    )


def test_acronym_names_keep_their_capitals() -> None:
    assert _explain("uti_ache") == "Because you reported UTI-type ache."


def test_unknown_symptom_id_falls_back_to_readable_words() -> None:
    assert _explain("swollen_glands") == "Because you reported swollen glands."


def test_knowledge_names_cover_every_condition_symptom() -> None:
    symptom_ids = {s.id for c in get_catalog().conditions for s in c.symptoms}

    missing = sorted(i for i in symptom_ids if knowledge_symptom_name(i) is None)

    assert missing == []


def test_unknown_id_has_no_knowledge_name() -> None:
    assert knowledge_symptom_name("not_a_symptom") is None


def test_every_dataset_condition_gets_a_safe_line_without_raw_ids() -> None:
    explainer = ConditionExplainer()
    for condition in get_catalog().conditions:
        ids = tuple(s.id for s in condition.symptoms)
        line = explainer.explain(_prediction(*ids))

        assert_safe_wording(line)
        assert "_" not in line
        assert len(line) <= 500  # Condition.why max_length


def test_more_than_max_listed_counts_every_extra_symptom() -> None:
    ids = tuple(NAMES)[: MAX_LISTED + 3]

    assert _explain(*ids).endswith(f"and {text.other_symptoms(3)}.")


def test_join_names_rejects_an_empty_list() -> None:
    with pytest.raises(ValueError, match="at least one name"):
        join_names([])
