"""Book service for business logic."""

import hashlib
import uuid
from typing import Literal

import structlog
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import RedisCache
from app.config import settings
from app.models.book import Book, Rating
from app.models.user import User
from app.repositories.book_repo import BookRepository
from app.schemas.book import (
    BookCreate,
    BookFilters,
    BookListItem,
    BookListResponse,
    BookResponse,
    BookStats,
    BookUpdate,
    BookUploadResponse,
    DownloadUrlResponse,
    UserBrief,
)
from app.schemas.common import create_pagination
from app.schemas.rating import RatingCreate, RatingListResponse, RatingResponse
from app.services.embedding_service import create_embedding_service
from app.services.page_service import PageService
from app.storage import get_storage_provider

logger = structlog.get_logger(__name__)


def detect_file_type_by_magic(content: bytes) -> str | None:
    """Detect file type by magic bytes (first few bytes of file).

    Returns:
        File type string ('pdf', 'epub', 'txt') or None if not recognized.
    """
    if len(content) < 4:
        return None

    # PDF: starts with %PDF
    if content[:4] == b"%PDF":
        return "pdf"

    # EPUB: ZIP file with specific content (PK signature)
    # EPUB is a ZIP archive, we check for ZIP signature
    if content[:2] == b"PK":
        # Could be EPUB (which is a specialized ZIP)
        # For more robust check, we'd look for "mimetype" entry
        return "epub"

    # TXT: Check if it's valid UTF-8 or ASCII text
    # Sample first 1000 bytes to check for text
    sample = content[:1000]
    try:
        sample.decode("utf-8")
        # Additional check: no null bytes in text files
        if b"\x00" not in sample:
            return "txt"
    except UnicodeDecodeError:
        pass

    return None


