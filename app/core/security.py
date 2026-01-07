"""Security utilities for authentication and authorization."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import ApiKey, User

# Password hashing context using Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The subject (usually user ID)
        extra_claims: Additional claims to include in the token
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)

    expire = datetime.now(timezone.utc) + expires_delta

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, str]:
    """
    Create a refresh token.

    Returns:
        Tuple of (raw_token, token_hash) - store the hash, give raw to client
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.jwt_refresh_token_expire_days)

    # Generate a secure random token
    raw_token = secrets.token_urlsafe(32)

    # Hash for storage
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    return raw_token, token_hash


def verify_access_token(token: str) -> dict[str, Any] | None:
    """
    Verify and decode a JWT access token.

    Returns:
        Decoded payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )

        # Verify it's an access token
        if payload.get("type") != "access":
            return None

        return payload
    except JWTError:
        return None


def verify_refresh_token_hash(raw_token: str, stored_hash: str) -> bool:
    """Verify a refresh token against its stored hash."""
    computed_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return secrets.compare_digest(computed_hash, stored_hash)


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, key_prefix, key_hash)
        - full_key: Give to user (only shown once)
        - key_prefix: First 12 chars for lookup
        - key_hash: Argon2 hash for storage
    """
    # Generate random key with prefix
    random_part = secrets.token_urlsafe(32)
    full_key = f"{settings.api_key_prefix}{random_part}"

    # Extract prefix for lookup (first 12 chars)
    key_prefix = full_key[:12]

    # Hash the full key for secure storage
    key_hash = pwd_context.hash(full_key)

    return full_key, key_prefix, key_hash


def verify_api_key_hash(api_key: str, stored_hash: str) -> bool:
    """Verify an API key against its stored hash."""
    return pwd_context.verify(api_key, stored_hash)


async def verify_api_key(db: AsyncSession, api_key: str) -> User | None:
    """
    Verify an API key and return the associated user.

    Args:
        db: Database session
        api_key: The API key to verify

    Returns:
        User if valid, None otherwise
    """
    if not api_key or not api_key.startswith(settings.api_key_prefix):
        return None

    # Extract prefix for lookup
    key_prefix = api_key[:12]

    # Find API key by prefix
    stmt = (
        select(ApiKey)
        .where(ApiKey.key_prefix == key_prefix)
        .where(ApiKey.expires_at.is_(None) | (ApiKey.expires_at > datetime.now(timezone.utc)))
    )
    result = await db.execute(stmt)
    api_key_record = result.scalar_one_or_none()

    if not api_key_record:
        return None

    # Verify the full key
    if not verify_api_key_hash(api_key, api_key_record.key_hash):
        return None

    # Update last used timestamp
    api_key_record.last_used_at = datetime.now(timezone.utc)

    # Get and return the user
    stmt = select(User).where(User.id == api_key_record.user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
