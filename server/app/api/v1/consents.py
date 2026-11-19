"""Expose the endpoint for recording versioned consent.

Owner: Harsh | Task: S1-HAR-4, S2-HAR-3 | Issues: #50, #174 | Requirement: DR-08
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Response, status
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
    status_code=status.HTTP_200_OK,
    summary="Read the active privacy policy version",
    description=(
        "Returns the active privacy and terms policy version required for valid "
        "clinical triage consent under DPDP Act and GDPR regulations."
    ),
    responses={
        status.HTTP_200_OK: {
            "model": ConsentRequest,
            "description": (
                "Active policy version currently required for assessment creation."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "policyVersion": "v1.0",
                    }
                }
            },
        }
    },
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
    description=(
        "Persists explicit user acceptance of the supplied privacy policy version "
        "and returns a unique consent identifier required to begin an assessment."
    ),
    responses={
        status.HTTP_201_CREATED: {
            "model": ConsentResponse,
            "description": "Consent record created successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "consentId": "00000000-0000-4000-8000-0000000000c1",
                    }
                }
            },
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": (
                "Consent recording rejected due to policy version mismatch or conflict."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "code": "CONFLICT",
                        "message": (
                            "Policy version must match the active current "
                            "policy version."
                        ),
                        "details": None,
                        "requestId": "req_1234567890abcdef",
                    }
                }
            },
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "Validation failed on consent payload.",
            "content": {
                "application/json": {
                    "example": {
                        "code": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "details": [
                            {
                                "loc": ["body", "policyVersion"],
                                "msg": "Field required",
                                "type": "missing",
                            }
                        ],
                        "requestId": "req_1234567890abcdef",
                    }
                }
            },
        },
    },
)
def create_consent(
    body: Annotated[
        ConsentRequest,
        Body(
            openapi_examples={
                "standard": {
                    "summary": "Accept current policy version",
                    "value": {
                        "policyVersion": "v1.0",
                    },
                }
            }
        ),
    ],
    session_factory: SessionFactoryDep,
) -> ConsentResponse:
    """Save acceptance of the supplied policy version and return its ID."""
    consent_id = consent.record_consent(session_factory, body.policy_version)
    return ConsentResponse(consent_id=consent_id)
