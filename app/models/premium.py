"""Premium and Stripe-related database models."""

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
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class PremiumRequest(Base, UUIDMixin, TimestampMixin):
    """Premium access request from a user."""

    __tablename__ = "premium_requests"

    # Requester
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Contact info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Usage info
    user_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # student, teacher, researcher, etc.
    current_usage: Mapped[str | None] = mapped_column(Text, nullable=True)
    interested_features: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(100)),
        nullable=True,
    )
    use_case: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Organization details
    team_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    budget: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timeline: Mapped[str | None] = mapped_column(String(100), nullable=True)
    additional_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Review status
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
    )  # pending, approved, rejected, in_review

    # Admin review
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], backref="premium_requests"
    )
    reviewer: Mapped["User | None"] = relationship(
        "User", foreign_keys=[reviewed_by]
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'in_review')",
            name="check_premium_request_status",
        ),
        Index("idx_premium_requests_status", "status"),
        Index("idx_premium_requests_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<PremiumRequest user={self.user_id} status={self.status}>"


class PremiumFeature(Base, UUIDMixin, TimestampMixin):
    """Available premium features."""

    __tablename__ = "premium_features"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )

    def __repr__(self) -> str:
        return f"<PremiumFeature {self.name} active={self.is_active}>"


class UserPremiumSubscription(Base, UUIDMixin, TimestampMixin):
    """User premium subscription record."""

    __tablename__ = "user_premium_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # premium, enterprise
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], backref="premium_subscriptions"
    )
    granter: Mapped["User | None"] = relationship(
        "User", foreign_keys=[granted_by]
    )

    __table_args__ = (
        Index("idx_user_premium_sub_active", "user_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<UserPremiumSubscription user={self.user_id} type={self.subscription_type}>"


class StripePaymentIntent(Base, UUIDMixin, TimestampMixin):
    """Stripe payment intent tracking."""

    __tablename__ = "stripe_payment_intents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stripe_payment_intent_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    stripe_client_secret: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    credit_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(10),
        default="usd",
        server_default="usd",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
    )  # pending, completed, failed, cancelled, refunded

    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default="{}",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="payment_intents")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed', 'cancelled', 'refunded')",
            name="check_payment_intent_status",
        ),
        CheckConstraint("amount > 0", name="check_payment_amount_positive"),
        CheckConstraint("credit_amount > 0", name="check_credit_amount_positive"),
        Index("idx_stripe_payment_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<StripePaymentIntent {self.stripe_payment_intent_id} status={self.status}>"


class UserUploadLimit(Base, UUIDMixin, TimestampMixin):
    """User upload limits and storage tracking."""

    __tablename__ = "user_upload_limits"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    is_premium: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    max_file_size_mb: Mapped[int] = mapped_column(
        Integer,
        default=50,
        server_default="50",
    )
    total_storage_mb: Mapped[int] = mapped_column(
        Integer,
        default=500,
        server_default="500",
    )
    current_storage_mb: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    uploads_this_month: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    monthly_upload_count: Mapped[int] = mapped_column(
        Integer,
        default=20,
        server_default="20",
    )
    reset_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="upload_limits")

    __table_args__ = (
        CheckConstraint("max_file_size_mb > 0", name="check_max_file_size_positive"),
        CheckConstraint("total_storage_mb > 0", name="check_total_storage_positive"),
        CheckConstraint("current_storage_mb >= 0", name="check_current_storage_non_negative"),
        CheckConstraint("uploads_this_month >= 0", name="check_uploads_non_negative"),
        CheckConstraint("monthly_upload_count > 0", name="check_monthly_count_positive"),
    )

    def __repr__(self) -> str:
        return f"<UserUploadLimit user={self.user_id} premium={self.is_premium}>"

    @property
    def storage_remaining_mb(self) -> int:
        """Get remaining storage in MB."""
        return max(0, self.total_storage_mb - self.current_storage_mb)

    @property
    def uploads_remaining(self) -> int:
        """Get remaining uploads this month."""
        return max(0, self.monthly_upload_count - self.uploads_this_month)
