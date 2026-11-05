"""Label and skin-tone mapping for the skin-image dataset.

Responsibilities:
    - Map each source's condition names to the model classes
      (docs/cv-plan.md §2, §4).
    - Decide a SCIN case's class from its top-weighted dermatologist label.
    - Turn Fitzpatrick skin types into the reporting groups from the config.

The mapping tables are reviewed in the dataset card (README.md §3); change
both together.

Owner: Nisarg (cv) · Task: S1-NIS-5 · Requirements: NFR-07
"""

import ast
import statistics
from collections.abc import Iterable, Mapping
from typing import NamedTuple

UNCLEAR = "unclear"
UNKNOWN_SKIN_TONE = "unknown"

# SCIN `weighted_skin_condition_label` names -> class. SCIN already merges
# synonyms ("Nummular eczema" -> "Eczema"), so exact names are enough.
SCIN_LABELS: Mapping[str, str] = {
    "Eczema": "eczema",
    "Tinea": "fungal_infection",
    "Urticaria": "urticaria",
    "Scabies": "scabies",
    "Acne": "acne",
    "Chicken pox exanthem": "chickenpox",
    "Cellulitis": "cellulitis",
    "Cellulitis of hand excluding finger": "cellulitis",
}

# Variants that look like a class but are a different condition or code
# (for example tinea versicolor is B36.0, not dermatophytosis B35). Cases led
# by them are left out: as `unclear` they would teach the model that a class
# look-alike is "not judgeable".
SCIN_LEFT_OUT: frozenset[str] = frozenset(
    {
        "Infected eczema",
        "Lichenified eczema",
        "Lichenified eczematous dermatitis",
        "Crusted eczematous dermatitis",
        "Acute constitutional eczema",
        "Acute-on-chronic dyshidrotic eczema of hands",
        "Tinea Versicolor",
        "Candida",
        "Candida infection of flexural skin",
        "Candida intertrigo",
        "Candidal intertrigo",
        "Deep fungal infection",
        "deep fungal infection",
        "Fungal dermatitis",
        "Fungal dermatosis",
        "Urticarial vasculitis",
        "Pruritic urticarial papules and plaques of pregnancy",
        "Acne keloidalis",
        "Acne urticata",
        "Acneiform eruption",
        "Erysipelas",
    }
)

# Fitzpatrick17k `label` values -> class. Fitzpatrick17k only supplements the
# classes; `unclear` comes from SCIN (dataset card §2).
FITZPATRICK17K_LABELS: Mapping[str, str] = {
    "eczema": "eczema",
    "urticaria": "urticaria",
    "scabies": "scabies",
    "acne": "acne",
    "acne vulgaris": "acne",
}
FITZPATRICK17K_WRONG_LABEL = "3 Wrongly labelled"


class LabelDecision(NamedTuple):
    """Outcome of mapping one source label.

    Attributes:
        label: Model class, or ``None`` when the image is left out.
        reason: Why, for the dataset summary.
    """

    label: str | None
    reason: str


def scin_case_label(weighted_label: str) -> LabelDecision:
    """Pick the class for a SCIN case from ``weighted_skin_condition_label``.

    A case gets a class only when that class is its top-weighted label. A case
    with no label (not gradable) or a top label outside the classes becomes
    ``unclear``. A tie between labels that lead to different outcomes, or a
    class look-alike, is left out.

    Args:
        weighted_label: The raw column value, e.g. ``"{'Eczema': 0.69}"``.

    Returns:
        The decision.

    Raises:
        TypeError: If the value is not a dict literal of name -> weight.
        ValueError: If the value is not a Python literal at all.

    Example:
        >>> scin_case_label("{'Eczema': 0.6, 'Psoriasis': 0.4}")
        LabelDecision(label='eczema', reason='top_label')
    """
    top = scin_top_labels(weighted_label)
    if not top:
        return LabelDecision(UNCLEAR, "no_label")
    outcomes = {_scin_outcome(name) for name in top}
    if len(outcomes) > 1:
        return LabelDecision(None, "tied_top_labels")
    return outcomes.pop()


def scin_top_labels(weighted_label: str) -> tuple[str, ...]:
    """Names sharing the highest weight in ``weighted_skin_condition_label``.

    Args:
        weighted_label: The raw column value; empty when the case was not
            gradable.

    Returns:
        The top names, sorted; empty when there is no label.

    Raises:
        TypeError: If the value is not a dict literal of name -> weight.
        ValueError: If the value is not a Python literal at all.
    """
    if not weighted_label.strip():
        return ()
    try:
        weights = ast.literal_eval(weighted_label)
    except SyntaxError as exc:
        raise ValueError(f"unreadable weighted label: {weighted_label!r}") from exc
    if not isinstance(weights, dict):
        raise TypeError(f"not a weighted label: {weighted_label!r}")
    if not weights:
        return ()
    top_weight = max(weights.values())
    return tuple(sorted(name for name, w in weights.items() if w == top_weight))


def _scin_outcome(name: str) -> LabelDecision:
    """Decision for a single SCIN condition name."""
    if name in SCIN_LABELS:
        return LabelDecision(SCIN_LABELS[name], "top_label")
    if name in SCIN_LEFT_OUT:
        return LabelDecision(None, "class_look_alike")
    return LabelDecision(UNCLEAR, "outside_classes")


def fitzpatrick17k_label(label: str, qc: str) -> LabelDecision:
    """Pick the class for a Fitzpatrick17k image.

    Args:
        label: The ``label`` column.
        qc: The ``qc`` column; images reviewed as wrongly labelled are left out.

    Returns:
        The decision; labels outside the mapping are left out, not ``unclear``.
    """
    if qc.strip() == FITZPATRICK17K_WRONG_LABEL:
        return LabelDecision(None, "wrongly_labelled")
    mapped = FITZPATRICK17K_LABELS.get(label.strip())
    if mapped is None:
        return LabelDecision(None, "not_used")
    return LabelDecision(mapped, "mapped_label")


def parse_fitzpatrick_type(value: str) -> int | None:
    """Read a Fitzpatrick type from ``"FST3"`` (SCIN) or ``"3"`` (Fitzpatrick17k).

    Args:
        value: The raw value.

    Returns:
        The type 1-6, or ``None`` when missing or unknown (``-1``, ``NONE_...``).
    """
    text = value.strip().upper().removeprefix("FST")
    if not text.isdigit():
        return None
    number = int(text)
    return number if 1 <= number <= 6 else None


def skin_tone_group(types: Iterable[int], groups: Mapping[str, tuple[int, ...]]) -> str:
    """Group the Fitzpatrick types estimated for one image or case.

    Args:
        types: Every estimate available (SCIN has up to 3 dermatologists).
        groups: Group name -> Fitzpatrick types, from the config.

    Returns:
        The group of the lower median estimate, or ``unknown`` if none.

    Example:
        >>> skin_tone_group([2, 3, 5], {"light": (1, 2), "medium": (3, 4)})
        'medium'
    """
    estimates = sorted(types)
    if not estimates:
        return UNKNOWN_SKIN_TONE
    # Why: the lower median is always a real estimate, and with two
    # dermatologists who disagree it picks the lighter one consistently.
    middle = statistics.median_low(estimates)
    for name, members in groups.items():
        if middle in members:
            return name
    return UNKNOWN_SKIN_TONE
