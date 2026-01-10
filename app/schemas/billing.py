"""Billing schemas for credits, transactions, and usage."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


class OperationType(str, Enum):
    """Types of billable operations."""

    CHAT = "chat"
    SUMMARY = "summary"
    SEARCH = "search"
    EMBEDDING = "embedding"
    FLASHCARDS = "flashcards"
    QUIZ = "quiz"
    CREDIT_PURCHASE = "credit_purchase"
    CREDIT_REFUND = "credit_refund"
    FREE_CREDIT = "free_credit"


# Response Schemas


class CreditBalanceResponse(BaseModel):
    """User's current credit balance."""

    balance_cents: int = Field(description="Current paid balance in cents")
    balance_dollars: float = Field(description="Current paid balance in dollars")
    free_credits_remaining: int = Field(description="Remaining free credits in cents")
    total_available_cents: int = Field(description="Total available credits (paid + free)")
    lifetime_usage_cents: int = Field(description="Total credits used over lifetime")
    lifetime_usage_dollars: float = Field(description="Total credits used in dollars")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "balance_cents": 500,
                "balance_dollars": 5.00,
                "free_credits_remaining": 75,
                "total_available_cents": 575,
                "lifetime_usage_cents": 1250,
                "lifetime_usage_dollars": 12.50,
            }
        }
    )


class TransactionResponse(BaseModel):
    """A billing transaction record."""

    id: UUID
    operation_type: str
    operation_id: UUID | None = None
    model: str
    tokens_input: int
    tokens_output: int
    total_tokens: int
    cost_cents: int
    cost_dollars: float
    balance_after: int | None = None
    description: str | None = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "operation_type": "chat",
                "operation_id": "550e8400-e29b-41d4-a716-446655440001",
                "model": "gpt-4o-mini",
                "tokens_input": 150,
                "tokens_output": 500,
                "total_tokens": 650,
                "cost_cents": 3,
                "cost_dollars": 0.03,
                "balance_after": 497,
                "description": "Chat message in session",
                "created_at": "2026-01-09T12:00:00Z",
            }
        }
    )


class TransactionListResponse(BaseModel):
    """Paginated transaction list response."""

    data: list[TransactionResponse]
    pagination: Pagination


class UsageLimitsResponse(BaseModel):
    """User's current usage limits."""

    # Daily token limits
    daily_tokens_limit: int = Field(description="Maximum tokens per day")
    daily_tokens_used: int = Field(description="Tokens used today")
    daily_tokens_remaining: int = Field(description="Tokens remaining today")
    daily_reset_at: datetime | None = Field(description="When daily limit resets")

    # Monthly cost limits
    monthly_cost_limit_cents: int = Field(description="Maximum monthly cost in cents")
    monthly_cost_used_cents: int = Field(description="Cost used this month in cents")
    monthly_cost_remaining_cents: int = Field(description="Cost remaining this month in cents")
    monthly_reset_at: datetime | None = Field(description="When monthly limit resets")

    # Status flags
    is_daily_limit_exceeded: bool
    is_monthly_limit_exceeded: bool

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "daily_tokens_limit": 100000,
                "daily_tokens_used": 25000,
                "daily_tokens_remaining": 75000,
                "daily_reset_at": "2026-01-10T00:00:00Z",
                "monthly_cost_limit_cents": 1000,
                "monthly_cost_used_cents": 250,
                "monthly_cost_remaining_cents": 750,
                "monthly_reset_at": "2026-02-01T00:00:00Z",
                "is_daily_limit_exceeded": False,
                "is_monthly_limit_exceeded": False,
            }
        }
    )


class UsageSummaryResponse(BaseModel):
    """Summary of usage over a time period."""

    period_start: datetime
    period_end: datetime
    total_transactions: int
    total_tokens_input: int
    total_tokens_output: int
    total_tokens: int
    total_cost_cents: int
    total_cost_dollars: float

    # Breakdown by operation type
    by_operation: dict[str, dict]

    # Breakdown by model
    by_model: dict[str, dict]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "period_start": "2026-01-01T00:00:00Z",
                "period_end": "2026-01-31T23:59:59Z",
                "total_transactions": 150,
                "total_tokens_input": 45000,
                "total_tokens_output": 120000,
                "total_tokens": 165000,
                "total_cost_cents": 850,
                "total_cost_dollars": 8.50,
                "by_operation": {
                    "chat": {"count": 100, "tokens": 100000, "cost_cents": 500},
                    "summary": {"count": 50, "tokens": 65000, "cost_cents": 350},
                },
                "by_model": {
                    "gpt-4o-mini": {"count": 120, "tokens": 140000, "cost_cents": 700},
                    "claude-3-haiku": {"count": 30, "tokens": 25000, "cost_cents": 150},
                },
            }
        }
    )


class CostEstimateResponse(BaseModel):
    """Estimated cost for an operation."""

    model: str
    estimated_tokens_input: int
    estimated_tokens_output: int
    estimated_cost_cents: int
    estimated_cost_dollars: float
    can_afford: bool = Field(description="Whether user has enough credits")
    balance_after_cents: int = Field(description="Balance after operation if affordable")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model": "gpt-4o-mini",
                "estimated_tokens_input": 500,
                "estimated_tokens_output": 2000,
                "estimated_cost_cents": 5,
                "estimated_cost_dollars": 0.05,
                "can_afford": True,
                "balance_after_cents": 495,
            }
        }
    )


# Request Schemas


class CostEstimateRequest(BaseModel):
    """Request to estimate cost of an operation."""

    model: str = Field(..., description="Model to use for estimation")
    estimated_input_tokens: int = Field(
        ..., ge=1, description="Estimated input tokens"
    )
    estimated_output_tokens: int = Field(
        ..., ge=1, description="Estimated output tokens"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "model": "gpt-4o-mini",
                "estimated_input_tokens": 500,
                "estimated_output_tokens": 2000,
            }
        }
    )


class TransactionFilters(BaseModel):
    """Filters for listing transactions."""

    operation_type: OperationType | None = Field(
        default=None, description="Filter by operation type"
    )
    model: str | None = Field(default=None, description="Filter by model")
    start_date: datetime | None = Field(
        default=None, description="Filter by start date"
    )
    end_date: datetime | None = Field(default=None, description="Filter by end date")


# Error Schemas


class InsufficientCreditsError(BaseModel):
    """Error response when user has insufficient credits."""

    error: str = "insufficient_credits"
    message: str = "You do not have enough credits for this operation"
    required_cents: int
    available_cents: int
    shortfall_cents: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "insufficient_credits",
                "message": "You do not have enough credits for this operation",
                "required_cents": 10,
                "available_cents": 5,
                "shortfall_cents": 5,
            }
        }
    )


class UsageLimitExceededError(BaseModel):
    """Error response when usage limit is exceeded."""

    error: str = "usage_limit_exceeded"
    message: str
    limit_type: str  # "daily_tokens" or "monthly_cost"
    limit_value: int
    current_usage: int
    reset_at: datetime | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "usage_limit_exceeded",
                "message": "Daily token limit exceeded",
                "limit_type": "daily_tokens",
                "limit_value": 100000,
                "current_usage": 100000,
                "reset_at": "2026-01-10T00:00:00Z",
            }
        }
    )
