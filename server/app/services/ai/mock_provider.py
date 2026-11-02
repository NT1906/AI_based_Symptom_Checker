"""Mock AI provider returning deterministic fixture extractions.

Responsibilities:
    - Return realistic, fixture-backed extractions when AI_PROVIDER=mock.
    - Support comprehensive canonical symptom coverage aligned with symptoms.json.
    - Allow teammates and CI to run tests without OpenAI API keys.
    - Support deterministic failure simulation for error handling tests.

Owner: Nishith · Task: S1-NIT-1 · Requirements: FR-03, FR-17, NFR-05
"""

import json
import logging
from pathlib import Path
import re
from typing import Any

from app.services.ai.gateway import AiError, AiTimeoutError, AiValidationError
from app.services.ai.schemas import (
    ClarificationResult,
    Duration,
    DurationUnitEnum,
    ExtractedSymptom,
    ExtractionResult,
    SeverityEnum,
)

logger = logging.getLogger(__name__)

# Base fallback lay term to canonical symptom ID mapping (100 canonical symptoms)
BASE_FIXTURE_MAP: dict[str, str] = {
    # General
    "fever": "fever",
    "feverish": "fever",
    "high temperature": "fever",
    "bukhar": "fever",
    "bukhaar": "fever",
    "tez bukhar": "fever",
    "chills": "chills",
    "shivering": "chills",
    "thandi lag rahi": "chills",
    "fatigue": "fatigue",
    "tired": "fatigue",
    "exhausted": "fatigue",
    "weakness": "fatigue",
    "thakan": "fatigue",
    "kamzori": "fatigue",
    "body aches": "body_aches",
    "body pain": "body_aches",
    "badan dard": "body_aches",
    "sweating": "sweating",
    "night sweats": "night_sweats",
    "weight loss": "weight_loss",
    "loss of appetite": "loss_of_appetite",
    "dizziness": "dizziness",
    "dizzy": "dizziness",
    "lightheaded": "dizziness",
    "chakkar": "dizziness",
    "fainting": "fainting",
    "swollen neck glands": "swollen_neck_glands",
    "excessive thirst": "excessive_thirst",
    "pale skin": "pale_skin",
    # Neurological
    "headache": "headache",
    "head hurts": "headache",
    "head pain": "headache",
    "sar dard": "headache",
    "sudden severe headache": "sudden_severe_headache",
    "light sensitivity": "light_sensitivity",
    "sound sensitivity": "sound_sensitivity",
    "visual aura": "visual_aura",
    "stiff neck": "stiff_neck",
    "confusion": "confusion",
    "seizure": "seizure",
    "facial droop": "facial_droop",
    "one sided weakness": "one_sided_weakness",
    "slurred speech": "slurred_speech",
    "sudden vision loss": "sudden_vision_loss",
    # Musculoskeletal
    "joint pain": "joint_pain",
    "joint swelling": "joint_swelling",
    "lower back pain": "lower_back_pain",
    "back pain": "lower_back_pain",
    "kamar dard": "lower_back_pain",
    "muscle stiffness": "muscle_stiffness",
    # ENT
    "runny nose": "runny_nose",
    "nasal congestion": "nasal_congestion",
    "stuffy nose": "nasal_congestion",
    "sneezing": "sneezing",
    "sore throat": "sore_throat",
    "throat hurts": "sore_throat",
    "galey me dard": "sore_throat",
    "painful swallowing": "painful_swallowing",
    "facial pain": "facial_pain_or_pressure",
    "loss of smell": "loss_of_smell_or_taste",
    "loss of taste": "loss_of_smell_or_taste",
    # Respiratory
    "cough": "cough",
    "coughing": "cough",
    "khansi": "cough",
    "productive cough": "productive_cough",
    "coughing blood": "coughing_blood",
    "shortness of breath": "shortness_of_breath",
    "trouble breathing": "shortness_of_breath",
    "hard to breathe": "shortness_of_breath",
    "breathless": "shortness_of_breath",
    "wheezing": "wheezing",
    "chest tightness": "chest_tightness",
    "bluish lips": "bluish_lips_or_face",
    # Eye
    "red eye": "red_eye",
    "pink eye": "red_eye",
    "itchy eyes": "itchy_eyes",
    "watery eyes": "watery_eyes",
    "eye discharge": "eye_discharge",
    "pain behind eyes": "pain_behind_eyes",
    "blurred vision": "blurred_vision",
    # Cardiovascular
    "chest pain": "chest_pain",
    "chhati me dard": "chest_pain",
    "pain spreading to arm": "pain_spreading_to_arm_jaw_or_back",
    "pain spreading to the arm": "pain_spreading_to_arm_jaw_or_back",
    "pain that goes to my left arm": "pain_spreading_to_arm_jaw_or_back",
    "pain that goes to arm": "pain_spreading_to_arm_jaw_or_back",
    "goes to my left arm": "pain_spreading_to_arm_jaw_or_back",
    "goes to my arm": "pain_spreading_to_arm_jaw_or_back",
    "goes to left arm": "pain_spreading_to_arm_jaw_or_back",
    "pain radiating to arm": "pain_spreading_to_arm_jaw_or_back",
    "radiating to arm": "pain_spreading_to_arm_jaw_or_back",
    "palpitations": "palpitations",
    # Gastrointestinal
    "nausea": "nausea",
    "feeling sick": "nausea",
    "vomiting": "vomiting",
    "threw up": "vomiting",
    "throwing up": "nausea",
    "ulti": "vomiting",
    "diarrhea": "diarrhea",
    "loose motions": "diarrhea",
    "dast": "diarrhea",
    "constipation": "constipation",
    "abdominal pain": "abdominal_pain",
    "stomach pain": "abdominal_pain",
    "stomach ache": "abdominal_pain",
    "tummy ache": "abdominal_pain",
    "pet me dard": "abdominal_pain",
    "lower right abdominal pain": "lower_right_abdominal_pain",
    "upper right abdominal pain": "upper_right_abdominal_pain",
    "heartburn": "heartburn",
    "acid reflux": "acid_regurgitation",
    "bloating": "bloating",
    "vomiting blood": "vomiting_blood",
    "black stool": "black_or_bloody_stool",
    "bloody stool": "black_or_bloody_stool",
    # Urinary
    "burning urination": "burning_urination",
    "frequent urination": "frequent_urination",
    "cloudy urine": "cloudy_or_smelly_urine",
    "blood in urine": "blood_in_urine",
    "flank pain": "flank_pain",
    # Skin
    "skin rash": "skin_rash",
    "rash": "skin_rash",
    "itchy skin": "itchy_skin",
    "khujli": "itchy_skin",
    "dry skin": "dry_skin",
    "scaly skin": "scaly_skin",
    "ring shaped rash": "ring_shaped_rash",
    "hives": "hives",
    "skin swelling": "skin_swelling",
    "blisters": "fluid_filled_blisters",
    "fluid filled blisters": "fluid_filled_blisters",
    "pimples": "pimples",
    "spreading redness": "spreading_redness",
    "non blanching rash": "non_blanching_rash",
    # Mental Health
    "thoughts of self harm": "thoughts_of_self_harm",
}


