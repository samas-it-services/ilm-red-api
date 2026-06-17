"""RBAC API endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import AdminUser, CurrentUser, DBSession
from app.schemas.common import PaginatedResponse, create_pagination
from app.schemas.rbac import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionResponse,
    RoleAssignmentLogResponse,
    RoleResponse,
    UserRoleAssign,
    UserRoleResponse,
    UserRolesResponse,
)
from app.services.rbac_service import RBACService

router = APIRouter()


@router.get(
    "/roles",
    response_model=list[RoleResponse],
    summary="List all roles",
)
async def list_roles(
    db: DBSession,
    current_user: CurrentUser,
) -> list[RoleResponse]:
    """List all active roles."""
    service = RBACService(db)
    return await service.get_roles()


@router.get(
    "/roles/{role_id}/permissions",
    response_model=list[PermissionResponse],
    summary="Get permissions for a role",
)
async def get_role_permissions(
    role_id: uuid.UUID,
    db: DBSession,
    current_user: AdminUser,
) -> list[PermissionResponse]:
    """Get all permissions associated with a role. Requires admin."""
    service = RBACService(db)
    return await service.get_role_permissions(role_id)


@router.get(
    "/users/{user_id}/roles",
    response_model=UserRolesResponse,
    summary="Get roles for a user",
)
async def get_user_roles(
    user_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> UserRolesResponse:
    """Get all roles for a user. Admin can view any user, others can view themselves."""
    if user_id != current_user.id and not current_user.is_admin:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view other user's roles")
    service = RBACService(db)
    return await service.get_user_roles(user_id)


@router.post(
    "/users/{user_id}/roles",
    response_model=UserRoleResponse,
    status_code=201,
    summary="Assign role to user",
)
async def assign_role(
    user_id: uuid.UUID,
    data: UserRoleAssign,
    db: DBSession,
    current_user: AdminUser,
) -> UserRoleResponse:
    """Assign a role to a user. Requires admin."""
    service = RBACService(db)
    return await service.assign_role(user_id, data.role_name, current_user.id, data.reason)


@router.delete(
    "/users/{user_id}/roles/{role_id}",
    status_code=204,
    summary="Revoke role from user",
)
async def revoke_role(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    db: DBSession,
    current_user: AdminUser,
) -> None:
    """Revoke a role from a user. Requires admin."""
    service = RBACService(db)
    await service.revoke_role(user_id, role_id, current_user.id)


@router.get(
    "/permissions",
    response_model=list[PermissionResponse],
    summary="List all permissions",
)
async def list_permissions(
    db: DBSession,
    current_user: AdminUser,
) -> list[PermissionResponse]:
    """List all permissions. Requires admin."""
    service = RBACService(db)
    return await service.get_all_permissions()


@router.post(
    "/permissions/check",
    response_model=PermissionCheckResponse,
    summary="Check if current user has a permission",
)
async def check_permission(
    data: PermissionCheckRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> PermissionCheckResponse:
    """Check if the current user has a specific permission."""
    service = RBACService(db)
    return await service.check_permission(current_user.id, data.permission_name)


@router.get(
    "/users/{user_id}/roles/history",
    response_model=PaginatedResponse[RoleAssignmentLogResponse],
    summary="Get role assignment history",
)
async def get_role_history(
    user_id: uuid.UUID,
    db: DBSession,
    current_user: AdminUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[RoleAssignmentLogResponse]:
    """Get role assignment audit log for a user. Requires admin."""
    service = RBACService(db)
    logs, total = await service.get_assignment_history(user_id, page, limit)
    return PaginatedResponse(
        data=logs,
        pagination=create_pagination(page, limit, total),
    )
