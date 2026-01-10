"""Chat schemas for sessions, messages, and feedback."""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


class MessageRole(str, Enum):
    """Chat message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class FinishReason(str, Enum):
    """AI response finish reasons."""

    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"


# Request Schemas


class ChatSessionCreate(BaseModel):
    """Create a new chat session."""

    title: str | None = Field(default=None, max_length=200)
    book_id: UUID | None = Field(default=None, description="Optional book context for the chat")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Discussion about Islamic Finance",
                "book_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    )


class ChatSessionUpdate(BaseModel):
    """Update chat session metadata."""

    title: str | None = Field(default=None, max_length=200)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated Chat Title",
            }
        }
    )


class ChatMessageCreate(BaseModel):
    """Send a new message in a chat session."""

    content: str = Field(..., min_length=1, max_length=32000)
    model: str | None = Field(
        default=None,
        max_length=50,
        description="Optional model override (e.g., 'gpt-4o', 'claude-3-sonnet')",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Can you explain the concept of riba in Islamic finance?",
                "model": None,
            }
        }
    )


class MessageFeedbackCreate(BaseModel):
    """Submit feedback on an AI message."""

    rating: Literal[-1, 1] = Field(..., description="Thumbs down (-1) or thumbs up (1)")
    comment: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rating": 1,
                "comment": "Very helpful and accurate explanation.",
            }
        }
    )


# Response Schemas


class BookBrief(BaseModel):
    """Brief book information for embedding in responses."""

    id: UUID
    title: str
    author: str | None = None
    cover_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ChatMessageResponse(BaseModel):
    """Chat message response."""

    id: UUID
    session_id: UUID
    role: str
    content: str
    tokens_input: int | None = None
    tokens_output: int | None = None
    cost_cents: int | None = None
    model: str | None = None
    finish_reason: str | None = None
    safety_flags: list = Field(default_factory=list)
    created_at: datetime
    has_feedback: bool = False

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "role": "assistant",
                "content": "Riba is an Arabic term that refers to...",
                "tokens_input": 45,
                "tokens_output": 320,
                "cost_cents": 2,
                "model": "gpt-4o-mini",
                "finish_reason": "stop",
                "safety_flags": [],
                "created_at": "2026-01-09T12:00:00Z",
                "has_feedback": False,
            }
        }
    )


class ChatSessionResponse(BaseModel):
    """Chat session response (without messages)."""

    id: UUID
    title: str | None
    book_id: UUID | None = None
    book: BookBrief | None = None
    message_count: int
    last_model: str | None = None
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Discussion about Islamic Finance",
                "book_id": "550e8400-e29b-41d4-a716-446655440002",
                "book": {
                    "id": "550e8400-e29b-41d4-a716-446655440002",
                    "title": "Introduction to Islamic Finance",
                    "author": "Muhammad Ibn Ahmad",
                    "cover_url": None,
                },
                "message_count": 10,
                "last_model": "gpt-4o-mini",
                "is_archived": False,
                "created_at": "2026-01-09T10:00:00Z",
                "updated_at": "2026-01-09T12:00:00Z",
            }
        }
    )


class ChatSessionDetail(BaseModel):
    """Chat session with messages."""

    id: UUID
    title: str | None
    book_id: UUID | None = None
    book: BookBrief | None = None
    message_count: int
    last_model: str | None = None
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Discussion about Islamic Finance",
                "book_id": None,
                "book": None,
                "message_count": 2,
                "last_model": "gpt-4o-mini",
                "is_archived": False,
                "created_at": "2026-01-09T10:00:00Z",
                "updated_at": "2026-01-09T12:00:00Z",
                "messages": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "session_id": "550e8400-e29b-41d4-a716-446655440000",
                        "role": "user",
                        "content": "What is riba?",
                        "tokens_input": None,
                        "tokens_output": None,
                        "cost_cents": None,
                        "model": None,
                        "finish_reason": None,
                        "safety_flags": [],
                        "created_at": "2026-01-09T10:00:00Z",
                        "has_feedback": False,
                    },
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440002",
                        "session_id": "550e8400-e29b-41d4-a716-446655440000",
                        "role": "assistant",
                        "content": "Riba is an Arabic term...",
                        "tokens_input": 10,
                        "tokens_output": 150,
                        "cost_cents": 1,
                        "model": "gpt-4o-mini",
                        "finish_reason": "stop",
                        "safety_flags": [],
                        "created_at": "2026-01-09T10:00:05Z",
                        "has_feedback": False,
                    },
                ],
            }
        }
    )


class ChatSessionListItem(BaseModel):
    """Simplified chat session for list responses."""

    id: UUID
    title: str | None
    book_id: UUID | None = None
    message_count: int
    last_model: str | None = None
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime
    # Preview of last message
    last_message_preview: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ChatSessionListResponse(BaseModel):
    """Paginated chat session list response."""

    data: list[ChatSessionListItem]
    pagination: Pagination


class ChatMessageListResponse(BaseModel):
    """Paginated chat message list response."""

    data: list[ChatMessageResponse]
    pagination: Pagination


class MessageFeedbackResponse(BaseModel):
    """Message feedback response."""

    id: UUID
    message_id: UUID
    rating: int
    comment: str | None = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440003",
                "message_id": "550e8400-e29b-41d4-a716-446655440001",
                "rating": 1,
                "comment": "Very helpful explanation!",
                "created_at": "2026-01-09T12:05:00Z",
            }
        }
    )


# Streaming schemas


class StreamChunk(BaseModel):
    """SSE stream chunk for streaming responses."""

    type: Literal["content", "done", "error"] = "content"
    content: str | None = None
    message_id: UUID | None = None
    # Sent with 'done' type
    tokens_input: int | None = None
    tokens_output: int | None = None
    cost_cents: int | None = None
    model: str | None = None
    finish_reason: str | None = None
    # Sent with 'error' type
    error: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"type": "content", "content": "Riba is "},
                {"type": "content", "content": "an Arabic term..."},
                {
                    "type": "done",
                    "message_id": "550e8400-e29b-41d4-a716-446655440001",
                    "tokens_input": 45,
                    "tokens_output": 320,
                    "cost_cents": 2,
                    "model": "gpt-4o-mini",
                    "finish_reason": "stop",
                },
            ]
        }
    )
