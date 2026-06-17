"""Quote repository for database operations."""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import Quote, QuoteView


class QuoteRepository:
    """Repository for Quote database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Quote CRUD operations

    async def create(
        self,
        text: str,
        author: str | None = None,
        source: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        is_featured: bool = False,
        is_active: bool = True,
        display_date: date | None = None,
        created_by: uuid.UUID | None = None,
    ) -> Quote:
        """Create a new quote."""
        quote = Quote(
            text=text,
            author=author,
            source=source,
            category=category,
            tags=tags or [],
            is_featured=is_featured,
            is_active=is_active,
            display_date=display_date,
            created_by=created_by,
        )
        self.db.add(quote)
        await self.db.flush()
        await self.db.refresh(quote)
        return quote

    async def get_by_id(self, quote_id: uuid.UUID) -> Quote | None:
        """Get quote by ID."""
        stmt = select(Quote).where(Quote.id == quote_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_quotes(
        self,
        category: str | None = None,
        is_featured: bool | None = None,
        is_active: bool | None = None,
        search_query: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Quote], int]:
        """List quotes with filtering and pagination."""
        conditions: list = []

        if category:
            conditions.append(Quote.category == category)
        if is_featured is not None:
            conditions.append(Quote.is_featured == is_featured)
        if is_active is not None:
            conditions.append(Quote.is_active == is_active)
        if search_query:
            search_pattern = f"%{search_query}%"
            conditions.append(Quote.text.ilike(search_pattern))

        # Count query
        count_stmt = select(func.count(Quote.id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        offset = (page - 1) * limit
        stmt = (
            select(Quote)
            .order_by(Quote.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.db.execute(stmt)
        quotes = list(result.scalars().all())

        return quotes, total

    async def get_daily_quote(self, target_date: date | None = None) -> Quote | None:
        """Get the quote of the day.

        Looks for a quote with a matching display_date.
        If none found, falls back to a deterministic selection based on the date.
        """
        if target_date is None:
            target_date = date.today()

        # First try to find a quote specifically assigned to this date
        stmt = (
            select(Quote)
            .where(
                and_(
                    Quote.display_date == target_date,
                    Quote.is_active.is_(True),
                )
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        quote = result.scalar_one_or_none()

        if quote:
            return quote

        # Fallback: deterministic selection based on date
        # Use the date's ordinal as a seed for consistent results
        day_ordinal = target_date.toordinal()

        # Count active quotes
        count_stmt = select(func.count(Quote.id)).where(Quote.is_active.is_(True))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        if total == 0:
            return None

        # Pick a quote based on the day
        offset = day_ordinal % total
        stmt = (
            select(Quote)
            .where(Quote.is_active.is_(True))
            .order_by(Quote.id)
            .offset(offset)
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_random_quote(self) -> Quote | None:
        """Get a random active quote."""
        stmt = (
            select(Quote)
            .where(Quote.is_active.is_(True))
            .order_by(func.random())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(
        self,
        quote: Quote,
        **kwargs,
    ) -> Quote:
        """Update quote fields."""
        for key, value in kwargs.items():
            if hasattr(quote, key) and value is not None:
                setattr(quote, key, value)

        quote.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(quote)
        return quote

    async def delete(self, quote: Quote) -> None:
        """Permanently delete a quote."""
        await self.db.delete(quote)
        await self.db.flush()

    async def increment_view_count(self, quote_id: uuid.UUID) -> None:
        """Atomically increment the view count of a quote."""
        stmt = (
            update(Quote)
            .where(Quote.id == quote_id)
            .values(view_count=Quote.view_count + 1)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    # QuoteView operations

    async def record_view(
        self,
        quote_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> QuoteView:
        """Record a view of a quote."""
        view = QuoteView(
            quote_id=quote_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(view)
        await self.db.flush()

        # Also increment the cached view count
        await self.increment_view_count(quote_id)

        return view
