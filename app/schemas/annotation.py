"""Annotation schemas for bookmarks, highlights, and notes."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Bookmark schemas
class BookmarkCreate(BaseModel):
    """Create bookmark request."""

    page_number: int = Field(..., ge=1)
    note: str | None = Field(None, max_length=500)
    color: str | None = Field(None, max_length=20)


class BookmarkResponse(BaseModel):
    """Bookmark response."""

    id: UUID
    user_id: UUID
    book_id: UUID
    page_number: int
    note: str | None
    color: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Highlight schemas
class HighlightCreate(BaseModel):
    """Create highlight request."""

    page_number: int = Field(..., ge=1)
    text_content: str = Field(..., min_length=1, max_length=5000)
    position: dict = Field(..., description="Position data: {x, y, width, height}")
    color: str = Field(default="#FFFF00", max_length=20)
    note: str | None = Field(None, max_length=500)


class HighlightUpdate(BaseModel):
    """Update highlight request."""

    note: str | None = Field(None, max_length=500)


class HighlightResponse(BaseModel):
    """Highlight response."""

    id: UUID
    user_id: UUID
    book_id: UUID
    page_number: int
    text_content: str
    position: dict
    color: str
    note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Note schemas
class NoteCreate(BaseModel):
    """Create note request."""

    page_number: int | None = Field(None, ge=1, description="Page number (null for book-level note)")
    content: str = Field(..., min_length=1, max_length=10000)
    color: str | None = Field(None, max_length=20)


class NoteUpdate(BaseModel):
    """Update note request."""

    content: str | None = Field(None, min_length=1, max_length=10000)
    color: str | None = Field(None, max_length=20)


class NoteResponse(BaseModel):
    """Note response."""

    id: UUID
    user_id: UUID
    book_id: UUID
    page_number: int | None
    content: str
    color: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
