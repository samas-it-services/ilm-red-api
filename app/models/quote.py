"""Quote database models."""

import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class Quote(Base, UUIDMixin, TimestampMixin):
    """Inspirational quote for the platform."""

    __tablename__ = "quotes"

    # Content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Categorization
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        default=list,
        server_default="{}",
    )

    # Display control
    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )
    display_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    # Stats
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    # Creator (admin who added it)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    creator: Mapped["User | None"] = relationship("User", backref="created_quotes")
    views: Mapped[list["QuoteView"]] = relationship(
        "QuoteView",
        back_populates="quote",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_quotes_is_active", "is_active"),
        Index("idx_quotes_is_featured", "is_featured"),
        Index("idx_quotes_display_date", "display_date"),
        Index("idx_quotes_category", "category"),
    )

    def __repr__(self) -> str:
        preview = self.text[:40] if self.text else ""
        return f"<Quote '{preview}...' by {self.author}>"


class QuoteView(Base, UUIDMixin):
    """Tracks views of a specific quote."""

    __tablename__ = "quote_views"

    # Which quote was viewed
    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("quotes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Who viewed it (optional, for anonymous users)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Tracking information
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamp
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationships
    quote: Mapped["Quote"] = relationship("Quote", back_populates="views")

    __table_args__ = (
        Index("idx_quote_views_quote_id", "quote_id"),
        Index("idx_quote_views_viewed_at", "viewed_at"),
    )

    def __repr__(self) -> str:
        return f"<QuoteView quote={self.quote_id} at={self.viewed_at}>"
