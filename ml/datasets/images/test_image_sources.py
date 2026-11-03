"""Unit tests for reading SCIN and Fitzpatrick17k metadata into records.

Covers:
    - A SCIN case becomes one record per image, sharing its group, class and
      skin tone; left-out cases are counted per image.
    - Images reused across SCIN cases are left out.
    - A SCIN case without a labels row is an error.
    - Fitzpatrick17k rows: mapped, unused, missing URL, unknown skin type.

Owner: Nisarg (cv) · Task: S1-NIS-5 · Requirements: NFR-07
"""

import pytest
from image_sources import SCIN_BUCKET_URL, read_fitzpatrick17k, read_scin

GROUPS = {"light": (1, 2), "medium": (3, 4), "dark": (5, 6)}


def _case(case_id: str, *paths: str) -> dict[str, str]:
    padded = [*paths, "", "", ""][:3]
    return {
        "case_id": case_id,
        **{f"image_{i}_path": p for i, p in enumerate(padded, 1)},
    }


def _labels(case_id: str, weighted: str, *skin_types: str) -> dict[str, str]:
    padded = [*skin_types, "", "", ""][:3]
    row = {"case_id": case_id, "weighted_skin_condition_label": weighted}
    row.update(
        {
            f"dermatologist_fitzpatrick_skin_type_label_{i}": t
            for i, t in enumerate(padded, 1)
        }
    )
    return row


def test_scin_case_becomes_one_record_per_image() -> None:
    cases = [_case("c1", "dataset/images/1.png", "dataset/images/2.png")]
    labels = [_labels("c1", "{'Eczema': 0.8, 'Psoriasis': 0.2}", "FST5", "FST6")]

    records, left_out = read_scin(cases, labels, GROUPS)

    assert [r.image_id for r in records] == ["1", "2"]
    assert {r.group_id for r in records} == {"scin:c1"}
    assert {r.label for r in records} == {"eczema"}
    assert {r.skin_tone for r in records} == {"dark"}
    assert records[0].url == f"{SCIN_BUCKET_URL}/dataset/images/1.png"
    assert records[0].source_label == "Eczema"
    assert not left_out


def test_scin_ungradable_case_is_unclear_with_unknown_tone() -> None:
    records, _ = read_scin(
        [_case("c1", "dataset/images/1.png")], [_labels("c1", "")], GROUPS
    )

    assert records[0].label == "unclear"
    assert records[0].reason == "no_label"
    assert records[0].skin_tone == "unknown"


def test_scin_left_out_case_is_counted_per_image() -> None:
    cases = [_case("c1", "dataset/images/1.png", "dataset/images/2.png")]
    labels = [_labels("c1", "{'Eczema': 0.5, 'Psoriasis': 0.5}")]

    records, left_out = read_scin(cases, labels, GROUPS)

    assert records == []
    assert left_out == {"scin:tied_top_labels": 2}


def test_scin_image_shared_between_cases_is_left_out() -> None:
    cases = [
        _case("c1", "dataset/images/shared.png", "dataset/images/1.png"),
        _case("c2", "dataset/images/shared.png"),
    ]
    labels = [_labels("c1", "{'Acne': 1.0}"), _labels("c2", "{'Eczema': 1.0}")]

    records, left_out = read_scin(cases, labels, GROUPS)

    assert [r.image_id for r in records] == ["1"]
    assert left_out["scin:shared_between_cases"] == 2


def test_scin_case_without_labels_row_is_an_error() -> None:
    with pytest.raises(ValueError, match="no labels row"):
        read_scin([_case("c1", "dataset/images/1.png")], [], GROUPS)


def _fitz(
    md5: str, label: str, scale: str = "3", url: str = "https://a/x.jpg", qc: str = ""
) -> dict[str, str]:
    return {
        "md5hash": md5,
        "label": label,
        "fitzpatrick_scale": scale,
        "url": url,
        "qc": qc,
    }


def test_fitzpatrick17k_rows_map_to_records() -> None:
    rows = [
        _fitz("m1", "scabies", "6"),
        _fitz("m2", "psoriasis"),
        _fitz("m3", "acne", url=" "),
        _fitz("m4", "urticaria", "-1"),
    ]

    records, left_out = read_fitzpatrick17k(rows, GROUPS)

    assert [(r.image_id, r.label, r.skin_tone) for r in records] == [
        ("m1", "scabies", "dark"),
        ("m4", "urticaria", "unknown"),
    ]
    assert records[0].group_id == "fitzpatrick17k:m1"
    assert left_out == {"fitzpatrick17k:not_used": 1, "fitzpatrick17k:no_url": 1}
