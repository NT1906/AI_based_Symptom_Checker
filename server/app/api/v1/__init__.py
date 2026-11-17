"""Version 1 API routes package."""

from app.api.v1 import (
    assessments,
    auth,
    consents,
    health,
    history,
    profile,
)

__all__ = [
    "assessments",
    "auth",
    "consents",
    "health",
    "history",
    "profile",
]
