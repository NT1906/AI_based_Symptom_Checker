# Upload Service (`app.services.upload`)

**Owner:** Vivek (upload) · **Task:** S1-VIV-4 · **Requirements:** idea §3, DR-06

## Purpose
Provides pure, in-memory validation, format verification, decompression bomb prevention, and metadata sanitisation for optional symptom photos uploaded during clinical triage intake.

## Medical Safety & Privacy Guarantees (DR-06)
- **Zero Disk Persistence:** Uploaded photos are verified and sanitised strictly in volatile memory. No temporary files, disk caches, database records, or object storage writes occur.
- **Complete Metadata Purge:** Visual orientation (EXIF orientation tag) is transposed, after which all EXIF, GPS location tags, camera serial numbers, XMP data, and comments are permanently stripped by reconstructing clean RGB pixel buffers.
- **Decompression Bomb Protection:** Dimensions are defensively inspected from image headers before loading full pixel buffers; images exceeding 16 megapixels are rejected immediately.
- **No Diagnostic Role:** The upload service performs pure input hygiene and never generates or returns medical interpretations or advice.

## Public Interface
```python
from app.services.upload import (
    validate_and_sanitize_image,
    SanitizedImage,
    ImageTooLargeError,
    UnsupportedImageTypeError,
    InvalidImageError,
    MAX_UPLOAD_BYTES,  # 5 MB (5,242,880 bytes)
    MAX_PIXELS,  # 16,000,000 pixels
    ALLOWED_MIME_TYPES,  # {"image/jpeg", "image/png", "image/webp"}
)

# Example usage:
clean_image: SanitizedImage = validate_and_sanitize_image(
    data=raw_bytes,
    declared_content_type="image/jpeg",
)
```

## How to Test
Run unit tests for the upload service package from `server/`:
```bash
pytest tests/unit/upload -v
```
