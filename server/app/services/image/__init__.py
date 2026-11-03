"""Image service: turns an optional skin photo into visual symptoms.

Responsibilities:
    - Provide the ``ImageAnalyzer`` protocol and the mock analyzer.
    - Choose the analyzer from ``CV_PROVIDER``.
    - Map image labels to visual symptoms the orchestrator can merge.

Owner: Nisarg (image) · Task: S1-NIS-4 · Requirements: idea §3, NFR-05, NFR-07
"""

from app.services.image.analyzer import ImageAnalysisError, ImageAnalyzer
from app.services.image.factory import build_image_analyzer, get_image_analyzer
from app.services.image.findings import (
    LABEL_CONDITIONS,
    VISUAL_SYMPTOMS,
    build_analysis,
    to_extracted_symptoms,
)
from app.services.image.mock_analyzer import (
    DEFAULT_MOCK_LABEL,
    MOCK_ANALYZER_VERSION,
    MockImageAnalyzer,
)
from app.services.image.schemas import ImageAnalysis, ImageLabel, UnclearReason

__all__ = [
    "DEFAULT_MOCK_LABEL",
    "LABEL_CONDITIONS",
    "MOCK_ANALYZER_VERSION",
    "VISUAL_SYMPTOMS",
    "ImageAnalysis",
    "ImageAnalysisError",
    "ImageAnalyzer",
    "ImageLabel",
    "MockImageAnalyzer",
    "UnclearReason",
    "build_analysis",
    "build_image_analyzer",
    "get_image_analyzer",
    "to_extracted_symptoms",
]
