"""User repository for database operations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import ApiKey, RefreshToken, User


class UserRepository:
    """Repository for User database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str | uuid.UUID) -> User | None:
        """Get user by ID."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email (case-insensitive)."""
        stmt = select(User).where(User.email.ilike(email))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username (case-insensitive)."""
        stmt = select(User).where(User.username.ilike(username))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        username: str,
        display_name: str,
        password_hash: str | None = None,
        roles: list[str] | None = None,
    ) -> User:
        """Create a new user."""
        user = User(
            email=email.lower(),
            username=username.lower(),
            display_name=display_name,
            password_hash=password_hash,
            roles=roles or ["user"],
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update(self, user: User, **kwargs) -> User:
        """Update user fields."""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update_last_login(self, user: User) -> None:
        """Update user's last login timestamp."""
        user.last_login_at = datetime.now(UTC)
        await self.db.flush()

    # Refresh Token operations
    async def create_refresh_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Create a new refresh token."""
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        """Get refresh token by hash."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: RefreshToken) -> None:
        """Revoke a refresh token."""
        token.revoked_at = datetime.now(UTC)
        await self.db.flush()

    async def revoke_all_refresh_tokens(self, user_id: uuid.UUID) -> int:
        """Revoke all refresh tokens for a user. Returns count revoked."""
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.revoked_at.is_(None))
        )
        result = await self.db.execute(stmt)
        tokens = result.scalars().all()

        now = datetime.now(UTC)
        for token in tokens:
            token.revoked_at = now

        await self.db.flush()
        return len(tokens)

    # API Key operations
    async def create_api_key(
        self,
        user_id: uuid.UUID,
        name: str,
        key_prefix: str,
        key_hash: str,
        permissions: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> ApiKey:
        """Create a new API key."""
        api_key = ApiKey(
            user_id=user_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            permissions=permissions or ["read"],
            expires_at=expires_at,
        )
        self.db.add(api_key)
        await self.db.flush()
        await self.db.refresh(api_key)
        return api_key

    async def get_api_keys(self, user_id: uuid.UUID) -> list[ApiKey]:
        """Get all API keys for a user."""
        stmt = (
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_api_key_by_id(self, key_id: uuid.UUID) -> ApiKey | None:
        """Get API key by ID."""
        stmt = select(ApiKey).where(ApiKey.id == key_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_api_key(self, api_key: ApiKey) -> None:
        """Delete an API key."""
        await self.db.delete(api_key)
        await self.db.flush()
