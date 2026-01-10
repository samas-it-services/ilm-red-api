"""Billing repository for database operations."""

import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import UserCredits, BillingTransaction, UsageLimit


class BillingRepository:
    """Repository for Billing database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Credits operations

    async def get_credits(self, user_id: uuid.UUID) -> UserCredits | None:
        """Get user's credit balance."""
        stmt = select(UserCredits).where(UserCredits.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_credits(self, user_id: uuid.UUID) -> UserCredits:
        """Get or create user's credit balance."""
        credits = await self.get_credits(user_id)
        if not credits:
            credits = UserCredits(user_id=user_id)
            self.db.add(credits)
            await self.db.flush()
            await self.db.refresh(credits)
        return credits

    async def update_credits(
        self,
        credits: UserCredits,
        balance_cents: int | None = None,
        free_credits_remaining: int | None = None,
    ) -> UserCredits:
        """Update user's credits."""
        if balance_cents is not None:
            credits.balance_cents = balance_cents
        if free_credits_remaining is not None:
            credits.free_credits_remaining = free_credits_remaining

        credits.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(credits)
        return credits

    async def deduct_credits(
        self,
        user_id: uuid.UUID,
        amount_cents: int,
    ) -> tuple[bool, UserCredits]:
        """Deduct credits from user's balance.

        First uses free credits, then paid credits.

        Args:
            user_id: User ID
            amount_cents: Amount to deduct in cents

        Returns:
            Tuple of (success, credits)
        """
        credits = await self.get_or_create_credits(user_id)
        success = credits.deduct(amount_cents)
        if success:
            await self.db.flush()
            await self.db.refresh(credits)
        return success, credits

    async def add_credits(
        self,
        user_id: uuid.UUID,
        amount_cents: int,
    ) -> UserCredits:
        """Add credits to user's balance.

        Args:
            user_id: User ID
            amount_cents: Amount to add in cents

        Returns:
            Updated credits
        """
        credits = await self.get_or_create_credits(user_id)
        credits.add_credits(amount_cents)
        await self.db.flush()
        await self.db.refresh(credits)
        return credits

    # Transaction operations

    async def create_transaction(
        self,
        user_id: uuid.UUID,
        operation_type: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
        cost_cents: int,
        operation_id: uuid.UUID | None = None,
        balance_after: int | None = None,
        description: str | None = None,
    ) -> BillingTransaction:
        """Create a billing transaction record."""
        transaction = BillingTransaction(
            user_id=user_id,
            operation_type=operation_type,
            operation_id=operation_id,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_cents=cost_cents,
            balance_after=balance_after,
            description=description,
        )
        self.db.add(transaction)
        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction

    async def get_transaction(
        self,
        transaction_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> BillingTransaction | None:
        """Get transaction by ID, optionally filtering by user."""
        stmt = select(BillingTransaction).where(BillingTransaction.id == transaction_id)

        if user_id is not None:
            stmt = stmt.where(BillingTransaction.user_id == user_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_transactions(
        self,
        user_id: uuid.UUID,
        operation_type: str | None = None,
        model: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[BillingTransaction], int]:
        """List transactions for a user with filtering and pagination.

        Args:
            user_id: User ID
            operation_type: Optional filter by operation type
            model: Optional filter by model
            start_date: Optional filter by start date
            end_date: Optional filter by end date
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (transactions list, total count)
        """
        conditions = [BillingTransaction.user_id == user_id]

        if operation_type:
            conditions.append(BillingTransaction.operation_type == operation_type)

        if model:
            conditions.append(BillingTransaction.model == model)

        if start_date:
            conditions.append(BillingTransaction.created_at >= start_date)

        if end_date:
            conditions.append(BillingTransaction.created_at <= end_date)

        # Count query
        count_stmt = select(func.count(BillingTransaction.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        offset = (page - 1) * limit
        stmt = (
            select(BillingTransaction)
            .where(and_(*conditions))
            .order_by(BillingTransaction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        transactions = list(result.scalars().all())

        return transactions, total

    async def get_usage_summary(
        self,
        user_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """Get usage summary for a time period.

        Args:
            user_id: User ID
            start_date: Start of period
            end_date: End of period

        Returns:
            Dictionary with usage statistics
        """
        conditions = [
            BillingTransaction.user_id == user_id,
            BillingTransaction.created_at >= start_date,
            BillingTransaction.created_at <= end_date,
        ]

        # Total stats
        total_stmt = select(
            func.count(BillingTransaction.id),
            func.coalesce(func.sum(BillingTransaction.tokens_input), 0),
            func.coalesce(func.sum(BillingTransaction.tokens_output), 0),
            func.coalesce(func.sum(BillingTransaction.cost_cents), 0),
        ).where(and_(*conditions))

        total_result = await self.db.execute(total_stmt)
        total_row = total_result.one()

        # By operation type
        operation_stmt = select(
            BillingTransaction.operation_type,
            func.count(BillingTransaction.id),
            func.sum(BillingTransaction.tokens_input + BillingTransaction.tokens_output),
            func.sum(BillingTransaction.cost_cents),
        ).where(and_(*conditions)).group_by(BillingTransaction.operation_type)

        operation_result = await self.db.execute(operation_stmt)
        by_operation = {
            row[0]: {
                "count": row[1],
                "tokens": row[2] or 0,
                "cost_cents": row[3] or 0,
            }
            for row in operation_result.all()
        }

        # By model
        model_stmt = select(
            BillingTransaction.model,
            func.count(BillingTransaction.id),
            func.sum(BillingTransaction.tokens_input + BillingTransaction.tokens_output),
            func.sum(BillingTransaction.cost_cents),
        ).where(and_(*conditions)).group_by(BillingTransaction.model)

        model_result = await self.db.execute(model_stmt)
        by_model = {
            row[0]: {
                "count": row[1],
                "tokens": row[2] or 0,
                "cost_cents": row[3] or 0,
            }
            for row in model_result.all()
        }

        return {
            "period_start": start_date,
            "period_end": end_date,
            "total_transactions": total_row[0],
            "total_tokens_input": total_row[1],
            "total_tokens_output": total_row[2],
            "total_tokens": total_row[1] + total_row[2],
            "total_cost_cents": total_row[3],
            "by_operation": by_operation,
            "by_model": by_model,
        }

    # Usage limits operations

    async def get_limits(self, user_id: uuid.UUID) -> UsageLimit | None:
        """Get user's usage limits."""
        stmt = select(UsageLimit).where(UsageLimit.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_limits(self, user_id: uuid.UUID) -> UsageLimit:
        """Get or create user's usage limits."""
        limits = await self.get_limits(user_id)
        if not limits:
            limits = UsageLimit(user_id=user_id)
            self.db.add(limits)
            await self.db.flush()
            await self.db.refresh(limits)
        return limits

    async def update_limits(
        self,
        limits: UsageLimit,
        daily_tokens_limit: int | None = None,
        monthly_cost_limit_cents: int | None = None,
    ) -> UsageLimit:
        """Update user's usage limits."""
        if daily_tokens_limit is not None:
            limits.daily_tokens_limit = daily_tokens_limit
        if monthly_cost_limit_cents is not None:
            limits.monthly_cost_limit_cents = monthly_cost_limit_cents

        limits.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(limits)
        return limits

    async def record_usage(
        self,
        user_id: uuid.UUID,
        tokens: int,
        cost_cents: int,
    ) -> UsageLimit:
        """Record token and cost usage against limits.

        Args:
            user_id: User ID
            tokens: Number of tokens used
            cost_cents: Cost in cents

        Returns:
            Updated usage limits
        """
        limits = await self.get_or_create_limits(user_id)
        limits.record_usage(tokens, cost_cents)
        await self.db.flush()
        await self.db.refresh(limits)
        return limits

    async def check_and_reset_limits(self, user_id: uuid.UUID) -> UsageLimit:
        """Check if limits need to be reset and reset if necessary.

        Args:
            user_id: User ID

        Returns:
            Updated usage limits
        """
        limits = await self.get_or_create_limits(user_id)
        now = datetime.now(timezone.utc)

        # Check daily reset
        if limits.daily_reset_at is None or (
            now.date() > limits.daily_reset_at.date()
        ):
            limits.reset_daily()

        # Check monthly reset
        if limits.monthly_reset_at is None or (
            now.year > limits.monthly_reset_at.year
            or now.month > limits.monthly_reset_at.month
        ):
            limits.reset_monthly()

        await self.db.flush()
        await self.db.refresh(limits)
        return limits

    async def check_limits(
        self,
        user_id: uuid.UUID,
        tokens: int,
        cost_cents: int,
    ) -> tuple[bool, UsageLimit]:
        """Check if user can perform an operation within limits.

        Args:
            user_id: User ID
            tokens: Estimated tokens for operation
            cost_cents: Estimated cost for operation

        Returns:
            Tuple of (can_proceed, limits)
        """
        limits = await self.check_and_reset_limits(user_id)

        can_proceed = limits.can_use_tokens(tokens) and limits.can_incur_cost(cost_cents)
        return can_proceed, limits
