"""Expose the endpoint for recording versioned consent.

Owner: Harsh | Task: S1-HAR-4, S2-HAR-3 | Issues: #50, #174 | Requirement: DR-08
"""

from uuid import UUID

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from app.api.deps import SessionFactoryDep
from app.core.errors import ErrorResponse
from app.services.privacy import consent

router = APIRouter(tags=["consents"])


class ConsentRequest(BaseModel):
    """Policy version accepted by the user."""

    policy_version: str = Field(alias="policyVersion")


class ConsentResponse(BaseModel):
    """ID of the persisted consent record."""

    consent_id: UUID = Field(serialization_alias="consentId")


@router.get(
    "/consents/current-policy",
    response_model=ConsentRequest,
    summary="Read the active privacy policy version",
)
def get_current_policy(response: Response) -> ConsentRequest:
    """Return the version required for new consent records."""
    response.headers["Cache-Control"] = "no-store"
    return ConsentRequest(policyVersion=consent.CURRENT_POLICY_VERSION)


@router.post(
    "/consents",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record consent",
    responses={409: {"model": ErrorResponse}},
)
def create_consent(
    body: ConsentRequest, session_factory: SessionFactoryDep
) -> ConsentResponse:
    """Save acceptance of the supplied policy version and return its ID."""
    consent_id = consent.record_consent(session_factory, body.policy_version)
    return ConsentResponse(consent_id=consent_id)
