"""Page Service - Orchestrates page generation and retrieval.

This service coordinates PDF processing, text chunking, embedding generation,
and storage operations to provide page-first reading functionality.

Principle P1: Pages are for rendering (visual browsing).
Principle P2: Chunks are for thinking (AI understanding).
Principle P3: API orchestrates, storage serves (no streaming through API).
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.page import PageImage, TextChunk
from app.repositories.page_repo import PageRepository
from app.schemas.page import (
    GenerationStatus,
    PageDetailResponse,
    PageGenerationResponse,
    PageListResponse,
    PageMetadata,
)
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingProvider
from app.services.pdf_processor import PDFProcessor
from app.storage.base import StorageProvider

logger = logging.getLogger(__name__)

# Configuration
MAX_SYNC_PAGES = 100  # Maximum pages for synchronous generation
THUMBNAIL_EXPIRES_IN = 21600  # 6 hours
MEDIUM_EXPIRES_IN = 900  # 15 minutes


class PageServiceError(Exception):
    """Base exception for page service errors."""

    pass


class BookNotFoundError(PageServiceError):
    """Book not found."""

    pass


class UnsupportedFileTypeError(PageServiceError):
    """File type not supported for page generation."""

    pass


class TooManyPagesError(PageServiceError):
    """Book has too many pages for synchronous generation."""

    pass


class PageService:
    """Service for page generation and retrieval.

    Orchestrates the full page generation pipeline:
    1. Download PDF from storage
    2. Render pages to images at multiple resolutions
    3. Upload images to storage
    4. Extract text and create chunks
    5. Generate embeddings for chunks
    6. Save all metadata to database
    """

    def __init__(
        self,
        storage: StorageProvider,
        embedding_service: EmbeddingProvider,
    ):
        """Initialize page service.

        Args:
            storage: Storage provider for file operations.
            embedding_service: Service for generating text embeddings.
        """
        self.storage = storage
        self.embedding_service = embedding_service
        self.chunking_service = ChunkingService()

    async def generate_pages_and_chunks(
        self,
        book_id: uuid.UUID,
        db: AsyncSession,
        force: bool = False,
    ) -> PageGenerationResponse:
        """Generate page images and AI chunks for a book.

        This is the main orchestration method that:
        1. Validates the book exists and is a PDF
        2. Downloads the PDF from storage
        3. Renders pages at thumbnail and medium resolutions
        4. Uploads page images to storage
        5. Extracts text and creates chunks
        6. Generates embeddings for each chunk
        7. Saves all metadata to database

        Args:
            book_id: UUID of the book to process.
            db: Database session.
            force: If True, regenerate even if pages exist.

        Returns:
            PageGenerationResponse with status and counts.

        Raises:
            BookNotFoundError: If book doesn't exist.
            UnsupportedFileTypeError: If not a PDF.
            TooManyPagesError: If book exceeds MAX_SYNC_PAGES.
        """
        repo = PageRepository(db)

        # 1. Get and validate book
        book = await repo.get_book(book_id)
        if not book:
            raise BookNotFoundError(f"Book {book_id} not found")

        if book.file_type != "pdf":
            raise UnsupportedFileTypeError(
                f"Only PDF books supported for page generation, got {book.file_type}"
            )

        # Check if already processed
        existing_pages = await repo.get_page_count(book_id)
        if existing_pages > 0 and not force:
            existing_chunks = await repo.get_chunk_count(book_id)
            return PageGenerationResponse(
                book_id=book_id,
                status=GenerationStatus.COMPLETED,
                total_pages=existing_pages,
                total_chunks=existing_chunks,
                message="Pages already generated. Use force=true to regenerate.",
            )

        # Delete existing content if force regenerating
        if force and existing_pages > 0:
            await repo.delete_book_content(book_id)
            logger.info(f"Deleted existing pages for book {book_id}")

        # 2. Download PDF
        logger.info(f"Downloading PDF for book {book_id}")
        try:
            pdf_bytes = await self.storage.download(book.file_path)
        except FileNotFoundError:
            raise BookNotFoundError(f"PDF file not found for book {book_id}")

        # 3. Process PDF
        processor = PDFProcessor(pdf_bytes)
        try:
            # Validate page count
            if processor.page_count > MAX_SYNC_PAGES:
                raise TooManyPagesError(
                    f"Book has {processor.page_count} pages, max is {MAX_SYNC_PAGES}"
                )

            logger.info(f"Processing {processor.page_count} pages for book {book_id}")

            # 4. Generate page images
            pages_created = []
            for page_num in range(1, processor.page_count + 1):
                page_image = await self._process_page(
                    processor, book_id, page_num, repo
                )
                pages_created.append(page_image)

            # 5. Extract text and create chunks
            logger.info(f"Creating chunks for book {book_id}")
            pages_text = list(processor.extract_all_pages())
            chunks_data = self.chunking_service.chunk_book(
                [(p.page_number, p.text) for p in pages_text]
            )

            # 6. Generate embeddings and save chunks
            chunks_created = []
            for i, chunk_data in enumerate(chunks_data):
                try:
                    embedding = await self.embedding_service.embed(chunk_data.text)
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for chunk {i}: {e}")
                    embedding = None

                chunk = TextChunk(
                    book_id=book_id,
                    chunk_index=i,
                    text=chunk_data.text,
                    token_count=chunk_data.token_count,
                    page_start=chunk_data.page_start,
                    page_end=chunk_data.page_end,
                    embedding=embedding,
                )
                await repo.create_chunk(chunk)
                chunks_created.append(chunk)

            # 7. Update book page count
            book.page_count = processor.page_count
            await db.commit()

            logger.info(
                f"Generated {len(pages_created)} pages and {len(chunks_created)} "
                f"chunks for book {book_id}"
            )

            return PageGenerationResponse(
                book_id=book_id,
                status=GenerationStatus.COMPLETED,
                total_pages=len(pages_created),
                total_chunks=len(chunks_created),
            )

        except Exception as e:
            logger.error(f"Page generation failed for book {book_id}: {e}")
            await db.rollback()
            return PageGenerationResponse(
                book_id=book_id,
                status=GenerationStatus.FAILED,
                total_pages=0,
                total_chunks=0,
                message=str(e),
            )
        finally:
            processor.close()

    async def _process_page(
        self,
        processor: PDFProcessor,
        book_id: uuid.UUID,
        page_num: int,
        repo: PageRepository,
    ) -> PageImage:
        """Process a single page: render, upload, and save metadata.

        Args:
            processor: PDF processor instance.
            book_id: Book UUID.
            page_num: Page number (1-indexed).
            repo: Page repository.

        Returns:
            Created PageImage record.
        """
        # Render at all resolutions
        images = processor.render_page_resolutions(page_num)

        # Upload images
        paths = {}
        for res_name, img_bytes in images.items():
            path = f"books/{book_id}/pages/{res_name}/{page_num}.jpg"
            await self.storage.upload(path, img_bytes, "image/jpeg")
            paths[res_name] = path

        # Get dimensions
        dims = processor.get_page_dimensions(page_num)

        # Create database record
        page_image = PageImage(
            book_id=book_id,
            page_number=page_num,
            width=dims.width,
            height=dims.height,
            thumbnail_path=paths["thumbnail"],
            medium_path=paths["medium"],
        )
        await repo.create_page(page_image)

        return page_image

    async def get_page_list(
        self,
        book_id: uuid.UUID,
        db: AsyncSession,
    ) -> PageListResponse:
        """Get all pages for a book with thumbnail URLs.

        Args:
            book_id: Book UUID.
            db: Database session.

        Returns:
            PageListResponse with page metadata and thumbnail URLs.

        Raises:
            BookNotFoundError: If book doesn't exist.
        """
        repo = PageRepository(db)

        book = await repo.get_book(book_id)
        if not book:
            raise BookNotFoundError(f"Book {book_id} not found")

        pages = await repo.get_pages(book_id)

        # Determine generation status
        if not pages:
            status = GenerationStatus.NOT_STARTED
        else:
            status = GenerationStatus.COMPLETED

        # Generate signed URLs for thumbnails
        page_metadata = []
        for page in pages:
            thumbnail_url = await self.storage.get_signed_url(
                page.thumbnail_path,
                expires_in=THUMBNAIL_EXPIRES_IN,
                for_download=False,
            )
            page_metadata.append(
                PageMetadata(
                    page_number=page.page_number,
                    width=page.width,
                    height=page.height,
                    thumbnail_url=thumbnail_url,
                )
            )

        return PageListResponse(
            book_id=book_id,
            total_pages=len(pages),
            generation_status=status,
            pages=page_metadata,
        )

    async def get_page_detail(
        self,
        book_id: uuid.UUID,
        page_number: int,
        db: AsyncSession,
    ) -> PageDetailResponse:
        """Get a single page with all resolution URLs.

        Args:
            book_id: Book UUID.
            page_number: Page number (1-indexed).
            db: Database session.

        Returns:
            PageDetailResponse with signed URLs.

        Raises:
            BookNotFoundError: If page doesn't exist.
        """
        repo = PageRepository(db)

        page = await repo.get_page(book_id, page_number)
        if not page:
            raise BookNotFoundError(f"Page {page_number} not found for book {book_id}")

        # Generate signed URLs
        thumbnail_url = await self.storage.get_signed_url(
            page.thumbnail_path,
            expires_in=THUMBNAIL_EXPIRES_IN,
            for_download=False,
        )
        medium_url = await self.storage.get_signed_url(
            page.medium_path,
            expires_in=MEDIUM_EXPIRES_IN,
            for_download=False,
        )

        expires_at = datetime.now(UTC) + timedelta(seconds=MEDIUM_EXPIRES_IN)

        return PageDetailResponse(
            page_number=page.page_number,
            width=page.width,
            height=page.height,
            thumbnail_url=thumbnail_url,
            medium_url=medium_url,
            expires_at=expires_at,
        )

    async def get_book_context_for_rag(
        self,
        book_id: uuid.UUID,
        query: str,
        db: AsyncSession,
        limit: int = 5,
    ) -> str:
        """Get relevant book content for RAG.

        Embeds the query and finds similar chunks using pgvector.
        Returns formatted context with page citations.

        Args:
            book_id: Book UUID.
            query: User's query text.
            db: Database session.
            limit: Maximum chunks to return.

        Returns:
            Formatted context string with page citations.
        """
        repo = PageRepository(db)

        # Embed query
        try:
            query_embedding = await self.embedding_service.embed(query)
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return ""

        # Find similar chunks
        chunks = await repo.search_similar_chunks(book_id, query_embedding, limit)

        if not chunks:
            return ""

        # Format context with citations
        context_parts = []
        for chunk in chunks:
            citation = chunk.page_citation
            context_parts.append(f"[{citation}]\n{chunk.text}")

        return "\n\n---\n\n".join(context_parts)


def create_page_service(
    storage: StorageProvider,
    embedding_service: EmbeddingProvider,
) -> PageService:
    """Factory function to create page service.

    Args:
        storage: Storage provider instance.
        embedding_service: Embedding service instance.

    Returns:
        Configured PageService instance.
    """
    return PageService(storage=storage, embedding_service=embedding_service)
