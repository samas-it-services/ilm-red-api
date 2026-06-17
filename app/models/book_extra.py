"""Book Extra model for additional content like flashcards, quizzes, etc."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User


class BookExtra(Base, UUIDMixin, TimestampMixin):
    """BookExtra model for storing additional content related to a book."""

    __tablename__ = "book_extras"

    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Type of extra content
    type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Title of the extra content
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    # JSON content (flexible structure based on type)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Optional external URL (e.g. for audio/video)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Creator
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Status: draft, published, archived
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="published",
        server_default="published",
    )

    # Relationships
    book: Mapped["Book"] = relationship("Book", backref="extras")
    creator: Mapped["User"] = relationship("User")

    __table_args__ = (
        # Unique constraint: type + title per book
        UniqueConstraint("book_id", "type", "title", name="uq_book_extra_type_title"),

        # Check constraint for valid types
        CheckConstraint(
            "type IN ('flashcard', 'quiz', 'audio', 'podcast', 'video', 'infographic', 'simple_explanation', 'key_ideas')",
            name="check_book_extra_type",
        ),

        # Check constraint for valid status
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="check_book_extra_status",
        ),

        # Indexes
        Index("idx_book_extras_type", "type"),
        Index("idx_book_extras_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<BookExtra {self.type}: {self.title} (book={self.book_id})>"
