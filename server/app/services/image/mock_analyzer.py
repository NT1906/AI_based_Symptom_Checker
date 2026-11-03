"""Mock image analyzer used when ``CV_PROVIDER=mock`` (local runs and CI).

Responsibilities:
    - Return a fixed, configurable label for any non-empty photo, so the
      upload flow can be built and tested before the real model exists.
    - Simulate an analyzer failure for error-handling tests.

The mock never looks at the image content and never stores it.

Owner: Nisarg (image) · Task: S1-NIS-4 · Requirements: idea §3, NFR-05
"""

from app.core.errors import ValidationError
from app.core.logging import get_logger
from app.services.image.analyzer import ImageAnalysisError
from app.services.image.findings import build_analysis
from app.services.image.schemas import ImageAnalysis, ImageLabel, UnclearReason

logger = get_logger(__name__)

MOCK_ANALYZER_VERSION = "mock-1"
DEFAULT_MOCK_LABEL = ImageLabel.ECZEMA


class MockImageAnalyzer:
    """``ImageAnalyzer`` that returns the same label for every photo."""

    def __init__(
        self,
        label: ImageLabel = DEFAULT_MOCK_LABEL,
        *,
        reason: UnclearReason | None = None,
        fail: bool = False,
    ) -> None:
        """Create the mock.

        Args:
            label: Label returned for every photo.
            reason: Unclear reason, only for ``ImageLabel.UNCLEAR``.
            fail: If true, every call raises ``ImageAnalysisError``.

        Raises:
            pydantic.ValidationError: If ``reason`` is given for a clear label.
        """
        # Why: build once here so a bad label/reason pair fails at setup, not
        # in the middle of a request.
        self._analysis = build_analysis(label, MOCK_ANALYZER_VERSION, reason)
        self._fail = fail

    async def analyze(self, image: bytes) -> ImageAnalysis:
        """Return the configured analysis for any non-empty photo.

        Args:
            image: Image bytes; only checked for being non-empty.

        Returns:
            The configured analysis.

        Raises:
            ValidationError: If ``image`` is empty.
            ImageAnalysisError: If the mock was created with ``fail=True``.
        """
        if not image:
            raise ValidationError("The photo is empty")
        if self._fail:
            raise ImageAnalysisError(details={"provider": "mock"})
        # Only the size is logged, never the image (privacy-and-safety.md).
        logger.info(
            "image_analyzed",
            provider="mock",
            label=self._analysis.label.value,
            image_bytes=len(image),
        )
        return self._analysis
