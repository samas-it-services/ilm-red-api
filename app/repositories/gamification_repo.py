"""Gamification repository for database operations."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.gamification import (
    Badge,
    GamificationActivity,
    PointsHistory,
    Rank,
    UserActivityLog,
    UserBadge,
    UserRank,
)
from app.models.user import User


class GamificationRepository:
    """Repository for gamification database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Activity operations
    async def get_activity_by_name(self, name: str) -> GamificationActivity | None:
        stmt = select(GamificationActivity).where(
            GamificationActivity.name == name,
            GamificationActivity.is_active.is_(True),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_activities(self) -> list[GamificationActivity]:
        stmt = select(GamificationActivity).where(
            GamificationActivity.is_active.is_(True)
        ).order_by(GamificationActivity.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def log_activity(
        self, user_id: uuid.UUID, activity_id: uuid.UUID, points: int, metadata: dict
    ) -> UserActivityLog:
        log = UserActivityLog(
            user_id=user_id,
            activity_id=activity_id,
            points_earned=points,
            extra_metadata=metadata,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def get_last_activity_time(
        self, user_id: uuid.UUID, activity_id: uuid.UUID
    ) -> datetime | None:
        stmt = (
            select(UserActivityLog.created_at)
            .where(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_id == activity_id,
            )
            .order_by(UserActivityLog.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_daily_activities(
        self, user_id: uuid.UUID, activity_id: uuid.UUID
    ) -> int:
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(func.count())
            .select_from(UserActivityLog)
            .where(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_id == activity_id,
                UserActivityLog.created_at >= today_start,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def count_today_activities(self, user_id: uuid.UUID) -> int:
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(func.count())
            .select_from(UserActivityLog)
            .where(
                UserActivityLog.user_id == user_id,
                UserActivityLog.created_at >= today_start,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    # Points operations
    async def add_points(
        self, user_id: uuid.UUID, source: str, points: int,
        reason: str | None = None, source_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> PointsHistory:
        entry = PointsHistory(
            user_id=user_id,
            source=source,
            source_id=source_id,
            points=points,
            reason=reason,
            extra_metadata=metadata or {},
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def get_total_points(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.coalesce(func.sum(PointsHistory.points), 0))
            .where(PointsHistory.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_points_history(
        self, user_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> tuple[list[PointsHistory], int]:
        count_stmt = (
            select(func.count()).select_from(PointsHistory)
            .where(PointsHistory.user_id == user_id)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(PointsHistory)
            .where(PointsHistory.user_id == user_id)
            .order_by(PointsHistory.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    # Badge operations
    async def get_badge_by_name(self, name: str) -> Badge | None:
        stmt = select(Badge).where(Badge.name == name, Badge.is_active.is_(True))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_badges(self) -> list[Badge]:
        stmt = select(Badge).where(Badge.is_active.is_(True)).order_by(Badge.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def award_badge(
        self, user_id: uuid.UUID, badge_id: uuid.UUID,
        awarded_by: uuid.UUID | None = None, metadata: dict | None = None,
    ) -> UserBadge:
        user_badge = UserBadge(
            user_id=user_id,
            badge_id=badge_id,
            awarded_by=awarded_by,
            extra_metadata=metadata or {},
        )
        self.db.add(user_badge)
        await self.db.flush()
        # Reload with badge relationship
        stmt = (
            select(UserBadge)
            .options(selectinload(UserBadge.badge))
            .where(UserBadge.id == user_badge.id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def has_badge(self, user_id: uuid.UUID, badge_id: uuid.UUID) -> bool:
        stmt = (
            select(UserBadge.id)
            .where(UserBadge.user_id == user_id, UserBadge.badge_id == badge_id)
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_user_badges(self, user_id: uuid.UUID) -> list[UserBadge]:
        stmt = (
            select(UserBadge)
            .options(selectinload(UserBadge.badge))
            .where(UserBadge.user_id == user_id)
            .order_by(UserBadge.earned_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_user_badges(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count()).select_from(UserBadge)
            .where(UserBadge.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    # Rank operations
    async def get_all_ranks(self) -> list[Rank]:
        stmt = select(Rank).order_by(Rank.level)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_rank_for_points(self, points: int) -> Rank | None:
        stmt = (
            select(Rank)
            .where(Rank.min_points <= points)
            .order_by(Rank.min_points.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_rank(self, user_id: uuid.UUID) -> UserRank | None:
        stmt = (
            select(UserRank)
            .options(selectinload(UserRank.rank))
            .where(UserRank.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def set_user_rank(
        self, user_id: uuid.UUID, rank_id: uuid.UUID, total_points: int
    ) -> UserRank:
        existing = await self.get_user_rank(user_id)
        if existing:
            existing.rank_id = rank_id
            existing.current_points = total_points
            existing.total_points_earned = total_points
            existing.rank_achieved_at = datetime.now(UTC)
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            user_rank = UserRank(
                user_id=user_id,
                rank_id=rank_id,
                current_points=total_points,
                total_points_earned=total_points,
                rank_achieved_at=datetime.now(UTC),
            )
            self.db.add(user_rank)
            await self.db.flush()
            return user_rank

    # Leaderboard
    async def get_leaderboard(
        self, page: int = 1, limit: int = 20
    ) -> tuple[list[dict], int]:
        count_stmt = (
            select(func.count(func.distinct(PointsHistory.user_id)))
            .select_from(PointsHistory)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(
                PointsHistory.user_id,
                func.sum(PointsHistory.points).label("total_points"),
                User.username,
                User.display_name,
                User.avatar_url,
            )
            .join(User, User.id == PointsHistory.user_id)
            .group_by(PointsHistory.user_id, User.username, User.display_name, User.avatar_url)
            .order_by(func.sum(PointsHistory.points).desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        entries = []
        for idx, row in enumerate(rows):
            entries.append({
                "user_id": row.user_id,
                "username": row.username,
                "display_name": row.display_name,
                "avatar_url": row.avatar_url,
                "total_points": row.total_points,
                "rank_position": (page - 1) * limit + idx + 1,
            })
        return entries, total
