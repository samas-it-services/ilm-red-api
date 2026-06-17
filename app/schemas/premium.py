"""Premium and Stripe schemas for API request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


# ============================================================================
# Premium Request Schemas
# ============================================================================


class PremiumRequestCreate(BaseModel):
    """Schema for submitting a premium request."""

    name: str = Field(..., max_length=200, description="Full name")
    email: str = Field(..., max_length=255, description="Contact email")
    organization: str | None = Field(default=None, max_length=255, description="Organization name")
    user_type: str | None = Field(
        default=None,
        max_length=50,
        description="User type (student, teacher, researcher, etc.)",
    )
    current_usage: str | None = Field(default=None, description="How you currently use the platform")
    interested_features: list[str] | None = Field(
        default=None, description="Premium features you are interested in"
    )
    use_case: str | None = Field(default=None, description="Your primary use case")
    team_size: str | None = Field(default=None, max_length=50, description="Team size")
    budget: str | None = Field(default=None, max_length=100, description="Budget range")
    timeline: str | None = Field(default=None, max_length=100, description="Timeline for upgrade")
    additional_notes: str | None = Field(default=None, description="Additional notes")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Ali Khan",
                "email": "ali.khan@example.com",
                "organization": "Islamic University",
                "user_type": "researcher",
                "current_usage": "Regular book reading and AI chat",
                "interested_features": ["unlimited_uploads", "advanced_ai", "team_access"],
                "use_case": "Academic research and teaching materials",
                "team_size": "10-50",
                "budget": "$50-100/month",
                "timeline": "Within 1 month",
            }
        }
    )


class PremiumRequestUpdate(BaseModel):
    """Schema for updating a premium request (owner only, before review)."""

    name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    user_type: str | None = Field(default=None, max_length=50)
    current_usage: str | None = Field(default=None)
    interested_features: list[str] | None = Field(default=None)
    use_case: str | None = Field(default=None)
    team_size: str | None = Field(default=None, max_length=50)
    budget: str | None = Field(default=None, max_length=100)
    timeline: str | None = Field(default=None, max_length=100)
    additional_notes: str | None = Field(default=None)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "use_case": "Updated use case description",
                "team_size": "50-100",
            }
        }
    )


class PremiumRequestResponse(BaseModel):
    """Premium request response."""

    id: UUID
    user_id: UUID
    name: str
    email: str
    organization: str | None = None
    user_type: str | None = None
    current_usage: str | None = None
    interested_features: list[str] | None = None
    use_case: str | None = None
    team_size: str | None = None
    budget: str | None = None
    timeline: str | None = None
    additional_notes: str | None = None
    status: str
    admin_notes: str | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "name": "Ali Khan",
                "email": "ali.khan@example.com",
                "organization": "Islamic University",
                "status": "pending",
                "created_at": "2026-01-15T10:30:00Z",
                "updated_at": "2026-01-15T10:30:00Z",
            }
        }
    )


class PremiumRequestListResponse(BaseModel):
    """Paginated premium request list response."""

    data: list[PremiumRequestResponse]
    pagination: Pagination


# ============================================================================
# Admin Review Schemas
# ============================================================================


class PremiumRequestApprove(BaseModel):
    """Schema for approving a premium request."""

    admin_notes: str | None = Field(default=None, description="Notes from admin")
    subscription_type: str = Field(
        default="premium",
        description="Subscription type to grant (premium or enterprise)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "admin_notes": "Approved for academic use",
                "subscription_type": "premium",
            }
        }
    )


class PremiumRequestReject(BaseModel):
    """Schema for rejecting a premium request."""

    admin_notes: str = Field(..., description="Reason for rejection")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "admin_notes": "Insufficient information provided. Please resubmit with organization details.",
            }
        }
    )


# ============================================================================
# Premium Feature Schemas
# ============================================================================


class PremiumFeatureResponse(BaseModel):
    """Premium feature response."""

    id: UUID
    name: str
    description: str | None = None
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "unlimited_uploads",
                "description": "Upload unlimited books with no file size restrictions",
                "is_active": True,
            }
        }
    )


# ============================================================================
# Subscription Schemas
# ============================================================================


class UserPremiumSubscriptionResponse(BaseModel):
    """User premium subscription response."""

    id: UUID
    user_id: UUID
    subscription_type: str
    start_date: datetime
    end_date: datetime | None = None
    is_active: bool
    granted_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# ============================================================================
# Stripe Schemas
# ============================================================================


class StripePaymentIntentResponse(BaseModel):
    """Stripe payment intent response."""

    id: UUID
    user_id: UUID
    stripe_payment_intent_id: str
    amount: int
    credit_amount: int
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# ============================================================================
# Upload Limit Schemas
# ============================================================================


class UserUploadLimitResponse(BaseModel):
    """User upload limits response."""

    id: UUID
    user_id: UUID
    is_premium: bool
    max_file_size_mb: int
    total_storage_mb: int
    current_storage_mb: int
    uploads_this_month: int
    monthly_upload_count: int
    reset_date: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# ============================================================================
# Stats Schemas
# ============================================================================


class PremiumRequestStats(BaseModel):
    """Statistics about premium requests."""

    total_requests: int
    pending_requests: int
    approved_requests: int
    rejected_requests: int
    in_review_requests: int
    approval_rate: float = Field(description="Approval rate as percentage")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_requests": 100,
                "pending_requests": 20,
                "approved_requests": 60,
                "rejected_requests": 15,
                "in_review_requests": 5,
                "approval_rate": 80.0,
            }
        }
    )
