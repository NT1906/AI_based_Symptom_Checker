"""Unit tests for image cleaning, using tiny generated images.

Covers:
    - Missing, undecodable and too-small images are dropped with a reason.
    - A near-duplicate across splits keeps the test copy, so test never leaks
      into training; duplicates with conflicting labels are all dropped.
    - Different images are never merged; the report applies the class-size rule.

Owner: Nisarg (cv) · Task: S1-NIS-5 · Requirements: NFR-07
"""

from pathlib import Path

from clean_images import MIN_SIDE_PX, clean, dhash, duplicate_sets
from PIL import Image


def _gradient(width: int = 200, height: int = 160, flip: bool = False) -> Image.Image:
    image = Image.new("RGB", (width, height))
    for x in range(width):
        for y in range(height):
            value = (x * 255 // width + y * 64 // height) % 256
            image.putpixel((width - 1 - x if flip else x, y), (value, 100, 255 - value))
    return image


def _row(
    image_id: str, split: str, label: str = "acne", source: str = "scin"
) -> dict[str, str]:
    return {
        "image_id": image_id,
        "source": source,
        "split": split,
        "label": label,
        "skin_tone": "light",
        "url": f"https://x/{image_id}.png",
    }


def _save(root: Path, image_id: str, image: Image.Image, source: str = "scin") -> None:
    path = root / source / f"{image_id}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def test_dhash_is_stable_under_resize_and_differs_for_other_images() -> None:
    base = _gradient()

    assert dhash(base) == dhash(base.resize((400, 320)))
    assert dhash(base) != dhash(_gradient(flip=True))


def test_drops_missing_undecodable_and_small_images(tmp_path: Path) -> None:
    _save(tmp_path, "ok", _gradient())
    _save(tmp_path, "small", _gradient(MIN_SIDE_PX - 1, 300))
    (tmp_path / "scin" / "broken.png").write_bytes(b"not an image")
    rows = [
        _row("ok", "train"),
        _row("small", "train"),
        _row("broken", "train"),
        _row("gone", "train"),
    ]

    kept, report = clean(rows, tmp_path, min_train=1, min_test=0)

    assert [r["image_id"] for r in kept] == ["ok"]
    assert report["dropped"] == {
        "scin:missing": 1,
        "scin:too_small": 1,
        "scin:undecodable": 1,
    }


def test_duplicate_across_splits_keeps_the_test_copy(tmp_path: Path) -> None:
    _save(tmp_path, "train_copy", _gradient())
    _save(
        tmp_path, "test_copy", _gradient().resize((300, 240)), source="fitzpatrick17k"
    )
    rows = [
        _row("train_copy", "train"),
        _row("test_copy", "test", source="fitzpatrick17k"),
    ]

    kept, report = clean(rows, tmp_path, min_train=1, min_test=1)

    assert [r["image_id"] for r in kept] == ["test_copy"]
    assert report["dropped"] == {"scin:duplicate": 1}


def test_duplicates_with_conflicting_labels_are_all_dropped(tmp_path: Path) -> None:
    _save(tmp_path, "a", _gradient())
    _save(tmp_path, "b", _gradient())
    rows = [_row("a", "train", "acne"), _row("b", "train", "eczema")]

    kept, report = clean(rows, tmp_path, min_train=1, min_test=0)

    assert kept == []
    assert report["dropped"] == {"scin:duplicate_conflicting_labels": 2}


def test_different_images_are_not_merged() -> None:
    hashes = {"a": dhash(_gradient()), "b": dhash(_gradient(flip=True))}

    assert duplicate_sets(hashes) == []


def test_duplicate_sets_find_close_hashes_only() -> None:
    hashes = {"a": 0b1111, "b": 0b0111, "c": 0xFFFF_0000_FFFF_0000}

    assert duplicate_sets(hashes) == [["a", "b"]]


def test_report_applies_class_size_rule(tmp_path: Path) -> None:
    _save(tmp_path, "t1", _gradient())
    _save(tmp_path, "t2", _gradient(flip=True))
    rows = [_row("t1", "train"), _row("t2", "test")]

    _, report = clean(rows, tmp_path, min_train=2, min_test=1)

    assert report["class_size_check"] == {
        "acne": {"train": 1, "test": 1, "meets_minimum": False}
    }
