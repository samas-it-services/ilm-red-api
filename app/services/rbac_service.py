"""RBAC service for business logic."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Role
from app.models.user import User
from app.repositories.rbac_repo import RBACRepository
from app.schemas.rbac import (
    PermissionCheckResponse,
    PermissionResponse,
    RoleAssignmentLogResponse,
    RoleResponse,
    UserRoleResponse,
    UserRolesResponse,
)


class RBACService:
    """Service for RBAC operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RBACRepository(db)

    async def get_roles(self) -> list[RoleResponse]:
        """Get all active roles."""
        roles = await self.repo.get_roles()
        return [RoleResponse.model_validate(r) for r in roles]

    async def get_role_permissions(self, role_id: uuid.UUID) -> list[PermissionResponse]:
        """Get permissions for a role."""
        role = await self.repo.get_role_by_id(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        permissions = await self.repo.get_role_permissions(role_id)
        return [PermissionResponse.model_validate(p) for p in permissions]

    async def get_user_roles(self, user_id: uuid.UUID) -> UserRolesResponse:
        """Get all roles for a user."""
        user_roles = await self.repo.get_user_roles(user_id)
        roles = [RoleResponse.model_validate(ur.role) for ur in user_roles]
        return UserRolesResponse(user_id=user_id, roles=roles)

    async def assign_role(
        self,
        user_id: uuid.UUID,
        role_name: str,
        assigned_by: uuid.UUID,
        reason: str | None = None,
    ) -> UserRoleResponse:
        """Assign a role to a user."""
        role = await self.repo.get_role_by_name(role_name)
        if not role:
            raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found")

        # Check if already assigned
        existing_roles = await self.repo.get_user_roles(user_id)
        if any(ur.role_id == role.id for ur in existing_roles):
            raise HTTPException(
                status_code=409,
                detail=f"Role '{role_name}' is already assigned to this user",
            )

        user_role = await self.repo.assign_role(user_id, role.id, assigned_by)
        await self.repo.log_assignment(user_id, role.id, "assigned", assigned_by, reason)

        return UserRoleResponse(
            id=user_role.id,
            role=RoleResponse.model_validate(user_role.role),
            assigned_at=user_role.assigned_at,
            assigned_by=user_role.assigned_by,
        )

    async def revoke_role(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        performed_by: uuid.UUID,
        reason: str | None = None,
    ) -> None:
        """Revoke a role from a user."""
        role = await self.repo.get_role_by_id(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        await self.repo.revoke_role(user_id, role_id)
        await self.repo.log_assignment(user_id, role_id, "revoked", performed_by, reason)

    async def check_permission(
        self, user_id: uuid.UUID, permission_name: str
    ) -> PermissionCheckResponse:
        """Check if a user has a permission."""
        has_perm = await self.repo.has_permission(user_id, permission_name)
        return PermissionCheckResponse(
            has_permission=has_perm,
            permission_name=permission_name,
        )

    async def get_all_permissions(self) -> list[PermissionResponse]:
        """Get all permissions."""
        permissions = await self.repo.get_permissions()
        return [PermissionResponse.model_validate(p) for p in permissions]

    async def get_assignment_history(
        self, user_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> tuple[list[RoleAssignmentLogResponse], int]:
        """Get role assignment history."""
        logs, total = await self.repo.get_assignment_history(user_id, page, limit)
        return [RoleAssignmentLogResponse.model_validate(log) for log in logs], total
