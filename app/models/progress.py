"""Reading progress database model."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User


class ReadingProgress(Base, UUIDMixin, TimestampMixin):
    """User's reading progress for books."""

    __tablename__ = "reading_progress"

    # User and book relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Progress tracking
    current_page: Mapped[int] = mapped_column(Integer, nullable=False)
    total_pages: Mapped[int] = mapped_column(Integer, nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False)

    # Timestamps
    last_read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Reading time tracking
    reading_time_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="reading_progress")
    book: Mapped["Book"] = relationship("Book", backref="reading_progress")

    __table_args__ = (
        # One progress record per user per book
        UniqueConstraint("user_id", "book_id", name="uq_progress_user_book"),
        # Check constraints
        CheckConstraint("current_page >= 1", name="check_current_page_positive"),
        CheckConstraint("total_pages >= 1", name="check_total_pages_positive"),
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="check_progress_percent_range",
        ),
        CheckConstraint("reading_time_seconds >= 0", name="check_reading_time_positive"),
        # Composite index for recent reads query
        Index("idx_reading_progress_user_last_read", "user_id", "last_read_at"),
    )

    def __repr__(self) -> str:
        return f"<ReadingProgress user={self.user_id} book={self.book_id} {self.progress_percent}%>"
