"""Authentication API endpoints for user registration, login, logout, and identity.

Responsibilities:
    - Expose REST routes for registration, credential login, logout,
      and session verification.
    - Set and clear HttpOnly, SameSite=Lax session cookies.
    - Prevent exposure of passwords, password hashes, or raw tokens in JSON payloads.

Owner: Vivek (api) · Task: S2-VIV-1 · Requirements: FR-01, NFR-03
"""

from typing import Any

from fastapi import APIRouter, Response, status

from app.api.deps import AuthServiceDep, CurrentUserDep, SettingsDep
from app.core.errors import ErrorResponse
from app.core.logging import get_logger
from app.services.auth.schemas import (
    LogoutResponse,
    UserLoginRequest,
    UserRead,
    UserRegisterRequest,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# Standard error response mappings
AUTH_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Invalid credentials or missing/expired authentication token",
    },
    status.HTTP_422_UNPROCESSABLE_ENTITY: {
        "model": ErrorResponse,
        "description": "Validation error on payload",
    },
}


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description=(
        "Registers a new user account with an Argon2id-hashed password. "
        "Rejects duplicate email addresses with a 409 Conflict error. "
        "Returns the created account representation without password hashes."
    ),
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Account with email already exists",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "Validation error on email or password",
        },
    },
)
async def register(
    payload: UserRegisterRequest,
    service: AuthServiceDep,
) -> UserRead:
    """Register a new user account.

    Args:
        payload: Validated registration payload with email and password.
        service: Injected authentication domain service.

    Returns:
        UserRead: Sanitized user account representation.
    """
    logger.info("auth_registration_attempt", email=payload.email)
    return await service.register_user(payload)


@router.post(
    "/login",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and set session cookie",
    description=(
        "Verifies credentials using Argon2id, generates a signed JWT, "
        "and sets it in an HttpOnly, SameSite=Lax cookie. "
        "The JWT is never returned in the JSON response."
    ),
    responses=AUTH_ERROR_RESPONSES,
)
async def login(
    payload: UserLoginRequest,
    response: Response,
    service: AuthServiceDep,
    settings: SettingsDep,
) -> UserRead:
    """Authenticate user credentials and configure session cookie.

    Args:
        payload: Login credentials.
        response: FastAPI response object for setting cookies.
        service: Injected authentication domain service.
        settings: Application settings.

    Returns:
        UserRead: Sanitized user account representation.
    """
    user, token = await service.authenticate_user(payload)

    is_secure = settings.app_env in ("production", "staging")
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )
    logger.info("auth_login_successful", user_id=str(user.id))
    return user


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Terminate authenticated session",
    description=(
        "Clears the HttpOnly session cookie. Safely succeeds whether the "
        "user is actively logged in or already logged out."
    ),
)
async def logout(
    response: Response,
    settings: SettingsDep,
) -> LogoutResponse:
    """Terminate the current authenticated session.

    Args:
        response: FastAPI response object for clearing cookies.
        settings: Application settings.

    Returns:
        LogoutResponse: Confirmation message indicating successful logout.
    """
    is_secure = settings.app_env in ("production", "staging")
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=is_secure,
    )
    logger.info("auth_logout_completed")
    return LogoutResponse(status="ok", message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
    description=(
        "Returns the account profile for the currently authenticated user "
        "extracted from the HttpOnly session cookie."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Missing, invalid, or expired session token",
        },
    },
)
async def get_current_user_profile(
    current_user: CurrentUserDep,
) -> UserRead:
    """Retrieve current authenticated user details.

    Args:
        current_user: Injected user resolved from valid session cookie.

    Returns:
        UserRead: Sanitized user account information.
    """
    logger.info("auth_profile_fetch", user_id=str(current_user.id))
    return current_user
