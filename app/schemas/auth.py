"""Authentication schemas."""

from datetime import datetime
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
