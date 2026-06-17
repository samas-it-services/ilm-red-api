"""Error log schemas for API request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


# Request Schemas


class ErrorLogCreate(BaseModel):
    """Schema for creating an error log entry."""

    error_type: str = Field(
        ..., max_length=100, description="Type of error (e.g., 'ValidationError', 'APIError')"
    )
    error_message: str = Field(..., description="Human-readable error message")
    stack_trace: str | None = Field(default=None, description="Full stack trace")
    user_id: UUID | None = Field(default=None, description="User ID if authenticated")
    book_id: UUID | None = Field(default=None, description="Related book ID")
    session_id: UUID | None = Field(default=None, description="Related session ID")
    request_data: dict | None = Field(default=None, description="Request context data")
    severity: str = Field(
        default="medium",
        pattern="^(low|medium|high|critical)$",
        description="Error severity: low, medium, high, critical",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_type": "ValidationError",
                "error_message": "Invalid book format",
                "stack_trace": "Traceback (most recent call last):\n  ...",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "book_id": "550e8400-e29b-41d4-a716-446655440001",
                "severity": "medium",
                "request_data": {"endpoint": "/v1/books", "method": "POST"},
            }
        }
    )


class ErrorLogResolve(BaseModel):
    """Schema for marking an error as resolved."""

    notes: str | None = Field(default=None, description="Resolution notes")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "notes": "Fixed by deploying hotfix v2.3.1",
            }
        }
    )


# Response Schemas


class ErrorLogResponse(BaseModel):
    """Full error log response."""

    id: UUID
    error_code: str
    error_type: str
    error_message: str
    stack_trace: str | None = None
    user_id: UUID | None = None
    book_id: UUID | None = None
    session_id: UUID | None = None
    request_data: dict = Field(default_factory=dict)
    severity: str
    ip_address: str | None = None
    user_agent: str | None = None
    resolved: bool
    resolved_at: datetime | None = None
    resolved_by: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "error_code": "ERR-00042",
                "error_type": "ValidationError",
                "error_message": "Invalid book format",
                "severity": "medium",
                "resolved": False,
                "created_at": "2026-01-15T10:30:00Z",
            }
        }
    )


class ErrorLogCreateResponse(BaseModel):
    """Response after creating an error log entry."""

    error_code: str = Field(description="Unique error tracking code")
    id: UUID = Field(description="Error log ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "ERR-00042",
                "id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    )


class ErrorLogListResponse(BaseModel):
    """Paginated error log list response."""

    data: list[ErrorLogResponse]
    pagination: Pagination
