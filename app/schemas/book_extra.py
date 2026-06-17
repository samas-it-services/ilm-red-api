"""Book Extra schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


class BookExtraType(str, Enum):
    """Types of book extra content."""

    FLASHCARD = "flashcard"
    QUIZ = "quiz"
    AUDIO = "audio"
    PODCAST = "podcast"
    VIDEO = "video"
    INFOGRAPHIC = "infographic"
    SIMPLE_EXPLANATION = "simple_explanation"
    KEY_IDEAS = "key_ideas"


class BookExtraStatus(str, Enum):
    """Status of book extra content."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class BookExtraBase(BaseModel):
    """Base schema for BookExtra."""

    type: BookExtraType
    title: str = Field(..., min_length=1, max_length=200)
    content: dict = Field(..., description="JSON content structure depends on type")
    url: str | None = Field(default=None, max_length=500)
    status: BookExtraStatus = BookExtraStatus.PUBLISHED


class BookExtraCreate(BookExtraBase):
    """Schema for creating a BookExtra."""

    pass


class BookExtraUpdate(BaseModel):
    """Schema for updating a BookExtra."""

    type: BookExtraType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: dict | None = None
    url: str | None = Field(default=None, max_length=500)
    status: BookExtraStatus | None = None


class BookExtraResponse(BookExtraBase):
    """Schema for BookExtra response."""

    id: UUID
    book_id: UUID
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookExtraListResponse(BaseModel):
    """Paginated list of BookExtras."""

    data: list[BookExtraResponse]
    pagination: Pagination
