"""Expose the endpoint for recording versioned consent.

Owner: Harsh | Task: S1-HAR-4 | Issue: #50 | Requirement: DR-08
"""

from uuid import UUID

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.api.deps import SessionFactoryDep
from app.services.privacy.consent import record_consent

router = APIRouter(tags=["consents"])


class ConsentRequest(BaseModel):
    """Policy version accepted by the user."""

    policy_version: str = Field(alias="policyVersion")


class ConsentResponse(BaseModel):
    """ID of the persisted consent record."""

    consent_id: UUID = Field(serialization_alias="consentId")


@router.post(
    "/consents",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record consent",
)
def create_consent(
    body: ConsentRequest, session_factory: SessionFactoryDep
) -> ConsentResponse:
    """Save acceptance of the supplied policy version and return its ID."""
    consent_id = record_consent(session_factory, body.policy_version)
    return ConsentResponse(consent_id=consent_id)
