"""Anonymous guest session storage and token ownership.

Owner: Kavya (Database) · Task: S1-KAV-4 · Requirements: idea § 10
"""

from datetime import datetime, UTC
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, RecordMixin

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.user import User


class GuestSession(RecordMixin, Base):
    """Anonymous guest session holding a cryptographic token hash for ownership.

    Enables unauthenticated users to complete triage assessments without friction
    (idea § 10). Raw session bearer tokens are never persisted in plaintext;
    only the SHA-256 hash (64 hex characters) is stored.
    """

    __tablename__ = "guest_sessions"
    __table_args__ = (
        CheckConstraint(
            "length(trim(token_hash)) = 64",
            name="token_hash_length_64",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="expires_after_created",
        ),
        Index("ix_guest_sessions_expires_at", "expires_at"),
    )

    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    claimed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    claimed_by_user: Mapped["User | None"] = relationship(
        back_populates="claimed_guest_sessions"
    )
    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="guest_session", passive_deletes="all"
    )

    @property
    def is_expired(self) -> bool:
        """Whether the guest session has passed its expiration timestamp."""
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return expires <= datetime.now(UTC)

    @property
    def is_claimed(self) -> bool:
        """Whether the session assessments have been transferred to an account."""
        return self.claimed_at is not None
