"""Reading progress repository."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Integer, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.progress import ReadingProgress


class ProgressRepository:
    """Repository for reading progress operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_progress(self, user_id: UUID, book_id: UUID) -> ReadingProgress | None:
        """Get user's progress for a specific book."""
        query = select(ReadingProgress).where(
            and_(
                ReadingProgress.user_id == user_id,
                ReadingProgress.book_id == book_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def upsert_progress(
        self,
        user_id: UUID,
        book_id: UUID,
        current_page: int,
        total_pages: int,
        reading_time_seconds: int = 0,
    ) -> ReadingProgress:
        """Create or update reading progress."""
        # Calculate progress percentage
        progress_percent = int((current_page / total_pages) * 100) if total_pages > 0 else 0

        # Check if progress exists
        existing = await self.get_progress(user_id, book_id)

        if existing:
            # Update existing progress
            existing.current_page = current_page
            existing.total_pages = total_pages
            existing.progress_percent = progress_percent
            existing.last_read_at = datetime.now(UTC)
            existing.reading_time_seconds += reading_time_seconds
            existing.updated_at = datetime.now(UTC)

            # Mark as completed if reached 100%
            if progress_percent >= 100 and existing.completed_at is None:
                existing.completed_at = datetime.now(UTC)

            await self.db.flush()
            return existing
        else:
            # Create new progress
            progress = ReadingProgress(
                user_id=user_id,
                book_id=book_id,
                current_page=current_page,
                total_pages=total_pages,
                progress_percent=progress_percent,
                reading_time_seconds=reading_time_seconds,
                started_at=datetime.now(UTC),
                last_read_at=datetime.now(UTC),
                completed_at=datetime.now(UTC) if progress_percent >= 100 else None,
            )
            self.db.add(progress)
            await self.db.flush()
            return progress

    async def get_recent_reads(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[tuple[ReadingProgress, Book]]:
        """Get user's recent reads with book info."""
        query = (
            select(ReadingProgress, Book)
            .join(Book, ReadingProgress.book_id == Book.id)
            .where(ReadingProgress.user_id == user_id)
            .order_by(ReadingProgress.last_read_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.all()

    async def calculate_streak(self, user_id: UUID) -> tuple[int, int]:
        """Calculate current and longest reading streak in days.

        Returns:
            Tuple of (current_streak, longest_streak)
        """
        # Get all reading dates for the user
        query = (
            select(func.date(ReadingProgress.last_read_at).label("read_date"))
            .where(ReadingProgress.user_id == user_id)
            .group_by(func.date(ReadingProgress.last_read_at))
            .order_by(func.date(ReadingProgress.last_read_at).desc())
        )
        result = await self.db.execute(query)
        read_dates = [row[0] for row in result.all()]

        if not read_dates:
            return (0, 0)

        # Calculate current streak (consecutive days from today backwards)
        today = datetime.now(UTC).date()
        current_streak = 0

        for i, read_date in enumerate(read_dates):
            expected_date = today - timedelta(days=i)
            if read_date == expected_date:
                current_streak += 1
            else:
                break

        # Calculate longest streak
        longest_streak = 0
        temp_streak = 1

        for i in range(1, len(read_dates)):
            prev_date = read_dates[i - 1]
            curr_date = read_dates[i]

            # Check if consecutive days
            if (prev_date - curr_date).days == 1:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1

        longest_streak = max(longest_streak, temp_streak, current_streak)

        return (current_streak, longest_streak)

    async def get_stats(self, user_id: UUID) -> dict:
        """Get user's reading statistics."""
        # Total books started and completed
        query = (
            select(
                func.count(ReadingProgress.id).label("total_started"),
                func.sum(
                    func.cast(ReadingProgress.completed_at.isnot(None), Integer)
                ).label("total_completed"),
                func.sum(ReadingProgress.reading_time_seconds).label("total_time"),
            )
            .where(ReadingProgress.user_id == user_id)
        )
        result = await self.db.execute(query)
        row = result.one()

        total_started = row.total_started or 0
        total_completed = row.total_completed or 0
        total_time = row.total_time or 0

        # Calculate streaks
        current_streak, longest_streak = await self.calculate_streak(user_id)

        # Calculate average pages per day (last 30 days)
        thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
        pages_query = (
            select(func.count(ReadingProgress.id).label("updates"))
            .where(
                and_(
                    ReadingProgress.user_id == user_id,
                    ReadingProgress.last_read_at >= thirty_days_ago,
                )
            )
        )
        pages_result = await self.db.execute(pages_query)
        updates_last_30_days = pages_result.scalar() or 0
        avg_pages_per_day = updates_last_30_days / 30.0 if updates_last_30_days > 0 else 0

        # Format reading time
        hours = total_time // 3600
        minutes = (total_time % 3600) // 60
        time_formatted = f"{hours}h {minutes}m"

        return {
            "total_books_started": total_started,
            "total_books_completed": total_completed,
            "total_reading_time_seconds": total_time,
            "total_reading_time_formatted": time_formatted,
            "current_streak_days": current_streak,
            "longest_streak_days": longest_streak,
            "avg_pages_per_day": round(avg_pages_per_day, 1),
        }

    async def delete_progress(self, user_id: UUID, book_id: UUID) -> bool:
        """Delete user's progress for a book."""
        progress = await self.get_progress(user_id, book_id)
        if progress:
            await self.db.delete(progress)
            await self.db.flush()
            return True
        return False
