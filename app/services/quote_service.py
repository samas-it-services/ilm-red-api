"""Quote service for business logic."""

import uuid
from datetime import date

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import Quote
from app.models.user import User
from app.repositories.quote_repo import QuoteRepository
from app.schemas.common import create_pagination
from app.schemas.quote import (
    QuoteCreate,
    QuoteListResponse,
    QuoteResponse,
    QuoteUpdate,
)

logger = structlog.get_logger(__name__)


class QuoteService:
    """Service for quote-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = QuoteRepository(db)

    async def create_quote(
        self,
        admin: User,
        data: QuoteCreate,
    ) -> QuoteResponse:
        """Create a new quote (admin only).

        Args:
            admin: Admin user creating the quote
            data: Quote creation data

        Returns:
            Created quote response
        """
        quote = await self.repo.create(
            text=data.text,
            author=data.author,
            source=data.source,
            category=data.category,
            tags=data.tags,
            is_featured=data.is_featured,
            is_active=data.is_active,
            display_date=data.display_date,
            created_by=admin.id,
        )

        await self.db.commit()

        logger.info(
            "quote_created",
            quote_id=str(quote.id),
            admin_id=str(admin.id),
            author=data.author,
        )

        return self._quote_to_response(quote)

    async def get_quote(self, quote_id: uuid.UUID) -> QuoteResponse:
        """Get a quote by ID.

        Args:
            quote_id: Quote UUID

        Returns:
            Quote response

        Raises:
            HTTPException: If quote not found
        """
        quote = await self.repo.get_by_id(quote_id)

        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quote not found",
            )

        return self._quote_to_response(quote)

    async def list_quotes(
        self,
        category: str | None = None,
        is_featured: bool | None = None,
        is_active: bool | None = None,
        search_query: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> QuoteListResponse:
        """List quotes with filtering and pagination.

        Args:
            category: Optional category filter
            is_featured: Optional featured filter
            is_active: Optional active filter
            search_query: Optional text search
            page: Page number
            limit: Items per page

        Returns:
            Paginated quote list
        """
        quotes, total = await self.repo.list_quotes(
            category=category,
            is_featured=is_featured,
            is_active=is_active,
            search_query=search_query,
            page=page,
            limit=limit,
        )

        items = [self._quote_to_response(q) for q in quotes]

        return QuoteListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    async def get_daily_quote(
        self,
        target_date: date | None = None,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> QuoteResponse:
        """Get the daily quote.

        Args:
            target_date: Date to get quote for (defaults to today)
            user_id: Optional viewer user ID
            ip_address: Optional viewer IP address
            user_agent: Optional viewer user agent

        Returns:
            Daily quote response

        Raises:
            HTTPException: If no quotes available
        """
        quote = await self.repo.get_daily_quote(target_date)

        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No daily quote available",
            )

        # Record the view
        await self.repo.record_view(
            quote_id=quote.id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.db.commit()

        return self._quote_to_response(quote)

    async def get_random_quote(
        self,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> QuoteResponse:
        """Get a random active quote.

        Args:
            user_id: Optional viewer user ID
            ip_address: Optional viewer IP address
            user_agent: Optional viewer user agent

        Returns:
            Random quote response

        Raises:
            HTTPException: If no quotes available
        """
        quote = await self.repo.get_random_quote()

        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No quotes available",
            )

        # Record the view
        await self.repo.record_view(
            quote_id=quote.id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.db.commit()

        return self._quote_to_response(quote)

    async def update_quote(
        self,
        quote_id: uuid.UUID,
        data: QuoteUpdate,
    ) -> QuoteResponse:
        """Update a quote (admin only).

        Args:
            quote_id: Quote UUID
            data: Update data

        Returns:
            Updated quote response

        Raises:
            HTTPException: If quote not found
        """
        quote = await self.repo.get_by_id(quote_id)

        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quote not found",
            )

        # Build update dict
        update_data = {}
        if data.text is not None:
            update_data["text"] = data.text
        if data.author is not None:
            update_data["author"] = data.author
        if data.source is not None:
            update_data["source"] = data.source
        if data.category is not None:
            update_data["category"] = data.category
        if data.tags is not None:
            update_data["tags"] = data.tags
        if data.is_featured is not None:
            update_data["is_featured"] = data.is_featured
        if data.is_active is not None:
            update_data["is_active"] = data.is_active
        if data.display_date is not None:
            update_data["display_date"] = data.display_date

        if update_data:
            quote = await self.repo.update(quote, **update_data)
            await self.db.commit()

        logger.info(
            "quote_updated",
            quote_id=str(quote_id),
            fields_updated=list(update_data.keys()),
        )

        return self._quote_to_response(quote)

    async def delete_quote(self, quote_id: uuid.UUID) -> None:
        """Delete a quote (admin only).

        Args:
            quote_id: Quote UUID

        Raises:
            HTTPException: If quote not found
        """
        quote = await self.repo.get_by_id(quote_id)

        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quote not found",
            )

        await self.repo.delete(quote)
        await self.db.commit()

        logger.info("quote_deleted", quote_id=str(quote_id))

    # Helper methods

    def _quote_to_response(self, quote: Quote) -> QuoteResponse:
        """Convert Quote model to response schema."""
        return QuoteResponse(
            id=quote.id,
            text=quote.text,
            author=quote.author,
            source=quote.source,
            category=quote.category,
            tags=quote.tags or [],
            is_featured=quote.is_featured,
            is_active=quote.is_active,
            display_date=quote.display_date,
            view_count=quote.view_count,
            created_by=quote.created_by,
            created_at=quote.created_at,
            updated_at=quote.updated_at,
        )
