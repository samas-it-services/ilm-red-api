"""Page and TextChunk database models for page-first reading platform."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class PageImage(Base, UUIDMixin):
    """Page image metadata for a book page.

    Stores metadata about rendered page images at different resolutions.
    Actual images are stored in blob storage (Azure Blob / local).

    Principle P1: Pages are for rendering (visual browsing).
    """

    __tablename__ = "page_images"

    # Book relationship
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Page identification (1-indexed)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Original dimensions (from PDF)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)

    # Storage paths (relative to book storage root)
    # e.g., "books/{book_id}/pages/thumb/1.jpg"
    thumbnail_path: Mapped[str] = mapped_column(String(500), nullable=False)
    medium_path: Mapped[str] = mapped_column(String(500), nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow(),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    book: Mapped["Book"] = relationship("Book", backref="page_images")

    __table_args__ = (
        # Unique constraint: one page image record per page per book
        Index(
            "ix_page_images_book_page",
            "book_id",
            "page_number",
            unique=True,
        ),
        # Index for listing pages in order
        Index("ix_page_images_book_order", "book_id", "page_number"),
    )

    def __repr__(self) -> str:
        return f"<PageImage book={self.book_id} page={self.page_number}>"


class TextChunk(Base, UUIDMixin):
    """Chunked text from a book for AI/RAG processing.

    Stores book text split into AI-friendly chunks with embeddings
    for semantic search. Each chunk maps to a page range for citations.

    Principle P2: Chunks are for thinking (AI understanding).
    """

    __tablename__ = "text_chunks"

    # Book relationship
    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Chunk ordering (0-indexed)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Page mapping (for citations)
    # e.g., "Pages 15-17" - allows AI to cite sources
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)

    # Embedding vector for semantic search (OpenAI text-embedding-3-small = 1536 dims)
    # Nullable because embedding generation is async
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),
        nullable=True,
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow(),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    book: Mapped["Book"] = relationship("Book", backref="text_chunks")

    __table_args__ = (
        # Unique constraint: one chunk index per book
        Index(
            "ix_text_chunks_book_chunk",
            "book_id",
            "chunk_index",
            unique=True,
        ),
        # Index for listing chunks in order
        Index("ix_text_chunks_book_order", "book_id", "chunk_index"),
        # pgvector index for semantic search (IVFFlat for approximate nearest neighbor)
        # Note: Index will be created only if embedding column has values
        Index(
            "ix_text_chunks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},  # Number of lists for IVFFlat
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<TextChunk book={self.book_id} chunk={self.chunk_index} pages={self.page_start}-{self.page_end}>"

    @property
    def page_citation(self) -> str:
        """Format page range for citation display."""
        if self.page_start == self.page_end:
            return f"Page {self.page_start}"
        return f"Pages {self.page_start}-{self.page_end}"


# Import Book for type hints (avoid circular import)
from app.models.book import Book  # noqa: E402, F401
