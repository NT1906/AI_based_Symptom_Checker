"""Build the authenticated user's paginated assessment history.

Owner: Harsh · Task: S2-HAR-1 · Issue: #172 · Requirements: FR-02
Saved results in history: Nisarg · Task: S2-NIS-16 · Issue: #313
"""

from typing import Any
from uuid import UUID

from pydantic import Field
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.assessment import Assessment
from app.repositories.assessment_repository import (
    get_assessment_by_id,
    list_assessments_by_user,
)
from app.schemas.assessment import AssessmentRead
from app.schemas.base import SchemaBase
from app.schemas.result import AssessmentResult

logger = get_logger(__name__)

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MAX_PAGE_OFFSET = 2_147_483_647


class HistoryPage(SchemaBase):
    """One page of assessment summaries and the offset of the next page, if any."""

    items: list[AssessmentRead]
    next_offset: int | None = Field(default=None, ge=0)


class HistoryDetail(AssessmentRead):
    """One past assessment with its saved result, when one was kept."""

    result: AssessmentResult | None = Field(
        default=None,
        description="The result shown when the assessment finished, if saved",
    )


def stored_result(raw: dict[str, Any] | None) -> AssessmentResult | None:
    """Parse a saved result, or None if there is none or it no longer fits."""
    if not raw:
        return None
    try:
        return AssessmentResult.model_validate(raw)
    except PydanticValidationError:
        # Why: an old or damaged result must not break the whole history page.
        logger.warning("stored_result_unreadable")
        return None


def _summary(row: Assessment) -> AssessmentRead:
    """History summary for one row, with the saved result's top condition."""
    item = AssessmentRead.model_validate(row)
    result = stored_result(row.result)
    if result is None or not result.conditions:
        return item
    top = min(result.conditions, key=lambda condition: condition.rank)
    return item.model_copy(update={"top_condition": top.name})


class HistoryService:
    """Read stored assessment metadata through the assessment repository."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Save the factory for short-lived read sessions."""
        self._session_factory = session_factory

    def list_history(self, user_id: UUID, limit: int, offset: int) -> HistoryPage:
        """Return one page for the authenticated user, using a lookahead row."""
        with self._session_factory() as session:
            rows = list_assessments_by_user(session, user_id, limit + 1, offset)
            items = [_summary(row) for row in rows[:limit]]
        return HistoryPage(
            items=items,
            next_offset=offset + limit if len(rows) > limit else None,
        )

    def get_detail(self, user_id: UUID, assessment_id: UUID) -> HistoryDetail:
        """Return an owned assessment with its saved result, or a generic 404."""
        with self._session_factory() as session:
            row = get_assessment_by_id(session, assessment_id)
            if row is None or row.user_id != user_id:
                raise NotFoundError("Assessment not found")
            summary = _summary(row)
            return HistoryDetail(
                **summary.model_dump(), result=stored_result(row.result)
            )
