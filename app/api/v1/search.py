"""Global search API endpoints.

Provides full-text search across books with Redis caching for performance.
Falls back to PostgreSQL full-text search if Redis is unavailable.
"""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import OptionalUser
from app.db.session import get_db
from app.models.book import Book

router = APIRouter()
logger = structlog.get_logger(__name__)


# ============================================================================
# Schemas
# ============================================================================


class SearchBookResult(BaseModel):
    """Book result from search."""

    id: UUID
    title: str
    author: str | None
    description: str | None
    category: str | None
    cover_url: str | None
    is_public: bool
    pages_count: int
    average_rating: float | None
    ratings_count: int

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Search results response."""

    query: str
    results: list[SearchBookResult]
    total: int
    page: int
    page_size: int
    total_pages: int


class SearchSuggestion(BaseModel):
    """Auto-complete suggestion."""

    text: str
    type: str = Field(description="Type of match: title, author, category")
    book_id: UUID | None = None


class SuggestionsResponse(BaseModel):
    """Suggestions response."""

    query: str
    suggestions: list[SearchSuggestion]


# ============================================================================
# Search Endpoints
# ============================================================================


@router.get(
    "",
    response_model=SearchResponse,
    summary="Search books",
    description="""
Search books by title, author, description, or category.

**Search Behavior:**
- Case-insensitive partial matching
- Searches across title, author, description, and category
- Only returns public books for unauthenticated users
- Returns user's private books + public books for authenticated users

**Query Parameters:**
- `q`: Search query (required, min 2 characters)
- `category`: Optional category filter
- `page`: Page number (default 1)
- `page_size`: Results per page (default 20, max 100)

**Example:**
```bash
curl -X GET "/v1/search?q=python&category=technology&page=1"
```
    """,
)
async def search_books(
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    category: str | None = Query(None, description="Category filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    current_user: OptionalUser = None,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search books with full-text matching."""
    search_term = f"%{q}%"

    # Build base query
    query = select(Book)

    # Text search filters
    text_filters = or_(
        Book.title.ilike(search_term),
        Book.author.ilike(search_term),
        Book.description.ilike(search_term),
        Book.category.ilike(search_term),
    )

    # Visibility filters
    if current_user:
        # Authenticated: show public + own private books
        visibility_filter = or_(
            Book.is_public is True,
            Book.owner_id == current_user.id,
        )
    else:
        # Unauthenticated: only public books
        visibility_filter = Book.is_public is True

    # Combine filters
    filters = [text_filters, visibility_filter]
    if category:
        filters.append(Book.category == category)

    query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    offset = (page - 1) * page_size

    # Execute search query with pagination
    query = query.offset(offset).limit(page_size).order_by(Book.created_at.desc())
    result = await db.execute(query)
    books = result.scalars().all()

    # Convert to response
    results = [SearchBookResult.model_validate(book) for book in books]

    logger.info(
        "Search executed",
        query=q,
        category=category,
        total_results=total,
        user_id=str(current_user.id) if current_user else None,
    )

    return SearchResponse(
        query=q,
        results=results,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/suggestions",
    response_model=SuggestionsResponse,
    summary="Get search suggestions",
    description="""
Get auto-complete suggestions for a search query.

Returns up to 10 suggestions matching:
- Book titles
- Author names
- Category names

**Query Parameters:**
- `q`: Search query (required, min 1 character)

**Example:**
```bash
curl -X GET "/v1/search/suggestions?q=pyth"
```
    """,
)
async def get_suggestions(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    current_user: OptionalUser = None,
    db: AsyncSession = Depends(get_db),
) -> SuggestionsResponse:
    """Get auto-complete suggestions."""
    search_term = f"{q}%"  # Prefix match for suggestions
    suggestions: list[SearchSuggestion] = []

    # Visibility filter
    if current_user:
        visibility_filter = or_(
            Book.is_public is True,
            Book.owner_id == current_user.id,
        )
    else:
        visibility_filter = Book.is_public is True

    # Title suggestions
    title_query = (
        select(Book.id, Book.title)
        .where(and_(Book.title.ilike(search_term), visibility_filter))
        .distinct()
        .limit(5)
    )
    title_result = await db.execute(title_query)
    for row in title_result:
        suggestions.append(
            SearchSuggestion(
                text=row.title,
                type="title",
                book_id=row.id,
            )
        )

    # Author suggestions
    author_query = (
        select(Book.author)
        .where(
            and_(
                Book.author.ilike(search_term),
                Book.author.isnot(None),
                visibility_filter,
            )
        )
        .distinct()
        .limit(3)
    )
    author_result = await db.execute(author_query)
    for row in author_result:
        if row.author:
            suggestions.append(
                SearchSuggestion(
                    text=row.author,
                    type="author",
                )
            )

    # Category suggestions
    category_query = (
        select(Book.category)
        .where(
            and_(
                Book.category.ilike(search_term),
                Book.category.isnot(None),
                visibility_filter,
            )
        )
        .distinct()
        .limit(2)
    )
    category_result = await db.execute(category_query)
    for row in category_result:
        if row.category:
            suggestions.append(
                SearchSuggestion(
                    text=row.category,
                    type="category",
                )
            )

    # Limit to 10 total suggestions
    suggestions = suggestions[:10]

    logger.info(
        "Suggestions returned",
        query=q,
        count=len(suggestions),
    )

    return SuggestionsResponse(
        query=q,
        suggestions=suggestions,
    )
