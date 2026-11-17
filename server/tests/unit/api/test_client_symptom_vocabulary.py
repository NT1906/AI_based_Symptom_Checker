"""The client's symptom picker must use the server's canonical symptom IDs.

Covers:
    - Every ``id`` in ``client/src/components/assessment/canonicalSymptoms.ts``
      resolves to itself in the knowledge vocabulary. A symptom the user adds
      from the picker is sent by ID; an unknown ID would silently drop out of
      the risk engine, so a red flag added there would never raise the risk.
    - The list covers the whole vocabulary, with no duplicates.

Owner: Nisarg (integration) · Task: S2-NIS-13 · Requirements: FR-03, FR-06
"""

import re
from pathlib import Path

from app.services.knowledge import get_normalizer

CLIENT_LIST = (
    Path(__file__).resolve().parents[4]
    / "client/src/components/assessment/canonicalSymptoms.ts"
)
ITEM = re.compile(r'\{ id: "([a-z0-9_]+)", name: "[^"]+", bodySystem: "[a-z_]+" \}')


def _client_ids() -> list[str]:
    return ITEM.findall(CLIENT_LIST.read_text(encoding="utf-8"))


def test_every_client_symptom_id_resolves_to_itself() -> None:
    normalizer = get_normalizer()

    unknown = [
        symptom_id
        for symptom_id in _client_ids()
        if (match := normalizer.normalize(symptom_id)) is None
        or match.canonical_id != symptom_id
    ]

    assert unknown == []


def test_client_list_covers_the_vocabulary_once() -> None:
    ids = _client_ids()

    assert len(ids) == len(set(ids))
    assert set(ids) == {symptom.id for symptom in get_normalizer().list_all()}
