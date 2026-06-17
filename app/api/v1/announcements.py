"""Feature announcements API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.api.v1.deps import AdminUser, CurrentUser, DBSession, OptionalUser
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementListResponse,
    AnnouncementResponse,
    AnnouncementUpdate,
    UnreadCountResponse,
)
from app.services.announcement_service import AnnouncementService

router = APIRouter()


# ---------- Public Endpoints ----------


@router.get(
    "",
    response_model=AnnouncementListResponse,
    summary="List announcements",
    description="List feature announcements with optional filtering and pagination.",
)
async def list_announcements(
    db: DBSession,
    current_user: OptionalUser,
    priority: str | None = Query(None, description="Filter by priority (low/normal/high/critical)"),
    is_featured: bool | None = Query(None, description="Filter featured announcements"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
    sort_by: str = Query("published_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
) -> AnnouncementListResponse:
    """List feature announcements.

    Published announcements visible to everyone.
    Draft/archived only visible to admins.
    """
    service = AnnouncementService(db)
    return await service.list_announcements(
        user=current_user,
        priority=priority,
        is_featured=is_featured,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread announcement count",
    description="Get the number of published announcements the user has not yet viewed.",
)
async def get_unread_count(
    db: DBSession,
    current_user: CurrentUser,
) -> UnreadCountResponse:
    """Get unread announcement count for the current user.

    Returns the number of published announcements that the user has not viewed.
    """
    service = AnnouncementService(db)
    return await service.get_unread_count(current_user)


@router.get(
    "/{slug}",
    response_model=AnnouncementResponse,
    summary="Get announcement detail",
    description="Get a single announcement by slug. Automatically tracks the view.",
)
async def get_announcement(
    slug: str,
    request: Request,
    db: DBSession,
    current_user: OptionalUser,
) -> AnnouncementResponse:
    """Get announcement by slug.

    Automatically tracks the view for the current user.
    """
    service = AnnouncementService(db)
    return await service.get_announcement(
        slug=slug,
        user=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )


# ---------- Admin Endpoints ----------


@router.post(
    "",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create announcement (admin)",
    description="Create a new feature announcement. Requires admin role.",
)
async def create_announcement(
    data: AnnouncementCreate,
    db: DBSession,
    current_user: AdminUser,
) -> AnnouncementResponse:
    """Create a new feature announcement (admin only).

    - **title**: Announcement title (required)
    - **content**: Content in markdown (required)
    - **status**: draft or published (default: draft)
    - **priority**: low, normal, high, or critical (default: normal)
    """
    service = AnnouncementService(db)
    return await service.create_announcement(data, current_user)


@router.put(
    "/{announcement_id}",
    response_model=AnnouncementResponse,
    summary="Update announcement (admin)",
    description="Update a feature announcement. Requires admin role.",
)
async def update_announcement(
    announcement_id: UUID,
    data: AnnouncementUpdate,
    db: DBSession,
    current_user: AdminUser,
) -> AnnouncementResponse:
    """Update a feature announcement (admin only)."""
    service = AnnouncementService(db)
    return await service.update_announcement(announcement_id, data, current_user)


@router.delete(
    "/{announcement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete announcement (admin)",
    description="Delete a feature announcement. Requires admin role.",
)
async def delete_announcement(
    announcement_id: UUID,
    db: DBSession,
    current_user: AdminUser,
) -> None:
    """Delete a feature announcement (admin only)."""
    service = AnnouncementService(db)
    await service.delete_announcement(announcement_id, current_user)
