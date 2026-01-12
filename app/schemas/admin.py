"""Admin schemas for user, book, rating, and system management."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ============================================================================
# User Management Schemas
# ============================================================================


class AdminUserResponse(BaseModel):
    """Admin view of a user (includes sensitive fields)."""

    id: UUID
    email: EmailStr
    email_verified: bool
    username: str
    display_name: str
    avatar_url: str | None
    bio: str | None
    roles: list[str]
    status: Literal["active", "suspended", "deleted"]
    preferences: dict | None
    extra_data: dict | None
    created_at: datetime
    last_login_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AdminUserUpdate(BaseModel):
    """Admin update for a user (can modify roles, status)."""

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    roles: list[str] | None = Field(
        default=None,
        description="User roles: user, premium, admin, super_admin",
    )
    status: Literal["active", "suspended", "deleted"] | None = Field(
        default=None,
        description="Account status",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "roles": ["user", "premium"],
                "status": "active",
            }
        }
    )


class AdminUserListParams(BaseModel):
    """Query parameters for listing users."""

    search: str | None = Field(
        default=None,
        description="Search by email, username, or display_name",
    )
    status: Literal["active", "suspended", "deleted"] | None = Field(
        default=None,
        description="Filter by status",
    )
    role: str | None = Field(
        default=None,
        description="Filter by role",
    )
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


# ============================================================================
# Book Management Schemas
# ============================================================================


class AdminBookResponse(BaseModel):
    """Admin view of a book (includes processing status)."""

    id: UUID
    title: str
    author: str | None = None
    description: str | None = None
    category: str | None = None
    cover_url: str | None = None
    file_url: str | None = None
    visibility: Literal["public", "private", "friends"]
    owner_id: UUID
    owner_username: str | None = None
    page_count: int | None = None
    average_rating: float | None = None
    ratings_count: int = 0
    processing_status: Literal["pending", "processing", "ready", "failed"] = "ready"
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminBookListParams(BaseModel):
    """Query parameters for listing books."""

    search: str | None = Field(
        default=None,
        description="Search by title or author",
    )
    category: str | None = Field(default=None, description="Filter by category")
    owner_id: UUID | None = Field(default=None, description="Filter by owner")
    visibility: Literal["public", "private", "friends"] | None = Field(
        default=None, description="Filter by visibility"
    )
    has_pages: bool | None = Field(
        default=None,
        description="Filter by whether book has pages generated",
    )
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class BookProcessingRequest(BaseModel):
    """Request to trigger book processing."""

    force: bool = Field(
        default=False,
        description="Force regeneration even if already processed",
    )


class BookProcessingResponse(BaseModel):
    """Response from book processing request."""

    book_id: UUID
    action: str
    status: Literal["queued", "processing", "completed", "failed"]
    message: str


# ============================================================================
# Chat Session Management Schemas
# ============================================================================


class AdminChatSessionResponse(BaseModel):
    """Admin view of a chat session."""

    id: UUID
    book_id: UUID
    book_title: str | None = None
    user_id: UUID
    user_username: str | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminChatMessageResponse(BaseModel):
    """A message in a chat session."""

    id: UUID
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminChatSessionDetailResponse(BaseModel):
    """Detailed view of a chat session with messages."""

    id: UUID
    book_id: UUID
    book_title: str | None = None
    user_id: UUID
    user_username: str | None = None
    messages: list[AdminChatMessageResponse]
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminChatListParams(BaseModel):
    """Query parameters for listing chat sessions."""

    book_id: UUID | None = Field(default=None, description="Filter by book")
    user_id: UUID | None = Field(default=None, description="Filter by user")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


# ============================================================================
# System Statistics Schema
# ============================================================================


class SystemStatsResponse(BaseModel):
    """System-wide statistics."""

    total_users: int = Field(description="Total registered users")
    active_users: int = Field(description="Users with active status")
    admin_users: int = Field(description="Users with admin role")

    total_books: int = Field(description="Total books in the system")
    public_books: int = Field(description="Books marked as public")
    private_books: int = Field(description="Books marked as private")
    books_with_pages: int = Field(description="Books with pages generated")

    total_chat_sessions: int = Field(description="Total chat sessions")
    total_chat_messages: int = Field(description="Total chat messages")

    storage_used_bytes: int = Field(description="Total storage used in bytes")
    storage_used_formatted: str = Field(description="Human-readable storage used")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_users": 1500,
                "active_users": 1420,
                "admin_users": 5,
                "total_books": 5000,
                "public_books": 3200,
                "private_books": 1800,
                "books_with_pages": 4500,
                "total_chat_sessions": 12000,
                "total_chat_messages": 85000,
                "storage_used_bytes": 107374182400,
                "storage_used_formatted": "100.0 GB",
            }
        }
    )


# ============================================================================
# Rating Management Schemas
# ============================================================================


class AdminRatingResponse(BaseModel):
    """Admin view of a rating."""

    id: UUID
    book_id: UUID
    book_title: str | None = None
    user_id: UUID
    user_username: str | None = None
    rating: int
    review: str | None = None
    flag_count: int = 0
    is_flagged: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminRatingListParams(BaseModel):
    """Query parameters for listing ratings."""

    book_id: UUID | None = Field(default=None, description="Filter by book")
    user_id: UUID | None = Field(default=None, description="Filter by user")
    flagged_only: bool = Field(default=False, description="Show only flagged ratings")
    min_rating: int | None = Field(default=None, ge=1, le=5, description="Minimum rating")
    max_rating: int | None = Field(default=None, ge=1, le=5, description="Maximum rating")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class RatingAnalytics(BaseModel):
    """Rating analytics for admin."""

    total_ratings: int
    average_rating: float
    distribution: dict[str, int]  # {"1": 10, "2": 20, ...}
    top_rated_books: list[dict]  # [{book_id, title, avg_rating, count}, ...]
    most_reviewed_books: list[dict]
    recent_flagged_count: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_ratings": 1250,
                "average_rating": 4.2,
                "distribution": {"1": 45, "2": 78, "3": 203, "4": 412, "5": 512},
                "top_rated_books": [],
                "most_reviewed_books": [],
                "recent_flagged_count": 5,
            }
        }
    )


# ============================================================================
# Pagination Response
# ============================================================================


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    items: list
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(cls, items: list, total: int, page: int, page_size: int):
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
