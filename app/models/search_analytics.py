"""Search analytics database model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class SearchAnalytics(Base, UUIDMixin):
    """Tracks search queries and their outcomes for analytics."""

    __tablename__ = "search_analytics"

    # Who searched (nullable for anonymous users)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # Search details
    search_query: Mapped[str] = mapped_column(String(500), nullable=False)
    search_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # e.g., full_text, semantic, autocomplete
    search_source: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # e.g., web, mobile, api

    # Filters applied during the search
    filters_used: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )

    # Results
    result_count: Mapped[int] = mapped_column(Integer, nullable=False)
    results_clicked: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    # Performance
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cache_hit: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<SearchAnalytics q='{self.search_query[:30]}' results={self.result_count}>"
