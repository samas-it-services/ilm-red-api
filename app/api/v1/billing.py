"""Billing API endpoints for credits and usage management."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.v1.deps import CurrentUser, DBSession
from app.schemas.billing import (
    CostEstimateRequest,
    CostEstimateResponse,
    CreditBalanceResponse,
    OperationType,
    TransactionFilters,
    TransactionListResponse,
    TransactionResponse,
    UsageLimitsResponse,
    UsageSummaryResponse,
)
from app.services.billing_service import BillingService

router = APIRouter()


# Credit balance endpoints


@router.get(
    "/balance",
    response_model=CreditBalanceResponse,
    summary="Get credit balance",
    description="Get your current credit balance including free and paid credits.",
)
async def get_balance(
    db: DBSession,
    current_user: CurrentUser,
) -> CreditBalanceResponse:
    """Get your current credit balance.

    Returns:
    - **balance_cents**: Current paid balance in cents
    - **free_credits_remaining**: Remaining free credits
    - **total_available_cents**: Total available (paid + free)
    - **lifetime_usage_cents**: Total credits used over lifetime
    """
    service = BillingService(db)
    return await service.get_balance(current_user)


# Usage limits endpoints


@router.get(
    "/limits",
    response_model=UsageLimitsResponse,
    summary="Get usage limits",
    description="Get your current daily and monthly usage limits.",
)
async def get_limits(
    db: DBSession,
    current_user: CurrentUser,
) -> UsageLimitsResponse:
    """Get your current usage limits.

    Returns daily token limits and monthly cost limits along with current usage.
    Limits reset automatically at midnight (daily) and the 1st of each month (monthly).
    """
    service = BillingService(db)
    return await service.get_limits(current_user)


# Usage summary endpoints


@router.get(
    "/usage",
    response_model=UsageSummaryResponse,
    summary="Get usage summary",
    description="Get a summary of your AI usage over a time period.",
)
async def get_usage_summary(
    db: DBSession,
    current_user: CurrentUser,
    period: Literal["day", "week", "month"] = Query(
        "month",
        description="Time period for summary",
    ),
) -> UsageSummaryResponse:
    """Get a summary of your AI usage.

    - **period**: Time period - 'day' (today), 'week' (this week), 'month' (this month)

    Returns aggregated statistics including:
    - Total tokens and cost
    - Breakdown by operation type (chat, summary, etc.)
    - Breakdown by AI model
    """
    service = BillingService(db)
    return await service.get_usage_summary(current_user, period)


# Transaction endpoints


@router.get(
    "/transactions",
    response_model=TransactionListResponse,
    summary="List transactions",
    description="List your billing transactions with optional filtering.",
)
async def list_transactions(
    db: DBSession,
    current_user: CurrentUser,
    operation_type: OperationType | None = Query(
        None,
        description="Filter by operation type",
    ),
    model: str | None = Query(
        None,
        description="Filter by AI model",
    ),
    start_date: datetime | None = Query(
        None,
        description="Filter by start date (ISO format)",
    ),
    end_date: datetime | None = Query(
        None,
        description="Filter by end date (ISO format)",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> TransactionListResponse:
    """List your billing transactions.

    Transactions are sorted by date (most recent first).
    Use filters to narrow down results.
    """
    service = BillingService(db)

    filters = TransactionFilters(
        operation_type=operation_type,
        model=model,
        start_date=start_date,
        end_date=end_date,
    )

    return await service.list_transactions(
        user=current_user,
        filters=filters,
        page=page,
        limit=limit,
    )


@router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get transaction",
    description="Get details of a specific transaction.",
)
async def get_transaction(
    transaction_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> TransactionResponse:
    """Get details of a specific transaction.

    Returns full transaction details including tokens used and cost.
    """
    service = BillingService(db)
    return await service.get_transaction(transaction_id, current_user)


# Cost estimation endpoints


@router.post(
    "/estimate",
    response_model=CostEstimateResponse,
    summary="Estimate cost",
    description="Estimate the cost of an AI operation before executing it.",
)
async def estimate_cost(
    db: DBSession,
    current_user: CurrentUser,
    data: CostEstimateRequest,
) -> CostEstimateResponse:
    """Estimate the cost of an AI operation.

    - **model**: AI model to use (e.g., 'gpt-4o-mini', 'claude-3-haiku')
    - **estimated_input_tokens**: Expected input tokens
    - **estimated_output_tokens**: Expected output tokens

    Returns the estimated cost and whether you can afford it with current balance.
    """
    service = BillingService(db)
    return await service.estimate_cost(current_user, data)
