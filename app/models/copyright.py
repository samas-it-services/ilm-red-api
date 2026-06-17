"""Copyright and book discovery reward database models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class BookDiscoveryReward(Base, UUIDMixin):
    """Reward record for users who discover and contribute book copyright information."""

    __tablename__ = "book_discovery_rewards"

    # Book relationship
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # User who discovered/contributed
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Copyright details
    isbn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    copyright_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    legal_declaration: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Passage content offered
    passage_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Link to suggestion that triggered this reward
    suggestion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Reward info
    points_awarded: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Discovery date
    discovery_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_book_discovery_rewards_book", "book_id"),
        Index("idx_book_discovery_rewards_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<BookDiscoveryReward book={self.book_id} user={self.user_id} points={self.points_awarded}>"
