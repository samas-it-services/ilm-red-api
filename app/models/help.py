"""Help/Documentation database models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class HelpCategory(Base, UUIDMixin):
    """Help documentation category model."""

    __tablename__ = "help_categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Relationships
    articles: Mapped[list["HelpArticle"]] = relationship(
        "HelpArticle",
        back_populates="category",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_help_categories_sort_order", "sort_order"),
    )

    def __repr__(self) -> str:
        return f"<HelpCategory {self.name} ({self.id})>"


class HelpArticle(Base, UUIDMixin, TimestampMixin):
    """Help article model with multilingual support (English + Urdu)."""

    __tablename__ = "help_articles"

    # Category
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("help_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    slug: Mapped[str] = mapped_column(String(300), unique=True, nullable=False, index=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    # Author
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # English content (primary)
    title_en: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    content_en: Mapped[str] = mapped_column(Text, nullable=False)

    # Urdu content (optional)
    title_ur: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_ur: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(50)),
        nullable=True,
        default=list,
        server_default="{}",
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Flags
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Stats (denormalized for performance)
    view_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    helpful_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    not_helpful_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Visibility and publishing
    visibility: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="public",
        server_default="public",
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    category: Mapped["HelpCategory"] = relationship("HelpCategory", back_populates="articles")
    author: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[author_id],
        backref="help_articles_authored",
    )
    publisher: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[published_by],
        backref="help_articles_published",
    )
    article_views: Mapped[list["HelpArticleView"]] = relationship(
        "HelpArticleView",
        back_populates="article",
        cascade="all, delete-orphan",
    )
    feedbacks: Mapped[list["HelpArticleFeedback"]] = relationship(
        "HelpArticleFeedback",
        back_populates="article",
        cascade="all, delete-orphan",
    )
    shares: Mapped[list["HelpArticleShare"]] = relationship(
        "HelpArticleShare",
        back_populates="article",
        cascade="all, delete-orphan",
    )
    screenshots: Mapped[list["HelpArticleScreenshot"]] = relationship(
        "HelpArticleScreenshot",
        back_populates="article",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_help_articles_status", "status"),
        Index("idx_help_articles_sort_order", "sort_order"),
        Index("idx_help_articles_published_at", "published_at"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="check_help_article_status",
        ),
        CheckConstraint(
            "visibility IN ('public', 'private', 'members_only')",
            name="check_help_article_visibility",
        ),
    )

    def __repr__(self) -> str:
        return f"<HelpArticle {self.title_en[:30]} ({self.id})>"


class HelpArticleView(Base, UUIDMixin):
    """Help article view tracking model."""

    __tablename__ = "help_article_views"

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("help_articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationships
    article: Mapped["HelpArticle"] = relationship("HelpArticle", back_populates="article_views")

    __table_args__ = (
        Index("idx_help_article_views_article_id", "article_id"),
        Index("idx_help_article_views_viewed_at", "viewed_at"),
    )

    def __repr__(self) -> str:
        return f"<HelpArticleView article={self.article_id} at {self.viewed_at}>"


class HelpArticleFeedback(Base, UUIDMixin):
    """Help article feedback model (helpful / not helpful)."""

    __tablename__ = "help_article_feedbacks"

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("help_articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False)  # helpful / not_helpful
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationships
    article: Mapped["HelpArticle"] = relationship("HelpArticle", back_populates="feedbacks")

    __table_args__ = (
        Index("idx_help_article_feedbacks_article_id", "article_id"),
        CheckConstraint(
            "feedback_type IN ('helpful', 'not_helpful')",
            name="check_help_feedback_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<HelpArticleFeedback {self.feedback_type} for article={self.article_id}>"


class HelpArticleShare(Base, UUIDMixin):
    """Help article share tracking model."""

    __tablename__ = "help_article_shares"

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("help_articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    share_method: Mapped[str] = mapped_column(String(50), nullable=False)  # link, email, social
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    shared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationships
    article: Mapped["HelpArticle"] = relationship("HelpArticle", back_populates="shares")

    __table_args__ = (
        Index("idx_help_article_shares_article_id", "article_id"),
    )

    def __repr__(self) -> str:
        return f"<HelpArticleShare article={self.article_id} via {self.share_method}>"


class HelpArticleScreenshot(Base, UUIDMixin):
    """Help article screenshot/image model."""

    __tablename__ = "help_article_screenshots"

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("help_articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Relationships
    article: Mapped["HelpArticle"] = relationship("HelpArticle", back_populates="screenshots")

    __table_args__ = (
        Index("idx_help_article_screenshots_article_id", "article_id"),
    )

    def __repr__(self) -> str:
        return f"<HelpArticleScreenshot article={self.article_id} order={self.sort_order}>"
