"""Pydantic schemas package."""

from app.schemas.common import (
    Pagination,
    PaginatedResponse,
    ErrorResponse,
    ErrorDetail,
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

__all__ = [
    # Common
    "Pagination",
    "PaginatedResponse",
    "ErrorResponse",
    "ErrorDetail",
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
]
