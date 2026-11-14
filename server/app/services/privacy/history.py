"""Build the authenticated user's paginated assessment history.

Owner: Harsh · Task: S2-HAR-1 · Issue: #172 · Requirements: FR-02
"""

from uuid import UUID

from pydantic import Field
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import NotFoundError
from app.repositories.assessment_repository import (
    get_assessment_by_id,
    list_assessments_by_user,
)
from app.schemas.assessment import AssessmentRead
from app.schemas.base import SchemaBase

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MAX_PAGE_OFFSET = 2_147_483_647


class HistoryPage(SchemaBase):
    """One page of assessment summaries and the offset of the next page, if any."""

    items: list[AssessmentRead]
    next_offset: int | None = Field(default=None, ge=0)


class HistoryService:
    """Read stored assessment metadata through the assessment repository."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Save the factory for short-lived read sessions."""
        self._session_factory = session_factory

    def list_history(self, user_id: UUID, limit: int, offset: int) -> HistoryPage:
        """Return one page for the authenticated user, using a lookahead row."""
        with self._session_factory() as session:
            rows = list_assessments_by_user(session, user_id, limit + 1, offset)
            items = [AssessmentRead.model_validate(row) for row in rows[:limit]]
        return HistoryPage(
            items=items,
            next_offset=offset + limit if len(rows) > limit else None,
        )

    def get_detail(self, user_id: UUID, assessment_id: UUID) -> AssessmentRead:
        """Return stored metadata for an owned assessment or raise a generic 404."""
        with self._session_factory() as session:
            row = get_assessment_by_id(session, assessment_id)
            if row is None or row.user_id != user_id:
                raise NotFoundError("Assessment not found")
            return AssessmentRead.model_validate(row)
