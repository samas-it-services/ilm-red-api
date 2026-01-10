"""Authentication endpoints."""

import hashlib
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_api_key,
    hash_password,
    verify_password,
    verify_refresh_token_hash,
)
from app.core.exceptions import ConflictError, UnauthorizedError
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshRequest,
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyCreatedResponse,
)
from app.api.v1.deps import CurrentUser

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="""
Create a new user account and receive authentication tokens.

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

**Example:**
```bash
curl -X POST /v1/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{"email":"user@example.com","password":"SecurePass123!","username":"johndoe","display_name":"John Doe"}'
```

**Returns:** JWT access token (15 min) and refresh token (7 days)
    """,
    responses={
        409: {"description": "Email or username already exists"},
        422: {"description": "Validation error (weak password, invalid email format, etc.)"},
    },
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user account."""
    user_repo = UserRepository(db)

    # Check if email already exists
    existing = await user_repo.get_by_email(data.email)
    if existing:
        raise ConflictError("Email already registered")

    # Check if username already exists
    existing = await user_repo.get_by_username(data.username)
    if existing:
        raise ConflictError("Username already taken")

    # Create user
    password_hash = hash_password(data.password)
    user = await user_repo.create(
        email=data.email,
        username=data.username,
        display_name=data.display_name,
        password_hash=password_hash,
    )

    logger.info("User registered", user_id=str(user.id), email=user.email)

    # Generate tokens
    access_token = create_access_token(subject=str(user.id))

    raw_refresh, refresh_hash = create_refresh_token(subject=str(user.id))
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    await user_repo.create_refresh_token(user.id, refresh_hash, expires_at)

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
    description="""
Authenticate with email and password to receive tokens.

**Security:** Password is verified using Argon2 hashing.

**Example:**
```bash
curl -X POST /v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email":"user@example.com","password":"SecurePass123!"}'
```

**After Login:**
Use the `access_token` in the Authorization header:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```
    """,
    responses={
        401: {"description": "Invalid email or password"},
        403: {"description": "Account suspended or inactive"},
    },
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user with email and password."""
    user_repo = UserRepository(db)

    # Find user
    user = await user_repo.get_by_email(data.email)
    if not user or not user.password_hash:
        raise UnauthorizedError("Invalid email or password")

    # Verify password
    if not verify_password(data.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")

    # Check user status
    if user.status != "active":
        raise UnauthorizedError("Account is not active")

    # Update last login
    await user_repo.update_last_login(user)

    logger.info("User logged in", user_id=str(user.id))

    # Generate tokens
    access_token = create_access_token(subject=str(user.id))

    raw_refresh, refresh_hash = create_refresh_token(subject=str(user.id))
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    await user_repo.create_refresh_token(user.id, refresh_hash, expires_at)

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="""
Exchange a refresh token for a new access token.

**Token Rotation:** For security, the old refresh token is revoked and a new one is issued.

**When to Use:**
- Access tokens expire in 15 minutes
- Call this endpoint before expiration to maintain session
- Refresh tokens expire in 7 days

**Example:**
```bash
curl -X POST /v1/auth/refresh \\
  -H "Content-Type: application/json" \\
  -d '{"refresh_token":"your_refresh_token_here"}'
```
    """,
    responses={
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    user_repo = UserRepository(db)

    # Hash the provided token
    token_hash = hashlib.sha256(data.refresh_token.encode()).hexdigest()

    # Find the refresh token
    token = await user_repo.get_refresh_token(token_hash)
    if not token or not token.is_valid:
        raise UnauthorizedError("Invalid or expired refresh token")

    # Get user
    user = await user_repo.get_by_id(token.user_id)
    if not user or user.status != "active":
        raise UnauthorizedError("User not found or inactive")

    # Revoke old token (token rotation)
    await user_repo.revoke_refresh_token(token)

    logger.info("Token refreshed", user_id=str(user.id))

    # Generate new tokens
    access_token = create_access_token(subject=str(user.id))

    raw_refresh, refresh_hash = create_refresh_token(subject=str(user.id))
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    await user_repo.create_refresh_token(user.id, refresh_hash, expires_at)

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout and revoke refresh token",
    description="""
End session by revoking the refresh token.

**Note:** The access token remains valid until it expires (15 min max).
For immediate client-side logout, also discard the access token locally.

**Example:**
```bash
curl -X POST /v1/auth/logout \\
  -H "Content-Type: application/json" \\
  -d '{"refresh_token":"your_refresh_token_here"}'
```
    """,
)
async def logout(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Logout by revoking the refresh token."""
    user_repo = UserRepository(db)

    # Hash the provided token
    token_hash = hashlib.sha256(data.refresh_token.encode()).hexdigest()

    # Find and revoke the refresh token
    token = await user_repo.get_refresh_token(token_hash)
    if token and token.is_valid:
        await user_repo.revoke_refresh_token(token)
        logger.info("User logged out", user_id=str(token.user_id))


# API Key endpoints
@router.get(
    "/api-keys",
    response_model=list[ApiKeyResponse],
    summary="List API keys",
    description="""
Get all API keys for the authenticated user.

**Security:** Only the key prefix is returned (e.g., `ilm_abc12345...`), not the full key.

**Use Case:** View active keys, check last usage, manage key lifecycle.

**Requires:** Bearer token authentication
    """,
)
async def list_api_keys(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyResponse]:
    """List all API keys for the current user."""
    user_repo = UserRepository(db)
    keys = await user_repo.get_api_keys(current_user.id)
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.post(
    "/api-keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
    description="""
Generate a new API key for server-to-server integrations.

**IMPORTANT:** The full API key is only shown ONCE in this response. Store it securely!

**Example:**
```bash
curl -X POST /v1/auth/api-keys \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{"name":"Production Server","permissions":["read","write"],"expires_in_days":90}'
```

**Permissions:**
- `read` - Read-only access to books, profiles
- `write` - Create/update books, chat messages
- `admin` - Administrative operations (if authorized)

**Usage:**
```
X-API-Key: ilm_live_abc123...
```
    """,
)
async def create_api_key(
    data: ApiKeyCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedResponse:
    """Create a new API key."""
    user_repo = UserRepository(db)

    # Generate the key
    full_key, key_prefix, key_hash = generate_api_key()

    # Calculate expiration
    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

    # Create the key
    api_key = await user_repo.create_api_key(
        user_id=current_user.id,
        name=data.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        permissions=data.permissions,
        expires_at=expires_at,
    )

    logger.info("API key created", user_id=str(current_user.id), key_name=data.name)

    return ApiKeyCreatedResponse(
        api_key=full_key,
        key_info=ApiKeyResponse.model_validate(api_key),
    )


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete API key",
    description="""
Permanently revoke an API key.

**Effect:** Any requests using this key will immediately receive 401 Unauthorized.

**Example:**
```bash
curl -X DELETE /v1/auth/api-keys/550e8400-e29b-41d4-a716-446655440000 \\
  -H "Authorization: Bearer <token>"
```
    """,
    responses={
        404: {"description": "API key not found or doesn't belong to you"},
    },
)
async def delete_api_key(
    key_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an API key."""
    user_repo = UserRepository(db)

    from uuid import UUID
    api_key = await user_repo.get_api_key_by_id(UUID(key_id))

    if not api_key or api_key.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="API key not found")

    await user_repo.delete_api_key(api_key)
    logger.info("API key deleted", user_id=str(current_user.id), key_id=key_id)
