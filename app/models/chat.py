"""Chat-related database models."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User


class ChatSession(Base, UUIDMixin, TimestampMixin):
    """Chat session model for multi-turn AI conversations."""

    __tablename__ = "chat_sessions"

    # Owner relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional book context for book-specific chats
    book_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Session metadata
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_model: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Soft archive
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Wave 6: Extended session metadata
    ai_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    session_type: Mapped[str] = mapped_column(
        String(30), default="standard", server_default="standard"
    )
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expert_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    configuration: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    book_club_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", backref="chat_sessions")
    book: Mapped["Book | None"] = relationship("Book", backref="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    __table_args__ = (
        # Partial index for non-archived sessions by book
        Index("idx_chat_sessions_book", "book_id", postgresql_where="book_id IS NOT NULL"),
    )

    def __repr__(self) -> str:
        return f"<ChatSession {self.title or 'Untitled'} ({self.id})>"

    @property
    def is_archived(self) -> bool:
        """Check if session is archived."""
        return self.archived_at is not None

    def archive(self) -> None:
        """Archive this session."""
        self.archived_at = datetime.now(UTC)

    def unarchive(self) -> None:
        """Unarchive this session."""
        self.archived_at = None


class ChatMessage(Base, UUIDMixin):
    """Chat message model for storing conversation history."""

    __tablename__ = "chat_messages"

    # Session relationship
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Message content
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # AI response metadata (null for user messages)
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    finish_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Safety information
    safety_flags: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
    )

    # Wave 6: Extended message fields
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
    feedback: Mapped["MessageFeedback | None"] = relationship(
        "MessageFeedback",
        back_populates="message",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Index for fetching messages by session in order
        Index("idx_chat_messages_session_created", "session_id", "created_at"),
        # Check constraint for valid role
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="check_message_role",
        ),
    )

    def __repr__(self) -> str:
        content_preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"<ChatMessage {self.role}: {content_preview}>"

    @property
    def is_user_message(self) -> bool:
        """Check if this is a user message."""
        return self.role == "user"

    @property
    def is_assistant_message(self) -> bool:
        """Check if this is an assistant message."""
        return self.role == "assistant"

    @property
    def total_tokens(self) -> int | None:
        """Get total tokens for this message."""
        if self.tokens_input is None and self.tokens_output is None:
            return None
        return (self.tokens_input or 0) + (self.tokens_output or 0)


class MessageFeedback(Base, UUIDMixin):
    """User feedback on AI messages (thumbs up/down)."""

    __tablename__ = "message_feedback"

    # Relationships
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Feedback data
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # -1 or 1
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    message: Mapped["ChatMessage"] = relationship("ChatMessage", back_populates="feedback")
    user: Mapped["User"] = relationship("User", backref="message_feedback")

    __table_args__ = (
        # One feedback per user per message
        UniqueConstraint("message_id", "user_id", name="uq_feedback_message_user"),
        # Check constraint for valid rating
        CheckConstraint("rating IN (-1, 1)", name="check_feedback_rating"),
    )

    def __repr__(self) -> str:
        rating_str = "thumbs up" if self.rating == 1 else "thumbs down"
        return f"<MessageFeedback {rating_str} for message={self.message_id}>"

    @property
    def is_positive(self) -> bool:
        """Check if feedback is positive (thumbs up)."""
        return self.rating == 1

    @property
    def is_negative(self) -> bool:
        """Check if feedback is negative (thumbs down)."""
        return self.rating == -1


# ============================================================================
# Wave 6: Extended Chat Models
# ============================================================================


class ChatAdminAccessLog(Base, UUIDMixin):
    """Audit log for admin access to chat sessions."""

    __tablename__ = "chat_admin_access_logs"

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # view, export, delete
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    admin_user: Mapped["User"] = relationship("User", backref="chat_admin_access_logs")
    session: Mapped["ChatSession"] = relationship("ChatSession", backref="admin_access_logs")

    __table_args__ = (
        Index("idx_chat_admin_access_admin_created", "admin_user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ChatAdminAccessLog admin={self.admin_user_id} session={self.session_id} action={self.action}>"


class ChatEncryptionKey(Base, UUIDMixin):
    """Encryption keys for secure chat sessions."""

    __tablename__ = "chat_encryption_keys"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    key_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), default="AES-256-GCM", server_default="AES-256-GCM")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    session: Mapped["ChatSession"] = relationship("ChatSession", backref="encryption_key")

    def __repr__(self) -> str:
        return f"<ChatEncryptionKey session={self.session_id} v{self.key_version}>"


class ChatMessageRating(Base, UUIDMixin):
    """Detailed rating for individual chat messages (separate from MessageFeedback)."""

    __tablename__ = "chat_message_ratings"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5 stars
    category: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # accuracy, helpfulness, clarity
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    message: Mapped["ChatMessage"] = relationship("ChatMessage", backref="ratings")
    user: Mapped["User"] = relationship("User", backref="chat_message_ratings")

    __table_args__ = (
        UniqueConstraint("message_id", "user_id", "category", name="uq_chat_message_rating"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_chat_message_rating_value"),
    )

    def __repr__(self) -> str:
        return f"<ChatMessageRating {self.rating}/5 message={self.message_id}>"
