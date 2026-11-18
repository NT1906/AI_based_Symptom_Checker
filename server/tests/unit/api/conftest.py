"""Fixtures for API router unit tests.

Responsibilities:
    - Route unit tests check HTTP wiring and the published contract, not the
      assessment engine, so they run against the fixed-data
      ``DefaultAssessmentService`` (stable IDs such as ``STUB_ASSESSMENT_ID``).
      The app itself uses the orchestrator-backed service since S2-NIS-13;
      ``test_orchestrator_service.py`` covers that path end to end.

Owner: Nisarg (integration) · Task: S2-NIS-13 · Requirements: NFR-07
"""

from collections.abc import Iterator

import pytest
from app.api.deps import DefaultAssessmentService, get_assessment_service
from fastapi import FastAPI


@pytest.fixture(autouse=True)
def stub_assessment_service(app: FastAPI) -> Iterator[DefaultAssessmentService]:
    """Serve every assessment route of the test app from the stub service."""
    stub = DefaultAssessmentService()
    app.dependency_overrides[get_assessment_service] = lambda: stub
    yield stub
    app.dependency_overrides.pop(get_assessment_service, None)
