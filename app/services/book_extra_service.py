"""Book Extra service for business logic."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book_extra import BookExtra
from app.models.user import User
from app.repositories.book_extra_repo import BookExtraRepository
from app.repositories.book_repo import BookRepository
from app.schemas.book_extra import (
    BookExtraCreate,
    BookExtraListResponse,
    BookExtraResponse,
    BookExtraUpdate,
)
from app.schemas.common import create_pagination


class BookExtraService:
    """Service for book extra business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BookExtraRepository(db)
        self.book_repo = BookRepository(db)

    async def create_extra(
        self,
        book_id: uuid.UUID,
        extra_data: BookExtraCreate,
        user: User,
    ) -> BookExtraResponse:
        """Create a new book extra."""
        # Verify book exists and user has access (owner only for now)
        book = await self.book_repo.get_by_id(book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        # Only book owner or admin can add extras
        # Assuming admin check is done via role dependency, here we check ownership
        # If we want to allow others, we need a permission model.
        # For now, let's restrict to owner.
        if book.owner_id != user.id:
             # Ideally check for admin role here too, but that might be in the API layer
             # For simplicity, if not owner, 403.
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the book owner can add extras",
            )

        extra = await self.repo.create(
            book_id=book_id,
            type=extra_data.type.value,
            title=extra_data.title,
            content=extra_data.content,
            url=str(extra_data.url) if extra_data.url else None,
            created_by=user.id,
            status=extra_data.status.value,
        )
        await self.db.commit()
        return self._to_response(extra)

    async def get_extra(
        self,
        extra_id: uuid.UUID,
        user: User | None = None,
    ) -> BookExtraResponse:
        """Get book extra by ID."""
        extra = await self.repo.get_by_id(extra_id)
        if not extra:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book extra not found",
            )

        # Check access to the book
        # If public, anyone can see. If private, only owner.
        # Ideally we fetch the book to check visibility.
        # But `extra.book` relationship might not be loaded unless we eager load it.
        # The repo `get_by_id` joins `creator` but not `book`.
        # Let's fetch book separately or trust the caller?
        # Better to be safe.
        book = await self.book_repo.get_by_id(extra.book_id)
        if not book:
             # Should not happen due to FK
             raise HTTPException(status_code=404, detail="Book not found")

        if book.visibility != "public":
            if not user or book.owner_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied",
                )

        return self._to_response(extra)

    async def list_extras(
        self,
        book_id: uuid.UUID,
        user: User | None = None,
        type: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> BookExtraListResponse:
        """List extras for a book."""
        book = await self.book_repo.get_by_id(book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found",
            )

        # Access check
        if book.visibility != "public":
            if not user or book.owner_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied",
                )

        extras, total = await self.repo.list_by_book(
            book_id=book_id,
            type=type,
            status="published" if (not user or book.owner_id != user.id) else None, # Only owner sees drafts
            page=page,
            limit=limit,
        )

        return BookExtraListResponse(
            data=[self._to_response(e) for e in extras],
            pagination=create_pagination(page, limit, total),
        )

    async def update_extra(
        self,
        extra_id: uuid.UUID,
        updates: BookExtraUpdate,
        user: User,
    ) -> BookExtraResponse:
        """Update a book extra."""
        extra = await self.repo.get_by_id(extra_id)
        if not extra:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book extra not found",
            )

        if extra.created_by != user.id:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the creator can update this extra",
            )

        update_data = {}
        if updates.type is not None:
            update_data["type"] = updates.type.value
        if updates.title is not None:
            update_data["title"] = updates.title
        if updates.content is not None:
            update_data["content"] = updates.content
        if updates.url is not None:
            update_data["url"] = str(updates.url)
        if updates.status is not None:
            update_data["status"] = updates.status.value

        if update_data:
            extra = await self.repo.update(extra, **update_data)
            await self.db.commit()

        return self._to_response(extra)

    async def delete_extra(
        self,
        extra_id: uuid.UUID,
        user: User,
    ) -> None:
        """Delete a book extra."""
        extra = await self.repo.get_by_id(extra_id)
        if not extra:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book extra not found",
            )

        if extra.created_by != user.id:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the creator can delete this extra",
            )

        await self.repo.delete(extra)
        await self.db.commit()

    def _to_response(self, extra: BookExtra) -> BookExtraResponse:
        """Convert model to response schema."""
        return BookExtraResponse(
            id=extra.id,
            book_id=extra.book_id,
            type=extra.type,
            title=extra.title,
            content=extra.content,
            url=extra.url,
            status=extra.status,
            created_by=extra.created_by,
            created_at=extra.created_at,
            updated_at=extra.updated_at,
        )
