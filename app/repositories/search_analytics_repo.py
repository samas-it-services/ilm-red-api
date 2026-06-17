"""Search analytics repository for database operations."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search_analytics import SearchAnalytics


class SearchAnalyticsRepository:
    """Repository for SearchAnalytics database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

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
    ) -> SearchAnalytics:
        """Log a search event.

        Args:
            search_query: The search query string
            search_type: Type of search (full_text, semantic, autocomplete)
            result_count: Number of results returned
            user_id: Optional user ID
            search_source: Where the search originated (web, mobile, api)
            filters_used: Filters applied during search
            response_time_ms: Response time in milliseconds
            cache_hit: Whether results were served from cache

        Returns:
            Created SearchAnalytics record
        """
        analytics = SearchAnalytics(
            user_id=user_id,
            search_query=search_query,
            search_type=search_type,
            search_source=search_source,
            filters_used=filters_used or {},
            result_count=result_count,
            response_time_ms=response_time_ms,
            cache_hit=cache_hit,
        )
        self.db.add(analytics)
        await self.db.flush()
        return analytics

    async def record_click(self, analytics_id: uuid.UUID) -> None:
        """Increment the results_clicked count for a search event."""
        stmt = select(SearchAnalytics).where(SearchAnalytics.id == analytics_id)
        result = await self.db.execute(stmt)
        analytics = result.scalar_one_or_none()

        if analytics:
            analytics.results_clicked += 1
            await self.db.flush()

    async def get_popular_queries(
        self,
        days: int = 7,
        limit: int = 20,
    ) -> list[dict]:
        """Get the most popular search queries in the given time window.

        Args:
            days: Number of days to look back
            limit: Maximum number of results

        Returns:
            List of dicts with query, count, and avg_results
        """
        since = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(
                SearchAnalytics.search_query,
                func.count(SearchAnalytics.id).label("search_count"),
                func.avg(SearchAnalytics.result_count).label("avg_results"),
                func.avg(SearchAnalytics.response_time_ms).label("avg_response_ms"),
            )
            .where(SearchAnalytics.created_at >= since)
            .group_by(SearchAnalytics.search_query)
            .order_by(func.count(SearchAnalytics.id).desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "query": row.search_query,
                "search_count": row.search_count,
                "avg_results": round(float(row.avg_results), 1) if row.avg_results else 0,
                "avg_response_ms": round(float(row.avg_response_ms), 1) if row.avg_response_ms else 0,
            }
            for row in rows
        ]

    async def get_zero_result_queries(
        self,
        days: int = 7,
        limit: int = 20,
    ) -> list[dict]:
        """Get search queries that returned zero results.

        Args:
            days: Number of days to look back
            limit: Maximum number of results

        Returns:
            List of dicts with query and count
        """
        since = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(
                SearchAnalytics.search_query,
                func.count(SearchAnalytics.id).label("search_count"),
            )
            .where(
                and_(
                    SearchAnalytics.created_at >= since,
                    SearchAnalytics.result_count == 0,
                )
            )
            .group_by(SearchAnalytics.search_query)
            .order_by(func.count(SearchAnalytics.id).desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "query": row.search_query,
                "search_count": row.search_count,
            }
            for row in rows
        ]

    async def get_search_stats(
        self,
        days: int = 30,
    ) -> dict:
        """Get aggregated search statistics.

        Args:
            days: Number of days to look back

        Returns:
            Dict with total_searches, unique_queries, avg_results,
            avg_response_ms, cache_hit_rate, zero_result_rate
        """
        since = datetime.now(UTC) - timedelta(days=days)

        stmt = select(
            func.count(SearchAnalytics.id).label("total_searches"),
            func.count(func.distinct(SearchAnalytics.search_query)).label("unique_queries"),
            func.avg(SearchAnalytics.result_count).label("avg_results"),
            func.avg(SearchAnalytics.response_time_ms).label("avg_response_ms"),
            func.sum(
                func.cast(SearchAnalytics.cache_hit, Integer)
            ).label("cache_hits"),
            func.sum(
                func.case(
                    (SearchAnalytics.result_count == 0, 1),
                    else_=0,
                )
            ).label("zero_result_count"),
        ).where(SearchAnalytics.created_at >= since)

        result = await self.db.execute(stmt)
        row = result.one()

        total = row.total_searches or 0
        cache_hits = row.cache_hits or 0
        zero_results = row.zero_result_count or 0

        return {
            "total_searches": total,
            "unique_queries": row.unique_queries or 0,
            "avg_results": round(float(row.avg_results), 1) if row.avg_results else 0,
            "avg_response_ms": round(float(row.avg_response_ms), 1) if row.avg_response_ms else 0,
            "cache_hit_rate": round(cache_hits / total * 100, 1) if total > 0 else 0,
            "zero_result_rate": round(zero_results / total * 100, 1) if total > 0 else 0,
            "period_days": days,
        }

    async def get_search_volume_by_day(
        self,
        days: int = 30,
    ) -> list[dict]:
        """Get search volume grouped by day.

        Args:
            days: Number of days to look back

        Returns:
            List of dicts with date and search_count
        """
        since = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(
                func.date_trunc("day", SearchAnalytics.created_at).label("search_date"),
                func.count(SearchAnalytics.id).label("search_count"),
                func.count(func.distinct(SearchAnalytics.user_id)).label("unique_users"),
            )
            .where(SearchAnalytics.created_at >= since)
            .group_by(func.date_trunc("day", SearchAnalytics.created_at))
            .order_by(func.date_trunc("day", SearchAnalytics.created_at).asc())
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "date": row.search_date.isoformat() if row.search_date else None,
                "search_count": row.search_count,
                "unique_users": row.unique_users,
            }
            for row in rows
        ]
