"""Billing service for credit and usage management."""

import uuid
from datetime import UTC, datetime
from typing import Literal

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import MODEL_REGISTRY, get_model_config
from app.models.billing import BillingTransaction, UsageLimit, UserCredits
from app.models.user import User
from app.repositories.billing_repo import BillingRepository
from app.schemas.billing import (
    CostEstimateRequest,
    CostEstimateResponse,
    CreditBalanceResponse,
    TransactionFilters,
    TransactionListResponse,
    TransactionResponse,
    UsageLimitsResponse,
    UsageSummaryResponse,
)
from app.schemas.common import create_pagination

logger = structlog.get_logger(__name__)


class BillingService:
    """Service for billing-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BillingRepository(db)

    # Credit balance operations

    async def get_balance(self, user: User) -> CreditBalanceResponse:
        """Get user's current credit balance.

        Args:
            user: Current user

        Returns:
            Credit balance response
        """
        credits = await self.repo.get_or_create_credits(user.id)

        return CreditBalanceResponse(
            balance_cents=credits.balance_cents,
            balance_dollars=credits.balance_cents / 100,
            free_credits_remaining=credits.free_credits_remaining,
            total_available_cents=credits.balance_cents + credits.free_credits_remaining,
            lifetime_usage_cents=credits.lifetime_usage_cents,
            lifetime_usage_dollars=credits.lifetime_usage_cents / 100,
        )

    async def check_balance(
        self,
        user_id: uuid.UUID,
        required_cents: int,
    ) -> tuple[bool, UserCredits]:
        """Check if user has sufficient balance.

        Args:
            user_id: User ID
            required_cents: Required amount in cents

        Returns:
            Tuple of (has_sufficient, credits)
        """
        credits = await self.repo.get_or_create_credits(user_id)
        total_available = credits.balance_cents + credits.free_credits_remaining
        return total_available >= required_cents, credits

    async def deduct_credits(
        self,
        user_id: uuid.UUID,
        amount_cents: int,
        operation_type: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
        operation_id: uuid.UUID | None = None,
        description: str | None = None,
    ) -> BillingTransaction:
        """Deduct credits and record transaction.

        Args:
            user_id: User ID
            amount_cents: Amount to deduct
            operation_type: Type of operation
            model: Model used
            tokens_input: Input tokens
            tokens_output: Output tokens
            operation_id: Related operation ID
            description: Transaction description

        Returns:
            Created transaction

        Raises:
            HTTPException: If insufficient credits
        """
        # Deduct credits
        success, credits = await self.repo.deduct_credits(user_id, amount_cents)

        if not success:
            total_available = credits.balance_cents + credits.free_credits_remaining
            logger.warning(
                "insufficient_credits",
                user_id=str(user_id),
                required=amount_cents,
                available=total_available,
            )
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "insufficient_credits",
                    "message": "You do not have enough credits for this operation",
                    "required_cents": amount_cents,
                    "available_cents": total_available,
                    "shortfall_cents": amount_cents - total_available,
                },
            )

        # Record transaction
        transaction = await self.repo.create_transaction(
            user_id=user_id,
            operation_type=operation_type,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_cents=amount_cents,
            operation_id=operation_id,
            balance_after=credits.balance_cents + credits.free_credits_remaining,
            description=description,
        )

        # Record usage against limits
        await self.repo.record_usage(
            user_id=user_id,
            tokens=tokens_input + tokens_output,
            cost_cents=amount_cents,
        )

        logger.info(
            "credits_deducted",
            user_id=str(user_id),
            amount_cents=amount_cents,
            operation_type=operation_type,
            model=model,
            balance_after=credits.balance_cents + credits.free_credits_remaining,
        )

        return transaction

    async def add_credits(
        self,
        user_id: uuid.UUID,
        amount_cents: int,
        description: str = "Credit purchase",
    ) -> tuple[UserCredits, BillingTransaction]:
        """Add credits to user's balance.

        Args:
            user_id: User ID
            amount_cents: Amount to add
            description: Transaction description

        Returns:
            Tuple of (updated credits, transaction)
        """
        credits = await self.repo.add_credits(user_id, amount_cents)

        # Record transaction
        transaction = await self.repo.create_transaction(
            user_id=user_id,
            operation_type="credit_purchase",
            model="n/a",
            tokens_input=0,
            tokens_output=0,
            cost_cents=-amount_cents,  # Negative cost for credit addition
            balance_after=credits.balance_cents + credits.free_credits_remaining,
            description=description,
        )

        logger.info(
            "credits_added",
            user_id=str(user_id),
            amount_cents=amount_cents,
            new_balance=credits.balance_cents,
        )

        return credits, transaction

    # Usage limits operations

    async def get_limits(self, user: User) -> UsageLimitsResponse:
        """Get user's current usage limits.

        Args:
            user: Current user

        Returns:
            Usage limits response
        """
        limits = await self.repo.check_and_reset_limits(user.id)

        return UsageLimitsResponse(
            daily_tokens_limit=limits.daily_tokens_limit,
            daily_tokens_used=limits.daily_tokens_used,
            daily_tokens_remaining=limits.daily_tokens_remaining,
            daily_reset_at=limits.daily_reset_at,
            monthly_cost_limit_cents=limits.monthly_cost_limit_cents,
            monthly_cost_used_cents=limits.monthly_cost_used_cents,
            monthly_cost_remaining_cents=limits.monthly_cost_remaining_cents,
            monthly_reset_at=limits.monthly_reset_at,
            is_daily_limit_exceeded=limits.is_daily_limit_exceeded,
            is_monthly_limit_exceeded=limits.is_monthly_limit_exceeded,
        )

    async def check_limits(
        self,
        user_id: uuid.UUID,
        estimated_tokens: int,
        estimated_cost_cents: int,
    ) -> tuple[bool, UsageLimit]:
        """Check if user can perform operation within limits.

        Args:
            user_id: User ID
            estimated_tokens: Estimated tokens for operation
            estimated_cost_cents: Estimated cost for operation

        Returns:
            Tuple of (can_proceed, limits)

        Raises:
            HTTPException: If limits exceeded
        """
        can_proceed, limits = await self.repo.check_limits(
            user_id, estimated_tokens, estimated_cost_cents
        )

        if not can_proceed:
            if limits.is_daily_limit_exceeded:
                logger.warning(
                    "daily_limit_exceeded",
                    user_id=str(user_id),
                    limit=limits.daily_tokens_limit,
                    used=limits.daily_tokens_used,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "usage_limit_exceeded",
                        "message": "Daily token limit exceeded",
                        "limit_type": "daily_tokens",
                        "limit_value": limits.daily_tokens_limit,
                        "current_usage": limits.daily_tokens_used,
                        "reset_at": limits.daily_reset_at.isoformat() if limits.daily_reset_at else None,
                    },
                )
            elif limits.is_monthly_limit_exceeded:
                logger.warning(
                    "monthly_limit_exceeded",
                    user_id=str(user_id),
                    limit=limits.monthly_cost_limit_cents,
                    used=limits.monthly_cost_used_cents,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "usage_limit_exceeded",
                        "message": "Monthly cost limit exceeded",
                        "limit_type": "monthly_cost",
                        "limit_value": limits.monthly_cost_limit_cents,
                        "current_usage": limits.monthly_cost_used_cents,
                        "reset_at": limits.monthly_reset_at.isoformat() if limits.monthly_reset_at else None,
                    },
                )

        return can_proceed, limits

    # Transaction operations

    async def list_transactions(
        self,
        user: User,
        filters: TransactionFilters | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> TransactionListResponse:
        """List transactions for user with filtering.

        Args:
            user: Current user
            filters: Optional filters
            page: Page number
            limit: Items per page

        Returns:
            Paginated transaction list
        """
        operation_type = filters.operation_type.value if filters and filters.operation_type else None

        transactions, total = await self.repo.list_transactions(
            user_id=user.id,
            operation_type=operation_type,
            model=filters.model if filters else None,
            start_date=filters.start_date if filters else None,
            end_date=filters.end_date if filters else None,
            page=page,
            limit=limit,
        )

        return TransactionListResponse(
            data=[self._transaction_to_response(t) for t in transactions],
            pagination=create_pagination(page, limit, total),
        )

    async def get_transaction(
        self,
        transaction_id: uuid.UUID,
        user: User,
    ) -> TransactionResponse:
        """Get a single transaction.

        Args:
            transaction_id: Transaction ID
            user: Current user

        Returns:
            Transaction response

        Raises:
            HTTPException: If not found
        """
        transaction = await self.repo.get_transaction(transaction_id, user.id)

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found",
            )

        return self._transaction_to_response(transaction)

    async def get_usage_summary(
        self,
        user: User,
        period: Literal["day", "week", "month"] = "month",
    ) -> UsageSummaryResponse:
        """Get usage summary for a time period.

        Args:
            user: Current user
            period: Time period (day, week, month)

        Returns:
            Usage summary response
        """
        now = datetime.now(UTC)

        if period == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            # Start of week (Monday)
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # month
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        summary = await self.repo.get_usage_summary(user.id, start_date, now)

        return UsageSummaryResponse(
            period_start=summary["period_start"],
            period_end=summary["period_end"],
            total_transactions=summary["total_transactions"],
            total_tokens_input=summary["total_tokens_input"],
            total_tokens_output=summary["total_tokens_output"],
            total_tokens=summary["total_tokens"],
            total_cost_cents=summary["total_cost_cents"],
            total_cost_dollars=summary["total_cost_cents"] / 100,
            by_operation=summary["by_operation"],
            by_model=summary["by_model"],
        )

    # Cost estimation

    async def estimate_cost(
        self,
        user: User,
        data: CostEstimateRequest,
    ) -> CostEstimateResponse:
        """Estimate cost for an operation.

        Args:
            user: Current user
            data: Cost estimate request

        Returns:
            Cost estimate response

        Raises:
            HTTPException: If model not found
        """
        if data.model not in MODEL_REGISTRY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown model: {data.model}",
            )

        model_config = get_model_config(data.model)
        cost_usd = model_config.calculate_cost(
            data.estimated_input_tokens,
            data.estimated_output_tokens,
        )
        cost_cents = int(cost_usd * 100)

        credits = await self.repo.get_or_create_credits(user.id)
        total_available = credits.balance_cents + credits.free_credits_remaining
        can_afford = total_available >= cost_cents

        return CostEstimateResponse(
            model=data.model,
            estimated_tokens_input=data.estimated_input_tokens,
            estimated_tokens_output=data.estimated_output_tokens,
            estimated_cost_cents=cost_cents,
            estimated_cost_dollars=cost_usd,
            can_afford=can_afford,
            balance_after_cents=total_available - cost_cents if can_afford else 0,
        )

    # Helper methods

    def _transaction_to_response(
        self,
        transaction: BillingTransaction,
    ) -> TransactionResponse:
        """Convert transaction model to response schema."""
        return TransactionResponse(
            id=transaction.id,
            operation_type=transaction.operation_type,
            operation_id=transaction.operation_id,
            model=transaction.model,
            tokens_input=transaction.tokens_input,
            tokens_output=transaction.tokens_output,
            total_tokens=transaction.total_tokens,
            cost_cents=transaction.cost_cents,
            cost_dollars=transaction.cost_cents / 100,
            balance_after=transaction.balance_after,
            description=transaction.description,
            created_at=transaction.created_at,
        )


# Import at module level to avoid circular imports
from datetime import timedelta
