"""Annotations API endpoints for bookmarks, highlights, and notes."""

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.v1.deps import CurrentUser, DBSession
from app.schemas.annotation import (
    BookmarkCreate,
    BookmarkResponse,
    HighlightCreate,
    HighlightResponse,
    HighlightUpdate,
    NoteCreate,
    NoteResponse,
    NoteUpdate,
)
from app.services.annotation_service import AnnotationService

router = APIRouter()


# Bookmark endpoints
@router.get(
    "/books/{book_id}/bookmarks",
    response_model=list[BookmarkResponse],
    summary="Get bookmarks",
    description="Get all your bookmarks for a book.",
)
async def get_bookmarks(
    book_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> list[BookmarkResponse]:
    """Get bookmarks for a book."""
    service = AnnotationService(db)
    return await service.get_bookmarks(current_user.id, book_id)


@router.post(
    "/books/{book_id}/bookmarks",
    response_model=BookmarkResponse,
    status_code=201,
    summary="Add bookmark",
    description="Add a bookmark to a specific page.",
)
async def create_bookmark(
    book_id: UUID,
    data: BookmarkCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> BookmarkResponse:
    """Create a bookmark."""
    service = AnnotationService(db)
    return await service.create_bookmark(current_user.id, book_id, data)


@router.delete(
    "/books/{book_id}/bookmarks/{page_number}",
    status_code=204,
    summary="Delete bookmark",
    description="Remove a bookmark from a page.",
)
async def delete_bookmark(
    book_id: UUID,
    page_number: int,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Delete a bookmark."""
    service = AnnotationService(db)
    await service.delete_bookmark(current_user.id, book_id, page_number)


# Highlight endpoints
@router.get(
    "/books/{book_id}/highlights",
    response_model=list[HighlightResponse],
    summary="Get highlights",
    description="Get all your highlights for a book, optionally filtered by page.",
)
async def get_highlights(
    book_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
    page_number: int | None = Query(None, ge=1, description="Filter by page number"),
) -> list[HighlightResponse]:
    """Get highlights for a book."""
    service = AnnotationService(db)
    return await service.get_highlights(current_user.id, book_id, page_number)


@router.post(
    "/books/{book_id}/highlights",
    response_model=HighlightResponse,
    status_code=201,
    summary="Add highlight",
    description="Highlight text on a page.",
)
async def create_highlight(
    book_id: UUID,
    data: HighlightCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> HighlightResponse:
    """Create a highlight."""
    service = AnnotationService(db)
    return await service.create_highlight(current_user.id, book_id, data)


@router.put(
    "/books/{book_id}/highlights/{highlight_id}",
    response_model=HighlightResponse,
    summary="Update highlight",
    description="Update a highlight's note.",
)
async def update_highlight(
    book_id: UUID,
    highlight_id: UUID,
    data: HighlightUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> HighlightResponse:
    """Update a highlight."""
    service = AnnotationService(db)
    return await service.update_highlight(highlight_id, current_user.id, data)


@router.delete(
    "/books/{book_id}/highlights/{highlight_id}",
    status_code=204,
    summary="Delete highlight",
    description="Remove a highlight.",
)
async def delete_highlight(
    book_id: UUID,
    highlight_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Delete a highlight."""
    service = AnnotationService(db)
    await service.delete_highlight(highlight_id, current_user.id)


# Note endpoints
@router.get(
    "/books/{book_id}/notes",
    response_model=list[NoteResponse],
    summary="Get notes",
    description="Get all your notes for a book.",
)
async def get_notes(
    book_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> list[NoteResponse]:
    """Get notes for a book."""
    service = AnnotationService(db)
    return await service.get_notes(current_user.id, book_id)


@router.post(
    "/books/{book_id}/notes",
    response_model=NoteResponse,
    status_code=201,
    summary="Add note",
    description="Add a note to a page or the entire book.",
)
async def create_note(
    book_id: UUID,
    data: NoteCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> NoteResponse:
    """Create a note."""
    service = AnnotationService(db)
    return await service.create_note(current_user.id, book_id, data)


@router.put(
    "/books/{book_id}/notes/{note_id}",
    response_model=NoteResponse,
    summary="Update note",
    description="Update a note's content or color.",
)
async def update_note(
    book_id: UUID,
    note_id: UUID,
    data: NoteUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> NoteResponse:
    """Update a note."""
    service = AnnotationService(db)
    return await service.update_note(note_id, current_user.id, data)


@router.delete(
    "/books/{book_id}/notes/{note_id}",
    status_code=204,
    summary="Delete note",
    description="Remove a note.",
)
async def delete_note(
    book_id: UUID,
    note_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    """Delete a note."""
    service = AnnotationService(db)
    await service.delete_note(note_id, current_user.id)
