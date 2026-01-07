"""User schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserPreferences(BaseModel):
    """User preferences."""

    theme: str = Field(default="system", pattern=r"^(light|dark|system)$")
    language: str = Field(default="en", max_length=10)
    timezone: str = Field(default="UTC", max_length=50)
    notifications: dict[str, bool] = Field(
        default={"email": True, "push": True},
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "theme": "dark",
                "language": "en",
                "timezone": "America/New_York",
                "notifications": {"email": True, "push": False},
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
                },
            }
        }
    )
