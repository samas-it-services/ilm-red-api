"""Page and TextChunk schemas for page-first reading platform."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


class GenerationStatus(str, Enum):
    """Page generation status values."""

    NOT_STARTED = "not_started"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============= Page Schemas =============


class PageMetadata(BaseModel):
    """Single page metadata with thumbnail URL."""

    page_number: int = Field(ge=1, description="Page number (1-indexed)")
    width: int = Field(description="Original page width in pixels")
    height: int = Field(description="Original page height in pixels")
    thumbnail_url: str = Field(description="Signed URL for thumbnail image (150px)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page_number": 1,
                "width": 612,
                "height": 792,
                "thumbnail_url": "https://storage.../thumb/1.jpg?sig=...",
            }
        }
    )


class PageListResponse(BaseModel):
    """Response for listing book pages with thumbnails."""

    book_id: UUID = Field(description="Book ID")
    total_pages: int = Field(ge=0, description="Total number of pages")
    generation_status: GenerationStatus = Field(description="Page generation status")
    pages: list[PageMetadata] = Field(description="List of page metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "book_id": "123e4567-e89b-12d3-a456-426614174000",
                "total_pages": 120,
                "generation_status": "completed",
                "pages": [
                    {
                        "page_number": 1,
                        "width": 612,
                        "height": 792,
                        "thumbnail_url": "https://storage.../thumb/1.jpg?sig=...",
                    }
                ],
            }
        }
    )


class PageDetailResponse(BaseModel):
    """Response for single page with all resolution URLs."""

    page_number: int = Field(ge=1, description="Page number (1-indexed)")
    width: int = Field(description="Original page width in pixels")
    height: int = Field(description="Original page height in pixels")
    thumbnail_url: str = Field(description="Signed URL for thumbnail (150px)")
    medium_url: str = Field(description="Signed URL for medium resolution (800px)")
    expires_at: datetime = Field(description="When the signed URLs expire")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page_number": 12,
                "width": 612,
                "height": 792,
                "thumbnail_url": "https://storage.../thumb/12.jpg?sig=...",
                "medium_url": "https://storage.../med/12.jpg?sig=...",
                "expires_at": "2026-01-09T12:34:56Z",
            }
        }
    )


class PageGenerationRequest(BaseModel):
    """Request to generate pages for a book."""

    force: bool = Field(
        default=False,
        description="Regenerate even if pages already exist",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "force": False,
            }
        }
    )


class PageGenerationResponse(BaseModel):
    """Response after page generation completes."""

    book_id: UUID = Field(description="Book ID")
    status: GenerationStatus = Field(description="Generation status")
    total_pages: int = Field(ge=0, description="Total pages generated")
    total_chunks: int = Field(ge=0, description="Total text chunks created")
    message: str | None = Field(default=None, description="Additional message or error")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "book_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "completed",
                "total_pages": 120,
                "total_chunks": 45,
                "message": None,
            }
        }
    )


# ============= Chunk Schemas =============


class ChunkResponse(BaseModel):
    """Single text chunk response."""

    chunk_index: int = Field(ge=0, description="Chunk index (0-indexed)")
    text: str = Field(description="Chunk text content")
    token_count: int = Field(ge=0, description="Number of tokens in chunk")
    page_start: int = Field(ge=1, description="Start page number")
    page_end: int = Field(ge=1, description="End page number")
    page_citation: str = Field(description="Formatted page citation")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "chunk_index": 0,
                "text": "This is the first chunk of the book...",
                "token_count": 450,
                "page_start": 1,
                "page_end": 2,
                "page_citation": "Pages 1-2",
            }
        }
    )


class BookChunksResponse(BaseModel):
    """Response for listing book text chunks."""

    book_id: UUID = Field(description="Book ID")
    total_chunks: int = Field(ge=0, description="Total number of chunks")
    chunks: list[ChunkResponse] = Field(description="List of text chunks")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "book_id": "123e4567-e89b-12d3-a456-426614174000",
                "total_chunks": 45,
                "chunks": [
                    {
                        "chunk_index": 0,
                        "text": "This is the first chunk...",
                        "token_count": 450,
                        "page_start": 1,
                        "page_end": 2,
                        "page_citation": "Pages 1-2",
                    }
                ],
            }
        }
    )


# ============= RAG Citation Schemas =============


class PageCitation(BaseModel):
    """Citation reference for RAG responses."""

    page_start: int = Field(ge=1, description="Start page number")
    page_end: int = Field(ge=1, description="End page number")
    excerpt: str = Field(description="Relevant text excerpt")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page_start": 15,
                "page_end": 16,
                "excerpt": "...relevant text from the book...",
            }
        }
    )


class RAGContext(BaseModel):
    """RAG context metadata for chat responses."""

    chunks_used: int = Field(ge=0, description="Number of chunks used for context")
    tokens_added: int = Field(ge=0, description="Total tokens added to context")
    citations: list[PageCitation] = Field(description="Page citations from context")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "chunks_used": 5,
                "tokens_added": 1200,
                "citations": [
                    {
                        "page_start": 15,
                        "page_end": 16,
                        "excerpt": "...relevant text...",
                    }
                ],
            }
        }
    )
