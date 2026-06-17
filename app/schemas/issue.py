"""Issue and feature request schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


class IssueType(str, Enum):
    """Issue type options."""

    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    QUESTION = "question"
    TECHNICAL_ISSUE = "technical_issue"
    ACCOUNT_ISSUE = "account_issue"


class IssuePriority(str, Enum):
    """Issue priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class IssueStatus(str, Enum):
    """Issue status options."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


# Request Schemas


class IssueCreate(BaseModel):
    """Create a new issue."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1, max_length=10000)
    issue_type: IssueType = Field(default=IssueType.BUG)
    priority: IssuePriority = Field(default=IssuePriority.MEDIUM)
    error_code: str | None = Field(default=None, max_length=100)
    book_id: UUID | None = Field(default=None, description="Related book ID")
    session_id: UUID | None = Field(default=None, description="Related chat session ID")
    attachments: dict | None = Field(default=None, description="File attachments metadata")
    metadata: dict | None = Field(default=None, description="Additional context data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Cannot open PDF book",
                "description": "When I try to open the book 'Introduction to Fiqh', the page never loads.",
                "issue_type": "bug",
                "priority": "high",
                "book_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    )


class IssueUpdate(BaseModel):
    """Update an existing issue."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, min_length=1, max_length=10000)
    issue_type: IssueType | None = None
    priority: IssuePriority | None = None
    status: IssueStatus | None = None
    error_code: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated title",
                "priority": "urgent",
            }
        }
    )


class IssueStatusUpdate(BaseModel):
    """Admin status update for an issue."""

    status: IssueStatus = Field(..., description="New status for the issue")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "in_progress",
            }
        }
    )


class IssueResponseCreate(BaseModel):
    """Create a response to an issue."""

    response_text: str = Field(..., min_length=1, max_length=10000)
    is_internal: bool = Field(default=False, description="Internal note (not visible to user)")
    attached_article_id: UUID | None = Field(default=None, description="Link to a help article")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "response_text": "Thank you for reporting this. We are investigating the issue.",
                "is_internal": False,
            }
        }
    )


# Response Schemas


class IssueUserBrief(BaseModel):
    """Brief user info for issue responses."""

    id: UUID
    username: str
    display_name: str

    model_config = ConfigDict(from_attributes=True)


class IssueResponseResponse(BaseModel):
    """Issue response detail."""

    id: UUID
    issue_id: UUID
    responder: IssueUserBrief
    response_text: str
    is_internal: bool = False
    attached_article_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440010",
                "issue_id": "550e8400-e29b-41d4-a716-446655440005",
                "responder": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "username": "admin",
                    "display_name": "Admin User",
                },
                "response_text": "We are looking into this issue.",
                "is_internal": False,
                "attached_article_id": None,
                "created_at": "2026-01-15T10:30:00Z",
            }
        }
    )


class IssueResponse(BaseModel):
    """Full issue response."""

    id: UUID
    user_id: UUID
    user: IssueUserBrief
    error_code: str | None = None
    issue_type: str
    title: str
    description: str
    priority: str
    status: str
    book_id: UUID | None = None
    session_id: UUID | None = None
    attachments: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    response_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440005",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "username": "reader123",
                    "display_name": "Reader Name",
                },
                "error_code": None,
                "issue_type": "bug",
                "title": "Cannot open PDF book",
                "description": "When I try to open the book, the page never loads.",
                "priority": "high",
                "status": "open",
                "book_id": "550e8400-e29b-41d4-a716-446655440000",
                "session_id": None,
                "attachments": {},
                "metadata": {},
                "response_count": 2,
                "created_at": "2026-01-15T10:00:00Z",
                "updated_at": "2026-01-15T10:30:00Z",
            }
        }
    )


class IssueListResponse(BaseModel):
    """Paginated issue list response."""

    data: list[IssueResponse]
    pagination: Pagination


class IssueResponseListResponse(BaseModel):
    """Paginated issue response list."""

    data: list[IssueResponseResponse]
    pagination: Pagination
