"""In-memory image validation and metadata sanitisation service.

Responsibilities:
    - Validate upload payload size (max 5 MB) in memory without disk persistence.
    - Verify MIME type against binary magic bytes (JPEG, PNG, WebP).
    - Protect against decompression bombs with pre-decode pixel count caps (16 MP).
    - Transpose EXIF orientation upright and strip all metadata (EXIF, GPS, comments).

Owner: Vivek (upload) · Task: S1-VIV-4 · Requirements: idea §3, DR-06
"""

from dataclasses import dataclass
import io

from PIL import Image, ImageOps, UnidentifiedImageError

from app.services.upload.exceptions import (
    ImageTooLargeError,
    InvalidImageError,
    UnsupportedImageTypeError,
)

# ---------------------------------------------------------------------------
# Upload Policy Constants
# ---------------------------------------------------------------------------

MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024  # 5 MB
MAX_PIXELS: int = 16_000_000  # 16 Megapixels (guards 512 MB memory footprint)
ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)

# Magic byte signatures
_JPEG_MAGIC: bytes = b"\xff\xd8\xff"
_PNG_MAGIC: bytes = b"\x89PNG\r\n\x1a\n"
_WEBP_RIFF_PREFIX: bytes = b"RIFF"
_WEBP_HEADER_MARKER: bytes = b"WEBP"


@dataclass(frozen=True)
class SanitizedImage:
    """In-memory representation of a validated and sanitized image.

    Attributes:
        data: Sanitized image bytes stripped of all metadata.
        content_type: Verified MIME type string.
        width: Visual width in pixels after orientation normalization.
        height: Visual height in pixels after orientation normalization.
    """

    data: bytes
    content_type: str
    width: int
    height: int


def detect_mime_type(data: bytes) -> str | None:
    """Detect image MIME type from binary magic bytes header.

    Args:
        data: Raw image payload bytes.

    Returns:
        MIME type string if recognized and supported, else None.
    """
    if len(data) < 12:
        return None
    if data.startswith(_JPEG_MAGIC):
        return "image/jpeg"
    if data.startswith(_PNG_MAGIC):
        return "image/png"
    if data.startswith(_WEBP_RIFF_PREFIX) and data[8:12] == _WEBP_HEADER_MARKER:
        return "image/webp"
    return None


def validate_and_sanitize_image(
    data: bytes,
    declared_content_type: str | None = None,
    max_upload_bytes: int = MAX_UPLOAD_BYTES,
    max_pixels: int = MAX_PIXELS,
) -> SanitizedImage:
    """Validate raw image bytes and strip all metadata in memory.

    Enforces DR-06 privacy requirements:
    1. Rejects payload exceeding max size or empty data.
    2. Inspects magic bytes and ensures declared MIME type matches.
    3. Defensively checks resolution before loading pixel data to prevent
       decompression bombs.
    4. Applies EXIF orientation then strips all metadata (GPS, EXIF, comments)
       by creating a fresh image from raw RGB pixels.

    Args:
        data: Raw image file bytes.
        declared_content_type: Optional client-declared Content-Type header.
        max_upload_bytes: Maximum allowed byte size (default: 5 MB).
        max_pixels: Maximum allowed pixel area (default: 16 MP).

    Returns:
        SanitizedImage: Validated image bytes with clean metadata.

    Raises:
        InvalidImageError: If data is empty, corrupted, animated, or exceeds pixel cap.
        ImageTooLargeError: If byte size exceeds maximum threshold.
        UnsupportedImageTypeError: If file format is not permitted or does not match
            declared type.
    """
    # 1. Byte length checks
    if not data:
        raise InvalidImageError("Uploaded image file is empty.")
    if len(data) > max_upload_bytes:
        limit_mb = max_upload_bytes // (1024 * 1024)
        raise ImageTooLargeError(
            f"Image size exceeds the maximum allowed limit of {limit_mb} MB."
        )

    # 2. Magic byte inspection
    detected_mime = detect_mime_type(data)
    if detected_mime is None:
        raise UnsupportedImageTypeError(
            "Unsupported image format. Allowed formats: JPEG, PNG, WebP."
        )

    if declared_content_type is not None:
        clean_declared = declared_content_type.lower().split(";")[0].strip()
        if clean_declared not in ALLOWED_MIME_TYPES or clean_declared != detected_mime:
            raise UnsupportedImageTypeError(
                "Declared Content-Type does not match inspected image format."
            )

    # 3. Defensive decode and decompression bomb guard
    try:
        raw_stream = io.BytesIO(data)
        with Image.open(raw_stream) as img:
            width, height = img.size

            # Check resolution before full decode
            if width * height > max_pixels:
                raise InvalidImageError(
                    f"Image resolution ({width}x{height}) exceeds maximum "
                    f"allowed limit of {max_pixels} pixels."
                )

            # Reject multi-frame or animated formats (e.g. animated WebP)
            if getattr(img, "is_animated", False) or getattr(img, "n_frames", 1) > 1:
                raise InvalidImageError(
                    "Animated or multi-frame images are not supported."
                )

            # 4. Correct visual orientation before dropping EXIF tags
            transposed = ImageOps.exif_transpose(img)
            active_img = transposed if transposed is not None else img
            final_width, final_height = active_img.size

            # Reconstruct fresh image from RGB pixels to purge all metadata
            # (DR-06: GPS coordinates, camera serials, timestamps, and comments)
            clean_img = Image.new("RGB", (final_width, final_height))
            clean_img.paste(active_img.convert("RGB"))

            out_stream = io.BytesIO()
            pil_format = (
                "PNG"
                if detected_mime == "image/png"
                else ("WEBP" if detected_mime == "image/webp" else "JPEG")
            )
            clean_img.save(out_stream, format=pil_format)
            sanitized_bytes = out_stream.getvalue()

            return SanitizedImage(
                data=sanitized_bytes,
                content_type=detected_mime,
                width=final_width,
                height=final_height,
            )

    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        if isinstance(
            exc, (InvalidImageError, ImageTooLargeError, UnsupportedImageTypeError)
        ):
            raise
        raise InvalidImageError("Invalid or corrupted image data.") from None
