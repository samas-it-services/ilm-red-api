"""Blog-related database models."""

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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class BlogPost(Base, UUIDMixin, TimestampMixin):
    """Blog post model."""

    __tablename__ = "blog_posts"

    # Author
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(600), unique=True, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    featured_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status and visibility
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )
    visibility: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="public",
        server_default="public",
    )

    # Flags
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Publishing
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Stats (denormalized for performance)
    view_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    like_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    comment_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Reading metrics
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reading_time: Mapped[int | None] = mapped_column(Integer, nullable=True)  # minutes

    # Relationships
    author: Mapped["User"] = relationship("User", backref="blog_posts")  # noqa: F821
    categories: Mapped[list["BlogPostCategory"]] = relationship(
        "BlogPostCategory",
        back_populates="post",
        cascade="all, delete-orphan",
    )
    tags: Mapped[list["BlogPostTag"]] = relationship(
        "BlogPostTag",
        back_populates="post",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list["BlogComment"]] = relationship(
        "BlogComment",
        back_populates="post",
        cascade="all, delete-orphan",
    )
    likes: Mapped[list["BlogLike"]] = relationship(
        "BlogLike",
        back_populates="post",
        cascade="all, delete-orphan",
    )
    views: Mapped[list["BlogView"]] = relationship(
        "BlogView",
        back_populates="post",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_blog_posts_status", "status"),
        Index("idx_blog_posts_published_at", "published_at"),
        Index("idx_blog_posts_is_featured", "is_featured"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="check_blog_post_status",
        ),
        CheckConstraint(
            "visibility IN ('public', 'private', 'members_only')",
            name="check_blog_post_visibility",
        ),
    )

    def __repr__(self) -> str:
        return f"<BlogPost {self.title[:30]} ({self.id})>"


class BlogCategory(Base, UUIDMixin):
    """Blog category model."""

    __tablename__ = "blog_categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Relationships
    posts: Mapped[list["BlogPostCategory"]] = relationship(
        "BlogPostCategory",
        back_populates="category",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<BlogCategory {self.name} ({self.id})>"


class BlogTag(Base, UUIDMixin):
    """Blog tag model."""

    __tablename__ = "blog_tags"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationships
    posts: Mapped[list["BlogPostTag"]] = relationship(
        "BlogPostTag",
        back_populates="tag",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<BlogTag {self.name} ({self.id})>"


class BlogPostCategory(Base, UUIDMixin):
    """Many-to-many relationship between blog posts and categories."""

    __tablename__ = "blog_post_categories"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_categories.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    post: Mapped["BlogPost"] = relationship("BlogPost", back_populates="categories")
    category: Mapped["BlogCategory"] = relationship("BlogCategory", back_populates="posts")

    __table_args__ = (
        UniqueConstraint("post_id", "category_id", name="uq_blog_post_category"),
        Index("idx_blog_post_categories_post_id", "post_id"),
        Index("idx_blog_post_categories_category_id", "category_id"),
    )

    def __repr__(self) -> str:
        return f"<BlogPostCategory post={self.post_id} category={self.category_id}>"


class BlogPostTag(Base, UUIDMixin):
    """Many-to-many relationship between blog posts and tags."""

    __tablename__ = "blog_post_tags"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_tags.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    post: Mapped["BlogPost"] = relationship("BlogPost", back_populates="tags")
    tag: Mapped["BlogTag"] = relationship("BlogTag", back_populates="posts")

    __table_args__ = (
        UniqueConstraint("post_id", "tag_id", name="uq_blog_post_tag"),
        Index("idx_blog_post_tags_post_id", "post_id"),
        Index("idx_blog_post_tags_tag_id", "tag_id"),
    )

    def __repr__(self) -> str:
        return f"<BlogPostTag post={self.post_id} tag={self.tag_id}>"


class BlogComment(Base, UUIDMixin, TimestampMixin):
    """Blog comment model with threaded replies."""

    __tablename__ = "blog_comments"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Threaded replies
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_comments.id", ondelete="CASCADE"),
        nullable=True,
    )

    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Relationships
    post: Mapped["BlogPost"] = relationship("BlogPost", back_populates="comments")
    author: Mapped["User"] = relationship("User", backref="blog_comments")  # noqa: F821
    parent: Mapped["BlogComment | None"] = relationship(
        "BlogComment",
        remote_side="BlogComment.id",
        backref="replies",
    )

    __table_args__ = (
        Index("idx_blog_comments_post_id", "post_id"),
        Index("idx_blog_comments_parent_id", "parent_id"),
    )

    def __repr__(self) -> str:
        return f"<BlogComment {self.id} on post={self.post_id}>"


class BlogLike(Base, UUIDMixin):
    """Blog post like model."""

    __tablename__ = "blog_likes"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationships
    post: Mapped["BlogPost"] = relationship("BlogPost", back_populates="likes")
    user: Mapped["User"] = relationship("User", backref="blog_likes")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_blog_like_post_user"),
        Index("idx_blog_likes_post_id", "post_id"),
        Index("idx_blog_likes_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<BlogLike user={self.user_id} post={self.post_id}>"


class BlogView(Base, UUIDMixin):
    """Blog post view tracking model."""

    __tablename__ = "blog_views"

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationships
    post: Mapped["BlogPost"] = relationship("BlogPost", back_populates="views")

    __table_args__ = (
        Index("idx_blog_views_post_id", "post_id"),
        Index("idx_blog_views_viewed_at", "viewed_at"),
    )

    def __repr__(self) -> str:
        return f"<BlogView post={self.post_id} at {self.viewed_at}>"
