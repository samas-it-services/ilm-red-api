"""Reading progress API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.v1.deps import CurrentUser, DBSession
from app.schemas.progress import ProgressResponse, ProgressUpdate, ReadingStats, RecentRead
from app.services.progress_service import ProgressService

router = APIRouter()


@router.get(
    "/books/{book_id}/progress",
    response_model=ProgressResponse | None,
    summary="Get reading progress",
    description="Get your reading progress for a specific book.",
)
async def get_progress(
    book_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ProgressResponse | None:
    """Get user's progress for a book."""
    service = ProgressService(db)
    return await service.get_progress(current_user.id, book_id)


@router.put(
    "/books/{book_id}/progress",
    response_model=ProgressResponse,
    summary="Update reading progress",
    description="Update your reading progress for a book.",
)
async def update_progress(
    book_id: UUID,
    updates: ProgressUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> ProgressResponse:
    """Update user's reading progress."""
    service = ProgressService(db)
    return await service.update_progress(current_user.id, book_id, updates)


@router.delete(
    "/books/{book_id}/progress",
    status_code=204,
    summary="Reset reading progress",
    description="Delete your reading progress for a book.",
)
async def delete_progress(
    book_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Delete user's progress for a book."""
    service = ProgressService(db)
    await service.delete_progress(current_user.id, book_id)


@router.get(
    "/progress/recent",
    response_model=list[RecentRead],
    summary="Get recent reads",
    description="Get your recently read books with progress.",
)
async def get_recent_reads(
    current_user: CurrentUser,
    db: DBSession,
    limit: int = Query(10, ge=1, le=50, description="Number of recent reads to return"),
) -> list[RecentRead]:
    """Get user's recent reads."""
    service = ProgressService(db)
    return await service.get_recent_reads(current_user.id, limit)


@router.get(
    "/progress/stats",
    response_model=ReadingStats,
    summary="Get reading statistics",
    description="Get your reading statistics including streak and reading time.",
)
async def get_reading_stats(
    current_user: CurrentUser,
    db: DBSession,
) -> ReadingStats:
    """Get user's reading statistics."""
    service = ProgressService(db)
    return await service.get_stats(current_user.id)
