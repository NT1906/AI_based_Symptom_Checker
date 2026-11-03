"""Upload streaming byte caps, Starlette spool configuration, and custom route handlers.

Responsibilities:
    - Configure process-wide Starlette MultiPartParser spool threshold (6 MB).
    - Enforce route-level streaming byte cap (5 MB + 64 KB overhead) in volatile memory.
    - Terminate oversized streams mid-transmission to prevent memory
      exhaustion and disk rollovers.
    - Provide custom CappedUploadRoute and CappedUploadRequest for upload endpoints.

Owner: Vivek (core) · Task: S1-VIV-4 · Requirements: idea §3, DR-06
"""

from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any

from fastapi import Request, Response, status
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.formparsers import MultiPartParser

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024  # 5 MB
MULTIPART_OVERHEAD_BYTES: int = 64 * 1024  # 64 KB multipart boundaries/headers
STREAM_MAX_BYTES: int = MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD_BYTES  # 5,308,416 B
SPOOL_MAX_SIZE: int = 6 * 1024 * 1024  # 6 MB in-memory buffer before disk rollover


def configure_multipart_spool(spool_size: int = SPOOL_MAX_SIZE) -> None:
    """Configure Starlette's MultiPartParser spool size.

    Why: Starlette defaults spool_max_size to 1 MB. Any multipart file part
    exceeding 1 MB automatically rolls over into a temporary file on disk.
    Configuring this to 6 MB guarantees that all valid photos up to 5 MB
    remain strictly in memory throughout parsing, upholding DR-06.

    Args:
        spool_size: Maximum bytes to buffer in volatile memory per file part.
    """
    MultiPartParser.spool_max_size = spool_size


class UploadSizeExceededException(StarletteHTTPException):
    """Exception raised when an incoming upload stream exceeds the byte cap.

    Inherits from StarletteHTTPException so FastAPI does not catch and mask it
    as a generic 400 body parsing error.
    """

    def __init__(
        self,
        message: str = "Image size exceeds the maximum allowed limit of 5 MB.",
    ) -> None:
        """Initialize with HTTP 400 and code IMAGE_TOO_LARGE."""
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
        self.code = "IMAGE_TOO_LARGE"


class CappedUploadRequest(Request):
    """Request wrapper that enforces byte limits while streaming request bodies."""

    async def stream(self) -> AsyncGenerator[bytes, None]:
        """Stream chunks from the incoming body, counting bytes and aborting on cap.

        Yields:
            Raw chunk bytes.

        Raises:
            UploadSizeExceededException: If total bytes exceed STREAM_MAX_BYTES.
        """
        total_bytes = 0
        async for chunk in super().stream():
            total_bytes += len(chunk)
            if total_bytes > STREAM_MAX_BYTES:
                logger.warning(
                    "upload_stream_limit_exceeded",
                    bytes_received=total_bytes,
                    stream_max_bytes=STREAM_MAX_BYTES,
                )
                raise UploadSizeExceededException(
                    "Upload payload exceeds the maximum allowed size limit."
                )
            yield chunk


class CappedUploadRoute(APIRoute):
    """APIRoute injecting CappedUploadRequest for in-memory upload enforcement."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        """Wrap route execution with early Content-Length checks and capped streaming.

        Returns:
            Wrapped route handler callable.
        """
        original_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            # 1. Early rejection: reject upfront if Content-Length header is oversized
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > STREAM_MAX_BYTES:
                        logger.warning(
                            "upload_content_length_oversized",
                            declared_length=content_length,
                            stream_max_bytes=STREAM_MAX_BYTES,
                        )
                        raise UploadSizeExceededException(
                            "Upload payload exceeds maximum allowed size."
                        )
                except ValueError:
                    pass

            # 2. Wrap request to count bytes on chunked or streaming uploads
            capped_request = CappedUploadRequest(request.scope, request.receive)
            return await original_handler(capped_request)

        return custom_route_handler
