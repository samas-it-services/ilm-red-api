"""Expert configuration API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.v1.deps import AdminUser, DBSession, OptionalUser
from app.schemas.expert import (
    ExpertConfigCreate,
    ExpertConfigListResponse,
    ExpertConfigResponse,
    ExpertConfigUpdate,
)
from app.services.expert_service import ExpertService

router = APIRouter()


@router.get(
    "",
    response_model=ExpertConfigListResponse,
    summary="List expert configurations",
    description="List expert configurations with optional category filtering.",
)
async def list_experts(
    db: DBSession,
    current_user: OptionalUser,
    category: str | None = Query(None, description="Filter by category"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> ExpertConfigListResponse:
    """List expert configurations.

    Supports filtering by category and active status.
    """
    service = ExpertService(db)
    return await service.list_experts(
        category=category,
        is_active=is_active,
        page=page,
        limit=limit,
    )


@router.get(
    "/{expert_id}",
    response_model=ExpertConfigResponse,
    summary="Get expert configuration",
    description="Get detailed information about a specific expert configuration.",
)
async def get_expert(
    expert_id: UUID,
    db: DBSession,
    current_user: OptionalUser,
) -> ExpertConfigResponse:
    """Get expert configuration details by ID."""
    service = ExpertService(db)
    return await service.get_expert(expert_id)


@router.post(
    "",
    response_model=ExpertConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create expert configuration",
    description="Create a new expert configuration. Admin only.",
)
async def create_expert(
    data: ExpertConfigCreate,
    db: DBSession,
    current_user: AdminUser,
) -> ExpertConfigResponse:
    """Create a new expert configuration.

    Requires admin role.
    """
    service = ExpertService(db)
    return await service.create_expert(data)


@router.put(
    "/{expert_id}",
    response_model=ExpertConfigResponse,
    summary="Update expert configuration",
    description="Update an existing expert configuration. Admin only.",
)
async def update_expert(
    expert_id: UUID,
    updates: ExpertConfigUpdate,
    db: DBSession,
    current_user: AdminUser,
) -> ExpertConfigResponse:
    """Update an expert configuration.

    Requires admin role.
    """
    service = ExpertService(db)
    return await service.update_expert(expert_id, updates)


@router.delete(
    "/{expert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete expert configuration",
    description="Delete an expert configuration. Admin only.",
)
async def delete_expert(
    expert_id: UUID,
    db: DBSession,
    current_user: AdminUser,
) -> None:
    """Delete an expert configuration.

    Requires admin role. This permanently removes the configuration.
    """
    service = ExpertService(db)
    await service.delete_expert(expert_id)
