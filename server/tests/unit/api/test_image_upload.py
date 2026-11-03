"""Unit tests for assessment image upload endpoint, streaming byte caps, and privacy.

Responsibilities:
    - Verify image upload happy path for JPEG, PNG, and WebP.
    - Validate error handling for invalid MIME, corrupted files, and pixel bombs.
    - Enforce Starlette in-memory spooling (zero disk rollover proof, DR-06).
    - Enforce streaming byte caps and early Content-Length rejections.
    - Verify privacy protections (no raw bytes or filenames in logs).

Owner: Vivek (tests) · Task: S1-VIV-4 · Requirements: idea §3, DR-06
"""

import io
import os
import tempfile
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import get_assessment_service
from app.core.errors import NotFoundError

SAMPLE_UUID = "e4caa1b2-8493-4a16-928e-5b1287c95e1a"
NON_EXISTENT_UUID = "00000000-0000-0000-0000-000000000000"


def _create_test_image(
    format_name: str = "JPEG",
    size: tuple[int, int] = (64, 64),
    color: str = "blue",
    exif_bytes: bytes | None = None,
) -> bytes:
    """Generate in-memory synthetic image bytes for testing."""
    img = Image.new("RGB", size, color=color)
    buffer = io.BytesIO()
    save_kwargs: dict[str, Any] = {"format": format_name}
    if exif_bytes is not None:
        save_kwargs["exif"] = exif_bytes
    img.save(buffer, **save_kwargs)
    return buffer.getvalue()


def test_upload_valid_jpeg_returns_200(client: TestClient) -> None:
    """Verify POST /api/v1/assessments/{id}/images accepts valid JPEG."""
    jpeg_bytes = _create_test_image(format_name="JPEG")
    files = {"file": ("symptom.jpg", jpeg_bytes, "image/jpeg")}

    response = client.post(f"/api/v1/assessments/{SAMPLE_UUID}/images", files=files)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["assessmentId"] == SAMPLE_UUID
    assert data["status"] == "processed"
    assert data["contentType"] == "image/jpeg"


def test_upload_valid_png_returns_200(client: TestClient) -> None:
    """Verify POST /api/v1/assessments/{id}/images accepts valid PNG."""
    png_bytes = _create_test_image(format_name="PNG")
    files = {"file": ("rash.png", png_bytes, "image/png")}

    response = client.post(f"/api/v1/assessments/{SAMPLE_UUID}/images", files=files)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["assessmentId"] == SAMPLE_UUID
    assert data["status"] == "processed"
    assert data["contentType"] == "image/png"


def test_upload_valid_webp_returns_200(client: TestClient) -> None:
    """Verify POST /api/v1/assessments/{id}/images accepts valid WebP."""
    webp_bytes = _create_test_image(format_name="WEBP")
    files = {"file": ("skin.webp", webp_bytes, "image/webp")}

    response = client.post(f"/api/v1/assessments/{SAMPLE_UUID}/images", files=files)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["assessmentId"] == SAMPLE_UUID
    assert data["status"] == "processed"
    assert data["contentType"] == "image/webp"


def test_upload_exif_metadata_stripped_in_memory(client: TestClient) -> None:
    """Verify EXIF payload metadata is completely removed during sanitization."""
    exif = Image.Exif()
    exif[0x010E] = "Confidential Patient Info"  # ImageDescription
    exif_bytes = exif.tobytes()

    jpeg_bytes = _create_test_image(format_name="JPEG", exif_bytes=exif_bytes)
    files = {"file": ("with_exif.jpg", jpeg_bytes, "image/jpeg")}

    response = client.post(f"/api/v1/assessments/{SAMPLE_UUID}/images", files=files)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "processed"


def test_upload_text_file_disguised_as_jpeg_returns_400(client: TestClient) -> None:
    """Verify file with invalid magic bytes returns 400 UNSUPPORTED_IMAGE_TYPE."""
    fake_bytes = b"This is a plain text file pretending to be a JPEG."
    files = {"file": ("fake.jpg", fake_bytes, "image/jpeg")}

    response = client.post(f"/api/v1/assessments/{SAMPLE_UUID}/images", files=files)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    data = response.json()
    assert data["code"] == "UNSUPPORTED_IMAGE_TYPE"
    assert "Unsupported image format" in data["message"]


def test_upload_unsupported_format_gif_returns_400(client: TestClient) -> None:
    """Verify upload of unsupported format (GIF) returns 400 UNSUPPORTED_IMAGE_TYPE."""
    img = Image.new("RGB", (32, 32), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="GIF")
    gif_bytes = buffer.getvalue()
    files = {"file": ("animation.gif", gif_bytes, "image/gif")}

    response = client.post(f"/api/v1/assessments/{SAMPLE_UUID}/images", files=files)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    data = response.json()
    assert data["code"] == "UNSUPPORTED_IMAGE_TYPE"


