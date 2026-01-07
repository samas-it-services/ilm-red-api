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


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Register a new user account.

    Returns access and refresh tokens on success.
    """
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


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user with email and password.

    Returns access and refresh tokens on success.
    """
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


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    The old refresh token is revoked and a new one is issued (token rotation).
    """
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


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Logout by revoking the refresh token.
    """
    user_repo = UserRepository(db)

    # Hash the provided token
    token_hash = hashlib.sha256(data.refresh_token.encode()).hexdigest()

    # Find and revoke the refresh token
    token = await user_repo.get_refresh_token(token_hash)
    if token and token.is_valid:
        await user_repo.revoke_refresh_token(token)
        logger.info("User logged out", user_id=str(token.user_id))


# API Key endpoints
@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyResponse]:
    """List all API keys for the current user."""
    user_repo = UserRepository(db)
    keys = await user_repo.get_api_keys(current_user.id)
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedResponse:
    """
    Create a new API key.

    The full key is only returned once - store it securely!
    """
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


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
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
