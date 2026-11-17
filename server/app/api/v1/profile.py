"""Profile API endpoints for optional clinical context management.

Responsibilities:
    - Expose GET /api/v1/profile to retrieve current user profile context.
    - Expose PUT /api/v1/profile to create or replace profile attributes.
    - Expose PATCH /api/v1/profile for partial profile updates.
    - Expose DELETE /api/v1/profile to delete or reset profile context.
    - Enforce authentication on all routes via CurrentUserDep.
    - Apply no-store cache control headers to prevent caching health data.

Owner: Vivek (api) · Task: S2-VIV-3 · Requirements: FR-02, idea § 10
"""

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUserDep, ProfileServiceDep
from app.core.errors import ErrorResponse
from app.schemas.profile import ProfileUpdate
from app.services.profile.service import ProfileResponse

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user profile",
    description=(
        "Retrieve the optional clinical triage profile for the current "
        "authenticated user. Returns an empty profile structure if not yet set."
    ),
    responses={
        status.HTTP_200_OK: {
            "model": ProfileResponse,
            "description": "User profile successfully retrieved.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication credentials missing or invalid.",
        },
    },
)
async def get_profile(
    current_user: CurrentUserDep,
    profile_service: ProfileServiceDep,
    response: Response,
) -> ProfileResponse:
    """Retrieve current user's profile context."""
    response.headers["Cache-Control"] = "no-store"
    return profile_service.get_profile(current_user.id)


@router.put(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update user profile",
    description=(
        "Create or replace the optional clinical triage profile for the "
        "current authenticated user. Validates coarse age band, biological sex, "
        "and deduplicates chronic condition names."
    ),
    responses={
        status.HTTP_200_OK: {
            "model": ProfileResponse,
            "description": "Profile successfully saved or updated.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication credentials missing or invalid.",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "Invalid age band or biological sex provided.",
        },
    },
)
async def save_profile(
    payload: ProfileUpdate,
    current_user: CurrentUserDep,
    profile_service: ProfileServiceDep,
    response: Response,
) -> ProfileResponse:
    """Create or update current user's profile context."""
    response.headers["Cache-Control"] = "no-store"
    return profile_service.save_profile(current_user.id, payload)


@router.patch(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Partially update user profile",
    description=(
        "Partially update attributes of the current user's clinical profile. "
        "Attributes not specified in the payload remain untouched."
    ),
    responses={
        status.HTTP_200_OK: {
            "model": ProfileResponse,
            "description": "Profile successfully updated.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication credentials missing or invalid.",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "Invalid age band or biological sex provided.",
        },
    },
)
async def patch_profile(
    payload: ProfileUpdate,
    current_user: CurrentUserDep,
    profile_service: ProfileServiceDep,
    response: Response,
) -> ProfileResponse:
    """Partially update current user's profile context."""
    response.headers["Cache-Control"] = "no-store"
    existing = profile_service.get_profile(current_user.id)

    # Merge partial attributes over existing values
    merged = ProfileUpdate(
        age_band=(
            payload.age_band if payload.age_band is not None else existing.age_band
        ),
        biological_sex=(
            payload.biological_sex
            if payload.biological_sex is not None
            else existing.biological_sex
        ),
        chronic_conditions=(
            payload.chronic_conditions
            if payload.chronic_conditions is not None
            else existing.chronic_conditions
        ),
    )
    return profile_service.save_profile(current_user.id, merged)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user profile",
    description=(
        "Delete the optional clinical triage profile for the current user. "
        "Subsequent requests will see an empty profile."
    ),
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Profile successfully deleted.",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Authentication credentials missing or invalid.",
        },
    },
)
async def delete_profile(
    current_user: CurrentUserDep,
    profile_service: ProfileServiceDep,
) -> Response:
    """Delete current user's profile context."""
    profile_service.delete_profile(current_user.id)
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"Cache-Control": "no-store"},
    )
