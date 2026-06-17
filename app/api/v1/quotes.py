"""Quotes API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.api.v1.deps import AdminUser, DBSession, OptionalUser
from app.schemas.quote import (
    QuoteCreate,
    QuoteListResponse,
    QuoteResponse,
    QuoteUpdate,
)
from app.services.quote_service import QuoteService

router = APIRouter()


# Public endpoints


@router.get(
    "",
    response_model=QuoteListResponse,
    summary="List quotes",
    description="List quotes with optional filtering and pagination.",
)
async def list_quotes(
    db: DBSession,
    category: str | None = Query(None, description="Filter by category"),
    is_featured: bool | None = Query(None, description="Filter by featured status"),
    q: str | None = Query(None, description="Search in quote text"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> QuoteListResponse:
    """List active quotes with optional filtering.

    Public endpoint - no authentication required.
    Only active quotes are returned for non-admin users.
    """
    service = QuoteService(db)
    return await service.list_quotes(
        category=category,
        is_featured=is_featured,
        is_active=True,
        search_query=q,
        page=page,
        limit=limit,
    )


@router.get(
    "/daily",
    response_model=QuoteResponse,
    summary="Get daily quote",
    description="Get the quote of the day.",
)
async def get_daily_quote(
    request: Request,
    db: DBSession,
    current_user: OptionalUser,
) -> QuoteResponse:
    """Get the daily quote.

    Returns a consistent quote for the day. If a quote is assigned
    to today's date via display_date, that quote is returned.
    Otherwise, a deterministic selection is made based on the date.
    """
    service = QuoteService(db)
    return await service.get_daily_quote(
        user_id=current_user.id if current_user else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/random",
    response_model=QuoteResponse,
    summary="Get random quote",
    description="Get a random active quote.",
)
async def get_random_quote(
    request: Request,
    db: DBSession,
    current_user: OptionalUser,
) -> QuoteResponse:
    """Get a random active quote.

    Returns a randomly selected active quote from the database.
    Each call may return a different quote.
    """
    service = QuoteService(db)
    return await service.get_random_quote(
        user_id=current_user.id if current_user else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


# Admin endpoints


@router.post(
    "",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create quote (admin)",
    description="Create a new quote. Admin only.",
)
async def create_quote(
    data: QuoteCreate,
    db: DBSession,
    admin_user: AdminUser,
) -> QuoteResponse:
    """Create a new quote.

    - **text**: The quote text (required)
    - **author**: Who said or wrote it
    - **source**: Where it comes from (book, hadith collection, etc.)
    - **category**: Category for grouping (e.g., hadith, wisdom, motivation)
    - **tags**: Searchable tags
    - **is_featured**: Whether to feature this quote prominently
    - **display_date**: Specific date to display this quote as "quote of the day"
    """
    service = QuoteService(db)
    return await service.create_quote(admin_user, data)


@router.put(
    "/{quote_id}",
    response_model=QuoteResponse,
    summary="Update quote (admin)",
    description="Update an existing quote. Admin only.",
)
async def update_quote(
    quote_id: UUID,
    data: QuoteUpdate,
    db: DBSession,
    admin_user: AdminUser,
) -> QuoteResponse:
    """Update a quote.

    Only the provided fields will be updated.
    """
    service = QuoteService(db)
    return await service.update_quote(quote_id, data)


@router.delete(
    "/{quote_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete quote (admin)",
    description="Permanently delete a quote. Admin only.",
)
async def delete_quote(
    quote_id: UUID,
    db: DBSession,
    admin_user: AdminUser,
) -> None:
    """Permanently delete a quote and all its view records."""
    service = QuoteService(db)
    await service.delete_quote(quote_id)
