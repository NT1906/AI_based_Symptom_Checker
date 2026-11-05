"""Upload service package: in-memory image validation and sanitisation.

Responsibilities:
    - Export validation entry points for assessment image uploads.
    - Export domain exceptions for image upload validation.
    - Export policy constants (max size, allowed MIME types, pixel cap).

Owner: Vivek (upload) · Task: S1-VIV-4 · Requirements: idea §3, DR-06
"""

from app.services.upload.exceptions import (
    ImageTooLargeError,
    InvalidImageError,
    UnsupportedImageTypeError,
    UploadError,
)
from app.services.upload.validator import (
    ALLOWED_MIME_TYPES,
    MAX_PIXELS,
    MAX_UPLOAD_BYTES,
    SanitizedImage,
    detect_mime_type,
    validate_and_sanitize_image,
)

__all__ = [
    "ALLOWED_MIME_TYPES",
    "MAX_PIXELS",
    "MAX_UPLOAD_BYTES",
    "ImageTooLargeError",
    "InvalidImageError",
    "SanitizedImage",
    "UnsupportedImageTypeError",
    "UploadError",
    "detect_mime_type",
    "validate_and_sanitize_image",
]
