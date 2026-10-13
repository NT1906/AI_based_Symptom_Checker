"""Mock AI provider returning deterministic fixture extractions.

Responsibilities:
 - Return realistic, fixture-backed extractions when AI_PROVIDER=mock.
 - Allow teammates and CI to run tests without OpenAI API keys.
 - Support deterministic failure simulation for error handling tests.

Owner: Nishith · Task: S0-NIT-1 · Requirements: NFR-05
"""

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

# Common lay terms mapped to canonical symptom identifiers aligned with conditions.json
FIXTURE_SYMPTOM_MAP: dict[str, str] = {
    "headache": "headache",
    "head hurts": "headache",
    "head pain": "headache",
    "fever": "fever",
    "feverish": "fever",
    "high temperature": "fever",
    "chest pain": "chest_pain",
    "cough": "cough",
    "coughing": "cough",
    "shortness of breath": "shortness_of_breath",
    "hard to breathe": "shortness_of_breath",
    "trouble breathing": "shortness_of_breath",
    "sore throat": "sore_throat",
    "throat hurts": "sore_throat",
    "throat pain": "sore_throat",
    "nausea": "nausea",
    "feeling sick": "nausea",
    "vomiting": "vomiting",
    "threw up": "vomiting",
    "fatigue": "fatigue",
    "tired": "fatigue",
    "exhausted": "fatigue",
    "stomach pain": "abdominal_pain",
    "stomach ache": "abdominal_pain",
    "tummy ache": "abdominal_pain",
    "abdominal pain": "abdominal_pain",
    "rash": "rash",
    "dizziness": "dizziness",
    "dizzy": "dizziness",
    "lightheaded": "dizziness",
    "chills": "chills",
    "runny nose": "rhinorrhea",
}

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

        # Extract symptoms from fixture dictionary
        for phrase, canonical_name in FIXTURE_SYMPTOM_MAP.items():
            if (
                re.search(r"\b" + re.escape(phrase) + r"\b", cleaned)
                and canonical_name not in detected_canonical_names
            ):
                detected_canonical_names.add(canonical_name)

                # Extract duration heuristics
                duration = self._parse_duration(cleaned)
                onset = self._parse_onset(cleaned)

                # Extract severity heuristics
                severity = self._parse_severity(cleaned)

                # Extract location heuristics
                body_location = self._parse_location(cleaned, canonical_name)

                extracted_symptoms.append(
                    ExtractedSymptom(
                        name=canonical_name,
                        severity=severity,
                        duration=duration,
                        onset=onset,
                        body_location=body_location,
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
                question="Could you describe in a bit more detail what symptoms you are feeling?",
                question_type="CONTEXT",
                target_symptom=None,
            )

        # Check for missing duration on the primary symptom
        primary_symptom = symptoms[0]
        symptom_name = (
            primary_symptom.get("name")
            if isinstance(primary_symptom, dict)
            else getattr(primary_symptom, "name", "this")
        )

        display_name = symptom_name.replace("_", " ")

        # Candidate questions in priority order
        duration_q = f"How long have you been experiencing the {display_name}?"
        severity_q = f"On a scale of mild, moderate, or severe, how would you describe the {display_name}?"
        assoc_q = "Are you experiencing any other symptoms, such as fever, dizziness, or shortness of breath?"

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
        """Heuristic severity parser from descriptive text."""
        if any(
            w in text
            for w in [
                "severe",
                "terrible",
                "really bad",
                "worst",
                "unbearable",
                "extreme",
            ]
        ):
            return SeverityEnum.SEVERE
        if any(w in text for w in ["moderate", "pretty bad", "noticeable"]):
            return SeverityEnum.MODERATE
        if any(w in text for w in ["mild", "slight", "little bit", "minor"]):
            return SeverityEnum.MILD
        return SeverityEnum.UNKNOWN

    def _parse_duration(self, text: str) -> Duration | None:
        """Heuristic duration parser."""
        if "since yesterday" in text or "yesterday" in text:
            return Duration(value=1.0, unit=DurationUnitEnum.DAY)
        if "for a couple days" in text or "couple of days" in text:
            return Duration(value=2.0, unit=DurationUnitEnum.DAY)
        if "for a week" in text or "one week" in text:
            return Duration(value=1.0, unit=DurationUnitEnum.WEEK)

        # Match regex patterns like 'for 3 days', '2 weeks', '4 hours'
        match = re.search(r"(\d+(?:\.\d+)?)\s*(hour|day|week|month|year)s?\b", text)
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
        """Extract explicit onset phrases."""
        if "since yesterday" in text:
            return "since yesterday"
        match = re.search(r"(since\s+[a-zA-Z0-9\s]+|started\s+[a-zA-Z0-9\s]+ago)", text)
        if match:
            return match.group(0).strip()
        return None

    def _parse_location(self, text: str, canonical_name: str) -> str | None:
        """Extract body location if mentioned."""
        locations = [
            "forehead",
            "temple",
            "back of head",
            "left side",
            "right side",
            "upper chest",
            "lower abdomen",
            "throat",
            "stomach",
        ]
        for loc in locations:
            if loc in text:
                return loc
        return None
