"""Rating flag schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RatingFlagCreate(BaseModel):
    """Request to flag a rating."""

    reason: Literal["spam", "offensive", "irrelevant", "other"] = Field(
        ..., description="Reason for flagging"
    )
    details: str | None = Field(
        None, max_length=500, description="Additional details (optional)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reason": "spam",
                "details": "This review is copy-pasted from another site",
            }
        }
    )


class RatingFlagResponse(BaseModel):
    """Rating flag response."""

    id: UUID
    rating_id: UUID
    reporter_id: UUID
    reason: str
    details: str | None
    status: str
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class RatingFlagStats(BaseModel):
    """Flag statistics for a rating."""

    rating_id: UUID
    flag_count: int
    is_flagged: bool  # True if has any pending flags

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rating_id": "123e4567-e89b-12d3-a456-426614174000",
                "flag_count": 3,
                "is_flagged": True,
            }
        }
    )
