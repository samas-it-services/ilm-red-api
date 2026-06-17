"""Book service for business logic."""

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Literal

import structlog
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import RedisCache
from app.config import settings
from app.models.book import Book, BookAIProcessing, Rating
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
    ChatEnableResponse,
    ChatQuotaStatus,
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

        # Duplicate detection policy:
        #   1. Same owner already uploaded this exact file -> hard block (409).
        #      Re-uploading the same file is always a user error.
        #   2. A DIFFERENT owner already has this file -> allow the upload but
        #      annotate it as a global duplicate. We deliberately do NOT block
        #      cross-user duplicates: two users may legitimately own the same
        #      public-domain / royalty-free file, and hard-blocking would create
        #      false-positive copyright blocks. The duplicate is logged and
        #      surfaced in the response so moderation tooling can review it.
        same_owner_existing = await self.repo.get_by_hash(file_hash, owner.id)
        if same_owner_existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Duplicate file detected. This book already exists: "
                    f"{same_owner_existing.title}"
                ),
            )

        # Global (cross-owner) duplicate check — non-blocking.
        global_existing = await self.repo.get_by_hash(file_hash)
        is_global_duplicate = global_existing is not None
        if is_global_duplicate:
            logger.info(
                "global_duplicate_detected",
                file_hash=file_hash,
                owner_id=str(owner.id),
                existing_book_id=str(global_existing.id),
                existing_owner_id=str(global_existing.owner_id),
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
            is_global_duplicate=is_global_duplicate,
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

    async def record_view(
        self,
        book_id: uuid.UUID,
        viewer: User | None = None,
    ) -> None:
        """Atomically record a view for a book.

        Increments ``stats.views`` by one using an atomic SQL UPDATE.

        Policy:
            - Owners viewing their own book do NOT increment the counter
              (avoids self-inflated view counts).
            - Anonymous / public reads DO increment.
            - Never raises: view tracking is best-effort and must not break
              the read path.

        Args:
            book_id: Book being viewed.
            viewer: The viewing user, or ``None`` for anonymous reads.
        """
        try:
            book = await self.repo.get_by_id(book_id)
            if not book:
                return

            # Skip self-views by the owner.
            if viewer is not None and book.owner_id == viewer.id:
                return

            await self.repo.update_stats(book_id, views_increment=1)
            await self.db.commit()
        except Exception as e:  # noqa: BLE001 - best-effort, never break reads
            logger.warning("record_view_failed", book_id=str(book_id), error=str(e))

    # Chat enablement (self-serve, quota-gated)

    CHAT_PROCESSING_TYPE = "chat"

    def _chat_quota_limit(self, user: User) -> int | None:
        """Return the monthly chat-enable quota for a user.

        Returns ``None`` for unlimited (premium/admin), otherwise the
        configured free-tier monthly limit.
        """
        if user.is_premium or user.is_admin:
            return None
        return settings.chat_enable_monthly_quota_free

    async def _count_chat_enables_this_month(self, user: User) -> int:
        """Count books this user has enabled for chat in the current month."""
        now = datetime.now(UTC)
        month_start = datetime(now.year, now.month, 1, tzinfo=UTC)

        stmt = (
            select(func.count(BookAIProcessing.id))
            .join(Book, Book.id == BookAIProcessing.book_id)
            .where(
                Book.owner_id == user.id,
                BookAIProcessing.processing_type == self.CHAT_PROCESSING_TYPE,
                BookAIProcessing.created_at >= month_start,
            )
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def get_chat_quota_status(self, user: User) -> ChatQuotaStatus:
        """Get the current chat-enablement quota status for a user."""
        limit = self._chat_quota_limit(user)
        used = await self._count_chat_enables_this_month(user)
        if limit is None:
            return ChatQuotaStatus(
                used=used, limit=None, remaining=None, is_unlimited=True
            )
        return ChatQuotaStatus(
            used=used,
            limit=limit,
            remaining=max(0, limit - used),
            is_unlimited=False,
        )

    async def enable_chat(
        self,
        book_id: uuid.UUID,
        user: User,
    ) -> ChatEnableResponse:
        """Enable (enqueue) AI chat processing for a book — self-serve.

        Any authenticated uploader can request their own book be processed for
        chat, subject to a monthly quota. Premium/admin users are unlimited.

        Args:
            book_id: Book to enable chat for.
            user: Requesting user (must own the book).

        Returns:
            ChatEnableResponse with job status and quota.

        Raises:
            HTTPException: 404 if not found, 403 if not owner, 429 if quota hit.
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
                detail="Only the owner can enable chat for this book",
            )

        # Idempotency: if a chat processing job already exists (pending/processing/
        # completed), don't consume quota again — just report it.
        existing_stmt = select(BookAIProcessing).where(
            BookAIProcessing.book_id == book_id,
            BookAIProcessing.processing_type == self.CHAT_PROCESSING_TYPE,
        )
        existing = (await self.db.execute(existing_stmt)).scalars().first()
        if existing is not None:
            return ChatEnableResponse(
                book_id=book_id,
                status=existing.status,
                already_enabled=True,
                quota=await self.get_chat_quota_status(user),
                message="Chat processing was already enabled for this book.",
            )

        # Enforce monthly quota for non-premium users.
        limit = self._chat_quota_limit(user)
        if limit is not None:
            used = await self._count_chat_enables_this_month(user)
            if used >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Monthly chat-enable quota reached ({used}/{limit}). "
                        "Upgrade to premium for unlimited chat processing."
                    ),
                )

        # Enqueue a chat processing job (worker picks this up asynchronously).
        job = BookAIProcessing(
            book_id=book_id,
            processing_type=self.CHAT_PROCESSING_TYPE,
            status="pending",
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        logger.info(
            "chat_enable_enqueued",
            book_id=str(book_id),
            owner_id=str(user.id),
            job_id=str(job.id),
        )

        return ChatEnableResponse(
            book_id=book_id,
            status=job.status,
            already_enabled=False,
            quota=await self.get_chat_quota_status(user),
        )

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
