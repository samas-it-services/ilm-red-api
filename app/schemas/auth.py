"""Authentication schemas."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr = Field(description="User email address")
    password: str = Field(min_length=8, max_length=128, description="User password")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
            }
        }
    )


class RegisterRequest(BaseModel):
    """User registration request body."""

    email: EmailStr = Field(description="User email address")
    password: str = Field(min_length=8, max_length=128, description="User password")
    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique username (letters, numbers, underscore, hyphen)",
    )
    display_name: str = Field(min_length=1, max_length=100, description="Display name")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "username": "johndoe",
                "display_name": "John Doe",
            }
        }
    )


class TokenResponse(BaseModel):
    """Authentication token response."""

    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="Refresh token for obtaining new access tokens")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Access token expiration time in seconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "dGhpc2lzYXJlZnJlc2h0b2tlbg==",
                "token_type": "bearer",
                "expires_in": 900,
            }
        }
    )


class RefreshRequest(BaseModel):
    """Token refresh request body."""

    refresh_token: str = Field(description="Refresh token from previous login/refresh")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "dGhpc2lzYXJlZnJlc2h0b2tlbg==",
            }
        }
    )


class ApiKeyCreate(BaseModel):
    """API key creation request."""

    name: str = Field(min_length=1, max_length=100, description="Name for the API key")
    permissions: list[str] = Field(
        default=["read"],
        description="Permissions for this key",
    )
    expires_in_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="Expiration in days (None for no expiration)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "My Integration Key",
                "permissions": ["read", "write"],
                "expires_in_days": 90,
            }
        }
    )


class ApiKeyResponse(BaseModel):
    """API key response (without the secret)."""

    id: UUID
    name: str
    key_prefix: str = Field(description="First 12 characters of the key for identification")
    permissions: list[str]
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "My Integration Key",
                "key_prefix": "ilm_abc12345",
                "permissions": ["read", "write"],
                "last_used_at": None,
                "expires_at": "2025-04-15T00:00:00Z",
                "created_at": "2025-01-15T12:00:00Z",
            }
        }
    )


class ApiKeyCreatedResponse(BaseModel):
    """Response when API key is created (includes the full key once)."""

    api_key: str = Field(description="The full API key (only shown once)")
    key_info: ApiKeyResponse

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "api_key": "ilm_abc12345def67890ghijklmnop",
                "key_info": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "My Integration Key",
                    "key_prefix": "ilm_abc12345",
                    "permissions": ["read", "write"],
                    "last_used_at": None,
                    "expires_at": "2025-04-15T00:00:00Z",
                    "created_at": "2025-01-15T12:00:00Z",
                },
            }
        }
    )


# --- Google OAuth schemas ---


class GoogleOAuthRequest(BaseModel):
    """Google OAuth token exchange request."""

    code: str = Field(description="Authorization code from Google OAuth flow")
    redirect_uri: str = Field(description="Redirect URI used in the OAuth flow")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "4/0AX4XfWh...",
                "redirect_uri": "http://localhost:3000/auth/callback",
            }
        }
    )


class AuthTokenResponse(BaseModel):
    """OAuth authentication response with tokens and user info."""

    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="Refresh token for obtaining new access tokens")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Access token expiration time in seconds")
    user: dict[str, Any] = Field(description="Authenticated user profile data")
    is_new_user: bool = Field(description="Whether this is a newly created account")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "dGhpc2lzYXJlZnJlc2h0b2tlbg==",
                "token_type": "bearer",
                "expires_in": 900,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "username": "johndoe",
                    "display_name": "John Doe",
                },
                "is_new_user": False,
            }
        }
    )


class AuthMeResponse(BaseModel):
    """Full authenticated user profile with roles and permissions."""

    # Core user fields
    id: UUID
    email: EmailStr
    email_verified: bool
    username: str
    display_name: str
    avatar_url: str | None = None
    bio: str | None = None
    roles: list[str]
    status: str
    preferences: dict[str, Any] = Field(default_factory=dict)
    extra_data: dict[str, Any] | None = None

    # Extended profile fields
    profile_picture_url: str | None = None
    full_name: str | None = None
    location: str | None = None
    date_of_birth: date | None = None

    # Onboarding
    onboarding_completed: bool = False
    onboarding_completed_at: datetime | None = None

    # Premium
    is_premium_user: bool = False

    # Reading preferences
    favorite_genres: list[str] = Field(default_factory=list)
    reading_goal: int | None = None
    language_preference: list[str] = Field(default_factory=list)

    # Settings
    dark_mode: bool = False
    notifications_enabled: bool = True
    bookshelf_visibility: str = "public"
    developer_mode: bool = False
    ai_chat_settings: dict[str, Any] = Field(default_factory=dict)

    # Gamification
    total_points: int = 0
    current_rank_id: UUID | None = None
    badges_earned_count: int = 0

    # Activity
    last_login_at: datetime | None = None
    last_active_at: datetime | None = None
    created_at: datetime

    # Referral
    referral_source: str | None = None
    referred_by: UUID | None = None

    # RBAC enrichment
    permissions: list[str] = Field(
        default_factory=list,
        description="Permissions derived from RBAC roles",
    )

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
                "status": "active",
                "preferences": {"theme": "dark", "language": "en"},
                "full_name": "John Michael Doe",
                "location": "Milpitas, CA",
                "onboarding_completed": True,
                "is_premium_user": True,
                "favorite_genres": ["fiction", "science"],
                "reading_goal": 52,
                "language_preference": ["en"],
                "dark_mode": True,
                "notifications_enabled": True,
                "bookshelf_visibility": "public",
                "total_points": 1500,
                "badges_earned_count": 12,
                "created_at": "2025-01-01T12:00:00Z",
                "last_login_at": "2025-01-15T08:30:00Z",
                "permissions": ["books.read", "books.create", "chat.use"],
            }
        }
    )
