"""Unit tests for in-memory image validation and metadata sanitisation.

Responsibilities:
    - Test validation of allowed image formats (JPEG, PNG, WebP).
    - Test byte-size threshold enforcement (max 5 MB) and empty payload rejection.
    - Validate magic-byte inspection against mismatched or spoofed Content-Type headers.
    - Test complete purging of EXIF, GPS, and metadata tags (DR-06).
    - Test visual orientation normalization prior to metadata stripping.
    - Test pre-decode pixel count caps protecting against decompression bombs.

Owner: Vivek (tests) · Task: S1-VIV-4 · Requirements: idea §3, DR-06
"""

import io

from PIL import Image
import pytest

from app.services.upload.exceptions import (
    ImageTooLargeError,
    InvalidImageError,
    UnsupportedImageTypeError,
)
from app.services.upload.validator import (
    SanitizedImage,
    detect_mime_type,
    validate_and_sanitize_image,
)


def _make_synthetic_image_bytes(
    fmt: str = "PNG",
    size: tuple[int, int] = (30, 30),
    color: str = "blue",
    exif_dict: dict[int, object] | None = None,
) -> bytes:
    """Generate in-memory synthetic image bytes for testing."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    if exif_dict:
        exif = img.getexif()
        for k, v in exif_dict.items():
            exif[k] = v
        img.save(buf, format=fmt, exif=exif)
    else:
        img.save(buf, format=fmt)
    return buf.getvalue()


def test_valid_jpeg_png_webp_accepted() -> None:
    """Verify JPEG, PNG, and WebP images are accepted and sanitized."""
    formats = [
        ("JPEG", "image/jpeg"),
        ("PNG", "image/png"),
        ("WEBP", "image/webp"),
    ]
    for fmt, mime in formats:
        data = _make_synthetic_image_bytes(fmt=fmt, size=(40, 50))
        result = validate_and_sanitize_image(data, declared_content_type=mime)
        assert isinstance(result, SanitizedImage)
        assert result.content_type == mime
        assert result.width == 40
        assert result.height == 50
        assert len(result.data) > 0


def test_exact_max_upload_size_accepted() -> None:
    """Verify payload of exactly the maximum allowed byte size is accepted."""
    base_data = _make_synthetic_image_bytes("PNG", size=(10, 10))
    result = validate_and_sanitize_image(
        base_data,
        declared_content_type="image/png",
        max_upload_bytes=len(base_data),
    )
    assert result.width == 10


def test_oversize_payload_rejected() -> None:
    """Verify payload exceeding the maximum allowed size raises ImageTooLargeError."""
    data = _make_synthetic_image_bytes("PNG", size=(20, 20))
    with pytest.raises(ImageTooLargeError, match="Image size exceeds the maximum"):
        validate_and_sanitize_image(
            data,
            declared_content_type="image/png",
            max_upload_bytes=len(data) - 1,
        )


def test_empty_payload_rejected() -> None:
    """Verify empty image payload raises InvalidImageError."""
    with pytest.raises(InvalidImageError, match="Uploaded image file is empty"):
        validate_and_sanitize_image(b"", declared_content_type="image/png")


def test_disallowed_mime_type_rejected() -> None:
    """Verify unsupported formats such as GIF or SVG are rejected."""
    # GIF format
    gif_buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(gif_buf, format="GIF")
    gif_bytes = gif_buf.getvalue()

    with pytest.raises(UnsupportedImageTypeError, match="Unsupported image format"):
        validate_and_sanitize_image(gif_bytes, declared_content_type="image/gif")


def test_declared_mime_mismatch_magic_bytes_rejected() -> None:
    """Verify declared Content-Type differing from inspected magic bytes is rejected."""
    png_data = _make_synthetic_image_bytes("PNG")
    with pytest.raises(
        UnsupportedImageTypeError,
        match="Declared Content-Type does not match",
    ):
        validate_and_sanitize_image(png_data, declared_content_type="image/jpeg")


def test_non_image_disguised_as_jpg_rejected() -> None:
    """Verify text or random binary disguised as JPG is rejected."""
    fake_data = b"Hello, I am a plain text file pretending to be a JPG."
    with pytest.raises(UnsupportedImageTypeError, match="Unsupported image format"):
        validate_and_sanitize_image(fake_data, declared_content_type="image/jpeg")


def test_truncated_image_rejected() -> None:
    """Verify truncated or corrupted image data raises InvalidImageError."""
    valid_data = _make_synthetic_image_bytes("JPEG", size=(50, 50))
    # Cut off 90% of the payload leaving incomplete header
    truncated_data = valid_data[:30]
    with pytest.raises(InvalidImageError, match="Invalid or corrupted image data"):
        validate_and_sanitize_image(truncated_data, declared_content_type="image/jpeg")


def test_exif_metadata_and_gps_completely_stripped() -> None:
    """Verify all EXIF tags (UserComment, GPS) are purged in sanitized output."""
    # 0x9286: UserComment, 0x010E: ImageDescription
    exif_data = {
        0x9286: "Patient symptom description: confidential text",
        0x010E: "Camera serial 987654321 with GPS",
    }
    data = _make_synthetic_image_bytes("JPEG", size=(20, 20), exif_dict=exif_data)

    sanitized = validate_and_sanitize_image(data, declared_content_type="image/jpeg")
    # Verify confidential text is not in sanitized raw bytes
    assert b"confidential text" not in sanitized.data
    assert b"987654321" not in sanitized.data

    # Verify EXIF tags dictionary on resulting image is completely empty
    with Image.open(io.BytesIO(sanitized.data)) as clean_img:
        clean_exif = dict(clean_img.getexif())
        assert len(clean_exif) == 0


def test_exif_orientation_transposed_correctly() -> None:
    """Verify EXIF orientation (6: 90 CW) transposes dimensions and purges tag."""
    # Image size: width 20, height 40. Orientation 6 rotates 90 degrees CW -> (40, 20)
    data = _make_synthetic_image_bytes("JPEG", size=(20, 40), exif_dict={274: 6})

    sanitized = validate_and_sanitize_image(data, declared_content_type="image/jpeg")
    assert sanitized.width == 40
    assert sanitized.height == 20

    with Image.open(io.BytesIO(sanitized.data)) as clean_img:
        clean_exif = dict(clean_img.getexif())
        assert 274 not in clean_exif


def test_decompression_bomb_rejected_before_decode() -> None:
    """Verify image exceeding pixel resolution cap is rejected defensively."""
    # 50 x 50 = 2500 pixels. Set max_pixels to 2000
    data = _make_synthetic_image_bytes("PNG", size=(50, 50))
    with pytest.raises(InvalidImageError, match="resolution .* exceeds maximum"):
        validate_and_sanitize_image(
            data,
            declared_content_type="image/png",
            max_pixels=2000,
        )


def test_detect_mime_type_handles_short_data() -> None:
    """Verify detect_mime_type gracefully returns None for payloads < 12 bytes."""
    assert detect_mime_type(b"") is None
    assert detect_mime_type(b"\xff\xd8") is None
    assert detect_mime_type(b"short") is None
