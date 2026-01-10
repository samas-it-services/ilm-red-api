"""Safety-related database models."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.chat import ChatSession, ChatMessage


class SafetyFlag(Base):
    """Record of content safety checks and violations."""

    __tablename__ = "safety_flags"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Relationships
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Content details
    content_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'input' or 'output'
    content_preview: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # First 500 chars for review

    # Moderation results
    categories: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )  # Category flags from moderation API
    severity: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # low, medium, high, critical
    scores: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # Raw scores from moderation API

    # Action taken
    action_taken: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # allowed, warned, blocked, flagged_for_review

    # Metadata
    model_used: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # Moderation model used

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="safety_flags")
    message: Mapped["ChatMessage | None"] = relationship("ChatMessage", backref="safety_flags")
    session: Mapped["ChatSession | None"] = relationship("ChatSession", backref="safety_flags")

    __table_args__ = (
        Index("idx_safety_flags_user_created", "user_id", created_at.desc()),
        Index(
            "idx_safety_flags_severity",
            "severity",
            postgresql_where="severity IN ('high', 'critical')",
        ),
        Index(
            "idx_safety_flags_action",
            "action_taken",
            postgresql_where="action_taken = 'flagged_for_review'",
        ),
        CheckConstraint(
            "content_type IN ('input', 'output')",
            name="check_content_type",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="check_severity",
        ),
        CheckConstraint(
            "action_taken IN ('allowed', 'warned', 'blocked', 'flagged_for_review')",
            name="check_action_taken",
        ),
    )

    def __repr__(self) -> str:
        return f"<SafetyFlag {self.severity} {self.action_taken} user={self.user_id}>"

    @property
    def is_blocked(self) -> bool:
        """Check if content was blocked."""
        return self.action_taken == "blocked"

    @property
    def is_high_severity(self) -> bool:
        """Check if this is a high or critical severity flag."""
        return self.severity in ("high", "critical")

    @property
    def flagged_categories(self) -> list[str]:
        """Get list of flagged category names."""
        return [k for k, v in self.categories.items() if v]
