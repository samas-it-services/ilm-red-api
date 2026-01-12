"""Rating flag database model."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.book import Rating
    from app.models.user import User


class RatingFlag(Base, UUIDMixin):
    """User reports of inappropriate ratings."""

    __tablename__ = "rating_flags"

    # Relationship to rating and reporter
    rating_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ratings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Flag details
    reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # 'spam', 'offensive', 'irrelevant', 'other'
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Flag status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )  # 'pending', 'reviewed', 'dismissed'

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    rating: Mapped["Rating"] = relationship("Rating", backref="flags")
    reporter: Mapped["User"] = relationship("User", foreign_keys=[reporter_id], backref="reported_flags")
    resolver: Mapped["User"] = relationship("User", foreign_keys=[resolved_by])

    __table_args__ = (
        # One flag per user per rating
        UniqueConstraint("rating_id", "reporter_id", name="uq_flag_rating_reporter"),
        # Check constraint for valid reason
        CheckConstraint(
            "reason IN ('spam', 'offensive', 'irrelevant', 'other')",
            name="check_flag_reason",
        ),
        # Check constraint for valid status
        CheckConstraint(
            "status IN ('pending', 'reviewed', 'dismissed')",
            name="check_flag_status",
        ),
        # Index for flagged ratings query
        Index("idx_rating_flags_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<RatingFlag {self.reason} for rating={self.rating_id}>"
