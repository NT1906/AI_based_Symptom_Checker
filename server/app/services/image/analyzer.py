"""Image analyzer protocol and its error.

Responsibilities:
    - Define the ``ImageAnalyzer`` protocol that the mock (S1-NIS-4) and the
      ONNX analyzer (S2-NIS-6) both implement, so callers depend on the
      interface, not a provider (AI_RULES.md §4).
    - Define ``ImageAnalysisError`` for an analyzer that cannot run.

Images are analysed in memory and never stored or logged
(docs/privacy-and-safety.md).

Owner: Nisarg (image) · Task: S1-NIS-4 · Requirements: idea §3, NFR-05, DR-06
"""

from typing import Protocol, runtime_checkable

from fastapi import status

from app.core.errors import AppError
from app.services.image.schemas import ImageAnalysis


class ImageAnalysisError(AppError):
    """The analyzer could not run (model missing, not configured, or crashed).

    Callers treat this as "carry on with text only": a failed analysis never
    changes the assessment or its risk (docs/cv-plan.md §1).
    """

    def __init__(
        self,
        message: str = "Photo analysis is not available right now",
        details: dict[str, object] | None = None,
    ) -> None:
        """Initialize ImageAnalysisError with status 503."""
        super().__init__(
            message=message,
            code="IMAGE_ANALYSIS_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


@runtime_checkable
class ImageAnalyzer(Protocol):
    """Turns one validated photo into visual findings."""

    async def analyze(self, image: bytes) -> ImageAnalysis:
        """Analyse one photo.

        Args:
            image: Image bytes that already passed upload validation (size,
                type, EXIF stripped; S1-VIV-4). Never stored or logged.

        Returns:
            The analysis. A photo the analyzer cannot judge comes back as
            ``unclear`` with a reason, not as an error.

        Raises:
            ValidationError: If ``image`` is empty.
            ImageAnalysisError: If the analyzer cannot run.
        """
        ...
