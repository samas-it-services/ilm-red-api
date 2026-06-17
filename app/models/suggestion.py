"""Suggestion system database models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class UserSuggestion(Base, UUIDMixin, TimestampMixin):
    """User suggestion submitted for AI or admin response."""

    __tablename__ = "user_suggestions"

    # User relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Suggestion content
    suggestion_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    detected_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Book passage offering
    has_passage_offer: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    offered_book_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    offered_book_title: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # AI response
    ai_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Admin response
    admin_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_responder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    admin_response_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Status: pending, responded, admin_responded, closed
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", server_default="pending"
    )

    # Priority: low, medium, high
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium", server_default="medium"
    )

    # Read status
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    __table_args__ = (
        Index("idx_user_suggestions_user", "user_id"),
        Index("idx_user_suggestions_status", "status"),
        Index("idx_user_suggestions_priority", "priority"),
    )

    def __repr__(self) -> str:
        preview = self.suggestion_text[:40] + "..." if len(self.suggestion_text) > 40 else self.suggestion_text
        return f"<UserSuggestion {preview} ({self.status})>"


class SuggestionConfig(Base, UUIDMixin, TimestampMixin):
    """Per-user suggestion feature configuration."""

    __tablename__ = "suggestion_configs"

    # User relationship (one-to-one)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Configuration
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    ai_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    daily_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )

    __table_args__ = (
        Index("idx_suggestion_configs_user", "user_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<SuggestionConfig user={self.user_id} enabled={self.is_enabled}>"


class SuggestionSystemConfig(Base, UUIDMixin, TimestampMixin):
    """Global system configuration for the suggestion feature."""

    __tablename__ = "suggestion_system_configs"

    # System settings
    system_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    default_ai_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    default_daily_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )
    available_models: Mapped[list] = mapped_column(
        ARRAY(String(50)),
        default=list,
        server_default="{}",
    )

    def __repr__(self) -> str:
        return f"<SuggestionSystemConfig enabled={self.system_enabled}>"


class SuggestionFeedback(Base, UUIDMixin, TimestampMixin):
    """User feedback on a suggestion response."""

    __tablename__ = "suggestion_feedback"

    # Suggestion relationship
    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_suggestions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # User relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Feedback data
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_suggestion_feedback_suggestion", "suggestion_id"),
        Index("idx_suggestion_feedback_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<SuggestionFeedback suggestion={self.suggestion_id} type={self.feedback_type}>"


class SuggestionNotification(Base, UUIDMixin):
    """Notification related to a suggestion."""

    __tablename__ = "suggestion_notifications"

    # User relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Suggestion relationship
    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_suggestions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Notification content
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Read status
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_suggestion_notifications_user", "user_id"),
        Index("idx_suggestion_notifications_unread", "user_id", "is_read"),
    )

    def __repr__(self) -> str:
        return f"<SuggestionNotification user={self.user_id} type={self.notification_type}>"


class UserSuggestionUsage(Base, UUIDMixin, TimestampMixin):
    """Daily suggestion usage tracking per user."""

    __tablename__ = "user_suggestion_usage"

    # User relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Usage tracking
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    usage_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_suggestion_usage_user_date"),
        Index("idx_suggestion_usage_user_date", "user_id", "date"),
    )

    def __repr__(self) -> str:
        return f"<UserSuggestionUsage user={self.user_id} date={self.date} count={self.usage_count}>"
