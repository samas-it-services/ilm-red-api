"""Global search API endpoints.

Provides full-text search across books with Redis caching for performance.
Falls back to PostgreSQL full-text search if Redis is unavailable.
"""

import hashlib
import json
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import OptionalUser
from app.cache.redis_client import RedisCache
from app.db.session import get_db
from app.models.book import Book

router = APIRouter()
logger = structlog.get_logger(__name__)

# Cache TTLs
SEARCH_CACHE_TTL = 300  # 5 minutes for search results
SUGGESTIONS_CACHE_TTL = 600  # 10 minutes for suggestions


def _build_public_search_cache_key(q: str, category: str | None) -> str:
    """Build cache key for public books search (always cached)."""
    key_data = json.dumps({
        "q": q.lower(),
        "category": category,
        "public": True,
    }, sort_keys=True)
    key_hash = hashlib.md5(key_data.encode()).hexdigest()
    return f"search:public:{key_hash}"


def _build_public_suggestions_cache_key(q: str) -> str:
    """Build cache key for public book suggestions (always cached)."""
    key_hash = hashlib.md5(q.lower().encode()).hexdigest()
    return f"search:suggestions:public:{key_hash}"


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
    """Search books with full-text matching.

    Uses a two-tier caching strategy:
    1. Public books are always cached (5 min TTL)
    2. For authenticated users, private books are queried fresh and merged
    """
    search_term = f"%{q}%"
    cache_key = _build_public_search_cache_key(q, category)
    public_books: list[SearchBookResult] = []
    private_books: list[SearchBookResult] = []
    cache_hit = False

    # Text search filters (used for both public and private queries)
    text_filters = or_(
        Book.title.ilike(search_term),
        Book.author.ilike(search_term),
        Book.description.ilike(search_term),
        Book.category.ilike(search_term),
    )

    # Step 1: Try to get public books from cache
    try:
        redis = await RedisCache.get_client()
        cached_result = await redis.get(cache_key)
        if cached_result:
            public_books = [SearchBookResult.model_validate(b) for b in json.loads(cached_result)]
            cache_hit = True
            logger.debug("search_public_cache_hit", query=q, count=len(public_books))
    except Exception as e:
        logger.debug("search_cache_error", error=str(e))

    # Step 2: If cache miss, query public books from DB
    if not cache_hit:
        public_filters = [text_filters, Book.is_public == True]  # noqa: E712
        if category:
            public_filters.append(Book.category == category)

        public_query = (
            select(Book)
            .where(and_(*public_filters))
            .order_by(Book.created_at.desc())
            .limit(500)  # Cache up to 500 public results
        )
        result = await db.execute(public_query)
        public_books = [SearchBookResult.model_validate(b) for b in result.scalars().all()]

        # Cache the public results
        try:
            redis = await RedisCache.get_client()
            serialized = json.dumps([b.model_dump(mode="json") for b in public_books])
            await redis.setex(cache_key, SEARCH_CACHE_TTL, serialized)
            logger.debug("search_public_cached", query=q, count=len(public_books), ttl=SEARCH_CACHE_TTL)
        except Exception as e:
            logger.debug("search_cache_save_failed", error=str(e))

    # Step 3: For authenticated users, query their private books (uncached)
    if current_user:
        private_filters = [
            text_filters,
            Book.is_public == False,  # noqa: E712
            Book.owner_id == current_user.id,
        ]
        if category:
            private_filters.append(Book.category == category)

        private_query = (
            select(Book)
            .where(and_(*private_filters))
            .order_by(Book.created_at.desc())
            .limit(100)  # Reasonable limit for private books
        )
        result = await db.execute(private_query)
        private_books = [SearchBookResult.model_validate(b) for b in result.scalars().all()]
        logger.debug("search_private_queried", query=q, user_id=str(current_user.id), count=len(private_books))

    # Step 4: Merge results (private books first, then public)
    all_books = private_books + public_books

    # Remove duplicates (shouldn't happen but safety check)
    seen_ids = set()
    unique_books = []
    for book in all_books:
        if book.id not in seen_ids:
            seen_ids.add(book.id)
            unique_books.append(book)

    # Paginate the merged results
    total = len(unique_books)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    offset = (page - 1) * page_size
    paginated_results = unique_books[offset : offset + page_size]

    logger.info(
        "Search executed",
        query=q,
        category=category,
        total_results=total,
        public_count=len(public_books),
        private_count=len(private_books),
        cache_hit=cache_hit,
        user_id=str(current_user.id) if current_user else None,
    )

    return SearchResponse(
        query=q,
        results=paginated_results,
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
    """Get auto-complete suggestions.

    Uses two-tier caching:
    1. Public book suggestions are always cached (10 min TTL)
    2. For authenticated users, private book suggestions are queried fresh and merged
    """
    search_term = f"{q}%"  # Prefix match for suggestions
    cache_key = _build_public_suggestions_cache_key(q)
    public_suggestions: list[SearchSuggestion] = []
    private_suggestions: list[SearchSuggestion] = []
    cache_hit = False

    # Step 1: Try to get public suggestions from cache
    try:
        redis = await RedisCache.get_client()
        cached_result = await redis.get(cache_key)
        if cached_result:
            public_suggestions = [SearchSuggestion.model_validate(s) for s in json.loads(cached_result)]
            cache_hit = True
            logger.debug("suggestions_public_cache_hit", query=q, count=len(public_suggestions))
    except Exception as e:
        logger.debug("suggestions_cache_error", error=str(e))

    # Step 2: If cache miss, query public suggestions from DB
    if not cache_hit:
        public_filter = Book.is_public == True  # noqa: E712

        # Title suggestions (public)
        title_query = (
            select(Book.id, Book.title)
            .where(and_(Book.title.ilike(search_term), public_filter))
            .distinct()
            .limit(5)
        )
        title_result = await db.execute(title_query)
        for row in title_result:
            public_suggestions.append(SearchSuggestion(text=row.title, type="title", book_id=row.id))

        # Author suggestions (public)
        author_query = (
            select(Book.author)
            .where(and_(Book.author.ilike(search_term), Book.author.isnot(None), public_filter))
            .distinct()
            .limit(3)
        )
        author_result = await db.execute(author_query)
        for row in author_result:
            if row.author:
                public_suggestions.append(SearchSuggestion(text=row.author, type="author"))

        # Category suggestions (public)
        category_query = (
            select(Book.category)
            .where(and_(Book.category.ilike(search_term), Book.category.isnot(None), public_filter))
            .distinct()
            .limit(2)
        )
        category_result = await db.execute(category_query)
        for row in category_result:
            if row.category:
                public_suggestions.append(SearchSuggestion(text=row.category, type="category"))

        # Cache the public suggestions
        try:
            redis = await RedisCache.get_client()
            serialized = json.dumps([s.model_dump(mode="json") for s in public_suggestions])
            await redis.setex(cache_key, SUGGESTIONS_CACHE_TTL, serialized)
            logger.debug("suggestions_public_cached", query=q, count=len(public_suggestions), ttl=SUGGESTIONS_CACHE_TTL)
        except Exception as e:
            logger.debug("suggestions_cache_save_failed", error=str(e))

    # Step 3: For authenticated users, query their private book suggestions (uncached)
    if current_user:
        private_filter = and_(Book.is_public == False, Book.owner_id == current_user.id)  # noqa: E712

        # Title suggestions (private)
        private_title_query = (
            select(Book.id, Book.title)
            .where(and_(Book.title.ilike(search_term), private_filter))
            .distinct()
            .limit(3)
        )
        private_title_result = await db.execute(private_title_query)
        for row in private_title_result:
            private_suggestions.append(SearchSuggestion(text=row.title, type="title", book_id=row.id))

        # Author suggestions (private)
        private_author_query = (
            select(Book.author)
            .where(and_(Book.author.ilike(search_term), Book.author.isnot(None), private_filter))
            .distinct()
            .limit(2)
        )
        private_author_result = await db.execute(private_author_query)
        for row in private_author_result:
            if row.author:
                private_suggestions.append(SearchSuggestion(text=row.author, type="author"))

        logger.debug("suggestions_private_queried", query=q, user_id=str(current_user.id), count=len(private_suggestions))

    # Step 4: Merge suggestions (private first, then public), deduplicate by text
    all_suggestions = private_suggestions + public_suggestions
    seen_texts = set()
    unique_suggestions = []
    for s in all_suggestions:
        if s.text.lower() not in seen_texts:
            seen_texts.add(s.text.lower())
            unique_suggestions.append(s)

    # Limit to 10 total suggestions
    suggestions = unique_suggestions[:10]

    logger.info(
        "Suggestions returned",
        query=q,
        count=len(suggestions),
        public_count=len(public_suggestions),
        private_count=len(private_suggestions),
        cache_hit=cache_hit,
    )

    return SuggestionsResponse(query=q, suggestions=suggestions)
