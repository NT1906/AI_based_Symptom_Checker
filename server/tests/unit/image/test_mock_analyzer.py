"""Unit tests for the mock image analyzer and the analyzer factory.

Covers:
    - The mock satisfies ``ImageAnalyzer`` and returns its configured label.
    - Empty photos are rejected; ``fail=True`` simulates an analyzer failure.
    - ``CV_PROVIDER`` selection: mock works, ``onnx`` and unknown names fail
      with ``ImageAnalysisError`` instead of falling back to the mock.

Owner: Nisarg (image) · Task: S1-NIS-4 · Requirements: idea §3, NFR-05
"""

import pytest
from app.core.config import Settings
from app.core.errors import ValidationError
from app.services.image.analyzer import ImageAnalysisError, ImageAnalyzer
from app.services.image.factory import build_image_analyzer, get_image_analyzer
from app.services.image.mock_analyzer import (
    DEFAULT_MOCK_LABEL,
    MOCK_ANALYZER_VERSION,
    MockImageAnalyzer,
)
from app.services.image.schemas import ImageLabel, UnclearReason
from pydantic import ValidationError as SchemaValidationError

PHOTO = b"\xff\xd8\xff\xe0 fake jpeg bytes"


def test_mock_satisfies_protocol() -> None:
    assert isinstance(MockImageAnalyzer(), ImageAnalyzer)


async def test_mock_returns_default_label_with_findings() -> None:
    analysis = await MockImageAnalyzer().analyze(PHOTO)

    assert analysis.label is DEFAULT_MOCK_LABEL
    assert analysis.is_clear
    assert analysis.symptom_ids
    assert analysis.analyzer_version == MOCK_ANALYZER_VERSION


async def test_mock_returns_configured_unclear_result() -> None:
    mock = MockImageAnalyzer(ImageLabel.UNCLEAR, reason=UnclearReason.POOR_QUALITY)

    analysis = await mock.analyze(PHOTO)

    assert analysis.label is ImageLabel.UNCLEAR
    assert analysis.reason is UnclearReason.POOR_QUALITY
    assert analysis.symptom_ids == ()


async def test_mock_rejects_empty_photo() -> None:
    with pytest.raises(ValidationError, match="empty"):
        await MockImageAnalyzer().analyze(b"")


async def test_mock_simulates_analyzer_failure() -> None:
    with pytest.raises(ImageAnalysisError) as error:
        await MockImageAnalyzer(fail=True).analyze(PHOTO)

    assert error.value.code == "IMAGE_ANALYSIS_UNAVAILABLE"
    assert error.value.status_code == 503


def test_mock_rejects_reason_for_clear_label_at_setup() -> None:
    with pytest.raises(SchemaValidationError):
        MockImageAnalyzer(ImageLabel.ACNE, reason=UnclearReason.LOW_CONFIDENCE)


@pytest.mark.parametrize("provider", ["mock", " MOCK ", "Mock"])
def test_factory_builds_mock(provider: str) -> None:
    assert isinstance(build_image_analyzer(provider), MockImageAnalyzer)


def test_factory_refuses_onnx_until_it_exists() -> None:
    # Why: falling back to the mock in production would show fake findings.
    with pytest.raises(ImageAnalysisError) as error:
        build_image_analyzer("onnx")

    assert error.value.details == {"provider": "onnx"}


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ImageAnalysisError) as error:
        build_image_analyzer("gpt-vision")

    assert error.value.details == {
        "provider": "gpt-vision",
        "supported": ["mock", "onnx"],
    }


def test_dependency_uses_settings_provider(test_settings: Settings) -> None:
    assert isinstance(get_image_analyzer(test_settings), MockImageAnalyzer)
