"""Contributing-factor explanations: "Because you reported X and Y" per condition.

Responsibilities:
    - Turn a prediction's matched symptoms (heaviest first) into one
      plain-language sentence for the result's "Why:" line (FR-24).
    - Use the symptom display names from the knowledge service, so the user
      sees "joint pain", never ``joint_pain``.
    - List at most ``MAX_LISTED`` symptoms and count the rest, so the line
      stays short on a phone.

Only reported symptoms are named; the sentence never says what the condition
is or that the user has it (AI_RULES.md §2.1).

Owner: Nisarg (prediction) · Task: S2-NIS-2 · Requirements: FR-24, DR-05
"""

from collections.abc import Callable, Sequence

from app.services.knowledge import get_normalizer
from app.services.prediction import result_text as text
from app.services.prediction.schemas import ConditionPrediction

MAX_LISTED = 3

SymptomNamer = Callable[[str], str | None]
"""Returns a symptom's display name, or ``None`` if the ID is unknown."""


def knowledge_symptom_name(symptom_id: str) -> str | None:
    """Display name of a canonical symptom from the knowledge service.

    Args:
        symptom_id: Canonical symptom ID, e.g. ``joint_pain``.

    Returns:
        The display name, e.g. ``Joint pain``, or ``None`` if unknown.
    """
    symptom = get_normalizer().get_by_id(symptom_id)
    return symptom.name if symptom else None


def join_names(names: Sequence[str]) -> str:
    """Join names as "a", "a and b" or "a, b and c".

    Args:
        names: At least one name, in display order.

    Returns:
        The names in one phrase.

    Raises:
        ValueError: If ``names`` is empty.

    Example:
        >>> join_names(["fever", "headache", "joint pain"])
        'fever, headache and joint pain'
    """
    if not names:
        raise ValueError("at least one name is required")
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} and {names[-1]}"


class ConditionExplainer:
    """Builds the "Because you reported …" line for each predicted condition."""

    def __init__(self, symptom_name: SymptomNamer = knowledge_symptom_name) -> None:
        """Create the explainer.

        Args:
            symptom_name: Display-name lookup; defaults to the knowledge
                service. Replaceable in tests.
        """
        self._symptom_name = symptom_name

    def explain(self, prediction: ConditionPrediction) -> str:
        """Explain which reported symptoms point to one condition.

        Args:
            prediction: A ranked condition; its ``matched_symptom_ids`` are
                the reported symptoms it explains, heaviest first.

        Returns:
            One sentence, e.g. "Because you reported fever, joint pain and
            pain behind the eyes." More than ``MAX_LISTED`` symptoms end
            with "and 2 other symptoms".
        """
        ids = prediction.matched_symptom_ids
        names = [self._display(symptom_id) for symptom_id in ids[:MAX_LISTED]]
        extra = len(ids) - MAX_LISTED
        if extra > 0:
            names.append(text.other_symptoms(extra))
        return text.WHY_TEMPLATE.format(symptoms=join_names(names))

    def _display(self, symptom_id: str) -> str:
        """In-sentence name; falls back to the ID with spaces if unknown."""
        name = self._symptom_name(symptom_id) or symptom_id.replace("_", " ")
        return text.lower_first(name)
