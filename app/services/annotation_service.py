"""Annotation service for bookmarks, highlights, and notes."""

from uuid import UUID

import structlog
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.annotation_repo import AnnotationRepository
from app.schemas.annotation import (
    BookmarkCreate,
    BookmarkResponse,
    HighlightCreate,
    HighlightResponse,
    HighlightUpdate,
    NoteCreate,
    NoteResponse,
    NoteUpdate,
)

logger = structlog.get_logger(__name__)


class AnnotationService:
    """Service for annotation operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AnnotationRepository(db)

    # Bookmarks
    async def get_bookmarks(self, user_id: UUID, book_id: UUID) -> list[BookmarkResponse]:
        """Get bookmarks for a book."""
        bookmarks = await self.repo.get_bookmarks(user_id, book_id)
        return [BookmarkResponse.model_validate(b) for b in bookmarks]

    async def create_bookmark(
        self, user_id: UUID, book_id: UUID, data: BookmarkCreate
    ) -> BookmarkResponse:
        """Create a bookmark."""
        bookmark = await self.repo.create_bookmark(
            user_id, book_id, data.page_number, data.note, data.color
        )
        await self.db.commit()
        return BookmarkResponse.model_validate(bookmark)

    async def delete_bookmark(self, user_id: UUID, book_id: UUID, page_number: int) -> None:
        """Delete a bookmark."""
        deleted = await self.repo.delete_bookmark(user_id, book_id, page_number)
        if not deleted:
            raise HTTPException(status_code=404, detail="Bookmark not found")
        await self.db.commit()

    # Highlights
    async def get_highlights(
        self, user_id: UUID, book_id: UUID, page_number: int | None = None
    ) -> list[HighlightResponse]:
        """Get highlights for a book."""
        highlights = await self.repo.get_highlights(user_id, book_id, page_number)
        return [HighlightResponse.model_validate(h) for h in highlights]

    async def create_highlight(
        self, user_id: UUID, book_id: UUID, data: HighlightCreate
    ) -> HighlightResponse:
        """Create a highlight."""
        highlight = await self.repo.create_highlight(
            user_id,
            book_id,
            data.page_number,
            data.text_content,
            data.position,
            data.color,
            data.note,
        )
        await self.db.commit()
        return HighlightResponse.model_validate(highlight)

    async def update_highlight(
        self, highlight_id: UUID, user_id: UUID, data: HighlightUpdate
    ) -> HighlightResponse:
        """Update a highlight."""
        highlight = await self.repo.update_highlight(highlight_id, user_id, data.note)
        if not highlight:
            raise HTTPException(status_code=404, detail="Highlight not found")
        await self.db.commit()
        return HighlightResponse.model_validate(highlight)

    async def delete_highlight(self, highlight_id: UUID, user_id: UUID) -> None:
        """Delete a highlight."""
        deleted = await self.repo.delete_highlight(highlight_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Highlight not found")
        await self.db.commit()

    # Notes
    async def get_notes(self, user_id: UUID, book_id: UUID) -> list[NoteResponse]:
        """Get notes for a book."""
        notes = await self.repo.get_notes(user_id, book_id)
        return [NoteResponse.model_validate(n) for n in notes]

    async def create_note(
        self, user_id: UUID, book_id: UUID, data: NoteCreate
    ) -> NoteResponse:
        """Create a note."""
        note = await self.repo.create_note(
            user_id, book_id, data.page_number, data.content, data.color
        )
        await self.db.commit()
        return NoteResponse.model_validate(note)

    async def update_note(
        self, note_id: UUID, user_id: UUID, data: NoteUpdate
    ) -> NoteResponse:
        """Update a note."""
        note = await self.repo.update_note(note_id, user_id, data.content, data.color)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        await self.db.commit()
        return NoteResponse.model_validate(note)

    async def delete_note(self, note_id: UUID, user_id: UUID) -> None:
        """Delete a note."""
        deleted = await self.repo.delete_note(note_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Note not found")
        await self.db.commit()
