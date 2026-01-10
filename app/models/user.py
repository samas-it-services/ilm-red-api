"""User-related database models."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    pass


class User(Base, UUIDMixin, TimestampMixin):
    """User account model."""

    __tablename__ = "users"

    # Core fields
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)  # NULL for OAuth users

    # Profile
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Roles and status
    roles: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        default=["user"],
        server_default="{}",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        server_default="active",
    )  # active, suspended, deleted

    # Preferences stored as JSON
    preferences: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
    )

    # Extended profile data (future-proof JSON storage)
    extra_data: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
        nullable=True,
    )

    # Activity tracking
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        "OAuthAccount",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    api_keys: Mapped[list["ApiKey"]] = relationship(
        "ApiKey",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.email})>"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return any(role in self.roles for role in ["admin", "super_admin"])

    @property
    def is_premium(self) -> bool:
        """Check if user has premium subscription."""
        return any(role in self.roles for role in ["premium", "enterprise", "admin", "super_admin"])

    # Helper properties for common extra_data fields
    @property
    def full_name(self) -> str | None:
        """Get full name from extra_data."""
        return self.extra_data.get("full_name") if self.extra_data else None

    @property
    def city(self) -> str | None:
        """Get city from extra_data."""
        return self.extra_data.get("city") if self.extra_data else None

    @property
    def state_province(self) -> str | None:
        """Get state/province from extra_data."""
        return self.extra_data.get("state_province") if self.extra_data else None

    @property
    def country(self) -> str | None:
        """Get country from extra_data."""
        return self.extra_data.get("country") if self.extra_data else None

    @property
    def date_of_birth(self) -> str | None:
        """Get date of birth from extra_data."""
        return self.extra_data.get("date_of_birth") if self.extra_data else None


class OAuthAccount(Base, UUIDMixin):
    """OAuth account linked to a user (Google, Microsoft, GitHub)."""

    __tablename__ = "oauth_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # google, microsoft, github
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts")

    __table_args__ = (
        # Unique constraint on provider + provider_user_id
        {"sqlite_autoincrement": True},
    )

    def __repr__(self) -> str:
        return f"<OAuthAccount {self.provider}:{self.provider_user_id}>"


class ApiKey(Base, UUIDMixin):
    """API key for programmatic access."""

    __tablename__ = "api_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # First 12 chars for lookup
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # Argon2 hash

    # Permissions
    permissions: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        default=["read"],
        server_default="{}",
    )

    # Expiration and usage
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<ApiKey {self.name} ({self.key_prefix}...)>"


class RefreshToken(Base, UUIDMixin):
    """Refresh token for JWT authentication."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)."""
        now = datetime.now(timezone.utc)
        return self.revoked_at is None and self.expires_at > now

    def __repr__(self) -> str:
        return f"<RefreshToken {self.id} (user={self.user_id})>"
