"""RBAC repository for database operations."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rbac import (
    Permission,
    Role,
    RoleAssignmentLog,
    RolePermission,
    UserRole,
)


class RBACRepository:
    """Repository for RBAC database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Role operations
    async def get_roles(self) -> list[Role]:
        """Get all active roles."""
        stmt = select(Role).where(Role.is_active.is_(True)).order_by(Role.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_role_by_id(self, role_id: uuid.UUID) -> Role | None:
        """Get role by ID."""
        stmt = select(Role).where(Role.id == role_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_by_name(self, name: str) -> Role | None:
        """Get role by name."""
        stmt = select(Role).where(Role.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # Permission operations
    async def get_permissions(self) -> list[Permission]:
        """Get all permissions."""
        stmt = select(Permission).order_by(Permission.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_role_permissions(self, role_id: uuid.UUID) -> list[Permission]:
        """Get permissions for a specific role."""
        stmt = (
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
            .order_by(Permission.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # User role operations
    async def get_user_roles(self, user_id: uuid.UUID) -> list[UserRole]:
        """Get all roles for a user."""
        stmt = (
            select(UserRole)
            .options(selectinload(UserRole.role))
            .where(UserRole.user_id == user_id)
            .order_by(UserRole.assigned_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def assign_role(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: uuid.UUID | None = None,
    ) -> UserRole:
        """Assign a role to a user."""
        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
        )
        self.db.add(user_role)
        await self.db.flush()
        # Load the role relationship
        stmt = (
            select(UserRole)
            .options(selectinload(UserRole.role))
            .where(UserRole.id == user_role.id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def revoke_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        """Revoke a role from a user."""
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )
        result = await self.db.execute(stmt)
        user_role = result.scalar_one_or_none()
        if user_role:
            await self.db.delete(user_role)
            await self.db.flush()

    async def has_permission(self, user_id: uuid.UUID, permission_name: str) -> bool:
        """Check if a user has a specific permission via their roles."""
        stmt = (
            select(Permission.id)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user_id,
                Permission.name == permission_name,
                Role.is_active.is_(True),
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_user_permissions(self, user_id: uuid.UUID) -> list[str]:
        """Get all permission names for a user."""
        stmt = (
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user_id,
                Role.is_active.is_(True),
            )
            .distinct()
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # Audit log
    async def log_assignment(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        action: str,
        performed_by: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> RoleAssignmentLog:
        """Log a role assignment or revocation."""
        log = RoleAssignmentLog(
            user_id=user_id,
            role_id=role_id,
            action=action,
            performed_by=performed_by,
            reason=reason,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def get_assignment_history(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[RoleAssignmentLog], int]:
        """Get role assignment history for a user."""
        # Count
        count_stmt = (
            select(func.count())
            .select_from(RoleAssignmentLog)
            .where(RoleAssignmentLog.user_id == user_id)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Fetch
        stmt = (
            select(RoleAssignmentLog)
            .where(RoleAssignmentLog.user_id == user_id)
            .order_by(RoleAssignmentLog.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total
