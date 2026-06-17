"""Expert configuration and session analytics database models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ExpertConfiguration(Base, UUIDMixin, TimestampMixin):
    """Expert configuration for AI chat personas and model routing."""

    __tablename__ = "expert_configurations"

    # Core fields
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    field: Mapped[str | None] = mapped_column(String(200), nullable=True)
    traits: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
    )

    # Model preferences
    preferred_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preferred_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Prompt configuration
    system_prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Model configuration data (named model_config_data to avoid Pydantic conflict)
    model_config_data: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    __table_args__ = (
        Index("idx_expert_configurations_category", "category"),
        Index("idx_expert_configurations_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<ExpertConfiguration {self.name} ({self.category})>"


class SessionParticipant(Base, UUIDMixin):
    """Participant in a chat session (for collaborative/moderated sessions)."""

    __tablename__ = "session_participants"

    # Session relationship
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # User relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Role in session
    role: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # owner, moderator, participant

    # Timestamp
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_session_participant"),
        Index("idx_session_participants_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<SessionParticipant session={self.session_id} user={self.user_id} role={self.role}>"


class SessionAnalytics(Base, UUIDMixin, TimestampMixin):
    """Analytics data for chat sessions."""

    __tablename__ = "session_analytics"

    # Session relationship
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Expert and model info
    expert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    model_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_used: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Usage metrics
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    cost_usd: Mapped[float] = mapped_column(
        Numeric(10, 6), nullable=False, default=0, server_default="0"
    )

    # Performance metrics
    avg_response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Quality metrics
    user_satisfaction_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # QA promotion
    promoted_to_qa: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    # Referenced books
    books_referenced: Mapped[list] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        default=list,
        server_default="{}",
    )

    # Category
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("idx_session_analytics_session", "session_id"),
        Index("idx_session_analytics_expert", "expert_id"),
    )

    def __repr__(self) -> str:
        return f"<SessionAnalytics session={self.session_id} messages={self.message_count}>"
