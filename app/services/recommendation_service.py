"""Recommendation service for personalized book suggestions."""

from uuid import UUID

import structlog
from sqlalchemy import and_, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.progress import ReadingProgress
from app.schemas.recommendation import RecommendedBook

logger = structlog.get_logger(__name__)


class RecommendationService:
    """Service for generating personalized book recommendations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_recommendations(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[RecommendedBook]:
        """Get personalized book recommendations for a user.

        Algorithm:
        1. Get categories from user's recent reads (40% weight)
        2. Top-rated books user hasn't read (30% weight)
        3. Recently added books in relevant categories (30% weight)
        """
        # Get user's reading history to determine preferences
        reading_history_query = (
            select(Book.category)
            .join(ReadingProgress, ReadingProgress.book_id == Book.id)
            .where(ReadingProgress.user_id == user_id)
            .limit(10)
        )
        result = await self.db.execute(reading_history_query)
        user_categories = [row[0] for row in result.all()]

        # Get books user has already read
        read_books_query = select(ReadingProgress.book_id).where(
            ReadingProgress.user_id == user_id
        )
        result = await self.db.execute(read_books_query)
        read_book_ids = [row[0] for row in result.all()]

        recommendations = []

        # Strategy 1: Books in same categories as user's reads (if we have history)
        if user_categories:
            category_books_query = (
                select(Book)
                .where(
                    and_(
                        Book.category.in_(user_categories),
                        Book.visibility == "public",
                        Book.status == "ready",
                        Book.deleted_at.is_(None),
                        not_(Book.id.in_(read_book_ids)) if read_book_ids else True,
                    )
                )
                .order_by(
                    # Order by rating, then by created_at
                    Book.stats["rating_avg"].as_float().desc(),
                    Book.created_at.desc(),
                )
                .limit(limit // 2)
            )
            result = await self.db.execute(category_books_query)
            category_books = result.scalars().all()

            for book in category_books:
                reason = f"Based on your interest in {book.category}"
                recommendations.append(
                    RecommendedBook(
                        book_id=book.id,
                        title=book.title,
                        author=book.author,
                        category=book.category,
                        cover_url=book.cover_url,
                        average_rating=book.stats.get("rating_avg", 0.0),
                        ratings_count=book.stats.get("rating_count", 0),
                        reason=reason,
                    )
                )

        # Strategy 2: Top-rated books user hasn't read
        remaining = limit - len(recommendations)
        if remaining > 0:
            top_rated_query = (
                select(Book)
                .where(
                    and_(
                        Book.visibility == "public",
                        Book.status == "ready",
                        Book.deleted_at.is_(None),
                        Book.stats["rating_count"].as_integer() >= 3,  # At least 3 ratings
                        not_(Book.id.in_(read_book_ids)) if read_book_ids else True,
                        # Exclude books already recommended
                        not_(Book.id.in_([r.book_id for r in recommendations]))
                        if recommendations
                        else True,
                    )
                )
                .order_by(
                    Book.stats["rating_avg"].as_float().desc(),
                    Book.stats["rating_count"].as_integer().desc(),
                )
                .limit(remaining)
            )
            result = await self.db.execute(top_rated_query)
            top_books = result.scalars().all()

            for book in top_books:
                avg_rating = book.stats.get("rating_avg", 0.0)
                reason = f"Highly rated ({avg_rating:.1f}/5.0)"
                recommendations.append(
                    RecommendedBook(
                        book_id=book.id,
                        title=book.title,
                        author=book.author,
                        category=book.category,
                        cover_url=book.cover_url,
                        average_rating=avg_rating,
                        ratings_count=book.stats.get("rating_count", 0),
                        reason=reason,
                    )
                )

        logger.info(
            "Generated recommendations",
            user_id=str(user_id),
            count=len(recommendations),
            categories=user_categories,
        )

        return recommendations[:limit]
