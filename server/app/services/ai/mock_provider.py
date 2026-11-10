"""Mock AI provider returning deterministic fixture extractions.

Responsibilities:
    - Return realistic, fixture-backed extractions when AI_PROVIDER=mock.
    - Support comprehensive canonical symptom coverage aligned with symptoms.json.
    - Detect missing clinical information and generate targeted clarification questions.
    - Enforce a hard maximum of 3 clarification questions (FR-04, FR-19, FR-20).
    - Allow teammates and CI to run tests without OpenAI API keys.
    - Support deterministic failure simulation for error handling tests.

Owner: Nishith · Tasks: S1-NIT-2, S2-NIT-1
Requirements: FR-03, FR-04, FR-17, FR-19, FR-20, NFR-05, NFR-07
"""

import json
import logging
from pathlib import Path
import re
from typing import Any

from app.services.ai.gateway import AiError, AiTimeoutError, AiValidationError
from app.services.ai.missing_info import (
    SITE_SENSITIVE_SYMPTOMS,
    detect_missing_information,
    should_request_clarification,
)
from app.services.ai.schemas import (
    ClarificationResult,
    Duration,
    DurationUnitEnum,
    ExtractedSymptom,
    ExtractionResult,
    MissingFieldEnum,
    QuestionTypeEnum,
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
    "saddle numbness": "saddle_numbness",
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
    # Common Misspellings and Phonetic Typos (S2-NIT-1)
    "headack": "headache",
    "hedache": "headache",
    "headach": "headache",
    "stomake": "abdominal_pain",
    "stomake aking": "abdominal_pain",
    "naucea": "nausea",
    "nausia": "nausea",
    "nauseous": "nausea",
    "feel nauseous": "nausea",
    "dizzynes": "dizziness",
    "blured vission": "blurred_vision",
    "confution": "confusion",
    "droopin face": "facial_droop",
    "drooping face": "facial_droop",
    "vomting": "vomiting",
    "vomitting": "vomiting",
    "diarhea": "diarrhea",
    "diarrhoea": "diarrhea",
    "shiverring": "chills",
    # Expanded Hinglish & Idiomatic Descriptions (S2-NIT-1)
    "pet saaf nahi hua": "constipation",
    "dast lag gaye": "diarrhea",
    "sans phoolna": "shortness_of_breath",
    "seene me jakdan": "chest_tightness",
    "chhati me dabav": "chest_tightness",
    "bahut tezz bukhar": "fever",
    "susti": "fatigue",
    "gala kharab": "sore_throat",
    "kharrash": "sore_throat",
    "sar ghoom raha": "dizziness",
    "sar ghoom raha hai": "dizziness",
    "lal daane": "skin_rash",
    # Mental Health
    "thoughts of self harm": "thoughts_of_self_harm",
}


