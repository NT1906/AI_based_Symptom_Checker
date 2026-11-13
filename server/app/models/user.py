"""Optional registered user storage.

Owner: Harsh, Kavya · Tasks: S0-HAR-1, S1-KAV-4, S2-KAV-3
Requirements: FR-01, FR-02, idea § 10
"""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, RecordMixin

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.guest_session import GuestSession
    from app.models.profile import Profile


class User(RecordMixin, Base):
    """Optional account identity; password hashing belongs to the auth layer."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(trim(email)) > 0", name="email_not_blank"),
        CheckConstraint("email = lower(trim(email))", name="email_normalized"),
        CheckConstraint(
            "password_hash IS NULL OR length(trim(password_hash)) > 0",
            name="password_hash_not_blank",
        ),
    )

    email: Mapped[str] = mapped_column(String(320), unique=True)
    # NULL means no password login is possible (including the fictional seed).
    password_hash: Mapped[str | None] = mapped_column(Text)
    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="user", passive_deletes="all"
    )
    claimed_guest_sessions: Mapped[list["GuestSession"]] = relationship(
        back_populates="claimed_by_user", passive_deletes="all"
    )
    profile: Mapped["Profile | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
