"""Book API endpoints."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.api.v1.deps import CurrentUser, DBSession, OptionalUser

# Allowed sort fields for defense-in-depth
ALLOWED_SORT_FIELDS = {"created_at", "updated_at", "title", "author", "category"}
from app.schemas.book import (
    BookCategory,
    BookCreate,
    BookFilters,
    BookListResponse,
    BookResponse,
    BookStatus,
    BookUpdate,
    BookUploadResponse,
    DownloadUrlResponse,
    Visibility,
)
from app.schemas.rating import (
    RatingCreate,
    RatingListResponse,
    RatingResponse,
)
from app.services.book_service import BookService

router = APIRouter()


# Book CRUD endpoints


@router.post(
    "",
    response_model=BookUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new book",
    description="Upload a new book file (PDF, EPUB, or TXT) with metadata.",
)
async def upload_book(
    db: DBSession,
    current_user: CurrentUser,
    file: UploadFile = File(..., description="Book file (PDF, EPUB, or TXT)"),
    title: str = Form(..., min_length=1, max_length=500, description="Book title"),
    author: str | None = Form(None, max_length=255, description="Book author"),
    description: str | None = Form(None, max_length=5000, description="Book description"),
    category: BookCategory = Form(BookCategory.OTHER, description="Book category"),
    visibility: Visibility = Form(Visibility.PRIVATE, description="Visibility setting"),
    language: str = Form("en", max_length=10, description="Language code (e.g., 'en', 'ar')"),
    isbn: str | None = Form(None, max_length=20, description="ISBN (optional)"),
) -> BookUploadResponse:
    """Upload a new book.

    - **file**: Book file (supported formats: PDF, EPUB, TXT, max 500MB)
    - **title**: Book title (required)
    - **author**: Author name (optional)
    - **description**: Book description (optional)
    - **category**: Book category (default: other)
    - **visibility**: public, private, or friends (default: private)
    - **language**: Language code (default: en)
    - **isbn**: ISBN number (optional)

    The book will be uploaded and queued for processing.
    """
    service = BookService(db)

    metadata = BookCreate(
        title=title,
        author=author,
        description=description,
        category=category,
        visibility=visibility,
        language=language,
        isbn=isbn,
    )

    return await service.upload_book(file, metadata, current_user)


@router.get(
    "",
    response_model=BookListResponse,
    summary="List books",
    description="List books with optional filtering and pagination.",
)
async def list_books(
    db: DBSession,
    current_user: OptionalUser,
    q: str | None = Query(None, description="Search in title and author"),
    category: BookCategory | None = Query(None, description="Filter by category"),
    visibility: Visibility | None = Query(None, description="Filter by visibility (own books only)"),
    status: BookStatus | None = Query(None, description="Filter by processing status"),
    owner_id: UUID | None = Query(None, description="Filter by owner ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
) -> BookListResponse:
    """List books with filtering and pagination.

    Public books are visible to everyone.
    Private books are only visible to their owners.
    """
    # Validate sort field to prevent SQL injection
    if sort_by not in ALLOWED_SORT_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field. Allowed: {', '.join(sorted(ALLOWED_SORT_FIELDS))}",
        )

    service = BookService(db)

    filters = BookFilters(
        q=q,
        category=category,
        visibility=visibility,
        owner_id=owner_id,
        status=status,
    )

    return await service.list_books(
        user=current_user,
        filters=filters,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{book_id}",
    response_model=BookResponse,
    summary="Get book details",
    description="Get detailed information about a specific book.",
)
async def get_book(
    book_id: UUID,
    db: DBSession,
    current_user: OptionalUser,
) -> BookResponse:
    """Get book details by ID.

    Returns full book information including stats and download URL.
    """
    service = BookService(db)
    return await service.get_book(book_id, current_user)


@router.patch(
    "/{book_id}",
    response_model=BookResponse,
    summary="Update book",
    description="Update book metadata. Only the owner can update a book.",
)
async def update_book(
    book_id: UUID,
    updates: BookUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> BookResponse:
    """Update book metadata.

    Only the book owner can update the book.
    """
    service = BookService(db)
    return await service.update_book(book_id, updates, current_user)


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete book",
    description="Soft delete a book. Only the owner can delete a book.",
)
async def delete_book(
    book_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Delete a book (soft delete).

    Only the book owner can delete the book.
    The book will be marked as deleted but not permanently removed.
    """
    service = BookService(db)
    await service.delete_book(book_id, current_user)


@router.get(
    "/{book_id}/download",
    response_model=DownloadUrlResponse,
    summary="Get download URL",
    description="Get a signed URL for downloading the book file.",
)
async def get_download_url(
    book_id: UUID,
    db: DBSession,
    current_user: OptionalUser,
) -> DownloadUrlResponse:
    """Get a signed download URL for the book.

    The URL is valid for 1 hour.
    Only accessible for books with 'ready' status.
    """
    service = BookService(db)
    return await service.get_download_url(book_id, current_user)


# Rating endpoints


