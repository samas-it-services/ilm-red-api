"""Error logging database model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class ErrorLog(Base, UUIDMixin):
    """Application error log for tracking and debugging."""

    __tablename__ = "error_logs"

    # Auto-generated error code (e.g., ERR-00001)
    error_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )

    # Error details
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Context - user_id is FK, book_id is not (may reference deleted books)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    book_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Request metadata
    request_data: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        server_default="medium",
    )  # low, medium, high, critical

    # Client info
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Resolution tracking
    resolved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_error_logs_severity", "severity"),
        Index("idx_error_logs_resolved", "resolved"),
        Index("idx_error_logs_created_at", "created_at"),
        Index("idx_error_logs_error_type", "error_type"),
    )

    def __repr__(self) -> str:
        return f"<ErrorLog {self.error_code} ({self.error_type})>"
