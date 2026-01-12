"""Annotation repository for bookmarks, highlights, and notes."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import Bookmark, Highlight, Note


class AnnotationRepository:
    """Repository for annotation operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Bookmarks
    async def get_bookmarks(self, user_id: UUID, book_id: UUID) -> list[Bookmark]:
        """Get all bookmarks for a book."""
        query = select(Bookmark).where(
            and_(
                Bookmark.user_id == user_id,
                Bookmark.book_id == book_id,
            )
        ).order_by(Bookmark.page_number)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_bookmark(
        self, user_id: UUID, book_id: UUID, page_number: int, note: str | None, color: str | None
    ) -> Bookmark:
        """Create a bookmark."""
        bookmark = Bookmark(
            user_id=user_id,
            book_id=book_id,
            page_number=page_number,
            note=note,
            color=color,
        )
        self.db.add(bookmark)
        await self.db.flush()
        return bookmark

    async def delete_bookmark(self, user_id: UUID, book_id: UUID, page_number: int) -> bool:
        """Delete a bookmark."""
        query = select(Bookmark).where(
            and_(
                Bookmark.user_id == user_id,
                Bookmark.book_id == book_id,
                Bookmark.page_number == page_number,
            )
        )
        result = await self.db.execute(query)
        bookmark = result.scalar_one_or_none()
        if bookmark:
            await self.db.delete(bookmark)
            await self.db.flush()
            return True
        return False

    # Highlights
    async def get_highlights(
        self, user_id: UUID, book_id: UUID, page_number: int | None = None
    ) -> list[Highlight]:
        """Get highlights for a book, optionally filtered by page."""
        query = select(Highlight).where(
            and_(
                Highlight.user_id == user_id,
                Highlight.book_id == book_id,
            )
        )
        if page_number is not None:
            query = query.where(Highlight.page_number == page_number)
        query = query.order_by(Highlight.page_number, Highlight.created_at)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_highlight(
        self,
        user_id: UUID,
        book_id: UUID,
        page_number: int,
        text_content: str,
        position: dict,
        color: str,
        note: str | None,
    ) -> Highlight:
        """Create a highlight."""
        highlight = Highlight(
            user_id=user_id,
            book_id=book_id,
            page_number=page_number,
            text_content=text_content,
            position=position,
            color=color,
            note=note,
        )
        self.db.add(highlight)
        await self.db.flush()
        return highlight

    async def update_highlight(self, highlight_id: UUID, user_id: UUID, note: str | None) -> Highlight | None:
        """Update highlight note."""
        query = select(Highlight).where(
            and_(
                Highlight.id == highlight_id,
                Highlight.user_id == user_id,
            )
        )
        result = await self.db.execute(query)
        highlight = result.scalar_one_or_none()
        if highlight:
            highlight.note = note
            await self.db.flush()
        return highlight

    async def delete_highlight(self, highlight_id: UUID, user_id: UUID) -> bool:
        """Delete a highlight."""
        query = select(Highlight).where(
            and_(
                Highlight.id == highlight_id,
                Highlight.user_id == user_id,
            )
        )
        result = await self.db.execute(query)
        highlight = result.scalar_one_or_none()
        if highlight:
            await self.db.delete(highlight)
            await self.db.flush()
            return True
        return False

    # Notes
    async def get_notes(self, user_id: UUID, book_id: UUID) -> list[Note]:
        """Get all notes for a book."""
        query = select(Note).where(
            and_(
                Note.user_id == user_id,
                Note.book_id == book_id,
            )
        ).order_by(Note.page_number.nullsfirst(), Note.created_at)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_note(
        self,
        user_id: UUID,
        book_id: UUID,
        page_number: int | None,
        content: str,
        color: str | None,
    ) -> Note:
        """Create a note."""
        note = Note(
            user_id=user_id,
            book_id=book_id,
            page_number=page_number,
            content=content,
            color=color,
        )
        self.db.add(note)
        await self.db.flush()
        return note

    async def update_note(
        self, note_id: UUID, user_id: UUID, content: str | None, color: str | None
    ) -> Note | None:
        """Update a note."""
        query = select(Note).where(
            and_(
                Note.id == note_id,
                Note.user_id == user_id,
            )
        )
        result = await self.db.execute(query)
        note = result.scalar_one_or_none()
        if note:
            if content is not None:
                note.content = content
            if color is not None:
                note.color = color
            note.updated_at = datetime.now(UTC)
            await self.db.flush()
        return note

    async def delete_note(self, note_id: UUID, user_id: UUID) -> bool:
        """Delete a note."""
        query = select(Note).where(
            and_(
                Note.id == note_id,
                Note.user_id == user_id,
            )
        )
        result = await self.db.execute(query)
        note = result.scalar_one_or_none()
        if note:
            await self.db.delete(note)
            await self.db.flush()
            return True
        return False
