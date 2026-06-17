"""Book club AI database models."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class BookClubAICredits(Base, UUIDMixin, TimestampMixin):
    """AI credits balance for a book club."""

    __tablename__ = "book_club_ai_credits"

    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True,
    )
    total_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    used_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    remaining_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    monthly_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1000, server_default="1000")
    reset_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<BookClubAICredits club={self.club_id} remaining={self.remaining_credits}>"


class BookClubAICreditTransaction(Base, UUIDMixin):
    """AI credit transaction log for a book club."""

    __tablename__ = "book_club_ai_credit_transactions"

    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # credit, debit
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_before: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now())

    __table_args__ = (
        Index("idx_ai_credit_transactions_club", "club_id"),
    )

    def __repr__(self) -> str:
        return f"<BookClubAICreditTransaction {self.transaction_type} amount={self.amount}>"


class BookClubAIModel(Base, UUIDMixin, TimestampMixin):
    """AI model configuration for a book club."""

    __tablename__ = "book_club_ai_models"

    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    input_cost_per_1m_tokens: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    output_cost_per_1m_tokens: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<BookClubAIModel {self.model_name} club={self.club_id}>"


class BookClubAIChatSession(Base, UUIDMixin, TimestampMixin):
    """AI chat session within a book club."""

    __tablename__ = "book_club_ai_chat_sessions"

    club_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    book_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("books.id", ondelete="SET NULL"), nullable=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    session_name: Mapped[str] = mapped_column(String(300), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    participant_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_messages: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    messages: Mapped[list["BookClubAIChatMessage"]] = relationship(
        "BookClubAIChatMessage", back_populates="session", cascade="all, delete-orphan",
    )
    participants: Mapped[list["BookClubAIChatParticipant"]] = relationship(
        "BookClubAIChatParticipant", back_populates="session", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<BookClubAIChatSession {self.session_name}>"


class BookClubAIChatMessage(Base, UUIDMixin):
    """Message in a book club AI chat session."""

    __tablename__ = "book_club_ai_chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("book_club_ai_chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    message_type: Mapped[str] = mapped_column(String(20), nullable=False)  # user, ai, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now())

    session: Mapped["BookClubAIChatSession"] = relationship("BookClubAIChatSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<BookClubAIChatMessage {self.message_type} session={self.session_id}>"


class BookClubAIChatParticipant(Base, UUIDMixin):
    """Participant in a book club AI chat session."""

    __tablename__ = "book_club_ai_chat_participants"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("book_club_ai_chat_sessions.id", ondelete="CASCADE"), nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now())
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["BookClubAIChatSession"] = relationship("BookClubAIChatSession", back_populates="participants")

    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_ai_chat_participant"),
        Index("idx_ai_chat_participants_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<BookClubAIChatParticipant session={self.session_id} user={self.user_id}>"
