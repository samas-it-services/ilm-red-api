"""Quote schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


# Request Schemas


class QuoteCreate(BaseModel):
    """Create a new quote."""

    text: str = Field(..., min_length=1, max_length=5000)
    author: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=50)
    tags: list[str] = Field(default_factory=list, max_length=20)
    is_featured: bool = False
    is_active: bool = True
    display_date: date | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "The best of people are those who are most beneficial to people.",
                "author": "Prophet Muhammad (PBUH)",
                "source": "Al-Mu'jam al-Awsat",
                "category": "hadith",
                "tags": ["kindness", "service", "character"],
                "is_featured": True,
                "is_active": True,
            }
        }
    )


class QuoteUpdate(BaseModel):
    """Update an existing quote."""

    text: str | None = Field(default=None, min_length=1, max_length=5000)
    author: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=50)
    tags: list[str] | None = Field(default=None, max_length=20)
    is_featured: bool | None = None
    is_active: bool | None = None
    display_date: date | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_featured": True,
                "category": "wisdom",
            }
        }
    )


# Response Schemas


class QuoteResponse(BaseModel):
    """Full quote response."""

    id: UUID
    text: str
    author: str | None = None
    source: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_featured: bool = False
    is_active: bool = True
    display_date: date | None = None
    view_count: int = 0
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440020",
                "text": "The best of people are those who are most beneficial to people.",
                "author": "Prophet Muhammad (PBUH)",
                "source": "Al-Mu'jam al-Awsat",
                "category": "hadith",
                "tags": ["kindness", "service", "character"],
                "is_featured": True,
                "is_active": True,
                "display_date": "2026-01-15",
                "view_count": 42,
                "created_by": "550e8400-e29b-41d4-a716-446655440001",
                "created_at": "2026-01-10T08:00:00Z",
                "updated_at": "2026-01-10T08:00:00Z",
            }
        }
    )


class QuoteListResponse(BaseModel):
    """Paginated quote list response."""

    data: list[QuoteResponse]
    pagination: Pagination