def _load_canonical_vocabulary() -> dict[str, str]:
    """Load canonical symptoms and lay terms from dataset if available.

    Returns:
        Consolidated dictionary mapping phrases to canonical symptom IDs.
    """
    mapping = dict(BASE_FIXTURE_MAP)
    dataset_path = (
        Path(__file__).resolve().parents[4]
        / "ml"
        / "datasets"
        / "symptoms"
        / "symptoms.json"
    )
    if dataset_path.exists():
        try:
            with dataset_path.open(encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("symptoms", []):
                    symptom_id = item["id"]
                    mapping[symptom_id.replace("_", " ")] = symptom_id
                    mapping[item["name"].lower()] = symptom_id
                    for lay in item.get("lay_terms", []):
                        mapping[lay.lower()] = symptom_id
        except Exception as exc:
            logger.warning("Failed to load symptoms.json: %s", exc)
    return mapping


FIXTURE_SYMPTOM_MAP: dict[str, str] = _load_canonical_vocabulary()

MAX_CLARIFICATION_QUESTIONS: int = 3


class MockAiProvider:
    """Fixture-backed AI provider for local development, CI, and testing.

    Provides deterministic symptom extraction and clarification without external
    network calls or API keys. Fully conforms to the AiGateway protocol.
    """

    def __init__(self, default_latency_ms: float = 0.0) -> None:
        self.default_latency_ms = default_latency_ms

    async def extract_symptoms(
        self,
        message: str,
        conversation_history: str = "",
    ) -> ExtractionResult:
        """Extract structured symptoms using deterministic fixture heuristics.

        Args:
            message: Raw user text.
            conversation_history: Previous conversational turns.

        Returns:
            Validated ExtractionResult with detected canonical symptoms.

        Raises:
            AiTimeoutError: If __SIMULATE_TIMEOUT__ is present in input.
            AiValidationError: If __SIMULATE_VALIDATION_ERROR__ is present in input.
            AiError: If __SIMULATE_ERROR__ is present in input.
        """
        # Testing hooks for simulating edge failure modes
        if "__SIMULATE_TIMEOUT__" in message:
            raise AiTimeoutError("Simulated AI gateway timeout exceeded budget.")
        if "__SIMULATE_VALIDATION_ERROR__" in message:
            raise AiValidationError("Simulated malformed JSON response from model.")
        if "__SIMULATE_ERROR__" in message:
            raise AiError("Simulated upstream provider connection drop.")

        cleaned = message.lower().strip()
        if not cleaned:
            return ExtractionResult(
                symptoms=[],
                associated_symptoms=[],
                requires_clarification=False,
                clarification_reason=None,
            )

        extracted_symptoms: list[ExtractedSymptom] = []
        detected_canonical_names: set[str] = set()

        # Sort keys by length descending to match longest phrases first
        # (e.g. 'sudden severe headache' before 'headache')
        sorted_phrases = sorted(FIXTURE_SYMPTOM_MAP.keys(), key=len, reverse=True)

        # Extract symptoms from fixture dictionary
        for phrase in sorted_phrases:
            canonical_name = FIXTURE_SYMPTOM_MAP[phrase]
            # Word boundary matching
            pattern = rf"(?:\b|^){re.escape(phrase)}(?:\b|$)"
            if (
                re.search(pattern, cleaned)
                and canonical_name not in detected_canonical_names
            ):
                detected_canonical_names.add(canonical_name)

                # Extract duration heuristics
                duration = self._parse_duration(cleaned)
                onset = self._parse_onset(cleaned)

                # Extract severity heuristics
                severity = self._parse_severity(cleaned)

                # Extract location/body site heuristics
                body_site = self._parse_location(cleaned, canonical_name)

                extracted_symptoms.append(
                    ExtractedSymptom(
                        name=canonical_name,
                        severity=severity,
                        duration=duration,
                        onset=onset,
                        body_site=body_site,
                        body_location=body_site,
                        confidence=0.95,
                    )
                )

        # Determine clarification need (if symptoms found but duration is missing)
        requires_clarification = False
        clarification_reason = None
        if extracted_symptoms:
            has_duration = any(s.duration is not None for s in extracted_symptoms)
            if not has_duration:
                requires_clarification = True
                clarification_reason = "Duration information is missing."

        return ExtractionResult(
            symptoms=extracted_symptoms,
            associated_symptoms=[],
            requires_clarification=requires_clarification,
            clarification_reason=clarification_reason,
        )

    async def generate_clarification(
        self,
        structured_state: dict[str, Any],
        already_asked: list[str],
    ) -> ClarificationResult:
        """Generate targeted follow-up question adhering to safety limits.

        Enforces the max 3 question limit (FR-04, FR-19).

        Args:
            structured_state: Dictionary of currently collected symptom state.
            already_asked: List of questions already posed to the patient.

        Returns:
            ClarificationResult with conversational question or should_ask=False.
        """
        # Enforce hard cap of 3 questions
        if len(already_asked) >= MAX_CLARIFICATION_QUESTIONS:
            return ClarificationResult(
                should_ask=False,
                question=None,
                question_type=None,
                target_symptom=None,
            )

        symptoms = structured_state.get("symptoms", [])
        if not symptoms:
            return ClarificationResult(
                should_ask=True,
                question=(
                    "Could you describe in a bit more detail what symptoms you are"
                    " feeling?"
                ),
                question_type="CONTEXT",
                target_symptom=None,
            )

        # Check for missing duration on the primary symptom
        primary_symptom = symptoms[0]
        raw_name = (
            primary_symptom.get("name")
            if isinstance(primary_symptom, dict)
            else getattr(primary_symptom, "name", None)
        )
        symptom_name = str(raw_name) if raw_name else "this"
        display_name = symptom_name.replace("_", " ")

        # Candidate questions in priority order
        duration_q = f"How long have you been experiencing the {display_name}?"
        severity_q = (
            "On a scale of mild, moderate, or severe, how would you describe the "
            f"{display_name}?"
        )
        assoc_q = (
            "Are you experiencing any other symptoms, such as fever, dizziness, or"
            " shortness of breath?"
        )

        for candidate, q_type in [
            (duration_q, "DURATION"),
            (severity_q, "SEVERITY"),
            (assoc_q, "ASSOCIATED"),
        ]:
            if candidate not in already_asked:
                return ClarificationResult(
                    should_ask=True,
                    question=candidate,
                    question_type=q_type,
                    target_symptom=symptom_name,
                )

        return ClarificationResult(
            should_ask=False,
            question=None,
            question_type=None,
            target_symptom=None,
        )

    def _parse_severity(self, text: str) -> SeverityEnum:
        """Heuristic severity parser from descriptive English and Hinglish text.

        Args:
            text: Lowercased user text.

        Returns:
            Corresponding SeverityEnum member.
        """
        severe_terms = [
            "severe",
            "terrible",
            "really bad",
            "worst",
            "unbearable",
            "extreme",
            "tez",
            "bahut tez",
            "bahut zyada",
            "very bad",
        ]
        if any(w in text for w in severe_terms):
            return SeverityEnum.SEVERE
        if any(w in text for w in ["moderate", "pretty bad", "noticeable", "kafi"]):
            return SeverityEnum.MODERATE
        if any(
            w in text
            for w in [
                "mild",
                "slight",
                "little bit",
                "minor",
                "thoda sa",
                "halka",
            ]
        ):
            return SeverityEnum.MILD
        return SeverityEnum.UNKNOWN

    def _parse_duration(self, text: str) -> Duration | None:
        """Heuristic duration parser from natural phrasing.

        Args:
            text: Lowercased user text.

        Returns:
            Parsed Duration instance or None.
        """
        if "since yesterday" in text or "yesterday" in text:
            return Duration(value=1.0, unit=DurationUnitEnum.DAY)
        if "for a couple days" in text or "couple of days" in text:
            return Duration(value=2.0, unit=DurationUnitEnum.DAY)
        if "for a week" in text or "one week" in text:
            return Duration(value=1.0, unit=DurationUnitEnum.WEEK)
        if "all day" in text or "today" in text:
            return Duration(value=1.0, unit=DurationUnitEnum.DAY)

        # Match regex patterns like 'for 3 days', '2 weeks', '4 hours', 'past 3 days'
        match = re.search(
            r"(?:for|past|about)?\s*(\d+(?:\.\d+)?)\s*(hour|day|week|month|year)s?\b",
            text,
        )
        if match:
            val = float(match.group(1))
            unit_str = match.group(2).upper()
            try:
                unit = DurationUnitEnum(unit_str)
                return Duration(value=val, unit=unit)
            except ValueError:
                pass
        return None

    def _parse_onset(self, text: str) -> str | None:
        """Extract explicit onset phrases.

        Args:
            text: Lowercased user text.

        Returns:
            Onset phrasing string or None.
        """
        if "since yesterday" in text:
            return "since yesterday"
        if "this morning" in text:
            return "this morning"
        if "today" in text:
            return "today"
        match = re.search(
            r"(since\s+[a-zA-Z0-9\s]+|started\s+[a-zA-Z0-9\s]+ago|for\s+the\s+past\s+[a-zA-Z0-9\s]+)",
            text,
        )
        if match:
            return match.group(0).strip()
        return None

    def _parse_location(self, text: str, canonical_name: str) -> str | None:
        """Extract body site/location if mentioned, contextualized by symptom.

        Args:
            text: Lowercased user text.
            canonical_name: Canonical symptom identifier.

        Returns:
            Body location string or None.
        """
        # Specific contextual anatomical sites for key symptom types
        if canonical_name in {"chest_pain", "chest_tightness"}:
            if "upper chest" in text:
                return "upper chest"
            if "chest" in text:
                return "chest"

        if canonical_name == "pain_spreading_to_arm_jaw_or_back":
            if "left arm" in text:
                return "left arm"
            if "right arm" in text:
                return "right arm"
            if "jaw" in text:
                return "jaw"
            if "back" in text:
                return "back"

        if canonical_name in {"headache", "sudden_severe_headache"}:
            if "forehead" in text:
                return "forehead"
            if "temple" in text:
                return "temple"
            if "back of head" in text:
                return "back of head"

        if canonical_name in {"sore_throat", "painful_swallowing"}:
            if "throat" in text:
                return "throat"

        if canonical_name in {
            "abdominal_pain",
            "lower_right_abdominal_pain",
            "upper_right_abdominal_pain",
        }:
            if "lower right abdomen" in text:
                return "lower right abdomen"
            if "upper right abdomen" in text:
                return "upper right abdomen"
            if "lower abdomen" in text:
                return "lower abdomen"
            if "upper abdomen" in text:
                return "upper abdomen"
            if "abdomen" in text:
                return "abdomen"
            if "stomach" in text:
                return "stomach"

        if canonical_name == "lower_back_pain":
            if "lower back" in text:
                return "lower back"
            if "back" in text:
                return "back"

        # General fallbacks
        locations = [
            "lower right abdomen",
            "upper right abdomen",
            "lower abdomen",
            "upper abdomen",
            "abdomen",
            "stomach",
            "forehead",
            "temple",
            "back of head",
            "left arm",
            "right arm",
            "left side",
            "right side",
            "upper chest",
            "chest",
            "throat",
            "lower back",
            "back",
            "neck",
            "eyes",
            "skin",
        ]
        for loc in locations:
            if loc in text:
                return loc
        return None
