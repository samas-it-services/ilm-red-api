"""Rankings API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.v1.deps import AdminUser, DBSession, OptionalUser
from app.schemas.ranking import (
    LeaderboardResponse,
    PointsHistoryResponse,
    RankingContextResponse,
    RankingRefreshResponse,
    UserRankingResponse,
    UserRankingSummary,
)
from app.services.ranking_service import RankingService

router = APIRouter()


@router.get(
    "",
    response_model=LeaderboardResponse,
    summary="Global leaderboard",
    description="Get the global leaderboard with pagination.",
)
async def get_global_leaderboard(
    db: DBSession,
    current_user: OptionalUser,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> LeaderboardResponse:
    """Get the global leaderboard.

    Returns users ranked by total points in the global context.
    """
    service = RankingService(db)
    return await service.get_global_leaderboard(page=page, limit=limit)


@router.get(
    "/contexts",
    response_model=list[RankingContextResponse],
    summary="List ranking contexts",
    description="List all available ranking contexts.",
)
async def list_contexts(
    db: DBSession,
    current_user: OptionalUser,
    type: str | None = Query(None, description="Filter by context type (global, corporate, book_club)"),
    is_active: bool | None = Query(True, description="Filter by active status"),
) -> list[RankingContextResponse]:
    """List available ranking contexts.

    Contexts define different scopes for rankings (e.g., global, per book club).
    """
    service = RankingService(db)
    return await service.list_contexts(type=type, is_active=is_active)


@router.get(
    "/contexts/{context_id}",
    response_model=LeaderboardResponse,
    summary="Context leaderboard",
    description="Get the leaderboard for a specific ranking context.",
)
async def get_context_leaderboard(
    context_id: UUID,
    db: DBSession,
    current_user: OptionalUser,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> LeaderboardResponse:
    """Get the leaderboard for a specific ranking context.

    Returns users ranked by total points within the specified context.
    """
    service = RankingService(db)
    return await service.get_context_leaderboard(
        context_id=context_id,
        page=page,
        limit=limit,
    )


@router.get(
    "/contexts/{context_id}/users/{user_id}",
    response_model=UserRankingResponse,
    summary="User ranking in context",
    description="Get a specific user's ranking within a context.",
)
async def get_user_ranking_in_context(
    context_id: UUID,
    user_id: UUID,
    db: DBSession,
    current_user: OptionalUser,
) -> UserRankingResponse:
    """Get a user's ranking within a specific context.

    Returns rank position, total points, percentile, and activity stats.
    """
    service = RankingService(db)
    return await service.get_user_ranking_in_context(
        context_id=context_id,
        user_id=user_id,
    )


@router.get(
    "/users/{user_id}",
    response_model=UserRankingSummary,
    summary="User rankings across contexts",
    description="Get a user's rankings across all contexts.",
)
async def get_user_rankings(
    user_id: UUID,
    db: DBSession,
    current_user: OptionalUser,
) -> UserRankingSummary:
    """Get a user's rankings across all contexts.

    Returns a summary of the user's rank in every context they participate in.
    """
    service = RankingService(db)
    return await service.get_user_rankings(user_id=user_id)


@router.get(
    "/users/{user_id}/history",
    response_model=PointsHistoryResponse,
    summary="User ranking history",
    description="Get a user's points history with pagination.",
)
async def get_user_points_history(
    user_id: UUID,
    db: DBSession,
    current_user: OptionalUser,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> PointsHistoryResponse:
    """Get a user's points history.

    Returns a chronological list of points earned with source and reason.
    """
    service = RankingService(db)
    return await service.get_user_points_history(
        user_id=user_id,
        page=page,
        limit=limit,
    )


@router.post(
    "/admin/contexts/{context_id}/refresh",
    response_model=RankingRefreshResponse,
    summary="Recalculate rankings (admin)",
    description="Recalculate all rankings for a context. Admin only.",
)
async def refresh_rankings(
    context_id: UUID,
    db: DBSession,
    admin_user: AdminUser,
) -> RankingRefreshResponse:
    """Recalculate rankings for a context.

    Recomputes rank positions and percentiles based on current total points.
    Requires admin privileges.
    """
    service = RankingService(db)
    return await service.refresh_rankings(context_id=context_id)
