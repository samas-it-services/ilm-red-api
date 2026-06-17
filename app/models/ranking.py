"""Ranking system database models."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class RankingContext(Base, UUIDMixin, TimestampMixin):
    """Ranking context defines a scope for rankings (global, corporate, book club)."""

    __tablename__ = "ranking_contexts"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # global, corporate, book_club
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    settings: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )

    # Relationships
    ranking_settings: Mapped[list["RankingSetting"]] = relationship(
        "RankingSetting",
        back_populates="context",
        cascade="all, delete-orphan",
    )
    user_rankings: Mapped[list["UserContextRanking"]] = relationship(
        "UserContextRanking",
        back_populates="context",
        cascade="all, delete-orphan",
    )
    points_history: Mapped[list["ContextPointsHistory"]] = relationship(
        "ContextPointsHistory",
        back_populates="context",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "type IN ('global', 'corporate', 'book_club')",
            name="check_ranking_context_type",
        ),
        Index("idx_ranking_contexts_type", "type"),
        Index("idx_ranking_contexts_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<RankingContext {self.name} ({self.type})>"


class RankingSetting(Base, UUIDMixin, TimestampMixin):
    """Points configuration for a ranking context."""

    __tablename__ = "ranking_settings"

    context_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ranking_contexts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    points_value: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    multiplier_config: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )

    # Relationships
    context: Mapped["RankingContext"] = relationship(
        "RankingContext",
        back_populates="ranking_settings",
    )

    __table_args__ = (
        Index("idx_ranking_settings_context_activity", "context_id", "activity_type"),
    )

    def __repr__(self) -> str:
        return f"<RankingSetting {self.activity_type}: {self.points_value}pts>"


class UserContextRanking(Base, UUIDMixin, TimestampMixin):
    """User's ranking within a specific context."""

    __tablename__ = "user_context_rankings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    context_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ranking_contexts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    percentile: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Activity counters
    books_uploaded: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    books_reviewed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    badges_earned_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Timestamps
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="context_rankings")
    context: Mapped["RankingContext"] = relationship(
        "RankingContext",
        back_populates="user_rankings",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "context_id", name="uq_user_context_ranking"),
        Index("idx_user_context_rankings_rank", "context_id", "rank_position"),
        Index("idx_user_context_rankings_points", "context_id", "total_points"),
    )

    def __repr__(self) -> str:
        return f"<UserContextRanking user={self.user_id} rank={self.rank_position}>"


class ContextPointsHistory(Base, UUIDMixin):
    """History of points earned by a user in a context."""

    __tablename__ = "context_points_history"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    context_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ranking_contexts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 'metadata' is reserved by SQLAlchemy Declarative; keep DB column name.
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="points_history")
    context: Mapped["RankingContext"] = relationship(
        "RankingContext",
        back_populates="points_history",
    )

    __table_args__ = (
        Index("idx_points_history_user_context", "user_id", "context_id"),
        Index("idx_points_history_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ContextPointsHistory {self.source}: {self.points}pts>"
