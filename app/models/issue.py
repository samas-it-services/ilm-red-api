"""User issue and feature request database models."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


# Valid issue types
ISSUE_TYPES = [
    "bug",
    "feature_request",
    "question",
    "technical_issue",
    "account_issue",
]

# Valid priority levels
ISSUE_PRIORITIES = ["low", "medium", "high", "urgent"]

# Valid issue statuses
ISSUE_STATUSES = ["open", "in_progress", "resolved", "closed"]


class UserIssue(Base, UUIDMixin, TimestampMixin):
    """User-submitted issue or feature request."""

    __tablename__ = "user_issues"

    # Reporter
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Issue classification
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issue_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="bug",
        server_default="bug",
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Priority and status
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
        server_default="medium",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        server_default="open",
    )

    # Optional context references
    book_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Flexible data storage
    attachments: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default="{}",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="issues")
    responses: Mapped[list["UserIssueResponse"]] = relationship(
        "UserIssueResponse",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="UserIssueResponse.created_at.asc()",
    )

    __table_args__ = (
        # Check constraints for valid enum values
        CheckConstraint(
            "issue_type IN ('bug', 'feature_request', 'question', 'technical_issue', 'account_issue')",
            name="check_issue_type",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="check_issue_priority",
        ),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'closed')",
            name="check_issue_status",
        ),
        # Indexes for common queries
        Index("idx_user_issues_status", "status"),
        Index("idx_user_issues_type", "issue_type"),
        Index("idx_user_issues_priority", "priority"),
        Index("idx_user_issues_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<UserIssue {self.title[:30]} ({self.status})>"


class UserIssueResponse(Base, UUIDMixin):
    """Response to a user issue from staff or system."""

    __tablename__ = "user_issue_responses"

    # Parent issue
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Responder
    responder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Response content
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )

    # Optional link to a help article
    attached_article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationships
    issue: Mapped["UserIssue"] = relationship("UserIssue", back_populates="responses")
    responder: Mapped["User"] = relationship("User", backref="issue_responses")

    __table_args__ = (
        Index("idx_issue_responses_issue_id", "issue_id"),
    )

    def __repr__(self) -> str:
        return f"<UserIssueResponse issue={self.issue_id} by={self.responder_id}>"
