"""Pydantic schemas package."""

from app.schemas.common import (
    Pagination,
    PaginatedResponse,
    ErrorResponse,
    ErrorDetail,
    create_pagination,
)
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshRequest,
    ApiKeyCreate,
    ApiKeyResponse,
)
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    PublicUserResponse,
)
from app.schemas.book import (
    BookCategory,
    Visibility,
    BookStatus,
    BookStats,
    UserBrief,
    BookCreate,
    BookUpdate,
    BookFilters,
    BookResponse,
    BookListItem,
    BookListResponse,
    BookUploadResponse,
    DownloadUrlResponse,
)
from app.schemas.rating import (
    RatingCreate,
    RatingUpdate,
    RatingResponse,
    RatingListResponse,
    RatingSummary,
    FavoriteResponse,
    FavoriteListResponse,
)

__all__ = [
    # Common
    "Pagination",
    "PaginatedResponse",
    "ErrorResponse",
    "ErrorDetail",
    "create_pagination",
    # Auth
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "RefreshRequest",
    "ApiKeyCreate",
    "ApiKeyResponse",
    # User
    "UserResponse",
    "UserUpdate",
    "PublicUserResponse",
    # Book
    "BookCategory",
    "Visibility",
    "BookStatus",
    "BookStats",
    "UserBrief",
    "BookCreate",
    "BookUpdate",
    "BookFilters",
    "BookResponse",
    "BookListItem",
    "BookListResponse",
    "BookUploadResponse",
    "DownloadUrlResponse",
    # Rating
    "RatingCreate",
    "RatingUpdate",
    "RatingResponse",
    "RatingListResponse",
    "RatingSummary",
    "FavoriteResponse",
    "FavoriteListResponse",
]
