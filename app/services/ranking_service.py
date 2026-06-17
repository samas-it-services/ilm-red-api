"""Ranking service for business logic."""

import uuid

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.ranking_repo import RankingRepository
from app.schemas.common import create_pagination
from app.schemas.ranking import (
    LeaderboardEntry,
    LeaderboardResponse,
    PointsHistoryEntry,
    PointsHistoryResponse,
    RankingContextResponse,
    RankingRefreshResponse,
    UserBrief,
    UserRankingResponse,
    UserRankingSummary,
)

logger = structlog.get_logger(__name__)


class RankingService:
    """Service for ranking-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RankingRepository(db)

    async def get_global_leaderboard(
        self,
        page: int = 1,
        limit: int = 20,
    ) -> LeaderboardResponse:
        """Get the global leaderboard."""
        rankings, total, context = await self.repo.get_global_leaderboard(
            page=page,
            limit=limit,
        )

        entries = [
            self._ranking_to_leaderboard_entry(r) for r in rankings
        ]

        return LeaderboardResponse(
            data=entries,
            pagination=create_pagination(page, limit, total),
            context=RankingContextResponse.model_validate(context) if context else None,
        )

    async def list_contexts(
        self,
        type: str | None = None,
        is_active: bool | None = True,
    ) -> list[RankingContextResponse]:
        """List ranking contexts."""
        contexts = await self.repo.list_contexts(type=type, is_active=is_active)
        return [RankingContextResponse.model_validate(c) for c in contexts]

    async def get_context_leaderboard(
        self,
        context_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> LeaderboardResponse:
        """Get leaderboard for a specific context."""
        context = await self.repo.get_context_by_id(context_id)
        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ranking context not found",
            )

        rankings, total = await self.repo.get_leaderboard(
            context_id=context_id,
            page=page,
            limit=limit,
        )

        entries = [
            self._ranking_to_leaderboard_entry(r) for r in rankings
        ]

        return LeaderboardResponse(
            data=entries,
            pagination=create_pagination(page, limit, total),
            context=RankingContextResponse.model_validate(context),
        )

    async def get_user_ranking_in_context(
        self,
        context_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> UserRankingResponse:
        """Get user's ranking in a specific context."""
        context = await self.repo.get_context_by_id(context_id)
        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ranking context not found",
            )

        ranking = await self.repo.get_user_ranking(user_id, context_id)
        if not ranking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User ranking not found in this context",
            )

        return self._ranking_to_response(ranking)

    async def get_user_rankings(
        self,
        user_id: uuid.UUID,
    ) -> UserRankingSummary:
        """Get user's rankings across all contexts."""
        rankings = await self.repo.get_user_rankings_all_contexts(user_id)

        return UserRankingSummary(
            user_id=user_id,
            rankings=[self._ranking_to_response(r) for r in rankings],
        )

    async def get_user_points_history(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> PointsHistoryResponse:
        """Get user's points history."""
        history, total = await self.repo.get_user_points_history(
            user_id=user_id,
            page=page,
            limit=limit,
        )

        entries = [
            PointsHistoryEntry.model_validate(h) for h in history
        ]

        return PointsHistoryResponse(
            data=entries,
            pagination=create_pagination(page, limit, total),
        )

    async def refresh_rankings(
        self,
        context_id: uuid.UUID,
    ) -> RankingRefreshResponse:
        """Recalculate rankings for a context (admin only)."""
        context = await self.repo.get_context_by_id(context_id)
        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ranking context not found",
            )

        users_recalculated = await self.repo.recalculate_rankings(context_id)
        await self.db.commit()

        logger.info(
            "Rankings refreshed",
            context_id=str(context_id),
            users_recalculated=users_recalculated,
        )

        return RankingRefreshResponse(
            context_id=context_id,
            users_recalculated=users_recalculated,
        )

    # Helper methods

    def _ranking_to_response(self, ranking) -> UserRankingResponse:
        """Convert UserContextRanking model to response schema."""
        user_brief = None
        if ranking.user:
            user_brief = UserBrief(
                id=ranking.user.id,
                username=ranking.user.username,
                display_name=ranking.user.display_name,
                avatar_url=ranking.user.avatar_url,
            )

        return UserRankingResponse(
            id=ranking.id,
            user_id=ranking.user_id,
            context_id=ranking.context_id,
            rank_position=ranking.rank_position,
            total_points=ranking.total_points,
            percentile=ranking.percentile,
            rank_id=ranking.rank_id,
            books_uploaded=ranking.books_uploaded,
            books_reviewed=ranking.books_reviewed,
            badges_earned_count=ranking.badges_earned_count,
            last_activity_at=ranking.last_activity_at,
            calculated_at=ranking.calculated_at,
            user=user_brief,
        )

    def _ranking_to_leaderboard_entry(self, ranking) -> LeaderboardEntry:
        """Convert UserContextRanking model to leaderboard entry."""
        user_brief = UserBrief(
            id=ranking.user.id,
            username=ranking.user.username,
            display_name=ranking.user.display_name,
            avatar_url=ranking.user.avatar_url,
        )

        return LeaderboardEntry(
            rank_position=ranking.rank_position,
            total_points=ranking.total_points,
            percentile=ranking.percentile,
            books_uploaded=ranking.books_uploaded,
            books_reviewed=ranking.books_reviewed,
            badges_earned_count=ranking.badges_earned_count,
            last_activity_at=ranking.last_activity_at,
            user=user_brief,
        )
