"""Optional registered user storage.

Owner: Harsh · Task: S0-HAR-1 · Requirements: FR-01
"""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, RecordMixin

if TYPE_CHECKING:
    from app.models.assessment import Assessment


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
