"""Feature announcement schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


class AnnouncementStatus(str, Enum):
    """Announcement status options."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AnnouncementPriority(str, Enum):
    """Announcement priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# ---------- Request Schemas ----------


class AnnouncementCreate(BaseModel):
    """Create a feature announcement."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    excerpt: str | None = Field(default=None, max_length=1000)
    featured_image_url: str | None = Field(default=None, max_length=500)
    status: AnnouncementStatus = AnnouncementStatus.DRAFT
    priority: AnnouncementPriority = AnnouncementPriority.NORMAL
    is_featured: bool = False
    is_pinned: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "New AI Chat Feature Released",
                "content": "# New Feature\n\nWe are excited to announce...",
                "excerpt": "Chat with multiple AI models in your library.",
                "status": "draft",
                "priority": "normal",
            }
        }
    )


class AnnouncementUpdate(BaseModel):
    """Update a feature announcement."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = Field(default=None, min_length=1)
    excerpt: str | None = Field(default=None, max_length=1000)
    featured_image_url: str | None = Field(default=None, max_length=500)
    status: AnnouncementStatus | None = None
    priority: AnnouncementPriority | None = None
    is_featured: bool | None = None
    is_pinned: bool | None = None


# ---------- Response Schemas ----------


class AnnouncementResponse(BaseModel):
    """Full feature announcement response."""

    id: UUID
    title: str
    slug: str
    excerpt: str | None
    content: str
    featured_image_url: str | None
    status: str
    priority: str
    is_featured: bool
    is_pinned: bool
    published_at: datetime | None
    view_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnnouncementListItem(BaseModel):
    """Simplified announcement item for list responses."""

    id: UUID
    title: str
    slug: str
    excerpt: str | None
    featured_image_url: str | None
    status: str
    priority: str
    is_featured: bool
    is_pinned: bool
    published_at: datetime | None
    view_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnnouncementListResponse(BaseModel):
    """Paginated announcement list response."""

    data: list[AnnouncementListItem]
    pagination: Pagination


class UnreadCountResponse(BaseModel):
    """Unread announcement count response."""

    unread_count: int
    total_published: int
