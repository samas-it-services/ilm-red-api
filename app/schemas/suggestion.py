"""Suggestion system schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


# Request Schemas


class SuggestionCreate(BaseModel):
    """Submit a new suggestion."""

    suggestion_text: str = Field(..., min_length=1, max_length=5000)
    category: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "suggestion_text": "Can you recommend books on Islamic history?",
                "category": "recommendation",
            }
        }
    )


class SuggestionFeedbackCreate(BaseModel):
    """Submit feedback on a suggestion response."""

    feedback_type: str = Field(..., max_length=50)
    rating: int | None = Field(default=None, ge=1, le=5)
    feedback_text: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "feedback_type": "helpful",
                "rating": 5,
                "feedback_text": "Very helpful response!",
            }
        }
    )


class SuggestionConfigUpdate(BaseModel):
    """Update user's suggestion configuration."""

    is_enabled: bool | None = None
    ai_model: str | None = Field(default=None, max_length=50)
    daily_limit: int | None = Field(default=None, ge=1, le=50)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_enabled": True,
                "ai_model": "gpt-4",
                "daily_limit": 10,
            }
        }
    )


class SystemConfigUpdate(BaseModel):
    """Update system-wide suggestion configuration. Admin only."""

    system_enabled: bool | None = None
    default_ai_model: str | None = Field(default=None, max_length=50)
    default_daily_limit: int | None = Field(default=None, ge=1, le=100)
    available_models: list[str] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "system_enabled": True,
                "default_ai_model": "gpt-4",
                "default_daily_limit": 5,
                "available_models": ["gpt-4", "gpt-3.5-turbo"],
            }
        }
    )


# Response Schemas


class SuggestionResponse(BaseModel):
    """Full suggestion response."""

    id: UUID
    user_id: UUID
    suggestion_text: str
    category: str | None
    detected_language: str | None
    sentiment: str | None
    has_passage_offer: bool
    offered_book_id: UUID | None
    offered_book_title: str | None
    ai_response: str | None
    admin_response: str | None
    admin_responder_id: UUID | None
    admin_response_date: datetime | None
    status: str
    priority: str
    is_read: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SuggestionListItem(BaseModel):
    """Simplified suggestion for list responses."""

    id: UUID
    suggestion_text: str
    category: str | None
    status: str
    priority: str
    is_read: bool
    has_passage_offer: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SuggestionListResponse(BaseModel):
    """Paginated suggestion list response."""

    data: list[SuggestionListItem]
    pagination: Pagination


class SuggestionFeedbackResponse(BaseModel):
    """Feedback response."""

    id: UUID
    suggestion_id: UUID
    user_id: UUID
    feedback_type: str
    rating: int | None
    feedback_text: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SuggestionNotificationResponse(BaseModel):
    """Notification response."""

    id: UUID
    user_id: UUID
    suggestion_id: UUID
    notification_type: str
    title: str
    message: str | None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SuggestionNotificationListResponse(BaseModel):
    """Paginated notification list response."""

    data: list[SuggestionNotificationResponse]
    pagination: Pagination


class SuggestionConfigResponse(BaseModel):
    """User suggestion configuration response."""

    id: UUID
    user_id: UUID
    is_enabled: bool
    ai_model: str | None
    daily_limit: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SystemConfigResponse(BaseModel):
    """System suggestion configuration response."""

    id: UUID
    system_enabled: bool
    default_ai_model: str | None
    default_daily_limit: int
    available_models: list
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
