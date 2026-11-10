"""Unit tests for Prompt v2 multi-turn symptom extraction and eval fixes.

Responsibilities:
    - Validate multi-turn dialogue context resolution attributing replies to
      target symptoms.
    - Test co-occurring new symptom detection alongside clarifying answers.
    - Verify eval-driven improvements: common phonetic misspellings and
      Hinglish idioms.
    - Verify red-flag emergency combinations extract all constituent symptoms
      without truncation.
    - Test OpenAiProvider integration loading extraction.v2.txt.
    - Ensure medical-safety and non-diagnostic constraints are strictly
      preserved.

Owner: Nishith · Task: S2-NIT-1 · Requirements: FR-03, FR-17, FR-19, NFR-05, NFR-07
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai.mock_provider import MockAiProvider
from app.services.ai.openai_provider import EXTRACTION_PROMPT_PATH, OpenAiProvider
from app.services.ai.schemas import (
    Duration,
    DurationUnitEnum,
    ExtractedSymptom,
    ExtractionResult,
    SeverityEnum,
)

PROMPTS_DIR = (
    Path(__file__).resolve().parents[3] / "app" / "services" / "ai" / "prompts"
)


# ---------------------------------------------------------------------------
# Prompt File Invariant & Medical Safety Checks
# ---------------------------------------------------------------------------


def test_prompt_v2_file_exists_and_adheres_to_safety_invariants() -> None:
    """extraction.v2.txt must exist, be populated, and enforce safety rules."""
    v2_path = PROMPTS_DIR / "extraction.v2.txt"
    v1_path = PROMPTS_DIR / "extraction.v1.txt"

    assert v1_path.exists(), "extraction.v1.txt must remain intact"
    assert v2_path.exists(), "extraction.v2.txt must be present"

    content = v2_path.read_text(encoding="utf-8")
    assert len(content.strip()) > 500

    # Variable placeholders for runtime formatting
    assert "{conversation_history}" in content
    assert "{user_message}" in content

    # Non-negotiable medical safety rules (AI_RULES.md §2)
    assert "DO NOT provide any medical diagnosis" in content
    assert "NEVER invent, hallucinate, or assume symptoms" in content

    # Multi-turn resolution rules (FR-19)
    assert "MULTI-TURN CONVERSATION CONTEXT" in content
    assert "TARGET SYMPTOM ATTRIBUTION" in content

    # Eval-driven sections (NFR-07, report_v2.md)
    assert "COMMON MISSPELLINGS & PHONETIC TYPOS" in content
    assert "COMMON HINGLISH & TRANSLITERATED PHRASE MAPPINGS" in content
    assert "RED-FLAG EMERGENCY COMBINATIONS" in content


def test_openai_provider_points_to_extraction_v2() -> None:
    """OpenAiProvider must load extraction.v2.txt by default."""
    assert EXTRACTION_PROMPT_PATH.name == "extraction.v2.txt"
    assert EXTRACTION_PROMPT_PATH.exists()


# ---------------------------------------------------------------------------
# Multi-Turn Context Resolution Tests (FR-19)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_turn_clarification_duration_answer_mapped_to_target() -> None:
    """Standalone duration answer maps to questioned symptom in history."""
    provider = MockAiProvider()
    history = (
        "user: I have been experiencing a bad headache.\n"
        "assistant: About how long have you been experiencing the headache?"
    )
    result = await provider.extract_symptoms(
        message="for about 3 days now",
        conversation_history=history,
    )

    assert len(result.symptoms) == 1
    symptom = result.symptoms[0]
    assert symptom.name == "headache"
    assert symptom.duration is not None
    assert symptom.duration.value == 3.0
    assert symptom.duration.unit == DurationUnitEnum.DAY


@pytest.mark.asyncio
async def test_multi_turn_clarification_severity_and_duration_answered() -> None:
    """Standalone severity and duration in response map to active target symptom."""
    provider = MockAiProvider()
    history = (
        "user: I feel sick and have a fever.\n"
        "assistant: How long have you had the fever and how severe is it?"
    )
    result = await provider.extract_symptoms(
        message="since yesterday and it is really bad",
        conversation_history=history,
    )

    assert len(result.symptoms) == 1
    symptom = result.symptoms[0]
    assert symptom.name == "fever"
    assert symptom.duration is not None
    assert symptom.duration.value == 1.0
    assert symptom.duration.unit == DurationUnitEnum.DAY
    assert symptom.severity == SeverityEnum.SEVERE


@pytest.mark.asyncio
async def test_multi_turn_clarification_with_co_occurring_new_symptom() -> None:
    """When user answers clarification AND introduces new symptom, extract both."""
    provider = MockAiProvider()
    history = (
        "user: I've had a persistent cough.\n"
        "assistant: About how long have you been experiencing the cough?"
    )
    # User provides duration for cough, and introduces nausea
    result = await provider.extract_symptoms(
        message="for 2 weeks, and now I also feel nauseous",
        conversation_history=history,
    )

    symptom_names = {s.name for s in result.symptoms}
    assert "cough" in symptom_names
    assert "nausea" in symptom_names

    cough_symptom = next(s for s in result.symptoms if s.name == "cough")
    assert cough_symptom.duration is not None
    assert cough_symptom.duration.value == 2.0
    assert cough_symptom.duration.unit == DurationUnitEnum.WEEK


@pytest.mark.asyncio
async def test_multi_turn_targets_most_recent_assistant_question() -> None:
    """Map answers to symptom queried in latest assistant turn."""
    provider = MockAiProvider()
    history = (
        "user: I have lower back pain and also a mild cough.\n"
        "assistant: About how long have you been experiencing the lower back pain?"
    )
    result = await provider.extract_symptoms(
        message="for a week, pretty bad",
        conversation_history=history,
    )

    assert len(result.symptoms) == 1
    symptom = result.symptoms[0]
    assert symptom.name == "lower_back_pain"
    assert symptom.duration is not None
    assert symptom.duration.value == 1.0
    assert symptom.duration.unit == DurationUnitEnum.WEEK
    assert symptom.severity == SeverityEnum.MODERATE


# ---------------------------------------------------------------------------
# Eval-Driven Improvements: Phonetic Misspellings & Hinglish (NFR-07)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("input_text", "expected_canonical_name"),
    [
        ("I have severe headack since morning", "headache"),
        ("my stomake is hurting badly", "abdominal_pain"),
        ("feeling constant naucea all day", "nausea"),
        ("terrible dizzynes when standing up", "dizziness"),
        ("noticed blured vission today", "blurred_vision"),
        ("feeling general confution", "confusion"),
        ("noticed sudden droopin face on one side", "facial_droop"),
        ("uncontrollable vomting after meals", "vomiting"),
        ("having watery diarhea", "diarrhea"),
        ("sudden shiverring and feeling cold", "chills"),
    ],
)
async def test_phonetic_misspellings_normalized_to_canonical(
    input_text: str,
    expected_canonical_name: str,
) -> None:
    """Common phonetic patient misspellings map cleanly to canonical vocabulary."""
    provider = MockAiProvider()
    result = await provider.extract_symptoms(message=input_text)

    extracted_names = [s.name for s in result.symptoms]
    assert expected_canonical_name in extracted_names


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("hinglish_text", "expected_canonical_name"),
    [
        ("mujhe 3 din se pet saaf nahi hua", "constipation"),
        ("kal se dast lag gaye hain", "diarrhea"),
        ("thoda chalne pe sans phoolna shuru ho jata hai", "shortness_of_breath"),
        ("seene me jakdan mehsoos ho rahi hai", "chest_tightness"),
        ("bahut tezz bukhar hai kal se", "fever"),
        ("shareer me bahut kamzori aur thakan hai", "fatigue"),
        ("achanak chakkar aa rahe hain aur sar ghoom raha hai", "dizziness"),
        ("galey me dard aur kharrash hai", "sore_throat"),
        ("haath pair me lal daane nikal aaye hain", "skin_rash"),
    ],
)
async def test_hinglish_idiomatic_expressions_extracted(
    hinglish_text: str,
    expected_canonical_name: str,
) -> None:
    """Hinglish and Indian English expressions map to canonical concepts."""
    provider = MockAiProvider()
    result = await provider.extract_symptoms(message=hinglish_text)

    extracted_names = [s.name for s in result.symptoms]
    assert expected_canonical_name in extracted_names


@pytest.mark.asyncio
async def test_hinglish_tez_bukhar_assigns_severe_severity() -> None:
    """'Tez bukhar' or 'bahut tezz bukhar' maps to fever with SEVERE intensity."""
    provider = MockAiProvider()
    result = await provider.extract_symptoms(
        message="mujhe kal se bahut tezz bukhar hai"
    )

    fever = next((s for s in result.symptoms if s.name == "fever"), None)
    assert fever is not None
    assert fever.severity == SeverityEnum.SEVERE
    assert fever.duration is not None
    assert fever.duration.value == 1.0


# ---------------------------------------------------------------------------
# Red-Flag Emergency Grouping Preservation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stroke_fast_triad_extracts_all_constituent_symptoms() -> None:
    """FAST stroke triad extracts all present red-flag symptoms."""
    provider = MockAiProvider()
    input_text = (
        "My mother suddenly developed facial droop on the left side, "
        "one sided weakness, and her speech is slurred"
    )
    result = await provider.extract_symptoms(message=input_text)
    names = {s.name for s in result.symptoms}

    assert "facial_droop" in names
    assert "one_sided_weakness" in names
    assert "slurred_speech" in names


@pytest.mark.asyncio
async def test_cauda_equina_emergency_triad_extracted() -> None:
    """Cauda equina triad (saddle numbness + incontinence + back pain)."""
    provider = MockAiProvider()
    input_text = (
        "Severe lower back pain with saddle numbness and "
        "loss of bladder or bowel control since yesterday"
    )
    result = await provider.extract_symptoms(message=input_text)
    names = {s.name for s in result.symptoms}

    assert "lower_back_pain" in names
    assert "saddle_numbness" in names
    assert "loss_of_bladder_or_bowel_control" in names


# ---------------------------------------------------------------------------
# OpenAiProvider Structured Multi-Turn Format Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openai_provider_multi_turn_formatting() -> None:
    """Verify OpenAiProvider formats prompt v2 with conversation history."""
    mock_parsed = ExtractionResult(
        symptoms=[
            ExtractedSymptom(
                name="headache",
                severity=SeverityEnum.MODERATE,
                duration=Duration(value=3.0, unit=DurationUnitEnum.DAY),
                confidence=0.95,
            )
        ],
        associated_symptoms=[],
        requires_clarification=False,
    )

    choice = MagicMock()
    choice.message.parsed = mock_parsed
    choice.message.refusal = None
    completion = MagicMock()
    completion.choices = [choice]

    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(return_value=completion)

    provider = OpenAiProvider(client=mock_client)

    history = "user: I have a headache.\nassistant: How long have you had the headache?"
    res = await provider.extract_symptoms(
        message="For 3 days now, it is moderate",
        conversation_history=history,
    )

    assert len(res.symptoms) == 1
    assert res.symptoms[0].name == "headache"
    assert res.symptoms[0].duration is not None
    assert res.symptoms[0].duration.value == 3.0

    # Ensure format call received formatted multi-turn prompt
    mock_client.beta.chat.completions.parse.assert_awaited_once()
    await_args = mock_client.beta.chat.completions.parse.await_args
    assert await_args is not None
    sent_content = await_args.kwargs["messages"][0]["content"]
    assert "How long have you had the headache?" in sent_content
    assert "For 3 days now, it is moderate" in sent_content
    assert "MULTI-TURN CONVERSATION CONTEXT" in sent_content
