"""Shared API dependencies for authentication and authorization."""

import structlog
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_access_token, verify_api_key
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository

logger = structlog.get_logger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    api_key: str | None = Depends(api_key_header),
) -> User:
    """
    Get the current authenticated user from JWT token or API key.

    Supports two authentication methods:
    1. Bearer token (JWT) in Authorization header
    2. API key in X-API-Key header

    Also supports admin impersonation via `impersonating_user_id` JWT claim.
    When impersonating, the impersonated user is returned and the real admin ID
    is stored on request.state for audit logging.
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
                    # Check for impersonation claim
                    impersonating_user_id = payload.get("impersonating_user_id")
                    if impersonating_user_id:
                        # Verify the real user (sub) has super_admin role
                        if "super_admin" not in user.roles:
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail="Only super_admin can impersonate users",
                            )
                        # Load the impersonated user
                        impersonated_user = await user_repo.get_by_id(impersonating_user_id)
                        if not impersonated_user or impersonated_user.status != "active":
                            raise HTTPException(
                                status_code=status.HTTP_404_NOT_FOUND,
                                detail="Impersonated user not found or inactive",
                            )
                        # Store the real admin ID for audit logging
                        request.state.impersonating_admin_id = str(user.id)
                        request.state.is_impersonating = True
                        logger.info(
                            "Admin impersonating user",
                            admin_id=str(user.id),
                            target_user_id=str(impersonated_user.id),
                        )
                        return impersonated_user
                    # Normal authentication (no impersonation)
                    request.state.is_impersonating = False
                    request.state.impersonating_admin_id = None
                    return user

    # Try API key authentication
    if api_key:
        user = await verify_api_key(db, api_key)
        if user and user.status == "active":
            request.state.is_impersonating = False
            request.state.impersonating_admin_id = None
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    api_key: str | None = Depends(api_key_header),
) -> User | None:
    """
    Get the current user if authenticated, otherwise return None.

    Useful for endpoints that work both with and without authentication.
    """
    try:
        return await get_current_user(request, db, bearer, api_key)
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


def require_permission(permission_name: str):
    """
    Dependency factory to require a specific RBAC permission.

    Usage:
        @router.get("/protected", dependencies=[Depends(require_permission("books.create"))])
    """

    async def permission_checker(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        from app.repositories.rbac_repo import RBACRepository

        rbac_repo = RBACRepository(db)
        if not await rbac_repo.has_permission(user.id, permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_name}' required",
            )
        return user

    return permission_checker


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_roles("admin", "super_admin"))]
SuperAdminUser = Annotated[User, Depends(require_roles("super_admin"))]
