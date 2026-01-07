"""Common schemas used across the API."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Pagination(BaseModel):
    """Pagination metadata."""

    page: int = Field(ge=1, description="Current page number")
    limit: int = Field(ge=1, le=100, description="Items per page")
    total: int = Field(ge=0, description="Total number of items")
    total_pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether there's a next page")
    has_prev: bool = Field(description="Whether there's a previous page")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "limit": 20,
                "total": 100,
                "total_pages": 5,
                "has_next": True,
                "has_prev": False,
            }
        }
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    data: list[T]
    pagination: Pagination


class ErrorDetail(BaseModel):
    """Error detail structure."""

    code: str = Field(description="Error code")
    message: str = Field(description="Human-readable error message")
    details: Any | None = Field(default=None, description="Additional error details")
    request_id: str | None = Field(default=None, description="Request ID for tracing")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: ErrorDetail

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Validation failed",
                    "details": [{"field": "email", "message": "Invalid email format"}],
                    "request_id": "req_abc123",
                }
            }
        }
    )


def create_pagination(
    page: int,
    limit: int,
    total: int,
) -> Pagination:
    """Create pagination metadata."""
    total_pages = (total + limit - 1) // limit if total > 0 else 0

    return Pagination(
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