@router.post(
    "/{book_id}/ratings",
    response_model=RatingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Rate a book",
    description="Add or update your rating for a book.",
)
async def add_rating(
    book_id: UUID,
    rating: RatingCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> RatingResponse:
    """Add or update your rating for a book.

    - Rating must be 1-5 stars
    - Optional review text (max 2000 characters)
    - You cannot rate your own books
    - Updating will replace your previous rating
    """
    service = BookService(db)
    return await service.add_rating(book_id, rating, current_user)


@router.get(
    "/{book_id}/ratings",
    response_model=RatingListResponse,
    summary="Get book ratings",
    description="Get all ratings for a book with pagination.",
)
async def get_ratings(
    book_id: UUID,
    db: DBSession,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> RatingListResponse:
    """Get all ratings for a book.

    Includes the reviewer's information and review text.
    """
    service = BookService(db)
    return await service.get_ratings(book_id, page, limit)


@router.delete(
    "/{book_id}/ratings",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete your rating",
    description="Remove your rating from a book.",
)
async def delete_rating(
    book_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Delete your rating for a book."""
    service = BookService(db)
    await service.delete_rating(book_id, current_user)


# Favorite endpoints


@router.post(
    "/{book_id}/favorite",
    status_code=status.HTTP_201_CREATED,
    summary="Add to favorites",
    description="Add a book to your favorites.",
)
async def add_favorite(
    book_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Add a book to your favorites list."""
    service = BookService(db)
    await service.add_favorite(book_id, current_user)
    return {"message": "Book added to favorites"}


@router.delete(
    "/{book_id}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove from favorites",
    description="Remove a book from your favorites.",
)
async def remove_favorite(
    book_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Remove a book from your favorites list."""
    service = BookService(db)
    await service.remove_favorite(book_id, current_user)


@router.get(
    "/me/favorites",
    response_model=BookListResponse,
    summary="Get my favorites",
    description="Get your list of favorite books.",
)
async def get_my_favorites(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> BookListResponse:
    """Get your list of favorite books."""
    service = BookService(db)
    return await service.get_favorites(current_user, page, limit)


# ============= Page Endpoints =============
# Page-first reading: View book pages as images

from app.config import settings
from app.schemas.page import (
    PageDetailResponse,
    PageGenerationRequest,
    PageGenerationResponse,
    PageListResponse,
)
from app.services.embedding_service import create_embedding_service
from app.services.page_service import (
    BookNotFoundError,
    PageService,
    TooManyPagesError,
    UnsupportedFileTypeError,
)
from app.storage import get_storage_provider


def get_page_service() -> PageService:
    """Create page service with dependencies."""
    storage = get_storage_provider()
    embedding_service = create_embedding_service(
        api_key=settings.openai_api_key if hasattr(settings, 'openai_api_key') else None
    )
    return PageService(storage=storage, embedding_service=embedding_service)


@router.get(
    "/{book_id}/pages",
    response_model=PageListResponse,
    summary="List book pages",
    description="Get all pages for a book with thumbnail URLs.",
)
async def list_pages(
    book_id: UUID,
    db: DBSession,
    current_user: OptionalUser,
) -> PageListResponse:
    """List all pages for a book with thumbnail URLs.

    Returns metadata and signed thumbnail URLs for each page.
    Thumbnail URLs are valid for 6 hours.

    - **book_id**: UUID of the book
    """
    page_service = get_page_service()

    try:
        return await page_service.get_page_list(book_id, db)
    except BookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book {book_id} not found",
        )


@router.get(
    "/{book_id}/pages/{page_number}",
    response_model=PageDetailResponse,
    summary="Get page details",
    description="Get signed URLs for a specific page at all resolutions.",
)
async def get_page(
    book_id: UUID,
    page_number: int,
    db: DBSession,
    current_user: OptionalUser,
) -> PageDetailResponse:
    """Get details for a specific page including signed URLs.

    Returns signed URLs for thumbnail and medium resolutions.
    - Thumbnail URL valid for 6 hours
    - Medium URL valid for 15 minutes

    - **book_id**: UUID of the book
    - **page_number**: Page number (1-indexed)
    """
    page_service = get_page_service()

    try:
        return await page_service.get_page_detail(book_id, page_number, db)
    except BookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {page_number} not found for book {book_id}",
        )


@router.post(
    "/{book_id}/pages/generate",
    response_model=PageGenerationResponse,
    summary="Generate pages",
    description="Generate page images and AI chunks for a book.",
)
async def generate_pages(
    book_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    request: PageGenerationRequest | None = None,
) -> PageGenerationResponse:
    """Generate page images and AI chunks for a book.

    This endpoint processes a PDF book to:
    1. Render each page as images (thumbnail and medium resolutions)
    2. Extract text from all pages
    3. Chunk text for AI processing
    4. Generate embeddings for semantic search

    **Limitations (MVP):**
    - Only PDF books supported
    - Maximum 100 pages for synchronous processing
    - Processing is synchronous (waits for completion)

    - **book_id**: UUID of the book to process
    - **force**: If true, regenerate even if pages exist
    """
    page_service = get_page_service()
    force = request.force if request else False

    try:
        return await page_service.generate_pages_and_chunks(book_id, db, force=force)
    except BookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book {book_id} not found",
        )
    except UnsupportedFileTypeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except TooManyPagesError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
