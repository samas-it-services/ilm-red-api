"""Page repository for database operations."""

import uuid
from typing import Sequence

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.page import PageImage, TextChunk


class PageRepository:
    """Repository for PageImage and TextChunk database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============= Book Access =============

    async def get_book(self, book_id: uuid.UUID) -> Book | None:
        """Get book by ID."""
        result = await self.db.execute(
            select(Book).where(Book.id == book_id)
        )
        return result.scalar_one_or_none()

    # ============= PageImage Operations =============

    async def create_page(self, page: PageImage) -> PageImage:
        """Create a new page image record."""
        self.db.add(page)
        await self.db.flush()
        await self.db.refresh(page)
        return page

    async def get_page(
        self,
        book_id: uuid.UUID,
        page_number: int,
    ) -> PageImage | None:
        """Get a specific page by book ID and page number."""
        result = await self.db.execute(
            select(PageImage)
            .where(PageImage.book_id == book_id)
            .where(PageImage.page_number == page_number)
        )
        return result.scalar_one_or_none()

    async def get_pages(
        self,
        book_id: uuid.UUID,
    ) -> Sequence[PageImage]:
        """Get all pages for a book, ordered by page number."""
        result = await self.db.execute(
            select(PageImage)
            .where(PageImage.book_id == book_id)
            .order_by(PageImage.page_number)
        )
        return result.scalars().all()

    async def get_page_count(self, book_id: uuid.UUID) -> int:
        """Get total number of pages for a book."""
        pages = await self.get_pages(book_id)
        return len(pages)

    async def delete_pages(self, book_id: uuid.UUID) -> int:
        """Delete all pages for a book. Returns count deleted."""
        result = await self.db.execute(
            delete(PageImage).where(PageImage.book_id == book_id)
        )
        return result.rowcount

    # ============= TextChunk Operations =============

    async def create_chunk(self, chunk: TextChunk) -> TextChunk:
        """Create a new text chunk record."""
        self.db.add(chunk)
        await self.db.flush()
        await self.db.refresh(chunk)
        return chunk

    async def get_chunk(
        self,
        book_id: uuid.UUID,
        chunk_index: int,
    ) -> TextChunk | None:
        """Get a specific chunk by book ID and index."""
        result = await self.db.execute(
            select(TextChunk)
            .where(TextChunk.book_id == book_id)
            .where(TextChunk.chunk_index == chunk_index)
        )
        return result.scalar_one_or_none()

    async def get_chunks(
        self,
        book_id: uuid.UUID,
    ) -> Sequence[TextChunk]:
        """Get all chunks for a book, ordered by index."""
        result = await self.db.execute(
            select(TextChunk)
            .where(TextChunk.book_id == book_id)
            .order_by(TextChunk.chunk_index)
        )
        return result.scalars().all()

    async def get_chunk_count(self, book_id: uuid.UUID) -> int:
        """Get total number of chunks for a book."""
        chunks = await self.get_chunks(book_id)
        return len(chunks)

    async def delete_chunks(self, book_id: uuid.UUID) -> int:
        """Delete all chunks for a book. Returns count deleted."""
        result = await self.db.execute(
            delete(TextChunk).where(TextChunk.book_id == book_id)
        )
        return result.rowcount

    async def search_similar_chunks(
        self,
        book_id: uuid.UUID,
        query_embedding: list[float],
        limit: int = 5,
    ) -> Sequence[TextChunk]:
        """Find most similar chunks using pgvector cosine distance.

        Args:
            book_id: Book to search within.
            query_embedding: Query embedding vector (1536 dims).
            limit: Maximum number of chunks to return.

        Returns:
            List of TextChunk ordered by similarity (most similar first).
        """
        # Use pgvector's cosine distance operator
        # Lower distance = more similar
        result = await self.db.execute(
            select(TextChunk)
            .where(TextChunk.book_id == book_id)
            .where(TextChunk.embedding.isnot(None))
            .order_by(TextChunk.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        return result.scalars().all()

    # ============= Bulk Operations =============

    async def create_pages_bulk(
        self,
        pages: list[PageImage],
    ) -> list[PageImage]:
        """Create multiple page records at once."""
        self.db.add_all(pages)
        await self.db.flush()
        for page in pages:
            await self.db.refresh(page)
        return pages

    async def create_chunks_bulk(
        self,
        chunks: list[TextChunk],
    ) -> list[TextChunk]:
        """Create multiple chunk records at once."""
        self.db.add_all(chunks)
        await self.db.flush()
        for chunk in chunks:
            await self.db.refresh(chunk)
        return chunks

    async def delete_book_content(self, book_id: uuid.UUID) -> dict[str, int]:
        """Delete all pages and chunks for a book.

        Returns:
            Dict with counts of deleted pages and chunks.
        """
        pages_deleted = await self.delete_pages(book_id)
        chunks_deleted = await self.delete_chunks(book_id)
        return {
            "pages_deleted": pages_deleted,
            "chunks_deleted": chunks_deleted,
        }
