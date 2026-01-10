"""Billing-related database models."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserCredits(Base):
    """User credit balance for AI operations."""

    __tablename__ = "user_credits"

    # Primary key is the user_id (one-to-one relationship)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Balance in cents (1 dollar = 100 cents)
    balance_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Total usage over lifetime
    lifetime_usage_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Free tier credits (reset monthly for free users)
    free_credits_remaining: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default="100"
    )
    free_credits_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamp
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="credits")

    __table_args__ = (
        CheckConstraint("balance_cents >= 0", name="check_balance_non_negative"),
        CheckConstraint("free_credits_remaining >= 0", name="check_free_credits_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<UserCredits user={self.user_id} balance={self.balance_cents}>"

    @property
    def balance_dollars(self) -> float:
        """Get balance in dollars."""
        return self.balance_cents / 100

    @property
    def has_credits(self) -> bool:
        """Check if user has any credits (paid or free)."""
        return self.balance_cents > 0 or self.free_credits_remaining > 0

    def deduct(self, amount_cents: int) -> bool:
        """Deduct credits from balance.

        First uses free credits, then paid credits.

        Args:
            amount_cents: Amount to deduct in cents

        Returns:
            True if deduction successful, False if insufficient funds
        """
        if amount_cents <= 0:
            return True

        # First try free credits
        if self.free_credits_remaining >= amount_cents:
            self.free_credits_remaining -= amount_cents
            self.lifetime_usage_cents += amount_cents
            return True

        # Use remaining free credits, then paid
        remaining = amount_cents
        if self.free_credits_remaining > 0:
            remaining -= self.free_credits_remaining
            self.free_credits_remaining = 0

        # Check paid balance
        if self.balance_cents >= remaining:
            self.balance_cents -= remaining
            self.lifetime_usage_cents += amount_cents
            return True

        # Insufficient funds - rollback
        return False

    def add_credits(self, amount_cents: int) -> None:
        """Add credits to balance.

        Args:
            amount_cents: Amount to add in cents
        """
        if amount_cents > 0:
            self.balance_cents += amount_cents


class BillingTransaction(Base):
    """Record of AI operations and their costs."""

    __tablename__ = "billing_transactions"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # User relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Operation details
    operation_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # chat, summary, search, embedding, flashcards, quiz, credit_purchase, credit_refund, free_credit
    operation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )  # ID of the related operation (e.g., message_id)

    # AI usage details
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    # Balance after transaction (for audit trail)
    balance_after: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Description
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="billing_transactions")

    __table_args__ = (
        Index("idx_billing_transactions_user_created", "user_id", created_at.desc()),
        Index(
            "idx_billing_transactions_operation",
            "operation_type",
            "operation_id",
            postgresql_where="operation_id IS NOT NULL",
        ),
        CheckConstraint(
            "operation_type IN ('chat', 'summary', 'search', 'embedding', 'flashcards', 'quiz', 'credit_purchase', 'credit_refund', 'free_credit')",
            name="check_operation_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<BillingTransaction {self.operation_type} cost={self.cost_cents}>"

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.tokens_input + self.tokens_output

    @property
    def cost_dollars(self) -> float:
        """Get cost in dollars."""
        return self.cost_cents / 100


class UsageLimit(Base):
    """User-specific usage limits for rate limiting and quotas."""

    __tablename__ = "usage_limits"

    # Primary key is the user_id (one-to-one relationship)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Daily token limits
    daily_tokens_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100000, server_default="100000"
    )
    daily_tokens_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    daily_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Monthly cost limits (in cents)
    monthly_cost_limit_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1000, server_default="1000"
    )  # $10 default
    monthly_cost_used_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    monthly_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamp
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="usage_limits")

    __table_args__ = (
        CheckConstraint("daily_tokens_limit >= 0", name="check_daily_limit_non_negative"),
        CheckConstraint("monthly_cost_limit_cents >= 0", name="check_monthly_limit_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<UsageLimit user={self.user_id} daily={self.daily_tokens_used}/{self.daily_tokens_limit}>"

    @property
    def daily_tokens_remaining(self) -> int:
        """Get remaining daily tokens."""
        return max(0, self.daily_tokens_limit - self.daily_tokens_used)

    @property
    def monthly_cost_remaining_cents(self) -> int:
        """Get remaining monthly cost limit in cents."""
        return max(0, self.monthly_cost_limit_cents - self.monthly_cost_used_cents)

    @property
    def is_daily_limit_exceeded(self) -> bool:
        """Check if daily token limit is exceeded."""
        return self.daily_tokens_used >= self.daily_tokens_limit

    @property
    def is_monthly_limit_exceeded(self) -> bool:
        """Check if monthly cost limit is exceeded."""
        return self.monthly_cost_used_cents >= self.monthly_cost_limit_cents

    def can_use_tokens(self, tokens: int) -> bool:
        """Check if user can use the specified number of tokens.

        Args:
            tokens: Number of tokens to use

        Returns:
            True if within limits
        """
        return self.daily_tokens_used + tokens <= self.daily_tokens_limit

    def can_incur_cost(self, cost_cents: int) -> bool:
        """Check if user can incur the specified cost.

        Args:
            cost_cents: Cost in cents

        Returns:
            True if within limits
        """
        return self.monthly_cost_used_cents + cost_cents <= self.monthly_cost_limit_cents

    def record_usage(self, tokens: int, cost_cents: int) -> None:
        """Record token and cost usage.

        Args:
            tokens: Number of tokens used
            cost_cents: Cost in cents
        """
        self.daily_tokens_used += tokens
        self.monthly_cost_used_cents += cost_cents

    def reset_daily(self) -> None:
        """Reset daily usage counters."""
        self.daily_tokens_used = 0
        self.daily_reset_at = datetime.now(timezone.utc)

    def reset_monthly(self) -> None:
        """Reset monthly usage counters."""
        self.monthly_cost_used_cents = 0
        self.monthly_reset_at = datetime.now(timezone.utc)
