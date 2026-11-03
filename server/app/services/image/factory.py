"""Chooses the image analyzer from ``CV_PROVIDER``.

Responsibilities:
    - Return the ``MockImageAnalyzer`` for ``CV_PROVIDER=mock``.
    - Refuse ``onnx`` until ``OnnxImageAnalyzer`` exists (S2-NIS-6), instead of
      silently using the mock: fake findings must never reach real users.
    - Provide ``get_image_analyzer`` for FastAPI ``Depends``.

Owner: Nisarg (image) · Task: S1-NIS-4 · Requirements: NFR-05, NFR-08
"""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.services.image.analyzer import ImageAnalysisError, ImageAnalyzer
from app.services.image.mock_analyzer import MockImageAnalyzer

logger = get_logger(__name__)

SUPPORTED_PROVIDERS = ("mock", "onnx")


def build_image_analyzer(provider: str) -> ImageAnalyzer:
    """Create the analyzer for a provider name.

    Args:
        provider: ``CV_PROVIDER`` value; case and surrounding spaces are
            ignored.

    Returns:
        The analyzer.

    Raises:
        ImageAnalysisError: For ``onnx`` (not built yet) or an unknown name,
            so the upload endpoint carries on with text only.

    Example:
        >>> type(build_image_analyzer(" Mock ")).__name__
        'MockImageAnalyzer'
    """
    name = provider.strip().lower()
    if name == "mock":
        return MockImageAnalyzer()
    if name == "onnx":
        # OnnxImageAnalyzer (S2-NIS-6) replaces this branch.
        logger.error("image_analyzer_unavailable", provider=name)
        raise ImageAnalysisError(details={"provider": name})
    logger.error("unknown_image_provider", provider=name)
    raise ImageAnalysisError(
        details={"provider": name, "supported": list(SUPPORTED_PROVIDERS)}
    )


def get_image_analyzer(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ImageAnalyzer:
    """FastAPI dependency returning the analyzer for the current settings.

    Args:
        settings: Application settings (overridable in tests).

    Returns:
        The analyzer for ``settings.cv_provider``.

    Raises:
        ImageAnalysisError: If the configured provider cannot be used.
    """
    return build_image_analyzer(settings.cv_provider)
