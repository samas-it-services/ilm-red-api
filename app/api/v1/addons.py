"""Addon API endpoints."""

import uuid

from fastapi import APIRouter, Query

from app.api.v1.deps import AdminUser, CurrentUser, DBSession, OptionalUser
from app.schemas.addon import (
    AddonConfigUpdate,
    AddonInstallRequest,
    AddonListResponse,
    AddonRegistryResponse,
    AddonReviewCreate,
    AddonReviewResponse,
    BookClubAddonConfigResponse,
    GlobalAddonConfigResponse,
    GlobalAddonConfigUpdate,
)
from app.schemas.common import PaginatedResponse, create_pagination
from app.services.addon_service import AddonService

router = APIRouter()


# --- Marketplace ---


@router.get(
    "/",
    response_model=AddonListResponse,
    summary="List addons (marketplace)",
    description="Browse available addons with optional category and search filters.",
)
async def list_addons(
    db: DBSession,
    current_user: OptionalUser,
    category: str | None = Query(None, description="Filter by category"),
    status: str | None = Query(None, description="Filter by status"),
    search: str | None = Query(None, description="Search by name"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> AddonListResponse:
    """List addons in the marketplace."""
    service = AddonService(db)
    return await service.list_marketplace(
        category=category, status_filter=status, search=search, page=page, limit=limit,
    )


@router.get(
    "/{addon_id}",
    response_model=AddonRegistryResponse,
    summary="Get addon detail",
    description="Get detailed information about a specific addon.",
)
async def get_addon(
    addon_id: uuid.UUID,
    db: DBSession,
    current_user: OptionalUser,
) -> AddonRegistryResponse:
    """Get addon detail by ID."""
    service = AddonService(db)
    return await service.get_addon_detail(addon_id)


# --- Reviews ---


@router.get(
    "/{addon_id}/reviews",
    response_model=PaginatedResponse[AddonReviewResponse],
    summary="List addon reviews",
    description="Get paginated reviews for a specific addon.",
)
async def list_reviews(
    addon_id: uuid.UUID,
    db: DBSession,
    current_user: OptionalUser,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[AddonReviewResponse]:
    """List reviews for an addon."""
    service = AddonService(db)
    return await service.list_reviews(addon_id, page, limit)


@router.post(
    "/{addon_id}/reviews",
    response_model=AddonReviewResponse,
    status_code=201,
    summary="Create addon review",
    description="Submit a review for an addon. One review per user per addon.",
)
async def create_review(
    addon_id: uuid.UUID,
    data: AddonReviewCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> AddonReviewResponse:
    """Create a review for an addon."""
    service = AddonService(db)
    return await service.create_review(addon_id, data, current_user)


# --- Book Club Addon Management ---


@router.post(
    "/book-clubs/{club_id}/install",
    response_model=BookClubAddonConfigResponse,
    status_code=201,
    summary="Install addon for club",
    description="Install an addon for a book club. Requires club admin role.",
)
async def install_addon(
    club_id: uuid.UUID,
    data: AddonInstallRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> BookClubAddonConfigResponse:
    """Install an addon for a book club."""
    service = AddonService(db)
    return await service.install_addon_for_club(club_id, data, current_user)


@router.delete(
    "/book-clubs/{club_id}/{addon_id}",
    status_code=204,
    summary="Uninstall addon from club",
    description="Remove an addon from a book club. Requires club admin role.",
)
async def uninstall_addon(
    club_id: uuid.UUID,
    addon_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Uninstall an addon from a book club."""
    service = AddonService(db)
    await service.uninstall_addon_from_club(club_id, addon_id, current_user)


@router.put(
    "/book-clubs/{club_id}/{addon_id}/config",
    response_model=BookClubAddonConfigResponse,
    summary="Update club addon config",
    description="Update addon configuration for a specific club. Requires club admin role.",
)
async def update_club_addon_config(
    club_id: uuid.UUID,
    addon_id: uuid.UUID,
    data: AddonConfigUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> BookClubAddonConfigResponse:
    """Update addon configuration for a club."""
    service = AddonService(db)
    return await service.update_club_addon_config(club_id, addon_id, data, current_user)


@router.get(
    "/book-clubs/{club_id}",
    response_model=PaginatedResponse[BookClubAddonConfigResponse],
    summary="List club's installed addons",
    description="List all addons installed for a specific book club.",
)
async def list_club_addons(
    club_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[BookClubAddonConfigResponse]:
    """List installed addons for a club."""
    service = AddonService(db)
    return await service.list_club_addons(club_id, page, limit)


@router.get(
    "/book-clubs/{club_id}/available",
    response_model=AddonListResponse,
    summary="List available addons for club",
    description="List addons not yet installed for a book club. Requires club admin role.",
)
async def list_available_for_club(
    club_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> AddonListResponse:
    """List addons available for installation in a club."""
    service = AddonService(db)
    return await service.list_available_for_club(club_id, page, limit)


# --- Admin: Global Config ---


@router.get(
    "/admin/global-config",
    response_model=GlobalAddonConfigResponse,
    summary="Get global addon config",
    description="Get the global configuration for an addon. Admin only.",
)
async def get_global_config(
    db: DBSession,
    current_user: AdminUser,
    addon_id: uuid.UUID = Query(..., description="Addon ID to get config for"),
) -> GlobalAddonConfigResponse:
    """Get global addon configuration (admin only)."""
    service = AddonService(db)
    return await service.get_global_config(addon_id)


@router.put(
    "/admin/global-config",
    response_model=GlobalAddonConfigResponse,
    summary="Update global addon config",
    description="Create or update global addon configuration. Admin only.",
)
async def update_global_config(
    data: GlobalAddonConfigUpdate,
    db: DBSession,
    current_user: AdminUser,
) -> GlobalAddonConfigResponse:
    """Update global addon configuration (admin only)."""
    service = AddonService(db)
    return await service.update_global_config(data, current_user)
