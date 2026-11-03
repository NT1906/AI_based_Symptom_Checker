"""Image preprocessing shared by training and (later) the server.

Responsibilities:
    - Load a photo the same way everywhere: EXIF orientation fixed, RGB.
    - Resize the short side and centre-crop with Pillow only, so the server's
      ``OnnxImageAnalyzer`` (S2-NIS-6) can copy these steps exactly and a
      parity test can compare tensors (docs/cv-plan.md §7).

Owner: Nisarg (cv) · Task: S1-NIS-6 · Requirements: NFR-07
"""

from pathlib import Path

from PIL import Image, ImageOps

RESAMPLE = Image.Resampling.BILINEAR


def load_rgb(path: Path) -> Image.Image:
    """Open an image with its EXIF orientation applied, as RGB.

    Args:
        path: Image file.

    Returns:
        The decoded image (fully loaded, file closed).
    """
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        image.load()
    return image


def resize_short_side(image: Image.Image, size: int) -> Image.Image:
    """Resize so the shorter side is ``size``, keeping the aspect ratio.

    Example:
        >>> resize_short_side(Image.new("RGB", (400, 200)), 100).size
        (200, 100)
    """
    width, height = image.size
    scale = size / min(width, height)
    target = (max(size, round(width * scale)), max(size, round(height * scale)))
    return image.resize(target, RESAMPLE)


def center_crop(image: Image.Image, size: int) -> Image.Image:
    """Crop a ``size`` x ``size`` square from the centre.

    Raises:
        ValueError: If the image is smaller than ``size`` on either side.

    Example:
        >>> center_crop(Image.new("RGB", (300, 256)), 224).size
        (224, 224)
    """
    width, height = image.size
    if min(width, height) < size:
        raise ValueError(f"image {image.size} is smaller than the crop {size}")
    left = (width - size) // 2
    top = (height - size) // 2
    return image.crop((left, top, left + size, top + size))
