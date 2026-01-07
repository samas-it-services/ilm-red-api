"""Book repository for database operations."""

import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.book import Book, Rating, Favorite
from app.models.user import User


class BookRepository:
    """Repository for Book database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Book CRUD operations

    async def create(
        self,
        owner_id: uuid.UUID,
        title: str,
        file_path: str,
        file_hash: str,
        file_size: int,
        file_type: str,
        original_filename: str | None = None,
        author: str | None = None,
        description: str | None = None,
        category: str = "other",
        visibility: str = "private",
        language: str = "en",
        isbn: str | None = None,
    ) -> Book:
        """Create a new book."""
        book = Book(
            owner_id=owner_id,
            title=title,
            author=author,
            description=description,
            category=category,
            visibility=visibility,
            language=language,
            isbn=isbn,
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            file_type=file_type,
            original_filename=original_filename,
            status="processing",
        )
        self.db.add(book)
        await self.db.flush()
        await self.db.refresh(book)
        return book

    async def get_by_id(
        self,
        book_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Book | None:
        """Get book by ID."""
        stmt = (
            select(Book)
            .options(joinedload(Book.owner))
            .where(Book.id == book_id)
        )

        if not include_deleted:
            stmt = stmt.where(Book.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_hash(
        self,
        file_hash: str,
        owner_id: uuid.UUID,
    ) -> Book | None:
        """Get book by file hash and owner (for duplicate detection)."""
        stmt = (
            select(Book)
            .where(
                and_(
                    Book.file_hash == file_hash,
                    Book.owner_id == owner_id,
                    Book.deleted_at.is_(None),
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_books(
        self,
        user_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
        category: str | None = None,
        visibility: str | None = None,
        status: str | None = None,
        search_query: str | None = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> tuple[list[Book], int]:
        """List books with filtering, pagination, and sorting.

        Args:
            user_id: Current user (for visibility filtering)
            owner_id: Filter by specific owner
            category: Filter by category
            visibility: Filter by visibility (only if user is owner)
            status: Filter by status
            search_query: Search in title and author
            page: Page number (1-indexed)
            limit: Items per page
            sort_by: Field to sort by
            sort_order: Sort direction

        Returns:
            Tuple of (books list, total count)
        """
        # Base query
        base_conditions = [Book.deleted_at.is_(None)]

        # Owner filter
        if owner_id:
            base_conditions.append(Book.owner_id == owner_id)

        # Category filter
        if category:
            base_conditions.append(Book.category == category)

        # Status filter
        if status:
            base_conditions.append(Book.status == status)

        # Visibility filter based on user context
        if user_id:
            # User can see:
            # 1. All public books
            # 2. Their own books (any visibility)
            visibility_condition = or_(
                Book.visibility == "public",
                Book.owner_id == user_id,
            )
            if visibility:
                # If specific visibility requested, user must be owner
                base_conditions.append(Book.visibility == visibility)
                base_conditions.append(Book.owner_id == user_id)
            else:
                base_conditions.append(visibility_condition)
        else:
            # Unauthenticated: only public books
            base_conditions.append(Book.visibility == "public")

        # Search filter
        if search_query:
            search_pattern = f"%{search_query}%"
            search_condition = or_(
                Book.title.ilike(search_pattern),
                Book.author.ilike(search_pattern),
            )
            base_conditions.append(search_condition)

        # Count query
        count_stmt = select(func.count(Book.id)).where(and_(*base_conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        stmt = (
            select(Book)
            .options(joinedload(Book.owner))
            .where(and_(*base_conditions))
        )

        # Sorting
        sort_column = getattr(Book, sort_by, Book.created_at)
        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Pagination
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        books = list(result.scalars().unique().all())

        return books, total

    async def update(
        self,
        book: Book,
        **kwargs,
    ) -> Book:
        """Update book fields."""
        for key, value in kwargs.items():
            if hasattr(book, key) and value is not None:
                setattr(book, key, value)

        book.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(book)
        return book

    async def update_status(
        self,
        book_id: uuid.UUID,
        status: str,
        error_message: str | None = None,
        page_count: int | None = None,
    ) -> None:
        """Update book processing status."""
        values: dict = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if error_message is not None:
            values["processing_error"] = error_message
        if page_count is not None:
            values["page_count"] = page_count

        stmt = update(Book).where(Book.id == book_id).values(**values)
        await self.db.execute(stmt)
        await self.db.flush()

    async def soft_delete(self, book: Book) -> None:
        """Soft delete a book."""
        book.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def update_stats(
        self,
        book_id: uuid.UUID,
        views_increment: int = 0,
        downloads_increment: int = 0,
    ) -> None:
        """Update book stats atomically."""
        book = await self.get_by_id(book_id)
        if book:
            stats = book.stats.copy()
            stats["views"] = stats.get("views", 0) + views_increment
            stats["downloads"] = stats.get("downloads", 0) + downloads_increment
            book.stats = stats
            await self.db.flush()

    # Rating operations

    async def add_rating(
        self,
        book_id: uuid.UUID,
        user_id: uuid.UUID,
        rating_value: int,
        review: str | None = None,
    ) -> Rating:
        """Add or update a rating for a book."""
        # Check if rating already exists
        existing = await self.get_user_rating(book_id, user_id)

        if existing:
            # Update existing rating
            existing.rating = rating_value
            existing.review = review
            existing.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            await self.db.refresh(existing)
            rating = existing
        else:
            # Create new rating
            rating = Rating(
                book_id=book_id,
                user_id=user_id,
                rating=rating_value,
                review=review,
            )
            self.db.add(rating)
            await self.db.flush()
            await self.db.refresh(rating)

        # Update book stats
        await self._update_book_rating_stats(book_id)

        return rating

    async def get_user_rating(
        self,
        book_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Rating | None:
        """Get user's rating for a book."""
        stmt = (
            select(Rating)
            .options(joinedload(Rating.user))
            .where(
                and_(
                    Rating.book_id == book_id,
                    Rating.user_id == user_id,
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_ratings(
        self,
        book_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Rating], int]:
        """Get ratings for a book with pagination."""
        # Count
        count_stmt = select(func.count(Rating.id)).where(Rating.book_id == book_id)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data
        offset = (page - 1) * limit
        stmt = (
            select(Rating)
            .options(joinedload(Rating.user))
            .where(Rating.book_id == book_id)
            .order_by(Rating.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        ratings = list(result.scalars().unique().all())

        return ratings, total

    async def delete_rating(self, rating: Rating) -> None:
        """Delete a rating."""
        book_id = rating.book_id
        await self.db.delete(rating)
        await self.db.flush()

        # Update book stats
        await self._update_book_rating_stats(book_id)

    async def _update_book_rating_stats(self, book_id: uuid.UUID) -> None:
        """Update book's rating statistics."""
        # Calculate new stats
        stmt = select(
            func.count(Rating.id),
            func.coalesce(func.avg(Rating.rating), 0),
        ).where(Rating.book_id == book_id)

        result = await self.db.execute(stmt)
        row = result.one()
        rating_count, rating_avg = row

        # Update book
        book = await self.get_by_id(book_id)
        if book:
            stats = book.stats.copy()
            stats["rating_count"] = rating_count
            stats["rating_avg"] = round(float(rating_avg), 2)
            book.stats = stats
            await self.db.flush()

    # Favorite operations

    async def add_favorite(
        self,
        user_id: uuid.UUID,
        book_id: uuid.UUID,
    ) -> Favorite:
        """Add book to user's favorites."""
        # Check if already favorited
        existing = await self.get_favorite(user_id, book_id)
        if existing:
            return existing

        favorite = Favorite(user_id=user_id, book_id=book_id)
        self.db.add(favorite)
        await self.db.flush()
        return favorite

    async def remove_favorite(
        self,
        user_id: uuid.UUID,
        book_id: uuid.UUID,
    ) -> bool:
        """Remove book from user's favorites. Returns True if removed."""
        favorite = await self.get_favorite(user_id, book_id)
        if favorite:
            await self.db.delete(favorite)
            await self.db.flush()
            return True
        return False

    async def get_favorite(
        self,
        user_id: uuid.UUID,
        book_id: uuid.UUID,
    ) -> Favorite | None:
        """Get a specific favorite."""
        stmt = select(Favorite).where(
            and_(
                Favorite.user_id == user_id,
                Favorite.book_id == book_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_favorites(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Book], int]:
        """Get user's favorite books with pagination."""
        # Count
        count_stmt = select(func.count(Favorite.book_id)).where(
            Favorite.user_id == user_id
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data - join to get books
        offset = (page - 1) * limit
        stmt = (
            select(Book)
            .options(joinedload(Book.owner))
            .join(Favorite, Favorite.book_id == Book.id)
            .where(
                and_(
                    Favorite.user_id == user_id,
                    Book.deleted_at.is_(None),
                )
            )
            .order_by(Favorite.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        books = list(result.scalars().unique().all())

        return books, total

    async def is_favorited(
        self,
        user_id: uuid.UUID,
        book_id: uuid.UUID,
    ) -> bool:
        """Check if a book is in user's favorites."""
        favorite = await self.get_favorite(user_id, book_id)
        return favorite is not None
