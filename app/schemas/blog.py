"""Blog schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


class BlogPostStatus(str, Enum):
    """Blog post status options."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class BlogPostVisibility(str, Enum):
    """Blog post visibility options."""

    PUBLIC = "public"
    PRIVATE = "private"
    MEMBERS_ONLY = "members_only"


# ---------- Shared / Embedded ----------


class AuthorBrief(BaseModel):
    """Brief author information for embedding in responses."""

    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BlogCategoryBrief(BaseModel):
    """Brief category info embedded in post responses."""

    id: UUID
    name: str
    slug: str
    icon: str | None = None
    color: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BlogTagBrief(BaseModel):
    """Brief tag info embedded in post responses."""

    id: UUID
    name: str
    slug: str
    color: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Category ----------


class BlogCategoryCreate(BaseModel):
    """Create a blog category."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    icon: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=20)
    is_active: bool = True


class BlogCategoryResponse(BaseModel):
    """Blog category response."""

    id: UUID
    name: str
    slug: str
    description: str | None
    icon: str | None
    color: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ---------- Tag ----------


class BlogTagCreate(BaseModel):
    """Create a blog tag."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    color: str | None = Field(default=None, max_length=20)


class BlogTagResponse(BaseModel):
    """Blog tag response."""

    id: UUID
    name: str
    slug: str
    description: str | None
    color: str | None

    model_config = ConfigDict(from_attributes=True)


# ---------- Blog Post ----------


class BlogPostCreate(BaseModel):
    """Create a blog post."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    excerpt: str | None = Field(default=None, max_length=1000)
    featured_image_url: str | None = Field(default=None, max_length=500)
    status: BlogPostStatus = BlogPostStatus.DRAFT
    visibility: BlogPostVisibility = BlogPostVisibility.PUBLIC
    is_featured: bool = False
    is_pinned: bool = False
    category_ids: list[UUID] = Field(default_factory=list)
    tag_ids: list[UUID] = Field(default_factory=list)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Getting Started with ILM Red",
                "content": "# Welcome\n\nThis is a guide to get you started...",
                "excerpt": "A quick introduction to the platform.",
                "status": "draft",
                "visibility": "public",
            }
        }
    )


class BlogPostUpdate(BaseModel):
    """Update a blog post."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = Field(default=None, min_length=1)
    excerpt: str | None = Field(default=None, max_length=1000)
    featured_image_url: str | None = Field(default=None, max_length=500)
    status: BlogPostStatus | None = None
    visibility: BlogPostVisibility | None = None
    is_featured: bool | None = None
    is_pinned: bool | None = None
    category_ids: list[UUID] | None = None
    tag_ids: list[UUID] | None = None


class BlogPostResponse(BaseModel):
    """Full blog post response."""

    id: UUID
    title: str
    slug: str
    content: str
    excerpt: str | None
    featured_image_url: str | None
    status: str
    visibility: str
    is_featured: bool
    is_pinned: bool
    published_at: datetime | None
    view_count: int
    like_count: int
    comment_count: int
    word_count: int | None
    reading_time: int | None
    author: AuthorBrief
    categories: list[BlogCategoryBrief]
    tags: list[BlogTagBrief]
    is_liked: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BlogPostListItem(BaseModel):
    """Simplified blog post item for list responses."""

    id: UUID
    title: str
    slug: str
    excerpt: str | None
    featured_image_url: str | None
    status: str
    visibility: str
    is_featured: bool
    is_pinned: bool
    published_at: datetime | None
    view_count: int
    like_count: int
    comment_count: int
    reading_time: int | None
    author: AuthorBrief
    categories: list[BlogCategoryBrief]
    tags: list[BlogTagBrief]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BlogPostListResponse(BaseModel):
    """Paginated blog post list response."""

    data: list[BlogPostListItem]
    pagination: Pagination


# ---------- Comment ----------


class BlogCommentCreate(BaseModel):
    """Create a blog comment."""

    content: str = Field(..., min_length=1, max_length=5000)
    parent_id: UUID | None = None


class BlogCommentResponse(BaseModel):
    """Blog comment response."""

    id: UUID
    post_id: UUID
    content: str
    parent_id: UUID | None
    is_approved: bool
    author: AuthorBrief
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BlogCommentListResponse(BaseModel):
    """Paginated blog comment list response."""

    data: list[BlogCommentResponse]
    pagination: Pagination
