"""RBAC Pydantic schemas for request/response validation."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoleResponse(BaseModel):
    """Role response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    display_name: str
    description: str | None = None
    is_system: bool
    is_active: bool


class PermissionResponse(BaseModel):
    """Permission response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    resource: str | None = None
    action: str | None = None


class UserRoleAssign(BaseModel):
    """Request schema for assigning a role to a user."""

    role_name: str = Field(..., description="Role name to assign")
    reason: str | None = Field(None, description="Reason for assignment")


class PermissionCheckRequest(BaseModel):
    """Request schema for checking a permission."""

    permission_name: str = Field(..., description="Permission name to check")


class PermissionCheckResponse(BaseModel):
    """Response schema for permission check."""

    has_permission: bool
    permission_name: str


class UserRoleResponse(BaseModel):
    """Response schema for a user's role."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: RoleResponse
    assigned_at: datetime
    assigned_by: uuid.UUID | None = None


class UserRolesResponse(BaseModel):
    """Response schema for listing a user's roles."""

    user_id: uuid.UUID
    roles: list[RoleResponse]


class RoleAssignmentLogResponse(BaseModel):
    """Response schema for role assignment log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    action: str
    performed_by: uuid.UUID | None = None
    reason: str | None = None
    created_at: datetime
