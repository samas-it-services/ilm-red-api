"""User schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AIPreferences(BaseModel):
    """User AI preferences for model selection and behavior."""

    default_model: str | None = Field(
        default=None,
        description="User's preferred AI model for private books (e.g., 'gpt-4o-mini', 'claude-3-sonnet')",
    )
    default_vendor: Literal["openai", "anthropic", "qwen", "google", "xai", "deepseek"] | None = Field(
        default=None,
        description="Preferred AI vendor",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default sampling temperature for AI responses",
    )
    max_tokens: int = Field(
        default=4096,
        ge=256,
        le=32768,
        description="Default maximum tokens for AI responses",
    )
    streaming_enabled: bool = Field(
        default=True,
        description="Whether to stream AI responses",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "default_model": "gpt-4o-mini",
                "default_vendor": "openai",
                "temperature": 0.7,
                "max_tokens": 4096,
                "streaming_enabled": True,
            }
        }
    )


class UserPreferences(BaseModel):
    """User preferences."""

    theme: str = Field(default="system", pattern=r"^(light|dark|system)$")
    language: str = Field(default="en", max_length=10)
    timezone: str = Field(default="UTC", max_length=50)
    notifications: dict[str, bool] = Field(
        default={"email": True, "push": True},
    )
    ai: AIPreferences = Field(
        default_factory=AIPreferences,
        description="AI-related preferences for model selection",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "theme": "dark",
                "language": "en",
                "timezone": "America/New_York",
                "notifications": {"email": True, "push": False},
                "ai": {
                    "default_model": "gpt-4o-mini",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
            }
        }
    )


class UserResponse(BaseModel):
    """Full user response (for authenticated user)."""

    id: UUID
    email: EmailStr
    email_verified: bool
    username: str
    display_name: str
    avatar_url: str | None
    bio: str | None
    roles: list[str]
    preferences: dict
    created_at: datetime
    last_login_at: datetime | None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "email_verified": True,
                "username": "johndoe",
                "display_name": "John Doe",
                "avatar_url": "https://cdn.ilm-red.com/avatars/user123.jpg",
                "bio": "Book lover and knowledge seeker",
                "roles": ["user", "premium"],
                "preferences": {
                    "theme": "dark",
                    "language": "en",
                    "ai": {
                        "default_model": "gpt-4o-mini",
                        "temperature": 0.7,
                    },
                },
                "created_at": "2025-01-01T12:00:00Z",
                "last_login_at": "2025-01-15T08:30:00Z",
            }
        }
    )


class PublicUserResponse(BaseModel):
    """Public user profile (limited fields)."""

    id: UUID
    username: str
    display_name: str
    avatar_url: str | None
    bio: str | None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "johndoe",
                "display_name": "John Doe",
                "avatar_url": "https://cdn.ilm-red.com/avatars/user123.jpg",
                "bio": "Book lover and knowledge seeker",
            }
        }
    )


class UserUpdate(BaseModel):
    """User update request."""

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    preferences: UserPreferences | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "display_name": "John D.",
                "bio": "Updated bio",
                "preferences": {
                    "theme": "light",
                    "language": "en",
                    "ai": {
                        "default_model": "claude-3-sonnet",
                        "temperature": 0.8,
                    },
                },
            }
        }
    )
