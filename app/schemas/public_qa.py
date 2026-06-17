"""Public Q&A schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


class QAStatus(str, Enum):
    """Public QA status options."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class QAVisibility(str, Enum):
    """Public QA visibility options."""

    PUBLIC = "public"
    PREMIUM = "premium"
    ADMIN = "admin"


class VoteType(str, Enum):
    """Vote type options."""

    UPVOTE = "upvote"
    DOWNVOTE = "downvote"


class FeedbackType(str, Enum):
    """Feedback type options."""

    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"


class UserBrief(BaseModel):
    """Brief user information for embedding in QA responses."""

    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


# Request Schemas


class PromoteToPublicQARequest(BaseModel):
    """Request to promote a chat message to public Q&A."""

    original_message_id: UUID = Field(
        ...,
        description="ID of the original chat message to promote",
    )
    book_id: UUID = Field(
        ...,
        description="Book ID associated with this Q&A",
    )
    question: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The question text",
    )
    answer: str = Field(
        ...,
        min_length=1,
        max_length=20000,
        description="The answer text",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Title for the Q&A entry",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional description",
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Tags for categorization",
    )
    category: str | None = Field(
        default=None,
        max_length=100,
        description="Category for the Q&A",
    )
    status: QAStatus = Field(
        default=QAStatus.DRAFT,
        description="Initial status",
    )
    visibility: QAVisibility = Field(
        default=QAVisibility.PUBLIC,
        description="Visibility setting",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "original_message_id": "550e8400-e29b-41d4-a716-446655440000",
                "book_id": "550e8400-e29b-41d4-a716-446655440001",
                "question": "What is the concept of Riba in Islamic finance?",
                "answer": "Riba refers to the concept of usury or interest...",
                "title": "Understanding Riba in Islamic Finance",
                "description": "A clear explanation of the prohibition of interest",
                "tags": ["fiqh", "finance", "riba"],
                "category": "islamic_finance",
                "status": "draft",
                "visibility": "public",
            }
        }
    )


class PublicQAUpdate(BaseModel):
    """Request to update a public Q&A entry."""

    question: str | None = Field(default=None, min_length=1, max_length=5000)
    answer: str | None = Field(default=None, min_length=1, max_length=20000)
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    tags: list[str] | None = Field(default=None, max_length=10)
    category: str | None = Field(default=None, max_length=100)
    status: QAStatus | None = None
    visibility: QAVisibility | None = None
    featured: bool | None = None
    edit_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Reason for the edit",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated Title",
                "answer": "Updated and improved answer...",
                "edit_reason": "Added more detail to the answer",
            }
        }
    )


class VoteRequest(BaseModel):
    """Request to vote on a Q&A entry."""

    vote_type: VoteType = Field(
        ...,
        description="Type of vote: upvote or downvote",
    )
    explanation: str | None = Field(
        default=None,
        max_length=500,
        description="Optional explanation for the vote",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "vote_type": "upvote",
                "explanation": "Very clear and helpful answer",
            }
        }
    )


class FeedbackRequest(BaseModel):
    """Request to submit feedback on a Q&A entry."""

    feedback_type: FeedbackType = Field(
        ...,
        description="Type of feedback: helpful or not_helpful",
    )
    feedback_text: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional feedback text",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "feedback_type": "helpful",
                "feedback_text": "This answered my question perfectly",
            }
        }
    )


# Response Schemas


class PublicQAResponse(BaseModel):
    """Full public Q&A response."""

    id: UUID
    original_message_id: UUID
    book_id: UUID
    user_id: UUID
    question: str
    answer: str
    title: str
    description: str | None = None
    tags: list[str] = []
    category: str | None = None
    status: str
    visibility: str
    featured: bool = False
    upvotes: int = 0
    downvotes: int = 0
    net_votes: int = 0
    view_count: int = 0
    helpful_count: int = 0
    not_helpful_count: int = 0
    published_at: datetime | None = None
    last_edited_at: datetime | None = None
    user: UserBrief | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicQAListResponse(BaseModel):
    """Paginated public Q&A list response."""

    data: list[PublicQAResponse]
    pagination: Pagination


class VoteResponse(BaseModel):
    """Response after voting."""

    qa_id: UUID
    vote_type: str | None = None
    upvotes: int
    downvotes: int
    net_votes: int
    message: str


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""

    id: UUID
    qa_id: UUID
    feedback_type: str
    feedback_text: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EditHistoryEntry(BaseModel):
    """Single edit history entry."""

    id: UUID
    qa_id: UUID
    edited_by: UUID
    edited_at: datetime
    previous_question: str | None = None
    previous_answer: str | None = None
    previous_title: str | None = None
    previous_description: str | None = None
    previous_tags: list[str] | None = None
    previous_category: str | None = None
    edit_reason: str | None = None
    version_number: int
    editor: UserBrief | None = None

    model_config = ConfigDict(from_attributes=True)


class EditHistoryResponse(BaseModel):
    """Edit history response."""

    data: list[EditHistoryEntry]
    qa_id: UUID
