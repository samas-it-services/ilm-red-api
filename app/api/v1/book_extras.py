"""Book Extra API endpoints."""

import uuid

from fastapi import APIRouter, Query, status

from app.api.v1.deps import CurrentUser, DBSession, OptionalUser
from app.schemas.book_extra import (
    BookExtraCreate,
    BookExtraListResponse,
    BookExtraResponse,
    BookExtraUpdate,
)
from app.services.book_extra_service import BookExtraService

router = APIRouter()


@router.post(
    "/books/{book_id}/extras",
    response_model=BookExtraResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new book extra",
    description="Add extra content (flashcard, quiz, etc.) to a book. Only owner can add extras.",
)
async def create_book_extra(
    book_id: uuid.UUID,
    extra_data: BookExtraCreate,
    user: CurrentUser,
    db: DBSession,
) -> BookExtraResponse:
    """Create a new book extra."""
    service = BookExtraService(db)
    return await service.create_extra(book_id, extra_data, user)


@router.get(
    "/books/{book_id}/extras",
    response_model=BookExtraListResponse,
    summary="List extras for a book",
    description="Get list of extras for a specific book.",
)
async def list_book_extras(
    book_id: uuid.UUID,
    db: DBSession,
    user: OptionalUser,
    type: str | None = Query(None, description="Filter by extra type"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> BookExtraListResponse:
    """List book extras."""
    service = BookExtraService(db)
    return await service.list_extras(book_id, user, type, page, limit)


@router.get(
    "/extras/{extra_id}",
    response_model=BookExtraResponse,
    summary="Get a book extra",
    description="Get detailed information about a specific book extra.",
)
async def get_book_extra(
    extra_id: uuid.UUID,
    db: DBSession,
    user: OptionalUser,
) -> BookExtraResponse:
    """Get book extra by ID."""
    service = BookExtraService(db)
    return await service.get_extra(extra_id, user)


@router.patch(
    "/extras/{extra_id}",
    response_model=BookExtraResponse,
    summary="Update a book extra",
    description="Update book extra content. Only creator can update.",
)
async def update_book_extra(
    extra_id: uuid.UUID,
    updates: BookExtraUpdate,
    user: CurrentUser,
    db: DBSession,
) -> BookExtraResponse:
    """Update a book extra."""
    service = BookExtraService(db)
    return await service.update_extra(extra_id, updates, user)


@router.delete(
    "/extras/{extra_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a book extra",
    description="Delete a book extra. Only creator can delete.",
)
async def delete_book_extra(
    extra_id: uuid.UUID,
    user: CurrentUser,
    db: DBSession,
) -> None:
    """Delete a book extra."""
    service = BookExtraService(db)
    await service.delete_extra(extra_id, user)