class BookService:
    """Service for book-related business logic."""

    # Allowed MIME types for book uploads
    ALLOWED_MIME_TYPES = {
        "application/pdf": "pdf",
        "application/epub+zip": "epub",
        "text/plain": "txt",
        "application/x-epub+zip": "epub",
    }

    # Maximum file size (500 MB)
    MAX_FILE_SIZE = 500 * 1024 * 1024

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BookRepository(db)
        self.storage = get_storage_provider()

    async def _invalidate_search_cache(self) -> None:
        """Invalidate search cache after book mutations."""
        try:
            redis_client = await RedisCache.get_client()
            if redis_client:
                # Delete all search-related cache keys
                deleted = await redis_client.delete(*[
                    key async for key in redis_client.scan_iter("search:*")
                ])
                if deleted > 0:
                    logger.info("search_cache_invalidated", keys_deleted=deleted)
        except Exception as e:
            # Log but don't fail the operation if cache invalidation fails
            logger.warning("search_cache_invalidation_failed", error=str(e))

    async def upload_book(
        self,
        file: UploadFile,
        metadata: BookCreate,
        owner: User,
    ) -> BookUploadResponse:
        """Upload a new book.

        Args:
            file: Uploaded file
            metadata: Book metadata
            owner: Book owner

        Returns:
            Upload response with book ID and status

        Raises:
            HTTPException: If validation fails
        """
        # Read file content first for validation
        content = await file.read()

        # Check for empty file first (before other validations)
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded",
            )

        # Validate file extension is allowed
        filename = file.filename or ""
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        allowed_extensions = {"pdf", "epub", "txt"}
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type '.{ext}'. Allowed: PDF, EPUB, TXT",
            )

        # Validate file type by magic bytes (more secure than trusting Content-Type header)
        detected_type = detect_file_type_by_magic(content)
        if detected_type is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unrecognized file format. Allowed types: PDF, EPUB, TXT",
            )

        # Also validate Content-Type header matches detected type
        content_type = file.content_type or "application/octet-stream"
        if content_type in self.ALLOWED_MIME_TYPES:
            declared_type = self.ALLOWED_MIME_TYPES[content_type]
            if declared_type != detected_type:
                logger.warning(
                    "File type mismatch",
                    declared_type=declared_type,
                    detected_type=detected_type,
                    filename=file.filename,
                )
                # Trust the detected type over the declared type

        file_type = detected_type

        # Validate file size
        file_size = len(content)
        if file_size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {self.MAX_FILE_SIZE // (1024*1024)} MB",
            )

        # Calculate file hash for deduplication
        file_hash = hashlib.sha256(content).hexdigest()

        # Check for duplicates
        existing = await self.repo.get_by_hash(file_hash, owner.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate file detected. This book already exists: {existing.title}",
            )

        # Generate storage path
        book_id = uuid.uuid4()
        file_extension = file_type
        storage_path = f"books/{owner.id}/{book_id}/file.{file_extension}"

        # Upload to storage
        try:
            await self.storage.upload(storage_path, content, content_type)
        except Exception as e:
            logger.error("Failed to upload file to storage", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file",
            )

        # Create book record
        book = await self.repo.create(
            owner_id=owner.id,
            title=metadata.title,
            author=metadata.author,
            description=metadata.description,
            category=metadata.category.value if metadata.category else "other",
            visibility=metadata.visibility.value if metadata.visibility else "private",
            language=metadata.language,
            isbn=metadata.isbn,
            file_path=storage_path,
            file_hash=file_hash,
            file_size=file_size,
            file_type=file_type,
            original_filename=file.filename,
        )

        await self.db.commit()

        # Invalidate search cache
        await self._invalidate_search_cache()

        logger.info(
            "Book uploaded",
            book_id=str(book.id),
            owner_id=str(owner.id),
            file_type=file_type,
            file_size=file_size,
        )

        # Auto-generate pages for PDF files (<=100 pages, synchronous)
        if file_type == "pdf":
            try:
                embedding_service = create_embedding_service(
                    api_key=settings.openai_api_key if hasattr(settings, 'openai_api_key') else None
                )
                page_service = PageService(storage=self.storage, embedding_service=embedding_service)

                generation_result = await page_service.generate_pages_and_chunks(book.id, self.db)

                if generation_result.status.value == "completed":
                    logger.info(
                        "Auto-generated pages",
                        book_id=str(book.id),
                        pages=generation_result.total_pages,
                        chunks=generation_result.total_chunks,
                    )
                else:
                    logger.warning(
                        "Page generation incomplete",
                        book_id=str(book.id),
                        status=generation_result.status.value,
                        message=generation_result.message,
                    )
            except Exception as e:
                # Don't fail the upload if page generation fails
                logger.warning(
                    "Failed to auto-generate pages",
                    book_id=str(book.id),
                    error=str(e),
                )

        return BookUploadResponse(
            id=book.id,
            title=book.title,
            status=book.status,
            file_type=book.file_type,
            file_size=book.file_size,
        )

    async def get_book(
        self,
        book_id: uuid.UUID,
        user: User | None = None,
        include_download_url: bool = True,
    ) -> BookResponse:
        """Get book by ID.

        Args:
            book_id: Book ID
            user: Current user (for access control)
            include_download_url: Whether to include signed download URL

        Returns:
            Book response

        Raises:
            HTTPException: If book not found or access denied
        """
        book = await self.repo.get_by_id(book_id)

        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        # Check access
        if not self._can_access_book(book, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Get download URL if requested
        download_url = None
        if include_download_url and book.status == "ready":
            try:
                download_url = await self.storage.get_signed_url(
                    book.file_path,
                    expires_in=3600,
                )
            except Exception as e:
                logger.warning("Failed to generate download URL", error=str(e))

        return self._book_to_response(book, download_url)

    async def list_books(
        self,
        user: User | None = None,
        filters: BookFilters | None = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> BookListResponse:
        """List books with filtering and pagination."""
        filters = filters or BookFilters()

        books, total = await self.repo.list_books(
            user_id=user.id if user else None,
            owner_id=filters.owner_id,
            category=filters.category.value if filters.category else None,
            visibility=filters.visibility.value if filters.visibility else None,
            status=filters.status.value if filters.status else None,
            search_query=filters.q,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Convert to response items
        items = [self._book_to_list_item(book) for book in books]

        return BookListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    async def update_book(
        self,
        book_id: uuid.UUID,
        updates: BookUpdate,
        user: User,
    ) -> BookResponse:
        """Update book metadata.

        Args:
            book_id: Book ID
            updates: Fields to update
            user: Current user

        Returns:
            Updated book response

        Raises:
            HTTPException: If book not found or user not owner
        """
        book = await self.repo.get_by_id(book_id)

        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        if book.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owner can update this book",
            )

        # Build update dict
        update_data = {}
        if updates.title is not None:
            update_data["title"] = updates.title
        if updates.author is not None:
            update_data["author"] = updates.author
        if updates.description is not None:
            update_data["description"] = updates.description
        if updates.category is not None:
            update_data["category"] = updates.category.value
        if updates.visibility is not None:
            update_data["visibility"] = updates.visibility.value
        if updates.language is not None:
            update_data["language"] = updates.language
        if updates.isbn is not None:
            update_data["isbn"] = updates.isbn

        if update_data:
            book = await self.repo.update(book, **update_data)
            await self.db.commit()
            # Invalidate search cache
            await self._invalidate_search_cache()

        return self._book_to_response(book)

    async def delete_book(
        self,
        book_id: uuid.UUID,
        user: User,
    ) -> None:
        """Soft delete a book.

        Args:
            book_id: Book ID
            user: Current user

        Raises:
            HTTPException: If book not found or user not owner
        """
        book = await self.repo.get_by_id(book_id)

        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        if book.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owner can delete this book",
            )

        await self.repo.soft_delete(book)
        await self.db.commit()

        # Invalidate search cache
        await self._invalidate_search_cache()

        logger.info("Book deleted", book_id=str(book_id), owner_id=str(user.id))

    async def get_download_url(
        self,
        book_id: uuid.UUID,
        user: User | None = None,
    ) -> DownloadUrlResponse:
        """Get signed download URL for a book.

        Args:
            book_id: Book ID
            user: Current user

        Returns:
            Download URL response

        Raises:
            HTTPException: If book not found or access denied
        """
        book = await self.repo.get_by_id(book_id)

        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        if not self._can_access_book(book, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        if book.status != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Book is not ready for download (status: {book.status})",
            )

        # Generate signed URL
        expires_in = 3600  # 1 hour
        url = await self.storage.get_signed_url(
            book.file_path,
            expires_in=expires_in,
        )

        # Update download stats
        await self.repo.update_stats(book_id, downloads_increment=1)
        await self.db.commit()

        return DownloadUrlResponse(url=url, expires_in=expires_in)

    # Rating methods

    async def add_rating(
        self,
        book_id: uuid.UUID,
        rating_data: RatingCreate,
        user: User,
    ) -> RatingResponse:
        """Add or update a rating for a book."""
        book = await self.repo.get_by_id(book_id)

        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        if not self._can_access_book(book, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Don't allow rating own books
        if book.owner_id == user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot rate your own book",
            )

        rating = await self.repo.add_rating(
            book_id=book_id,
            user_id=user.id,
            rating_value=rating_data.rating,
            review=rating_data.review,
        )
        await self.db.commit()

        return self._rating_to_response(rating)

    async def get_ratings(
        self,
        book_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> RatingListResponse:
        """Get ratings for a book."""
        book = await self.repo.get_by_id(book_id)

        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        ratings, total = await self.repo.get_ratings(book_id, page, limit)

        return RatingListResponse(
            data=[self._rating_to_response(r) for r in ratings],
            pagination=create_pagination(page, limit, total),
        )

    async def delete_rating(
        self,
        book_id: uuid.UUID,
        user: User,
    ) -> None:
        """Delete user's rating for a book."""
        rating = await self.repo.get_user_rating(book_id, user.id)

        if not rating:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rating not found",
            )

        await self.repo.delete_rating(rating)
        await self.db.commit()

    # Favorite methods

    async def add_favorite(
        self,
        book_id: uuid.UUID,
        user: User,
    ) -> None:
        """Add book to user's favorites."""
        book = await self.repo.get_by_id(book_id)

        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        if not self._can_access_book(book, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        await self.repo.add_favorite(user.id, book_id)
        await self.db.commit()

    async def remove_favorite(
        self,
        book_id: uuid.UUID,
        user: User,
    ) -> None:
        """Remove book from user's favorites."""
        removed = await self.repo.remove_favorite(user.id, book_id)

        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not in favorites",
            )

        await self.db.commit()

    async def get_favorites(
        self,
        user: User,
        page: int = 1,
        limit: int = 20,
    ) -> BookListResponse:
        """Get user's favorite books."""
        books, total = await self.repo.get_user_favorites(user.id, page, limit)

        items = [self._book_to_list_item(book) for book in books]

        return BookListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    # Helper methods

    def _can_access_book(self, book: Book, user: User | None) -> bool:
        """Check if user can access a book."""
        if book.visibility == "public":
            return True
        if user and book.owner_id == user.id:
            return True
        # Future: handle "friends" visibility
        return False

    def _book_to_response(
        self,
        book: Book,
        download_url: str | None = None,
    ) -> BookResponse:
        """Convert Book model to response schema."""
        return BookResponse(
            id=book.id,
            title=book.title,
            author=book.author,
            description=book.description,
            category=book.category,
            visibility=book.visibility,
            language=book.language,
            isbn=book.isbn,
            file_type=book.file_type,
            file_size=book.file_size,
            page_count=book.page_count,
            cover_url=book.cover_url,
            status=book.status,
            processing_error=book.processing_error,
            stats=BookStats(**book.stats),
            owner=UserBrief(
                id=book.owner.id,
                username=book.owner.username,
                display_name=book.owner.display_name,
                avatar_url=book.owner.avatar_url,
            ),
            download_url=download_url,
            created_at=book.created_at,
            updated_at=book.updated_at,
        )

    def _book_to_list_item(self, book: Book) -> BookListItem:
        """Convert Book model to list item schema."""
        return BookListItem(
            id=book.id,
            title=book.title,
            author=book.author,
            category=book.category,
            visibility=book.visibility,
            file_type=book.file_type,
            file_size=book.file_size,
            page_count=book.page_count,
            cover_url=book.cover_url,
            status=book.status,
            stats=BookStats(**book.stats),
            owner=UserBrief(
                id=book.owner.id,
                username=book.owner.username,
                display_name=book.owner.display_name,
                avatar_url=book.owner.avatar_url,
            ),
            created_at=book.created_at,
        )

    def _rating_to_response(self, rating: Rating) -> RatingResponse:
        """Convert Rating model to response schema."""
        return RatingResponse(
            id=rating.id,
            book_id=rating.book_id,
            rating=rating.rating,
            review=rating.review,
            user=UserBrief(
                id=rating.user.id,
                username=rating.user.username,
                display_name=rating.user.display_name,
                avatar_url=rating.user.avatar_url,
            ),
            created_at=rating.created_at,
            updated_at=rating.updated_at,
        )