def _load_canonical_vocabulary() -> dict[str, str]:
    """Load canonical symptoms and lay terms from dataset if available.

    Checks both the deployed server knowledge directory and the repository ml directory.

    Returns:
        Consolidated dictionary mapping phrases to canonical symptom IDs.
    """
    mapping = dict(BASE_FIXTURE_MAP)
    candidates = [
        Path(__file__).resolve().parents[1] / "knowledge" / "data" / "symptoms.json",
        Path(__file__).resolve().parents[4]
        / "ml"
        / "datasets"
        / "symptoms"
        / "symptoms.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                with path.open(encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("symptoms", []):
                        symptom_id = item["id"]
                        mapping[symptom_id.replace("_", " ")] = symptom_id
                        mapping[item["name"].lower()] = symptom_id
                        for lay in item.get("lay_terms", []):
                            mapping[lay.lower()] = symptom_id
                break
            except Exception as exc:
                logger.warning("Failed to load symptoms file at %s: %s", path, exc)
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
        matched_spans: list[tuple[int, int]] = []

        # Sort keys by length descending to match longest phrases first
        # (e.g. 'sudden severe headache' before 'headache')
        sorted_phrases = sorted(FIXTURE_SYMPTOM_MAP.keys(), key=len, reverse=True)

        for phrase in sorted_phrases:
            canonical_name = FIXTURE_SYMPTOM_MAP[phrase]
            pattern = rf"(?:\b|^){re.escape(phrase)}(?:\b|$)"
            match = re.search(pattern, cleaned)
            if match and canonical_name not in detected_canonical_names:
                start, end = match.span()

                # Check if this match is contained within an already accepted span
                if any(s <= start and end <= e for s, e in matched_spans):
                    continue

                # Exclude explicitly negated mentions (e.g. 'no fever', 'no cough')
                negation_pattern = (
                    r"\b(?:no|not|neither|nor|without|never|don't have|"
                    r"do not have|don't feel|dont have)\s+[^.?!,;]{0,40}\b"
                    rf"{re.escape(phrase)}\b"
                )
                if re.search(negation_pattern, cleaned):
                    continue

                matched_spans.append((start, end))
                detected_canonical_names.add(canonical_name)

                # Extract attribute heuristics
                duration = self._parse_duration(cleaned)
                onset = self._parse_onset(cleaned)
                severity = self._parse_severity(cleaned, phrase=phrase)
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

        # Multi-turn clarification reply resolution (FR-19, S2-NIT-1):
        # When conversation history is present, search backwards to find the
        # active target symptom queried by the assistant or discussed most recently.
        # Attribute standalone response properties (severity, duration, onset, site)
        # to that target symptom (even when new symptoms are also introduced).
        if conversation_history:
            history_lines = [
                line.strip()
                for line in conversation_history.strip().split("\n")
                if line.strip()
            ]
            target_canonical: str | None = None
            for line in reversed(history_lines):
                line_lower = line.lower()
                for phrase in sorted_phrases:
                    canon = FIXTURE_SYMPTOM_MAP[phrase]
                    if phrase in line_lower or canon.replace("_", " ") in line_lower:
                        target_canonical = canon
                        break
                if target_canonical:
                    break

            if target_canonical and target_canonical not in detected_canonical_names:
                reply_sev = self._parse_severity(cleaned)
                reply_dur = self._parse_duration(cleaned)
                reply_onset = self._parse_onset(cleaned)
                reply_site = self._parse_location(cleaned, target_canonical)
                if (
                    reply_sev != SeverityEnum.UNKNOWN
                    or reply_dur is not None
                    or reply_onset is not None
                    or reply_site is not None
                ):
                    extracted_symptoms.append(
                        ExtractedSymptom(
                            name=target_canonical,
                            severity=reply_sev,
                            duration=reply_dur,
                            onset=reply_onset,
                            body_site=reply_site,
                            body_location=reply_site,
                            confidence=0.95,
                        )
                    )
                    detected_canonical_names.add(target_canonical)

        # Missing-information detection engine integration
        requires_clarification, clarification_reason = should_request_clarification(
            extracted_symptoms
        )

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

        Enforces the max 3 question limit (FR-04, FR-19, FR-20) and prioritizes
        critical information gaps (safety-critical red flags, duration, severity, site).

        Args:
            structured_state: Dictionary of currently collected symptom state.
            already_asked: List of questions already posed to the patient.

        Returns:
            ClarificationResult with conversational question or should_ask=False.
        """
        # Enforce hard cap of 3 questions
        turn_count = len(already_asked)
        context_count = int(structured_state.get("clarification_count", 0))
        if max(turn_count, context_count) >= MAX_CLARIFICATION_QUESTIONS:
            return ClarificationResult(
                should_ask=False,
                question=None,
                question_type=None,
                target_symptom=None,
                missing_field=None,
            )

        symptoms = structured_state.get("symptoms", [])
        if not symptoms:
            return ClarificationResult(
                should_ask=True,
                question=(
                    "Could you describe in a bit more detail what symptoms you are"
                    " feeling?"
                ),
                question_type=QuestionTypeEnum.CONTEXT,
                target_symptom=None,
                missing_field=None,
            )

        # Detect and rank missing information gaps by clinical priority
        gaps = detect_missing_information(symptoms)
        if not gaps:
            return ClarificationResult(
                should_ask=False,
                question=None,
                question_type=None,
                target_symptom=None,
                missing_field=None,
            )

        def _normalize_q(q: str) -> str:
            return re.sub(r"[^\w\s]", "", q).lower().strip()

        normalized_asked = {_normalize_q(q) for q in already_asked if q}

        # Evaluate candidate questions for each detected gap
        for gap in gaps:
            display_name = gap.symptom_name.replace("_", " ")
            candidate_question: str
            q_type: QuestionTypeEnum

            if gap.missing_field == MissingFieldEnum.ONSET:
                candidate_question = (
                    f"Did the {display_name} come on suddenly, "
                    "or has it built up gradually?"
                )
                q_type = QuestionTypeEnum.ONSET
            elif gap.missing_field == MissingFieldEnum.SEVERITY:
                candidate_question = (
                    f"How severe would you describe the {display_name} right now "
                    "(for instance: mild, moderate, or severe)?"
                )
                q_type = QuestionTypeEnum.SEVERITY
            elif gap.missing_field == MissingFieldEnum.DURATION:
                candidate_question = (
                    f"About how long have you been experiencing the {display_name}?"
                )
                q_type = QuestionTypeEnum.DURATION
            elif gap.missing_field == MissingFieldEnum.BODY_SITE:
                candidate_question = (
                    f"Where specifically on your body are you experiencing "
                    f"the {display_name}?"
                )
                q_type = QuestionTypeEnum.LOCATION
            else:
                candidate_question = (
                    f"Could you share a few more details about the {display_name}?"
                )
                q_type = QuestionTypeEnum.CONTEXT

            # Skip if already asked (casing and punctuation insensitive)
            if _normalize_q(candidate_question) not in normalized_asked:
                return ClarificationResult(
                    should_ask=True,
                    question=candidate_question,
                    question_type=q_type,
                    target_symptom=gap.symptom_name,
                    missing_field=gap.missing_field,
                )

        # Fallback candidate: general associated symptoms inquiry if not asked yet
        assoc_question = (
            "Are you noticing any other symptoms, such as fever, dizziness, or"
            " shortness of breath?"
        )
        if _normalize_q(assoc_question) not in normalized_asked:
            return ClarificationResult(
                should_ask=True,
                question=assoc_question,
                question_type=QuestionTypeEnum.ASSOCIATED,
                target_symptom=None,
                missing_field=MissingFieldEnum.ASSOCIATED,
            )

        # All relevant questions have been asked; proceed to confirmation
        return ClarificationResult(
            should_ask=False,
            question=None,
            question_type=None,
            target_symptom=None,
            missing_field=None,
        )

    @staticmethod
    def _match_severity_terms(snippet: str) -> SeverityEnum:
        """Match severity keywords in a given text snippet."""
        severe_terms = [
            "severe",
            "terrible",
            "really bad",
            "worst",
            "unbearable",
            "extreme",
            "intense",
            "excruciating",
            "tez",
            "bahut tez",
            "bahut tezz",
            "bahut zyada",
            "very bad",
            "high fever",
        ]
        if any(w in snippet for w in severe_terms):
            return SeverityEnum.SEVERE
        if any(
            w in snippet
            for w in [
                "moderate",
                "pretty bad",
                "noticeable",
                "medium",
                "kafi",
                "average",
                "tolerable",
            ]
        ):
            return SeverityEnum.MODERATE
        if any(
            w in snippet
            for w in [
                "mild",
                "slight",
                "little bit",
                "minor",
                "thoda sa",
                "halka",
                "not bad",
                "not severe",
                "not too bad",
                "bearable",
                "low",
            ]
        ):
            return SeverityEnum.MILD
        return SeverityEnum.UNKNOWN

    def _parse_severity(self, text: str, phrase: str | None = None) -> SeverityEnum:
        """Heuristic severity parser from descriptive English and Hinglish text.

        Args:
            text: Lowercased user text.
            phrase: Optional specific matched symptom phrase to check proximity.

        Returns:
            Corresponding SeverityEnum member.
        """
        target_text = text
        if phrase and phrase in text:
            # Isolate the clause containing the symptom phrase to avoid attribute bleed
            clauses = re.split(r"[,;]|(?:\b(?:and|but|while|with|also)\b)", text)
            for clause in clauses:
                if phrase in clause:
                    target_text = clause
                    break

        matched = self._match_severity_terms(target_text)
        if matched != SeverityEnum.UNKNOWN:
            return matched

        # Fallback: if the isolated clause has no severity, check if the full message
        # mentions a severity for this symptom (e.g. 'headache started yesterday
        # and it is mild') provided no competing symptom phrase is present.
        competing = [p for p in FIXTURE_SYMPTOM_MAP if p in text and p != phrase]
        if not competing:
            return self._match_severity_terms(text)

        return SeverityEnum.UNKNOWN

    def _parse_duration(self, text: str) -> Duration | None:
        """Heuristic duration parser from natural phrasing.

        Args:
            text: Lowercased user text.

        Returns:
            Parsed Duration instance or None.
        """
        if (
            "since yesterday" in text
            or "from yesterday" in text
            or "started yesterday" in text
            or "yesterday" in text
            or "kal se" in text
            or "24 hours" in text
        ):
            return Duration(value=1.0, unit=DurationUnitEnum.DAY)
        if "for a couple days" in text or "couple of days" in text:
            return Duration(value=2.0, unit=DurationUnitEnum.DAY)
        if "for a week" in text or "one week" in text:
            return Duration(value=1.0, unit=DurationUnitEnum.WEEK)
        if (
            "all day" in text
            or "since morning" in text
            or "this morning" in text
            or "aaj subah se" in text
        ):
            return Duration(value=1.0, unit=DurationUnitEnum.DAY)

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
        if "suddenly" in text or "sudden" in text:
            return "sudden"
        if "gradually" in text or "gradual" in text:
            return "gradual"
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
        chest_related = {
            "chest_pain",
            "chest_tightness",
            "pressure_or_squeezing_in_chest",
        }
        if canonical_name in chest_related:
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
            "abdominal_cramping",
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

        if canonical_name in {"lower_back_pain", "back_pain"}:
            if "lower back" in text:
                return "lower back"
            if "back" in text:
                return "back"

        if canonical_name in {"joint_pain", "joint_swelling"}:
            joints = ["knee", "elbow", "wrist", "shoulder", "ankle", "hip", "finger"]
            for j in joints:
                if j in text:
                    return j

        if canonical_name in SITE_SENSITIVE_SYMPTOMS:
            locations = [
                "face",
                "forehead",
                "arm",
                "left arm",
                "right arm",
                "leg",
                "left leg",
                "right leg",
                "chest",
                "back",
                "neck",
                "abdomen",
                "stomach",
                "hands",
                "feet",
            ]
            for loc in locations:
                if loc in text:
                    return loc

        return None
