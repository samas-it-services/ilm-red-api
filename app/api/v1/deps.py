"""Shared API dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.core.security import verify_access_token, verify_api_key
from app.repositories.user_repo import UserRepository

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    api_key: str | None = Depends(api_key_header),
) -> User:
    """
    Get the current authenticated user from JWT token or API key.

    Supports two authentication methods:
    1. Bearer token (JWT) in Authorization header
    2. API key in X-API-Key header
    """
    user_repo = UserRepository(db)

    # Try JWT authentication first
    if bearer:
        payload = verify_access_token(bearer.credentials)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                user = await user_repo.get_by_id(user_id)
                if user and user.status == "active":
                    return user

    # Try API key authentication
    if api_key:
        user = await verify_api_key(db, api_key)
        if user and user.status == "active":
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional(
    db: AsyncSession = Depends(get_db),
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    api_key: str | None = Depends(api_key_header),
) -> User | None:
    """
    Get the current user if authenticated, otherwise return None.

    Useful for endpoints that work both with and without authentication.
    """
    try:
        return await get_current_user(db, bearer, api_key)
    except HTTPException:
        return None


def require_roles(*roles: str):
    """
    Dependency factory to require specific roles.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_roles("admin"))])
    """

    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if not any(role in user.roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(roles)}",
            )
        return user

    return role_checker


def require_premium():
    """Dependency to require premium or higher subscription."""
    return require_roles("premium", "enterprise", "admin", "super_admin")


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
