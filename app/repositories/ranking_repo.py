"""Ranking repository for database operations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.ranking import (
    ContextPointsHistory,
    RankingContext,
    RankingSetting,
    UserContextRanking,
)


class RankingRepository:
    """Repository for ranking database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Context CRUD

    async def create_context(
        self,
        name: str,
        type: str,
        entity_id: uuid.UUID | None = None,
        settings: dict | None = None,
    ) -> RankingContext:
        """Create a new ranking context."""
        context = RankingContext(
            name=name,
            type=type,
            entity_id=entity_id,
            settings=settings or {},
        )
        self.db.add(context)
        await self.db.flush()
        await self.db.refresh(context)
        return context

    async def get_context_by_id(self, context_id: uuid.UUID) -> RankingContext | None:
        """Get a ranking context by ID."""
        stmt = select(RankingContext).where(RankingContext.id == context_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_contexts(
        self,
        type: str | None = None,
        is_active: bool | None = True,
    ) -> list[RankingContext]:
        """List ranking contexts with optional filtering."""
        conditions = []

        if type is not None:
            conditions.append(RankingContext.type == type)
        if is_active is not None:
            conditions.append(RankingContext.is_active == is_active)

        stmt = select(RankingContext)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(RankingContext.created_at.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_global_context(self) -> RankingContext | None:
        """Get the global ranking context."""
        stmt = select(RankingContext).where(
            and_(
                RankingContext.type == "global",
                RankingContext.is_active == True,  # noqa: E712
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    # User ranking queries

    async def get_user_ranking(
        self,
        user_id: uuid.UUID,
        context_id: uuid.UUID,
    ) -> UserContextRanking | None:
        """Get user's ranking in a specific context."""
        stmt = (
            select(UserContextRanking)
            .options(joinedload(UserContextRanking.user))
            .where(
                and_(
                    UserContextRanking.user_id == user_id,
                    UserContextRanking.context_id == context_id,
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_rankings_all_contexts(
        self,
        user_id: uuid.UUID,
    ) -> list[UserContextRanking]:
        """Get user's rankings across all contexts."""
        stmt = (
            select(UserContextRanking)
            .options(
                joinedload(UserContextRanking.user),
                joinedload(UserContextRanking.context),
            )
            .where(UserContextRanking.user_id == user_id)
            .order_by(UserContextRanking.context_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    # Leaderboard queries

    async def get_leaderboard(
        self,
        context_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[UserContextRanking], int]:
        """Get leaderboard for a context with pagination."""
        # Count
        count_stmt = select(func.count(UserContextRanking.id)).where(
            UserContextRanking.context_id == context_id
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data
        offset = (page - 1) * limit
        stmt = (
            select(UserContextRanking)
            .options(joinedload(UserContextRanking.user))
            .where(UserContextRanking.context_id == context_id)
            .order_by(UserContextRanking.rank_position.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rankings = list(result.scalars().unique().all())

        return rankings, total

    async def get_global_leaderboard(
        self,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[UserContextRanking], int, RankingContext | None]:
        """Get the global leaderboard with pagination."""
        global_context = await self.get_global_context()
        if not global_context:
            return [], 0, None

        rankings, total = await self.get_leaderboard(
            context_id=global_context.id,
            page=page,
            limit=limit,
        )
        return rankings, total, global_context

    # Points history

    async def add_points_history(
        self,
        user_id: uuid.UUID,
        context_id: uuid.UUID,
        source: str,
        points: int,
        source_id: uuid.UUID | None = None,
        reason: str | None = None,
        metadata: dict | None = None,
    ) -> ContextPointsHistory:
        """Record a points history entry."""
        entry = ContextPointsHistory(
            user_id=user_id,
            context_id=context_id,
            source=source,
            source_id=source_id,
            points=points,
            reason=reason,
            extra_metadata=metadata or {},
        )
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def get_user_points_history(
        self,
        user_id: uuid.UUID,
        context_id: uuid.UUID | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[ContextPointsHistory], int]:
        """Get points history for a user with pagination."""
        conditions = [ContextPointsHistory.user_id == user_id]
        if context_id is not None:
            conditions.append(ContextPointsHistory.context_id == context_id)

        # Count
        count_stmt = select(func.count(ContextPointsHistory.id)).where(
            and_(*conditions)
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data
        offset = (page - 1) * limit
        stmt = (
            select(ContextPointsHistory)
            .where(and_(*conditions))
            .order_by(ContextPointsHistory.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        history = list(result.scalars().all())

        return history, total

    # Ranking recalculation

    async def recalculate_rankings(self, context_id: uuid.UUID) -> int:
        """Recalculate all user rankings for a context.

        Recomputes rank_position and percentile based on total_points.
        Returns the number of users recalculated.
        """
        # Get all user rankings for this context ordered by points
        stmt = (
            select(UserContextRanking)
            .where(UserContextRanking.context_id == context_id)
            .order_by(UserContextRanking.total_points.desc())
        )
        result = await self.db.execute(stmt)
        rankings = list(result.scalars().all())

        total_users = len(rankings)
        if total_users == 0:
            return 0

        now = datetime.now(UTC)
        for i, ranking in enumerate(rankings):
            ranking.rank_position = i + 1
            ranking.percentile = round(
                ((total_users - (i + 1)) / total_users) * 100, 2
            ) if total_users > 1 else 100.0
            ranking.calculated_at = now

        await self.db.flush()
        return total_users

    async def upsert_user_ranking(
        self,
        user_id: uuid.UUID,
        context_id: uuid.UUID,
        total_points: int,
        books_uploaded: int = 0,
        books_reviewed: int = 0,
        badges_earned_count: int = 0,
    ) -> UserContextRanking:
        """Create or update a user's ranking in a context."""
        existing = await self.get_user_ranking(user_id, context_id)

        if existing:
            existing.total_points = total_points
            existing.books_uploaded = books_uploaded
            existing.books_reviewed = books_reviewed
            existing.badges_earned_count = badges_earned_count
            existing.last_activity_at = datetime.now(UTC)
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            ranking = UserContextRanking(
                user_id=user_id,
                context_id=context_id,
                rank_position=0,  # Will be recalculated
                total_points=total_points,
                books_uploaded=books_uploaded,
                books_reviewed=books_reviewed,
                badges_earned_count=badges_earned_count,
                last_activity_at=datetime.now(UTC),
            )
            self.db.add(ranking)
            await self.db.flush()
            await self.db.refresh(ranking)
            return ranking