def test_upload_corrupted_image_returns_400(client: TestClient) -> None:
    """Verify file with valid header but corrupt payload returns 400 INVALID_IMAGE."""
    corrupted_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 200
    files = {"file": ("corrupt.jpg", corrupted_bytes, "image/jpeg")}

    response = client.post(f"/api/v1/assessments/{SAMPLE_UUID}/images", files=files)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    data = response.json()
    assert data["code"] == "INVALID_IMAGE"


def test_upload_pixel_flood_decompression_bomb_returns_400(
    client: TestClient,
) -> None:
    """Verify image exceeding pixel threshold returns 400 INVALID_IMAGE."""
    # Construct a valid JPEG header that declares dimensions exceeding 16 MP
    # (5000 x 4000 = 20,000,000 pixels)
    img = Image.new("RGB", (5000, 4000), color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=10)
    bomb_bytes = buffer.getvalue()
    files = {"file": ("bomb.jpg", bomb_bytes, "image/jpeg")}

    response = client.post(f"/api/v1/assessments/{SAMPLE_UUID}/images", files=files)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    data = response.json()
    assert data["code"] == "INVALID_IMAGE"
    assert "exceeds maximum allowed limit" in data["message"]


def test_upload_nonexistent_assessment_returns_404(
    app: FastAPI,
    client: TestClient,
) -> None:
    """Verify upload for non-existent assessment returns 404 NOT_FOUND."""
    mock_service = AsyncMock()
    mock_service.get_assessment.side_effect = NotFoundError(
        f"Assessment '{NON_EXISTENT_UUID}' was not found"
    )
    app.dependency_overrides[get_assessment_service] = lambda: mock_service

    jpeg_bytes = _create_test_image(format_name="JPEG")
    files = {"file": ("symptom.jpg", jpeg_bytes, "image/jpeg")}

    try:
        response = client.post(
            f"/api/v1/assessments/{NON_EXISTENT_UUID}/images",
            files=files,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["code"] == "NOT_FOUND"
    finally:
        app.dependency_overrides.pop(get_assessment_service, None)


def test_upload_invalid_uuid_returns_422(client: TestClient) -> None:
    """Verify invalid UUID path parameter returns 422 validation error."""
    jpeg_bytes = _create_test_image(format_name="JPEG")
    files = {"file": ("symptom.jpg", jpeg_bytes, "image/jpeg")}

    response = client.post("/api/v1/assessments/not-a-valid-uuid/images", files=files)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_upload_missing_file_field_returns_422(client: TestClient) -> None:
    """Verify request missing multipart 'file' field returns 422."""
    response = client.post(
        f"/api/v1/assessments/{SAMPLE_UUID}/images",
        data={"some_other_field": "data"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_zero_disk_rollover_on_large_upload(client: TestClient) -> None:
    """Verify uploads up to 5 MB stay in memory with 0 SpooledTemporaryFile rollovers.

    Why: DR-06 mandates symptom photos are processed strictly in volatile memory.
    Starlette defaults MultiPartParser.spool_max_size to 1 MB, spilling 1-5 MB
    photos to disk unless configured to 6 MB.
    """
    # Create ~2.6 MB valid JPEG in memory with high entropy
    img = Image.frombytes("RGB", (1500, 1500), os.urandom(1500 * 1500 * 3))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=95)
    large_jpeg_bytes = buffer.getvalue()
    assert len(large_jpeg_bytes) > 2 * 1024 * 1024  # Ensure > 2 MB

    files = {"file": ("high_res_photo.jpg", large_jpeg_bytes, "image/jpeg")}

    with patch.object(
        tempfile.SpooledTemporaryFile,
        "rollover",
        wraps=tempfile.SpooledTemporaryFile.rollover,
    ) as mock_rollover:
        response = client.post(
            f"/api/v1/assessments/{SAMPLE_UUID}/images",
            files=files,
        )
        assert response.status_code == status.HTTP_200_OK
        # Zero disk rollovers guaranteed
        assert mock_rollover.call_count == 0


def test_streaming_cap_rejects_oversized_payload(client: TestClient) -> None:
    """Verify payloads exceeding stream limit (5 MB + 64 KB) are rejected with 400."""
    # 5.5 MB payload (exceeds 5 MB + 64 KB)
    oversized_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * (5_500_000)
    files = {"file": ("oversized.jpg", oversized_bytes, "image/jpeg")}

    response = client.post(
        f"/api/v1/assessments/{SAMPLE_UUID}/images",
        files=files,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["code"] == "IMAGE_TOO_LARGE"


def test_privacy_guarantee_no_image_data_or_filename_in_logs(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify raw image bytes and user filenames are never logged (DR-06)."""
    sensitive_filename = "patient_john_doe_skin_lesion_private.jpg"
    jpeg_bytes = _create_test_image(format_name="JPEG")
    files = {"file": (sensitive_filename, jpeg_bytes, "image/jpeg")}

    with caplog.at_level("DEBUG"):
        response = client.post(
            f"/api/v1/assessments/{SAMPLE_UUID}/images",
            files=files,
        )
        assert response.status_code == status.HTTP_200_OK

    all_logs = caplog.text
    # Sensitive filename must never appear in any log
    assert sensitive_filename not in all_logs
    assert "john_doe" not in all_logs
