"""Book Extra repository for database operations."""

import uuid
from typing import Literal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.book_extra import BookExtra


class BookExtraRepository:
    """Repository for BookExtra database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        book_id: uuid.UUID,
        type: str,
        title: str,
        content: dict,
        url: str | None = None,
        created_by: uuid.UUID | None = None,
        status: str = "published",
    ) -> BookExtra:
        """Create a new book extra."""
        extra = BookExtra(
            book_id=book_id,
            type=type,
            title=title,
            content=content,
            url=url,
            created_by=created_by,
            status=status,
        )
        self.db.add(extra)
        await self.db.flush()
        await self.db.refresh(extra)
        return extra

    async def get_by_id(
        self,
        extra_id: uuid.UUID,
    ) -> BookExtra | None:
        """Get book extra by ID."""
        stmt = (
            select(BookExtra)
            .options(joinedload(BookExtra.creator))
            .where(BookExtra.id == extra_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_book(
        self,
        book_id: uuid.UUID,
        type: str | None = None,
        status: str | None = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> tuple[list[BookExtra], int]:
        """List book extras for a book with filtering and pagination."""
        # Base query
        base_conditions = [BookExtra.book_id == book_id]

        if type:
            base_conditions.append(BookExtra.type == type)

        if status:
            base_conditions.append(BookExtra.status == status)

        # Count query
        count_stmt = select(func.count(BookExtra.id)).where(and_(*base_conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        stmt = (
            select(BookExtra)
            .where(and_(*base_conditions))
        )

        # Sorting
        sort_column = getattr(BookExtra, sort_by, BookExtra.created_at)
        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Pagination
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        extras = list(result.scalars().all())

        return extras, total

    async def update(
        self,
        extra: BookExtra,
        **kwargs,
    ) -> BookExtra:
        """Update book extra fields."""
        for key, value in kwargs.items():
            if hasattr(extra, key) and value is not None:
                setattr(extra, key, value)

        await self.db.flush()
        await self.db.refresh(extra)
        return extra

    async def delete(self, extra: BookExtra) -> None:
        """Delete a book extra."""
        await self.db.delete(extra)
        await self.db.flush()
