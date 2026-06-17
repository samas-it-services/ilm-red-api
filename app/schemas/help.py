"""Help/Documentation schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


class HelpArticleStatus(str, Enum):
    """Help article status options."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class HelpArticleVisibility(str, Enum):
    """Help article visibility options."""

    PUBLIC = "public"
    PRIVATE = "private"
    MEMBERS_ONLY = "members_only"


class HelpFeedbackType(str, Enum):
    """Help article feedback type."""

    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"


# ---------- Shared / Embedded ----------


class AuthorBrief(BaseModel):
    """Brief author information for embedding in responses."""

    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class HelpScreenshotResponse(BaseModel):
    """Help article screenshot response."""

    id: UUID
    image_url: str
    alt_text: str | None
    caption: str | None
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


# ---------- Category ----------


class HelpCategoryCreate(BaseModel):
    """Create a help category."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    icon: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=20)
    sort_order: int = 0
    is_active: bool = True


class HelpCategoryResponse(BaseModel):
    """Help category response."""

    id: UUID
    name: str
    slug: str
    description: str | None
    icon: str | None
    color: str | None
    sort_order: int
    is_active: bool
    article_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class HelpCategoryListResponse(BaseModel):
    """Help category list response."""

    data: list[HelpCategoryResponse]


# ---------- Article ----------


class HelpArticleCreate(BaseModel):
    """Create a help article."""

    category_id: UUID
    title_en: str = Field(..., min_length=1, max_length=500)
    content_en: str = Field(..., min_length=1)
    title_ur: str | None = Field(default=None, max_length=500)
    content_ur: str | None = None
    excerpt: str | None = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list)
    sort_order: int = 0
    is_featured: bool = False
    is_pinned: bool = False
    status: HelpArticleStatus = HelpArticleStatus.DRAFT
    visibility: HelpArticleVisibility = HelpArticleVisibility.PUBLIC

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category_id": "550e8400-e29b-41d4-a716-446655440000",
                "title_en": "How to Upload a Book",
                "content_en": "# Upload Guide\n\nFollow these steps to upload...",
                "excerpt": "Learn how to upload books to your library.",
                "tags": ["upload", "books", "getting-started"],
                "status": "draft",
            }
        }
    )


class HelpArticleUpdate(BaseModel):
    """Update a help article."""

    category_id: UUID | None = None
    title_en: str | None = Field(default=None, min_length=1, max_length=500)
    content_en: str | None = Field(default=None, min_length=1)
    title_ur: str | None = Field(default=None, max_length=500)
    content_ur: str | None = None
    excerpt: str | None = Field(default=None, max_length=1000)
    tags: list[str] | None = None
    sort_order: int | None = None
    is_featured: bool | None = None
    is_pinned: bool | None = None
    status: HelpArticleStatus | None = None
    visibility: HelpArticleVisibility | None = None


class HelpArticleResponse(BaseModel):
    """Full help article response."""

    id: UUID
    category_id: UUID
    slug: str
    status: str
    title_en: str
    content_en: str
    title_ur: str | None
    content_ur: str | None
    excerpt: str | None
    tags: list[str] | None
    sort_order: int
    is_featured: bool
    is_pinned: bool
    view_count: int
    helpful_count: int
    not_helpful_count: int
    visibility: str
    published_at: datetime | None
    author: AuthorBrief
    screenshots: list[HelpScreenshotResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HelpArticleListItem(BaseModel):
    """Simplified help article item for list responses."""

    id: UUID
    category_id: UUID
    slug: str
    status: str
    title_en: str
    title_ur: str | None
    excerpt: str | None
    tags: list[str] | None
    sort_order: int
    is_featured: bool
    is_pinned: bool
    view_count: int
    helpful_count: int
    not_helpful_count: int
    published_at: datetime | None
    author: AuthorBrief
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HelpArticleListResponse(BaseModel):
    """Paginated help article list response."""

    data: list[HelpArticleListItem]
    pagination: Pagination


# ---------- Feedback ----------


class HelpFeedbackCreate(BaseModel):
    """Create help article feedback."""

    feedback_type: HelpFeedbackType
    feedback_text: str | None = Field(default=None, max_length=2000)


class HelpFeedbackResponse(BaseModel):
    """Help article feedback response."""

    id: UUID
    article_id: UUID
    user_id: UUID
    feedback_type: str
    feedback_text: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Share ----------


class HelpShareCreate(BaseModel):
    """Create help article share record."""

    share_method: str = Field(..., max_length=50)  # link, email, social


class HelpShareResponse(BaseModel):
    """Help article share response."""

    id: UUID
    article_id: UUID
    share_method: str
    shared_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- View ----------


class HelpViewCreate(BaseModel):
    """Track help article view."""

    language: str = Field(default="en", max_length=10)
