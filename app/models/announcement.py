"""Feature announcement database models."""

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class FeatureAnnouncement(Base, UUIDMixin, TimestampMixin):
    """Feature announcement model for platform updates and new features."""

    __tablename__ = "feature_announcements"

    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(600), unique=True, nullable=False, index=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    featured_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    # Priority
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="normal",
        server_default="normal",
    )

    # Flags
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Publishing
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Stats (denormalized for performance)
    view_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Relationships
    announcement_views: Mapped[list["FeatureAnnouncementView"]] = relationship(
        "FeatureAnnouncementView",
        back_populates="announcement",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_feature_announcements_status", "status"),
        Index("idx_feature_announcements_published_at", "published_at"),
        Index("idx_feature_announcements_priority", "priority"),
        Index("idx_feature_announcements_is_pinned", "is_pinned"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="check_announcement_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'critical')",
            name="check_announcement_priority",
        ),
    )

    def __repr__(self) -> str:
        return f"<FeatureAnnouncement {self.title[:30]} ({self.id})>"


class FeatureAnnouncementView(Base, UUIDMixin):
    """Feature announcement view tracking model."""

    __tablename__ = "feature_announcement_views"

    announcement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("feature_announcements.id", ondelete="CASCADE"),
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
    announcement: Mapped["FeatureAnnouncement"] = relationship(
        "FeatureAnnouncement",
        back_populates="announcement_views",
    )

    __table_args__ = (
        Index("idx_announcement_views_announcement_id", "announcement_id"),
        Index("idx_announcement_views_user_id", "user_id"),
        Index("idx_announcement_views_viewed_at", "viewed_at"),
    )

    def __repr__(self) -> str:
        return f"<FeatureAnnouncementView announcement={self.announcement_id} at {self.viewed_at}>"
