"""Authentication API endpoints for user registration, login, logout, refresh, and CSRF.

Responsibilities:
    - Expose REST routes for registration, credential login, logout, session refresh,
      CSRF token distribution, and session verification.
    - Set and clear HttpOnly, SameSite=Lax session and refresh cookies.
    - Set readable CSRF cookies and validate anti-forgery headers.
    - Enforce token rotation and secure cookie scoping.

Owner: Vivek (api) · Task: S2-VIV-1, S2-VIV-2 · Requirements: FR-01, NFR-03
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Request, Response, status

from app.api.deps import AuthServiceDep, CurrentUserDep, SettingsDep
from app.core.config import Settings
from app.core.errors import ErrorResponse, UnauthorizedError
from app.core.logging import get_logger
from app.services.auth.schemas import (
    CsrfTokenResponse,
    LogoutResponse,
    UserLoginRequest,
    UserRead,
    UserRegisterRequest,
)
from app.services.auth.security import generate_csrf_token

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
    settings: Settings,
) -> None:
    """Set access, refresh, and CSRF cookies on the outgoing response.

    Args:
        response: FastAPI response object.
        access_token: Encoded short-lived access JWT.
        refresh_token: Encoded long-lived refresh JWT.
        csrf_token: Hexadecimal CSRF token.
        settings: Application configuration settings.
    """
    is_secure = settings.app_env in ("production", "staging")

    # Short-lived access token cookie (path=/)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )

    # Long-lived refresh token cookie scoped strictly to auth endpoints
    # (path=/api/v1/auth)
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path="/api/v1/auth",
    )

    # Client-readable CSRF token cookie (httponly=False so SPA can read and echo)
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=is_secure,
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path="/",
    )
    response.headers["X-CSRF-Token"] = csrf_token


def _clear_auth_cookies(
    response: Response,
    settings: Settings,
) -> None:
    """Clear all authentication and CSRF cookies with matching path attributes.

    Args:
        response: FastAPI response object.
        settings: Application configuration settings.
    """
    is_secure = settings.app_env in ("production", "staging")

    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=is_secure,
    )
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path="/api/v1/auth",
        httponly=True,
        samesite="lax",
        secure=is_secure,
    )
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        path="/",
        httponly=False,
        samesite="lax",
        secure=is_secure,
    )


# Standard error response mappings
AUTH_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Invalid credentials or missing/expired authentication token",
        "content": {
            "application/json": {
                "example": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid email or password",
                    "details": None,
                    "requestId": "req_1234567890abcdef",
                }
            }
        },
    },
    status.HTTP_422_UNPROCESSABLE_ENTITY: {
        "model": ErrorResponse,
        "description": "Validation error on payload",
        "content": {
            "application/json": {
                "example": {
                    "code": "VALIDATION_ERROR",
                    "message": "Validation failed on one or more fields.",
                    "details": [
                        {
                            "loc": ["body", "email"],
                            "msg": "value is not a valid email address",
                            "type": "value_error",
                        }
                    ],
                    "requestId": "req_1234567890abcdef",
                }
            }
        },
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
        status.HTTP_201_CREATED: {
            "model": UserRead,
            "description": "User account created successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "id": "00000000-0000-4000-8000-0000000000a1",
                        "email": "patient@example.com",
                        "createdAt": "2026-11-18T12:00:00Z",
                    }
                }
            },
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Account with email already exists",
            "content": {
                "application/json": {
                    "example": {
                        "code": "ACCOUNT_EXISTS",
                        "message": "A user with this email address already exists",
                        "details": None,
                        "requestId": "req_1234567890abcdef",
                    }
                }
            },
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "Validation error on email or password",
            "content": {
                "application/json": {
                    "example": {
                        "code": "VALIDATION_ERROR",
                        "message": "Password cannot be empty or solely whitespace.",
                        "details": None,
                        "requestId": "req_1234567890abcdef",
                    }
                }
            },
        },
    },
)
async def register(
    payload: Annotated[
        UserRegisterRequest,
        Body(
            openapi_examples={
                "valid_registration": {
                    "summary": "Valid user registration",
                    "description": (
                        "Registers a new user with standard email and strong password."
                    ),
                    "value": {
                        "email": "patient@example.com",
                        "password": "SecurePassword123!",
                    },
                }
            },
        ),
    ],
    service: AuthServiceDep,
) -> UserRead:
    """Register a new user account.

    Args:
        payload: Validated registration payload with email and password.
        service: Injected authentication domain service.

    Returns:
        UserRead: Sanitized user account representation.
    """
    logger.info("auth_registration_attempt")
    return await service.register_user(payload)


@router.post(
    "/login",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and set session cookies",
    description=(
        "Verifies credentials using Argon2id, generates access and refresh JWTs, "
        "and sets them in HttpOnly cookies with CSRF token protection."
    ),
    responses={
        status.HTTP_200_OK: {
            "model": UserRead,
            "description": (
                "Authentication successful; sets HttpOnly access and refresh "
                "session cookies."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "id": "00000000-0000-4000-8000-0000000000a1",
                        "email": "patient@example.com",
                        "createdAt": "2026-11-18T12:00:00Z",
                    }
                }
            },
        },
        **AUTH_ERROR_RESPONSES,
    },
)
async def login(
    payload: Annotated[
        UserLoginRequest,
        Body(
            openapi_examples={
                "valid_login": {
                    "summary": "Standard user login",
                    "description": (
                        "Submits credentials to establish an authenticated session."
                    ),
                    "value": {
                        "email": "patient@example.com",
                        "password": "SecurePassword123!",
                    },
                }
            },
        ),
    ],
    response: Response,
    service: AuthServiceDep,
    settings: SettingsDep,
) -> UserRead:
    """Authenticate user credentials and configure session cookies.

    Args:
        payload: Login credentials.
        response: FastAPI response object for setting cookies.
        service: Injected authentication domain service.
        settings: Application settings.

    Returns:
        UserRead: Sanitized user account representation.
    """
    user, access_token, refresh_token = await service.authenticate_user(payload)
    csrf_token = generate_csrf_token()
    _set_auth_cookies(response, access_token, refresh_token, csrf_token, settings)
    logger.info("auth_login_successful")
    return user


@router.post(
    "/refresh",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token and rotate refresh token",
    description=(
        "Validates the refresh token from cookie, rotates the token, "
        "and sets updated access, refresh, and CSRF cookies."
    ),
    responses={
        status.HTTP_200_OK: {
            "model": UserRead,
            "description": (
                "Session refreshed; rotates refresh token and issues "
                "fresh access cookie."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "id": "00000000-0000-4000-8000-0000000000a1",
                        "email": "patient@example.com",
                        "createdAt": "2026-11-18T12:00:00Z",
                    }
                }
            },
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Refresh token cookie missing, expired, or revoked",
            "content": {
                "application/json": {
                    "example": {
                        "code": "UNAUTHORIZED",
                        "message": "Refresh token session cookie missing",
                        "details": None,
                        "requestId": "req_1234567890abcdef",
                    }
                }
            },
        },
    },
)
async def refresh(
    request: Request,
    response: Response,
    service: AuthServiceDep,
    settings: SettingsDep,
) -> UserRead:
    """Validate refresh token and issue rotated token pair.

    Args:
        request: FastAPI request object containing cookies.
        response: FastAPI response object for updating cookies.
        service: Injected authentication domain service.
        settings: Application settings.

    Returns:
        UserRead: Sanitized user account representation.

    Raises:
        UnauthorizedError: If refresh token is missing, invalid, or expired.
    """
    raw_refresh = request.cookies.get(settings.refresh_cookie_name)
    if not raw_refresh:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_refresh = auth_header[7:].strip()

    if not raw_refresh:
        raise UnauthorizedError("Refresh token session cookie missing")

    user, new_access, new_refresh = await service.refresh_session(raw_refresh)
    csrf_token = generate_csrf_token()
    _set_auth_cookies(response, new_access, new_refresh, csrf_token, settings)
    logger.info("auth_session_refreshed")
    return user


@router.get(
    "/csrf",
    response_model=CsrfTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Get fresh CSRF token",
    description=(
        "Generates a fresh CSRF token, setting the csrf_token cookie and "
        "response header."
    ),
    responses={
        status.HTTP_200_OK: {
            "model": CsrfTokenResponse,
            "description": "Fresh CSRF token issued in payload and Set-Cookie header.",
            "content": {
                "application/json": {
                    "example": {
                        "csrfToken": "a1b2c3d4e5f60718293a4b5c6d7e8f90",
                    }
                }
            },
        }
    },
)
async def get_csrf(
    response: Response,
    settings: SettingsDep,
) -> CsrfTokenResponse:
    """Generate fresh CSRF token.

    Args:
        response: FastAPI response object.
        settings: Application settings.

    Returns:
        CsrfTokenResponse: Fresh CSRF token value.
    """
    csrf_token = generate_csrf_token()
    is_secure = settings.app_env in ("production", "staging")
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=is_secure,
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path="/",
    )
    response.headers["X-CSRF-Token"] = csrf_token
    return CsrfTokenResponse(csrf_token=csrf_token)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Terminate authenticated session",
    description=(
        "Clears access, refresh, and CSRF cookies, revoking the active refresh token."
    ),
    responses={
        status.HTTP_200_OK: {
            "model": LogoutResponse,
            "description": "Session terminated and authentication cookies cleared.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "message": "Successfully logged out",
                    }
                }
            },
        }
    },
)
async def logout(
    request: Request,
    response: Response,
    service: AuthServiceDep,
    settings: SettingsDep,
) -> LogoutResponse:
    """Terminate the current authenticated session.

    Args:
        request: FastAPI request object to inspect active tokens.
        response: FastAPI response object for clearing cookies.
        service: Injected authentication domain service.
        settings: Application settings.

    Returns:
        LogoutResponse: Confirmation message indicating successful logout.
    """
    raw_refresh = request.cookies.get(settings.refresh_cookie_name)
    if raw_refresh:
        service.revoke_token(raw_refresh)

    _clear_auth_cookies(response, settings)
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
        status.HTTP_200_OK: {
            "model": UserRead,
            "description": "Current user account information.",
            "content": {
                "application/json": {
                    "example": {
                        "id": "00000000-0000-4000-8000-0000000000a1",
                        "email": "patient@example.com",
                        "createdAt": "2026-11-18T12:00:00Z",
                    }
                }
            },
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Missing, invalid, or expired session token",
            "content": {
                "application/json": {
                    "example": {
                        "code": "UNAUTHORIZED",
                        "message": "Authentication required",
                        "details": None,
                        "requestId": "req_1234567890abcdef",
                    }
                }
            },
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
    logger.info("auth_profile_fetch")
    return current_user
