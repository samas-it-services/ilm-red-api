"""Premium API endpoints for premium requests, features, and admin management."""

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.v1.deps import AdminUser, CurrentUser, DBSession
from app.schemas.premium import (
    PremiumFeatureResponse,
    PremiumRequestApprove,
    PremiumRequestCreate,
    PremiumRequestListResponse,
    PremiumRequestReject,
    PremiumRequestResponse,
    PremiumRequestStats,
    PremiumRequestUpdate,
)
from app.services.premium_service import PremiumService

router = APIRouter()


# ============================================================================
# User-Facing Endpoints
# ============================================================================


@router.post(
    "/requests",
    response_model=PremiumRequestResponse,
    status_code=201,
    summary="Submit premium request",
    description="""
Submit a request for premium access.

Users can only have one pending/in_review request at a time.
If a previous request was rejected, a new one can be submitted.

**Requires:** Authentication
    """,
)
async def submit_request(
    data: PremiumRequestCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> PremiumRequestResponse:
    """Submit a premium access request."""
    service = PremiumService(db)
    return await service.submit_request(data, current_user)


@router.get(
    "/requests/mine",
    response_model=PremiumRequestResponse,
    summary="Get my premium request",
    description="""
Get your most recent premium request and its status.

**Requires:** Authentication
    """,
)
async def get_my_request(
    db: DBSession,
    current_user: CurrentUser,
) -> PremiumRequestResponse:
    """Get your most recent premium request."""
    service = PremiumService(db)
    return await service.get_my_request(current_user)


@router.put(
    "/requests/{request_id}",
    response_model=PremiumRequestResponse,
    summary="Update premium request",
    description="""
Update your premium request.

Only the request owner can update, and only while status is 'pending' or 'in_review'.

**Requires:** Authentication (owner only)
    """,
)
async def update_request(
    request_id: UUID,
    data: PremiumRequestUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> PremiumRequestResponse:
    """Update your premium request (before review)."""
    service = PremiumService(db)
    return await service.update_request(request_id, data, current_user)


# ============================================================================
# Public Endpoints
# ============================================================================


@router.get(
    "/features",
    response_model=list[PremiumFeatureResponse],
    summary="List premium features",
    description="""
List all available premium features.

**No authentication required** - public endpoint to show premium benefits.
    """,
)
async def list_features(
    db: DBSession,
) -> list[PremiumFeatureResponse]:
    """List all active premium features."""
    service = PremiumService(db)
    return await service.list_features()


# ============================================================================
# Admin Endpoints
# ============================================================================


@router.get(
    "/admin/requests",
    response_model=PremiumRequestListResponse,
    summary="List all premium requests (admin)",
    description="""
List all premium requests with optional status filtering and pagination.

**Filters:**
- `status`: Filter by status (pending, approved, rejected, in_review)

**Requires:** Admin role
    """,
)
async def list_all_requests(
    db: DBSession,
    admin_user: AdminUser,
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> PremiumRequestListResponse:
    """List all premium requests (admin)."""
    service = PremiumService(db)
    return await service.list_all_requests(
        status_filter=status,
        page=page,
        limit=limit,
    )


@router.post(
    "/admin/requests/{request_id}/approve",
    response_model=PremiumRequestResponse,
    summary="Approve premium request (admin)",
    description="""
Approve a premium request.

This will:
1. Update the request status to 'approved'
2. Create a premium subscription for the user
3. Upgrade the user's upload limits

**Requires:** Admin role
    """,
)
async def approve_request(
    request_id: UUID,
    db: DBSession,
    admin_user: AdminUser,
    data: PremiumRequestApprove | None = None,
) -> PremiumRequestResponse:
    """Approve a premium request."""
    service = PremiumService(db)
    approval_data = data or PremiumRequestApprove()
    return await service.approve_request(request_id, approval_data, admin_user)


@router.post(
    "/admin/requests/{request_id}/reject",
    response_model=PremiumRequestResponse,
    summary="Reject premium request (admin)",
    description="""
Reject a premium request with an explanation.

The admin_notes field is required to provide a rejection reason.

**Requires:** Admin role
    """,
)
async def reject_request(
    request_id: UUID,
    data: PremiumRequestReject,
    db: DBSession,
    admin_user: AdminUser,
) -> PremiumRequestResponse:
    """Reject a premium request with a reason."""
    service = PremiumService(db)
    return await service.reject_request(request_id, data, admin_user)


@router.get(
    "/admin/stats",
    response_model=PremiumRequestStats,
    summary="Premium request statistics (admin)",
    description="""
Get statistics about premium requests.

Includes total counts by status and approval rate.

**Requires:** Admin role
    """,
)
async def get_stats(
    db: DBSession,
    admin_user: AdminUser,
) -> PremiumRequestStats:
    """Get premium request statistics."""
    service = PremiumService(db)
    return await service.get_stats()
