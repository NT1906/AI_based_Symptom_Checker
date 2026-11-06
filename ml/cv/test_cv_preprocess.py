"""Unit tests for the shared Pillow preprocessing.

Covers:
    - Short-side resize keeps the aspect ratio; centre crop is exact.
    - EXIF orientation is applied and the image is converted to RGB.
    - A crop larger than the image is rejected.

Owner: Nisarg (cv) · Task: S1-NIS-6 · Requirements: NFR-07
"""

from pathlib import Path

import pytest
from cv_preprocess import center_crop, load_rgb, resize_short_side
from PIL import Image


def test_resize_short_side_keeps_aspect_ratio() -> None:
    assert resize_short_side(Image.new("RGB", (512, 384)), 256).size == (341, 256)
    assert resize_short_side(Image.new("RGB", (100, 300)), 256).size == (256, 768)


def test_center_crop_takes_the_middle() -> None:
    image = Image.new("RGB", (300, 224), "black")
    image.paste((255, 0, 0), (38, 0, 262, 224))

    cropped = center_crop(image, 224)

    assert cropped.size == (224, 224)
    assert cropped.getpixel((0, 0)) == (255, 0, 0)
    assert cropped.getpixel((223, 223)) == (255, 0, 0)


def test_center_crop_rejects_small_image() -> None:
    with pytest.raises(ValueError, match="smaller than the crop"):
        center_crop(Image.new("RGB", (200, 300)), 224)


def test_load_rgb_applies_exif_orientation(tmp_path: Path) -> None:
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 degrees clockwise when shown
    path = tmp_path / "photo.jpg"
    Image.new("L", (400, 200)).save(path, exif=exif)

    image = load_rgb(path)

    assert image.size == (200, 400)
    assert image.mode == "RGB"
