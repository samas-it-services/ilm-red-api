"""Public Q&A database models."""

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
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User


class PublicQA(Base, UUIDMixin, TimestampMixin):
    """Public Q&A promoted from chat conversations."""

    __tablename__ = "public_qa"

    original_message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Content
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Categorization
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        default=list,
        server_default="{}",
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status and visibility
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )  # draft, published, archived
    visibility: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="public",
        server_default="public",
    )  # public, premium, admin
    featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )

    # Voting
    upvotes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    downvotes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    net_votes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Engagement metrics
    view_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    helpful_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    not_helpful_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Edit tracking
    edit_history: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
    )

    # Publishing
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_edited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    book: Mapped["Book"] = relationship("Book", backref="public_qa")
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        backref="public_qa",
    )
    publisher: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[published_by],
    )
    editor: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[last_edited_by],
    )
    edit_history_records: Mapped[list["PublicQAEditHistory"]] = relationship(
        "PublicQAEditHistory",
        back_populates="qa",
        cascade="all, delete-orphan",
        order_by="PublicQAEditHistory.version_number.desc()",
    )
    feedback_records: Mapped[list["PublicQAFeedback"]] = relationship(
        "PublicQAFeedback",
        back_populates="qa",
        cascade="all, delete-orphan",
    )
    views: Mapped[list["PublicQAView"]] = relationship(
        "PublicQAView",
        back_populates="qa",
        cascade="all, delete-orphan",
    )
    votes: Mapped[list["PublicQAVote"]] = relationship(
        "PublicQAVote",
        back_populates="qa",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="check_public_qa_status",
        ),
        CheckConstraint(
            "visibility IN ('public', 'premium', 'admin')",
            name="check_public_qa_visibility",
        ),
        Index("idx_public_qa_status", "status"),
        Index("idx_public_qa_category", "category"),
        Index("idx_public_qa_featured", "featured"),
        Index("idx_public_qa_net_votes", "net_votes"),
    )

    def __repr__(self) -> str:
        return f"<PublicQA {self.title[:30]} ({self.status})>"


class PublicQAEditHistory(Base, UUIDMixin):
    """Edit history for a public Q&A entry."""

    __tablename__ = "public_qa_edit_history"

    qa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public_qa.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    edited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    edited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Previous values
    previous_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    previous_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_tags: Mapped[list | None] = mapped_column(ARRAY(String(50)), nullable=True)
    previous_category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Edit metadata
    edit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    qa: Mapped["PublicQA"] = relationship(
        "PublicQA",
        back_populates="edit_history_records",
    )
    editor: Mapped["User"] = relationship("User", backref="qa_edits")

    __table_args__ = (
        Index("idx_qa_edit_history_qa_version", "qa_id", "version_number"),
    )

    def __repr__(self) -> str:
        return f"<PublicQAEditHistory qa={self.qa_id} v{self.version_number}>"


class PublicQAFeedback(Base, UUIDMixin):
    """User feedback on a public Q&A entry."""

    __tablename__ = "public_qa_feedback"

    qa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public_qa.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    feedback_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # helpful, not_helpful
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    qa: Mapped["PublicQA"] = relationship(
        "PublicQA",
        back_populates="feedback_records",
    )
    user: Mapped["User"] = relationship("User", backref="qa_feedback")

    __table_args__ = (
        CheckConstraint(
            "feedback_type IN ('helpful', 'not_helpful')",
            name="check_qa_feedback_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<PublicQAFeedback {self.feedback_type} for qa={self.qa_id}>"


class PublicQAView(Base, UUIDMixin):
    """View tracking for public Q&A entries."""

    __tablename__ = "public_qa_views"

    qa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public_qa.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    viewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    qa: Mapped["PublicQA"] = relationship(
        "PublicQA",
        back_populates="views",
    )
    viewer: Mapped["User | None"] = relationship("User", backref="qa_views")

    __table_args__ = (
        Index("idx_qa_views_qa_viewer", "qa_id", "viewer_id"),
        Index("idx_qa_views_qa_ip", "qa_id", "ip_address"),
    )

    def __repr__(self) -> str:
        return f"<PublicQAView qa={self.qa_id} at {self.viewed_at}>"


class PublicQAVote(Base, UUIDMixin):
    """Vote on a public Q&A entry."""

    __tablename__ = "public_qa_votes"

    public_qa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public_qa.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    vote_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # upvote, downvote
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    qa: Mapped["PublicQA"] = relationship(
        "PublicQA",
        back_populates="votes",
    )
    user: Mapped["User"] = relationship("User", backref="qa_votes")

    __table_args__ = (
        UniqueConstraint("public_qa_id", "user_id", name="uq_public_qa_vote_user"),
        CheckConstraint(
            "vote_type IN ('upvote', 'downvote')",
            name="check_qa_vote_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<PublicQAVote {self.vote_type} by user={self.user_id}>"
