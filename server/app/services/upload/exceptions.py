"""Domain exceptions for upload processing and validation.

Responsibilities:
    - Define upload-specific error types inheriting from AppError.
    - Provide distinct machine-readable error codes and safe error messages.

Owner: Vivek (upload) · Task: S1-VIV-4 · Requirements: idea §3, DR-06
"""

from typing import Any

from fastapi import status

from app.core.errors import AppError


class UploadError(AppError):
    """Base exception for all upload validation and processing failures."""

    def __init__(
        self,
        message: str,
        code: str = "UPLOAD_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any | None = None,
    ) -> None:
        """Initialize upload error with HTTP 400 default status code."""
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class ImageTooLargeError(UploadError):
    """Raised when uploaded image size exceeds the allowed threshold."""

    def __init__(
        self,
        message: str = "Image size exceeds the maximum allowed limit of 5 MB.",
        details: Any | None = None,
    ) -> None:
        """Initialize with code IMAGE_TOO_LARGE."""
        super().__init__(
            message=message,
            code="IMAGE_TOO_LARGE",
            details=details,
        )


class UnsupportedImageTypeError(UploadError):
    """Raised when image format is not permitted or magic bytes mismatch."""

    def __init__(
        self,
        message: str = "Unsupported image format. Allowed formats: JPEG, PNG, WebP.",
        details: Any | None = None,
    ) -> None:
        """Initialize with code UNSUPPORTED_IMAGE_TYPE."""
        super().__init__(
            message=message,
            code="UNSUPPORTED_IMAGE_TYPE",
            details=details,
        )


class InvalidImageError(UploadError):
    """Raised when image is corrupt, empty, animated, or exceeds pixel limits."""

    def __init__(
        self,
        message: str = "Invalid or corrupted image data.",
        details: Any | None = None,
    ) -> None:
        """Initialize with code INVALID_IMAGE."""
        super().__init__(
            message=message,
            code="INVALID_IMAGE",
            details=details,
        )
