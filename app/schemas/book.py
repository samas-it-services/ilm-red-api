"""Book schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


class BookCategory(str, Enum):
    """Book categories."""

    QURAN = "quran"
    HADITH = "hadith"
    SEERAH = "seerah"
    FIQH = "fiqh"
    AQIDAH = "aqidah"
    TAFSIR = "tafsir"
    HISTORY = "history"
    SPIRITUALITY = "spirituality"
    CHILDREN = "children"
    FICTION = "fiction"
    NON_FICTION = "non-fiction"
    EDUCATION = "education"
    SCIENCE = "science"
    TECHNOLOGY = "technology"
    BIOGRAPHY = "biography"
    SELF_HELP = "self-help"
    OTHER = "other"


class Visibility(str, Enum):
    """Book visibility options."""

    PUBLIC = "public"
    PRIVATE = "private"
    FRIENDS = "friends"


class BookStatus(str, Enum):
    """Book processing status."""

    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class BookStats(BaseModel):
    """Book statistics."""

    views: int = 0
    downloads: int = 0
    rating_count: int = 0
    rating_avg: float = 0.0

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "views": 150,
                "downloads": 45,
                "rating_count": 12,
                "rating_avg": 4.5,
            }
        }
    )


class UserBrief(BaseModel):
    """Brief user information for embedding in responses."""

    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


# Request Schemas


class BookCreate(BaseModel):
    """Book creation request (metadata only, file uploaded separately)."""

    title: str = Field(..., min_length=1, max_length=500)
    author: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    category: BookCategory = BookCategory.OTHER
    visibility: Visibility = Visibility.PRIVATE
    language: str = Field(default="en", max_length=10)
    isbn: str | None = Field(default=None, max_length=20)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Introduction to Islamic Finance",
                "author": "Muhammad Ibn Ahmad",
                "description": "A comprehensive guide to Islamic finance principles.",
                "category": "fiqh",
                "visibility": "public",
                "language": "en",
            }
        }
    )


class BookUpdate(BaseModel):
    """Book update request."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    author: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    category: BookCategory | None = None
    visibility: Visibility | None = None
    language: str | None = Field(default=None, max_length=10)
    isbn: str | None = Field(default=None, max_length=20)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated Title",
                "visibility": "public",
            }
        }
    )


class BookFilters(BaseModel):
    """Book list filters."""

    q: str | None = Field(default=None, description="Search query")
    category: BookCategory | None = Field(default=None, description="Filter by category")
    visibility: Visibility | None = Field(default=None, description="Filter by visibility")
    owner_id: UUID | None = Field(default=None, description="Filter by owner")
    status: BookStatus | None = Field(default=None, description="Filter by status")


# Response Schemas


class BookResponse(BaseModel):
    """Full book response."""

    id: UUID
    title: str
    author: str | None
    description: str | None
    category: str
    visibility: str
    language: str
    isbn: str | None

    # File info
    file_type: str
    file_size: int
    page_count: int | None
    cover_url: str | None

    # Status
    status: str
    processing_error: str | None

    # Stats
    stats: BookStats

    # Owner
    owner: UserBrief

    # URLs
    download_url: str | None = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Introduction to Islamic Finance",
                "author": "Muhammad Ibn Ahmad",
                "description": "A comprehensive guide...",
                "category": "fiqh",
                "visibility": "public",
                "language": "en",
                "isbn": "978-0123456789",
                "file_type": "pdf",
                "file_size": 5242880,
                "page_count": 250,
                "cover_url": "https://cdn.example.com/covers/book.jpg",
                "status": "ready",
                "processing_error": None,
                "stats": {
                    "views": 150,
                    "downloads": 45,
                    "rating_count": 12,
                    "rating_avg": 4.5,
                },
                "owner": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "username": "author123",
                    "display_name": "Author Name",
                    "avatar_url": None,
                },
                "download_url": "https://cdn.example.com/books/...",
                "created_at": "2025-01-01T12:00:00Z",
                "updated_at": "2025-01-15T08:30:00Z",
            }
        }
    )


class BookListItem(BaseModel):
    """Simplified book item for list responses."""

    id: UUID
    title: str
    author: str | None
    category: str
    visibility: str
    file_type: str
    file_size: int
    page_count: int | None
    cover_url: str | None
    status: str
    stats: BookStats
    owner: UserBrief
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookListResponse(BaseModel):
    """Paginated book list response."""

    data: list[BookListItem]
    pagination: Pagination


class BookUploadResponse(BaseModel):
    """Response after book upload."""

    id: UUID
    title: str
    status: str
    file_type: str
    file_size: int
    message: str = "Book uploaded successfully. Processing will begin shortly."
    is_global_duplicate: bool = Field(
        default=False,
        description=(
            "True if an identical file (by content hash) is already owned by a "
            "different user. The upload is still allowed; this flag is "
            "informational for moderation/copyright review."
        ),
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "My Book",
                "status": "processing",
                "file_type": "pdf",
                "file_size": 5242880,
                "message": "Book uploaded successfully. Processing will begin shortly.",
                "is_global_duplicate": False,
            }
        }
    )


class ChatQuotaStatus(BaseModel):
    """Monthly chat-enablement quota status for a user."""

    used: int = Field(description="Books enabled for chat in the current month")
    limit: int | None = Field(
        description="Monthly limit, or null for unlimited (premium/admin)"
    )
    remaining: int | None = Field(
        description="Remaining enablements this month, or null for unlimited"
    )
    is_unlimited: bool = Field(
        default=False, description="True for premium/admin users (no quota)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "used": 2,
                "limit": 5,
                "remaining": 3,
                "is_unlimited": False,
            }
        }
    )


class ChatEnableResponse(BaseModel):
    """Response after requesting chat processing for a book."""

    book_id: UUID
    status: str = Field(description="Processing job status (e.g. 'pending')")
    already_enabled: bool = Field(
        default=False,
        description="True if the book was already enabled/queued for chat",
    )
    quota: ChatQuotaStatus
    message: str = "Chat processing has been enqueued for this book."

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "book_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "already_enabled": False,
                "quota": {
                    "used": 3,
                    "limit": 5,
                    "remaining": 2,
                    "is_unlimited": False,
                },
                "message": "Chat processing has been enqueued for this book.",
            }
        }
    )


class DownloadUrlResponse(BaseModel):
    """Download URL response."""

    url: str
    expires_in: int = Field(description="URL expiration time in seconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://storage.example.com/books/...",
                "expires_in": 3600,
            }
        }
    )
