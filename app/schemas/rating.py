"""Rating schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.book import UserBrief
from app.schemas.common import Pagination

# Request Schemas


class RatingCreate(BaseModel):
    """Rating creation request."""

    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    review: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional review text",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rating": 5,
                "review": "An excellent book that covers all the fundamentals.",
            }
        }
    )


class RatingUpdate(BaseModel):
    """Rating update request."""

    rating: int | None = Field(default=None, ge=1, le=5)
    review: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rating": 4,
                "review": "Updated review after re-reading.",
            }
        }
    )


# Response Schemas


class RatingResponse(BaseModel):
    """Full rating response."""

    id: UUID
    book_id: UUID
    rating: int
    review: str | None
    user: UserBrief
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "book_id": "550e8400-e29b-41d4-a716-446655440001",
                "rating": 5,
                "review": "An excellent book!",
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440002",
                    "username": "reader123",
                    "display_name": "John Doe",
                    "avatar_url": None,
                },
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-01T12:00:00Z",
            }
        }
    )


class RatingListResponse(BaseModel):
    """Paginated rating list response."""

    data: list[RatingResponse]
    pagination: Pagination


class RatingSummary(BaseModel):
    """Rating summary for a book."""

    average: float = Field(description="Average rating (1-5)")
    count: int = Field(description="Total number of ratings")
    distribution: dict[str, int] = Field(
        description="Rating distribution (1-5 stars)",
        default_factory=lambda: {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "average": 4.5,
                "count": 25,
                "distribution": {
                    "1": 0,
                    "2": 1,
                    "3": 2,
                    "4": 8,
                    "5": 14,
                },
            }
        }
    )


class FavoriteResponse(BaseModel):
    """Favorite response."""

    book_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FavoriteListResponse(BaseModel):
    """List of favorites response."""

    data: list[FavoriteResponse]
    pagination: Pagination
