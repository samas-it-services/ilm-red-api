"""Reading progress service."""

from uuid import UUID

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.book_repo import BookRepository
from app.repositories.progress_repo import ProgressRepository
from app.schemas.progress import ProgressResponse, ProgressUpdate, ReadingStats, RecentRead

logger = structlog.get_logger(__name__)


class ProgressService:
    """Service for reading progress operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.progress_repo = ProgressRepository(db)
        self.book_repo = BookRepository(db)

    async def get_progress(
        self,
        user_id: UUID,
        book_id: UUID,
    ) -> ProgressResponse | None:
        """Get user's progress for a book."""
        progress = await self.progress_repo.get_progress(user_id, book_id)

        if not progress:
            return None

        return ProgressResponse.model_validate(progress)

    async def update_progress(
        self,
        user_id: UUID,
        book_id: UUID,
        updates: ProgressUpdate,
    ) -> ProgressResponse:
        """Update user's reading progress."""
        # Verify book exists
        book = await self.book_repo.get_by_id(book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        # Update progress
        progress = await self.progress_repo.upsert_progress(
            user_id=user_id,
            book_id=book_id,
            current_page=updates.current_page,
            total_pages=updates.total_pages,
            reading_time_seconds=updates.reading_time_seconds,
        )

        await self.db.commit()

        logger.info(
            "Progress updated",
            user_id=str(user_id),
            book_id=str(book_id),
            progress=progress.progress_percent,
        )

        return ProgressResponse.model_validate(progress)

    async def get_recent_reads(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[RecentRead]:
        """Get user's recent reads with book info."""
        reads = await self.progress_repo.get_recent_reads(user_id, limit)

        return [
            RecentRead(
                book_id=progress.book_id,
                book_title=book.title,
                book_author=book.author,
                book_cover_url=book.cover_url,
                current_page=progress.current_page,
                total_pages=progress.total_pages,
                progress_percent=progress.progress_percent,
                last_read_at=progress.last_read_at,
            )
            for progress, book in reads
        ]

    async def get_stats(self, user_id: UUID) -> ReadingStats:
        """Get user's reading statistics."""
        stats = await self.progress_repo.get_stats(user_id)
        return ReadingStats(**stats)

    async def delete_progress(
        self,
        user_id: UUID,
        book_id: UUID,
    ) -> None:
        """Delete user's progress for a book."""
        deleted = await self.progress_repo.delete_progress(user_id, book_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No progress found for this book",
            )

        await self.db.commit()

        logger.info(
            "Progress deleted",
            user_id=str(user_id),
            book_id=str(book_id),
        )
