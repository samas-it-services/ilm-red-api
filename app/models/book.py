"""Book-related database models."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


# Book categories (aligned with OpenAPI spec)
BOOK_CATEGORIES = [
    "quran",
    "hadith",
    "seerah",
    "fiqh",
    "aqidah",
    "tafsir",
    "history",
    "spirituality",
    "children",
    "fiction",
    "non-fiction",
    "education",
    "science",
    "technology",
    "biography",
    "self-help",
    "other",
]


class Book(Base, UUIDMixin, TimestampMixin):
    """Book model for storing book metadata and file information."""

    __tablename__ = "books"

    # Owner relationship
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    isbn: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Visibility: public (everyone), private (owner only), friends (future)
    visibility: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="private",
        server_default="private",
    )

    # File information
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA256
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, epub, txt
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Book details
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Processing status: uploading, processing, ready, failed
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="processing",
        server_default="processing",
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Stats (cached aggregations)
    stats: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {"views": 0, "downloads": 0, "rating_count": 0, "rating_avg": 0.0},
        server_default='{"views": 0, "downloads": 0, "rating_count": 0, "rating_avg": 0.0}',
    )

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", backref="books")
    ratings: Mapped[list["Rating"]] = relationship(
        "Rating",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        "Favorite",
        back_populates="book",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Index for visibility filtering
        Index("idx_books_visibility", "visibility"),
        # Index for category filtering
        Index("idx_books_category", "category"),
        # Composite index for duplicate detection (same hash per owner)
        Index("idx_books_owner_hash", "owner_id", "file_hash"),
        # Check constraint for valid status
        CheckConstraint(
            "status IN ('uploading', 'processing', 'ready', 'failed')",
            name="check_book_status",
        ),
        # Check constraint for valid visibility
        CheckConstraint(
            "visibility IN ('public', 'private', 'friends')",
            name="check_book_visibility",
        ),
    )

    def __repr__(self) -> str:
        return f"<Book {self.title[:30]} ({self.id})>"

    @property
    def is_deleted(self) -> bool:
        """Check if book is soft-deleted."""
        return self.deleted_at is not None

    @property
    def is_ready(self) -> bool:
        """Check if book is ready for reading."""
        return self.status == "ready"

    def soft_delete(self) -> None:
        """Mark book as deleted."""
        self.deleted_at = datetime.now(timezone.utc)


class Rating(Base, UUIDMixin):
    """Rating and review for a book."""

    __tablename__ = "ratings"

    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Rating 1-5 stars
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    book: Mapped["Book"] = relationship("Book", back_populates="ratings")
    user: Mapped["User"] = relationship("User", backref="ratings")

    __table_args__ = (
        # One rating per user per book
        UniqueConstraint("book_id", "user_id", name="uq_rating_book_user"),
        # Check constraint for valid rating value
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_value"),
        # Index for fetching book ratings
        Index("idx_ratings_book_id", "book_id"),
    )

    def __repr__(self) -> str:
        return f"<Rating {self.rating}/5 for book={self.book_id}>"


class Favorite(Base):
    """User's favorite books (bookmarks)."""

    __tablename__ = "favorites"

    # Composite primary key
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="CASCADE"),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Relationships
    book: Mapped["Book"] = relationship("Book", back_populates="favorites")
    user: Mapped["User"] = relationship("User", backref="favorites")

    __table_args__ = (
        # Index for user's favorites listing
        Index("idx_favorites_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Favorite user={self.user_id} book={self.book_id}>"
