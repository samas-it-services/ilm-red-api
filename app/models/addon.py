"""Addon system database models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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


class AddonRegistry(Base, UUIDMixin, TimestampMixin):
    """Registry of all available addons (marketplace)."""

    __tablename__ = "addon_registry"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(500), nullable=True)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    author_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list, server_default="{}")
    entry_point: Mapped[str | None] = mapped_column(String(500), nullable=True)
    manifest_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bundle_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_schema: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    permissions: Mapped[list[str]] = mapped_column(ARRAY(String(100)), default=list, server_default="{}")
    is_official: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_free: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rating: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    review_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'deprecated', 'disabled')",
            name="check_addon_registry_status",
        ),
        Index("idx_addon_registry_category", "category"),
        Index("idx_addon_registry_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<AddonRegistry {self.name} ({self.slug})>"


class AddonPermission(Base, UUIDMixin):
    """Defined permissions that addons can request."""

    __tablename__ = "addon_permissions"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_dangerous: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    def __repr__(self) -> str:
        return f"<AddonPermission {self.name}>"


class AddonTab(Base, UUIDMixin):
    """Custom tabs added by addons to book club views."""

    __tablename__ = "addon_tabs"

    book_club_addon_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("book_club_addon_config.id", ondelete="CASCADE"),
        nullable=True,
    )
    tab_id: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    def __repr__(self) -> str:
        return f"<AddonTab {self.tab_id} ({self.label})>"


class AddonStorage(Base, UUIDMixin, TimestampMixin):
    """Key-value storage for addon data scoped to a book club."""

    __tablename__ = "addon_storage"

    addon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("addon_registry.id", ondelete="CASCADE"),
        nullable=False,
    )
    book_club_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    __table_args__ = (
        UniqueConstraint("addon_id", "book_club_id", "key", name="uq_addon_storage_key"),
        Index("idx_addon_storage_addon_club", "addon_id", "book_club_id"),
    )

    def __repr__(self) -> str:
        return f"<AddonStorage addon={self.addon_id} key={self.key}>"


class AddonErrorLog(Base, UUIDMixin):
    """Error logs from addon execution."""

    __tablename__ = "addon_error_logs"

    addon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("addon_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_club_addon_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AddonErrorLog addon={self.addon_id} type={self.error_type}>"


class AddonUsageAnalytics(Base, UUIDMixin):
    """Usage analytics for addon actions."""

    __tablename__ = "addon_usage_analytics"

    book_club_addon_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now(), nullable=False,
    )

    __table_args__ = (
        Index("idx_addon_usage_user", "user_id"),
        Index("idx_addon_usage_action", "action"),
    )

    def __repr__(self) -> str:
        return f"<AddonUsageAnalytics action={self.action}>"


class AddonReview(Base, UUIDMixin, TimestampMixin):
    """User review of an addon."""

    __tablename__ = "addon_reviews"

    addon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("addon_registry.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    __table_args__ = (
        UniqueConstraint("addon_id", "user_id", name="uq_addon_review_user"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_addon_review_rating"),
        Index("idx_addon_reviews_addon", "addon_id"),
    )

    def __repr__(self) -> str:
        return f"<AddonReview addon={self.addon_id} rating={self.rating}>"


class GlobalAddonConfig(Base, UUIDMixin, TimestampMixin):
    """Platform-wide addon configuration (admin-managed)."""

    __tablename__ = "global_addon_config"

    addon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("addon_registry.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_default_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    max_installations_per_club: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    configured_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<GlobalAddonConfig addon={self.addon_id}>"


class BookClubAddonConfig(Base, UUIDMixin, TimestampMixin):
    """Per-club addon installation and configuration."""

    __tablename__ = "book_club_addon_config"

    addon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("addon_registry.id", ondelete="CASCADE"),
        nullable=False,
    )
    book_club_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_enabled_by_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    can_be_disabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    default_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    max_installations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    configured_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("addon_id", "book_club_id", name="uq_club_addon_config"),
        Index("idx_club_addon_config_club", "book_club_id"),
    )

    def __repr__(self) -> str:
        return f"<BookClubAddonConfig addon={self.addon_id} club={self.book_club_id}>"


class DefaultAddonSeed(Base, UUIDMixin):
    """Seed data defining which addons are enabled by default for new clubs."""

    __tablename__ = "default_addon_seeds"

    addon_slug: Mapped[str] = mapped_column(String(200), nullable=False)
    is_enabled_by_default: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    default_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<DefaultAddonSeed {self.addon_slug}>"
