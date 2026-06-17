"""Gamification database models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class GamificationActivity(Base, UUIDMixin, TimestampMixin):
    """Activity type definition for gamification."""

    __tablename__ = "gamification_activities"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cooldown_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_daily_occurrences: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    def __repr__(self) -> str:
        return f"<GamificationActivity {self.name} ({self.points}pts)>"


class PointsHistory(Base, UUIDMixin):
    """Points ledger for tracking all point changes."""

    __tablename__ = "points_history"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 'metadata' is reserved by SQLAlchemy Declarative; keep DB column name.
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<PointsHistory user={self.user_id} {self.points:+d}pts>"


class UserActivityLog(Base, UUIDMixin):
    """Log of user activities for gamification tracking."""

    __tablename__ = "user_activity_log"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gamification_activities.id", ondelete="CASCADE"),
        nullable=False,
    )
    points_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 'metadata' is reserved by SQLAlchemy Declarative; keep DB column name.
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<UserActivityLog user={self.user_id} activity={self.activity_id}>"


class Badge(Base, UUIDMixin, TimestampMixin):
    """Badge definition."""

    __tablename__ = "badges"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="achievement"
    )  # achievement, participation, special, seasonal, admin
    icon: Mapped[str | None] = mapped_column(String(200), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rarity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="common"
    )  # common, uncommon, rare, epic, legendary
    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    def __repr__(self) -> str:
        return f"<Badge {self.name} ({self.rarity})>"


class UserBadge(Base, UUIDMixin):
    """Badge earned by a user."""

    __tablename__ = "user_badges"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    badge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("badges.id", ondelete="CASCADE"),
        nullable=False,
    )
    awarded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # 'metadata' is reserved by SQLAlchemy Declarative; keep DB column name.
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    badge: Mapped["Badge"] = relationship("Badge")

    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
    )

    def __repr__(self) -> str:
        return f"<UserBadge user={self.user_id} badge={self.badge_id}>"


class Rank(Base, UUIDMixin, TimestampMixin):
    """Rank/level definition."""

    __tablename__ = "ranks"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    min_points: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(200), nullable=True)
    benefits: Mapped[list[str]] = mapped_column(
        ARRAY(String(200)), default=list, server_default="{}"
    )

    def __repr__(self) -> str:
        return f"<Rank {self.name} (level {self.level}, {self.min_points}pts)>"


class UserRank(Base, UUIDMixin, TimestampMixin):
    """User's current rank."""

    __tablename__ = "user_ranks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    rank_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ranks.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_points_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank_achieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    rank: Mapped["Rank"] = relationship("Rank")

    def __repr__(self) -> str:
        return f"<UserRank user={self.user_id} rank={self.rank_id} pts={self.current_points}>"
