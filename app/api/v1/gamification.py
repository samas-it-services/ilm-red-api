"""Gamification API endpoints."""

import uuid

from fastapi import APIRouter, Query

from app.api.v1.deps import AdminUser, CurrentUser, DBSession, OptionalUser
from app.schemas.common import PaginatedResponse, create_pagination
from app.schemas.gamification import (
    ActivityResponse,
    AwardBadgeRequest,
    BadgeResponse,
    GamificationSummary,
    LeaderboardEntry,
    LogActivityRequest,
    LogActivityResponse,
    PointsHistoryResponse,
    RankResponse,
    UserBadgeResponse,
)
from app.services.gamification_service import GamificationService

router = APIRouter()


@router.post(
    "/log-activity",
    response_model=LogActivityResponse,
    summary="Log activity and award points",
)
async def log_activity(
    data: LogActivityRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> LogActivityResponse:
    """Log a gamification activity for the current user."""
    service = GamificationService(db)
    return await service.log_activity(current_user, data.activity_name, data.metadata)


@router.post(
    "/award-badge",
    response_model=UserBadgeResponse,
    status_code=201,
    summary="Award badge to user",
)
async def award_badge(
    data: AwardBadgeRequest,
    db: DBSession,
    current_user: AdminUser,
) -> UserBadgeResponse:
    """Award a badge to a user. Requires admin."""
    service = GamificationService(db)
    return await service.award_badge(
        data.user_id, data.badge_name, current_user.id, data.metadata
    )


@router.get(
    "/summary",
    response_model=GamificationSummary,
    summary="Get current user's gamification summary",
)
async def get_summary(
    db: DBSession,
    current_user: CurrentUser,
) -> GamificationSummary:
    """Get gamification summary for the current user."""
    service = GamificationService(db)
    return await service.get_summary(current_user.id)


@router.get(
    "/users/{user_id}/summary",
    response_model=GamificationSummary,
    summary="Get user's gamification summary",
)
async def get_user_summary(
    user_id: uuid.UUID,
    db: DBSession,
    current_user: OptionalUser,
) -> GamificationSummary:
    """Get gamification summary for any user."""
    service = GamificationService(db)
    return await service.get_summary(user_id)


@router.get(
    "/users/{user_id}/rank",
    response_model=RankResponse | None,
    summary="Get user's current rank",
)
async def get_user_rank(
    user_id: uuid.UUID,
    db: DBSession,
    current_user: OptionalUser,
) -> RankResponse | None:
    """Get current rank for a user."""
    service = GamificationService(db)
    return await service.get_user_rank(user_id)


@router.get(
    "/users/{user_id}/badges",
    response_model=list[UserBadgeResponse],
    summary="Get user's earned badges",
)
async def get_user_badges(
    user_id: uuid.UUID,
    db: DBSession,
    current_user: OptionalUser,
) -> list[UserBadgeResponse]:
    """Get all badges earned by a user."""
    service = GamificationService(db)
    return await service.get_user_badges(user_id)


@router.get(
    "/users/{user_id}/points-history",
    response_model=PaginatedResponse[PointsHistoryResponse],
    summary="Get user's points history",
)
async def get_points_history(
    user_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[PointsHistoryResponse]:
    """Get points history. Users can view their own, admins can view anyone."""
    if user_id != current_user.id and not current_user.is_admin:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    service = GamificationService(db)
    entries, total = await service.get_points_history(user_id, page, limit)
    return PaginatedResponse(
        data=entries,
        pagination=create_pagination(page, limit, total),
    )


@router.get(
    "/badges",
    response_model=list[BadgeResponse],
    summary="List all available badges",
)
async def list_badges(db: DBSession) -> list[BadgeResponse]:
    """List all available badges (public)."""
    service = GamificationService(db)
    return await service.get_all_badges()


@router.get(
    "/ranks",
    response_model=list[RankResponse],
    summary="List all ranks",
)
async def list_ranks(db: DBSession) -> list[RankResponse]:
    """List all ranks (public)."""
    service = GamificationService(db)
    return await service.get_all_ranks()


@router.get(
    "/activities",
    response_model=list[ActivityResponse],
    summary="List all activity types",
)
async def list_activities(
    db: DBSession,
    current_user: CurrentUser,
) -> list[ActivityResponse]:
    """List all gamification activity types."""
    service = GamificationService(db)
    return await service.get_all_activities()


@router.get(
    "/leaderboard",
    response_model=PaginatedResponse[LeaderboardEntry],
    summary="Get points leaderboard",
)
async def get_leaderboard(
    db: DBSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[LeaderboardEntry]:
    """Get points leaderboard (public)."""
    service = GamificationService(db)
    entries, total = await service.get_leaderboard(page, limit)
    return PaginatedResponse(
        data=entries,
        pagination=create_pagination(page, limit, total),
    )
