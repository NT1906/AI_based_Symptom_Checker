"""Define the authenticated data-rights service boundary.

Owner: Harsh · Task: S2-HAR-2 · Issue: #173 · Requirements: DR-06, NFR-04
"""

from typing import Protocol
from uuid import UUID

from pydantic import JsonValue


class DataRightsRepository(Protocol):
    """Provide owner-scoped export and transactional deletion of account data."""

    def export_user_data(self, user_id: UUID) -> dict[str, JsonValue]:
        """Read the account's exportable data, excluding credentials and tokens."""
        ...

    def delete_user_data(self, user_id: UUID) -> None:
        """Erase the account's data atomically; repeat deletion is a no-op."""
        ...


class DataRightsService:
    """Apply data-rights actions to the authenticated account."""

    def __init__(self, repository: DataRightsRepository) -> None:
        """Bind the database team's data-rights adapter."""
        self._repository = repository

    def export(self, user_id: UUID) -> dict[str, JsonValue]:
        """Return the account's exportable data."""
        return self._repository.export_user_data(user_id)

    def delete(self, user_id: UUID) -> None:
        """Delete the account's data through the transactional repository."""
        self._repository.delete_user_data(user_id)
