"""Gamification service for business logic."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.gamification_repo import GamificationRepository
from app.schemas.gamification import (
    ActivityResponse,
    BadgeResponse,
    GamificationSummary,
    LeaderboardEntry,
    LogActivityResponse,
    PointsHistoryResponse,
    RankResponse,
    UserBadgeResponse,
)


class GamificationService:
    """Service for gamification operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = GamificationRepository(db)

    async def log_activity(
        self, user: User, activity_name: str, metadata: dict
    ) -> LogActivityResponse:
        """Log an activity and award points."""
        activity = await self.repo.get_activity_by_name(activity_name)
        if not activity:
            raise HTTPException(status_code=404, detail=f"Activity '{activity_name}' not found")

        # Check cooldown
        if activity.cooldown_hours > 0:
            last_time = await self.repo.get_last_activity_time(user.id, activity.id)
            if last_time:
                cooldown_end = last_time + timedelta(hours=activity.cooldown_hours)
                if datetime.now(UTC) < cooldown_end:
                    return LogActivityResponse(
                        points_awarded=0,
                        new_total_points=await self.repo.get_total_points(user.id),
                        rank_changed=False,
                        new_rank=None,
                    )

        # Check daily limit
        daily_count = await self.repo.count_daily_activities(user.id, activity.id)
        if daily_count >= activity.max_daily_occurrences:
            return LogActivityResponse(
                points_awarded=0,
                new_total_points=await self.repo.get_total_points(user.id),
                rank_changed=False,
                new_rank=None,
            )

        # Log the activity
        await self.repo.log_activity(user.id, activity.id, activity.points, metadata)

        # Award points
        if activity.points > 0:
            await self.repo.add_points(
                user.id, activity_name, activity.points,
                reason=f"Activity: {activity.display_name}",
                metadata=metadata,
            )

        total_points = await self.repo.get_total_points(user.id)

        # Check for rank change
        rank_changed = False
        new_rank_name = None
        new_rank = await self.repo.get_rank_for_points(total_points)
        if new_rank:
            current_user_rank = await self.repo.get_user_rank(user.id)
            if not current_user_rank or current_user_rank.rank_id != new_rank.id:
                await self.repo.set_user_rank(user.id, new_rank.id, total_points)
                rank_changed = True
                new_rank_name = new_rank.display_name

        return LogActivityResponse(
            points_awarded=activity.points,
            new_total_points=total_points,
            rank_changed=rank_changed,
            new_rank=new_rank_name,
        )

    async def award_badge(
        self, user_id: uuid.UUID, badge_name: str,
        awarded_by: uuid.UUID | None = None, metadata: dict | None = None,
    ) -> UserBadgeResponse:
        """Award a badge to a user."""
        badge = await self.repo.get_badge_by_name(badge_name)
        if not badge:
            raise HTTPException(status_code=404, detail=f"Badge '{badge_name}' not found")

        if await self.repo.has_badge(user_id, badge.id):
            raise HTTPException(status_code=409, detail="User already has this badge")

        user_badge = await self.repo.award_badge(user_id, badge.id, awarded_by, metadata)

        # Award bonus points for badge
        if badge.points_awarded > 0:
            await self.repo.add_points(
                user_id, "badge_earned", badge.points_awarded,
                reason=f"Badge earned: {badge.display_name}",
                source_id=badge.id,
            )

        return UserBadgeResponse(
            id=user_badge.id,
            badge=BadgeResponse.model_validate(user_badge.badge),
            earned_at=user_badge.earned_at,
            awarded_by=user_badge.awarded_by,
        )

    async def get_summary(self, user_id: uuid.UUID) -> GamificationSummary:
        """Get gamification summary for a user."""
        total_points = await self.repo.get_total_points(user_id)
        user_rank = await self.repo.get_user_rank(user_id)
        user_badges = await self.repo.get_user_badges(user_id)
        badges_count = await self.repo.count_user_badges(user_id)
        activities_today = await self.repo.count_today_activities(user_id)

        current_rank = None
        if user_rank:
            current_rank = RankResponse.model_validate(user_rank.rank)

        recent_badges = [
            UserBadgeResponse(
                id=ub.id,
                badge=BadgeResponse.model_validate(ub.badge),
                earned_at=ub.earned_at,
                awarded_by=ub.awarded_by,
            )
            for ub in user_badges[:5]
        ]

        return GamificationSummary(
            user_id=user_id,
            total_points=total_points,
            current_rank=current_rank,
            recent_badges=recent_badges,
            badges_count=badges_count,
            activities_today=activities_today,
        )

    async def get_user_rank(self, user_id: uuid.UUID) -> RankResponse | None:
        user_rank = await self.repo.get_user_rank(user_id)
        if user_rank:
            return RankResponse.model_validate(user_rank.rank)
        return None

    async def get_user_badges(self, user_id: uuid.UUID) -> list[UserBadgeResponse]:
        user_badges = await self.repo.get_user_badges(user_id)
        return [
            UserBadgeResponse(
                id=ub.id,
                badge=BadgeResponse.model_validate(ub.badge),
                earned_at=ub.earned_at,
                awarded_by=ub.awarded_by,
            )
            for ub in user_badges
        ]

    async def get_points_history(
        self, user_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> tuple[list[PointsHistoryResponse], int]:
        entries, total = await self.repo.get_points_history(user_id, page, limit)
        return [PointsHistoryResponse.model_validate(e) for e in entries], total

    async def get_all_badges(self) -> list[BadgeResponse]:
        badges = await self.repo.get_all_badges()
        return [BadgeResponse.model_validate(b) for b in badges]

    async def get_all_ranks(self) -> list[RankResponse]:
        ranks = await self.repo.get_all_ranks()
        return [RankResponse.model_validate(r) for r in ranks]

    async def get_all_activities(self) -> list[ActivityResponse]:
        activities = await self.repo.get_all_activities()
        return [ActivityResponse.model_validate(a) for a in activities]

    async def get_leaderboard(
        self, page: int = 1, limit: int = 20
    ) -> tuple[list[LeaderboardEntry], int]:
        entries, total = await self.repo.get_leaderboard(page, limit)
        return [LeaderboardEntry(**e) for e in entries], total
