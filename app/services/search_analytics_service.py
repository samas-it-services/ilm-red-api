"""Search analytics service for business logic."""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.search_analytics_repo import SearchAnalyticsRepository

logger = structlog.get_logger(__name__)


class SearchAnalyticsService:
    """Service for search analytics business logic.

    This service is designed to be consumed by the existing search service
    to log search events and retrieve analytics data.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SearchAnalyticsRepository(db)

    async def log_search(
        self,
        search_query: str,
        search_type: str,
        result_count: int,
        user_id: uuid.UUID | None = None,
        search_source: str | None = None,
        filters_used: dict | None = None,
        response_time_ms: int | None = None,
        cache_hit: bool = False,
    ) -> uuid.UUID:
        """Log a search event and return the analytics record ID.

        This method is intended to be called from the search service
        after each search operation completes.

        Args:
            search_query: The search query string
            search_type: Type of search (full_text, semantic, autocomplete)
            result_count: Number of results returned
            user_id: Optional user ID
            search_source: Where the search originated
            filters_used: Filters applied during search
            response_time_ms: Response time in milliseconds
            cache_hit: Whether results were served from cache

        Returns:
            UUID of the created analytics record
        """
        analytics = await self.repo.log_search(
            search_query=search_query,
            search_type=search_type,
            result_count=result_count,
            user_id=user_id,
            search_source=search_source,
            filters_used=filters_used,
            response_time_ms=response_time_ms,
            cache_hit=cache_hit,
        )

        logger.debug(
            "search_logged",
            analytics_id=str(analytics.id),
            query=search_query[:50],
            search_type=search_type,
            result_count=result_count,
            response_time_ms=response_time_ms,
            cache_hit=cache_hit,
        )

        return analytics.id

    async def record_click(self, analytics_id: uuid.UUID) -> None:
        """Record that a user clicked on a search result.

        Args:
            analytics_id: ID of the search analytics record
        """
        await self.repo.record_click(analytics_id)

    async def get_popular_queries(
        self,
        days: int = 7,
        limit: int = 20,
    ) -> list[dict]:
        """Get the most popular search queries.

        Args:
            days: Number of days to look back
            limit: Maximum number of results

        Returns:
            List of popular queries with counts and avg results
        """
        return await self.repo.get_popular_queries(days=days, limit=limit)

    async def get_zero_result_queries(
        self,
        days: int = 7,
        limit: int = 20,
    ) -> list[dict]:
        """Get search queries that returned zero results.

        Useful for identifying content gaps and improving search quality.

        Args:
            days: Number of days to look back
            limit: Maximum number of results

        Returns:
            List of zero-result queries with occurrence counts
        """
        return await self.repo.get_zero_result_queries(days=days, limit=limit)

    async def get_search_stats(self, days: int = 30) -> dict:
        """Get aggregated search statistics.

        Args:
            days: Number of days to look back

        Returns:
            Dict with search metrics (total, unique, avg results,
            response time, cache hit rate, zero result rate)
        """
        return await self.repo.get_search_stats(days=days)

    async def get_search_volume_by_day(self, days: int = 30) -> list[dict]:
        """Get search volume grouped by day.

        Args:
            days: Number of days to look back

        Returns:
            List of daily search volumes
        """
        return await self.repo.get_search_volume_by_day(days=days)
