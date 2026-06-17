"""Help/Documentation repository for database operations."""

import re
import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.help import (
    HelpArticle,
    HelpArticleFeedback,
    HelpArticleScreenshot,
    HelpArticleShare,
    HelpArticleView,
    HelpCategory,
)


def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from a title."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug


class HelpRepository:
    """Repository for help/documentation database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Slug Helpers ----------

    async def _ensure_unique_article_slug(
        self,
        slug: str,
        exclude_id: uuid.UUID | None = None,
    ) -> str:
        """Ensure article slug is unique, appending a suffix if necessary."""
        base_slug = slug
        counter = 1
        while True:
            stmt = select(func.count(HelpArticle.id)).where(HelpArticle.slug == slug)
            if exclude_id:
                stmt = stmt.where(HelpArticle.id != exclude_id)
            result = await self.db.execute(stmt)
            if result.scalar_one() == 0:
                return slug
            slug = f"{base_slug}-{counter}"
            counter += 1

    async def _ensure_unique_category_slug(
        self,
        slug: str,
        exclude_id: uuid.UUID | None = None,
    ) -> str:
        """Ensure category slug is unique."""
        base_slug = slug
        counter = 1
        while True:
            stmt = select(func.count(HelpCategory.id)).where(HelpCategory.slug == slug)
            if exclude_id:
                stmt = stmt.where(HelpCategory.id != exclude_id)
            result = await self.db.execute(stmt)
            if result.scalar_one() == 0:
                return slug
            slug = f"{base_slug}-{counter}"
            counter += 1

    # ---------- Category CRUD ----------

    async def create_category(self, **kwargs) -> HelpCategory:
        """Create a help category."""
        if not kwargs.get("slug"):
            kwargs["slug"] = generate_slug(kwargs["name"])
        kwargs["slug"] = await self._ensure_unique_category_slug(kwargs["slug"])

        category = HelpCategory(**kwargs)
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def get_category_by_id(self, category_id: uuid.UUID) -> HelpCategory | None:
        """Get help category by ID."""
        stmt = select(HelpCategory).where(HelpCategory.id == category_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_categories(self, active_only: bool = True) -> list[HelpCategory]:
        """Get all help categories ordered by sort_order."""
        stmt = select(HelpCategory)
        if active_only:
            stmt = stmt.where(HelpCategory.is_active.is_(True))
        stmt = stmt.order_by(HelpCategory.sort_order.asc(), HelpCategory.name.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_article_count_by_category(self, category_id: uuid.UUID) -> int:
        """Get count of published articles in a category."""
        stmt = select(func.count(HelpArticle.id)).where(
            and_(
                HelpArticle.category_id == category_id,
                HelpArticle.status == "published",
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    # ---------- Article CRUD ----------

    async def create_article(
        self,
        author_id: uuid.UUID,
        category_id: uuid.UUID,
        title_en: str,
        content_en: str,
        title_ur: str | None = None,
        content_ur: str | None = None,
        excerpt: str | None = None,
        tags: list[str] | None = None,
        sort_order: int = 0,
        is_featured: bool = False,
        is_pinned: bool = False,
        status: str = "draft",
        visibility: str = "public",
    ) -> HelpArticle:
        """Create a new help article."""
        slug = generate_slug(title_en)
        slug = await self._ensure_unique_article_slug(slug)

        published_at = datetime.now(UTC) if status == "published" else None

        article = HelpArticle(
            author_id=author_id,
            category_id=category_id,
            slug=slug,
            title_en=title_en,
            content_en=content_en,
            title_ur=title_ur,
            content_ur=content_ur,
            excerpt=excerpt,
            tags=tags or [],
            sort_order=sort_order,
            is_featured=is_featured,
            is_pinned=is_pinned,
            status=status,
            visibility=visibility,
            published_at=published_at,
            published_by=author_id if published_at else None,
        )
        self.db.add(article)
        await self.db.flush()
        await self.db.refresh(article)
        return article

    async def get_article_by_id(self, article_id: uuid.UUID) -> HelpArticle | None:
        """Get help article by ID with relationships."""
        stmt = (
            select(HelpArticle)
            .options(
                joinedload(HelpArticle.author),
                joinedload(HelpArticle.screenshots),
            )
            .where(HelpArticle.id == article_id)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_article_by_slug(self, slug: str) -> HelpArticle | None:
        """Get help article by slug with relationships."""
        stmt = (
            select(HelpArticle)
            .options(
                joinedload(HelpArticle.author),
                joinedload(HelpArticle.screenshots),
            )
            .where(HelpArticle.slug == slug)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def list_articles(
        self,
        category_id: uuid.UUID | None = None,
        status: str | None = None,
        search_query: str | None = None,
        is_featured: bool | None = None,
        tags: list[str] | None = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "sort_order",
        sort_order: Literal["asc", "desc"] = "asc",
    ) -> tuple[list[HelpArticle], int]:
        """List help articles with filtering and pagination."""
        base_conditions = []

        if category_id:
            base_conditions.append(HelpArticle.category_id == category_id)

        if status:
            base_conditions.append(HelpArticle.status == status)

        if is_featured is not None:
            base_conditions.append(HelpArticle.is_featured == is_featured)

        if search_query:
            search_pattern = f"%{search_query}%"
            base_conditions.append(
                or_(
                    HelpArticle.title_en.ilike(search_pattern),
                    HelpArticle.content_en.ilike(search_pattern),
                    HelpArticle.title_ur.ilike(search_pattern),
                    HelpArticle.excerpt.ilike(search_pattern),
                )
            )

        if tags:
            # Match articles that have any of the specified tags
            for tag in tags:
                base_conditions.append(HelpArticle.tags.any(tag))

        where_clause = and_(*base_conditions) if base_conditions else True

        # Count query
        count_stmt = select(func.count(HelpArticle.id)).where(where_clause)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        stmt = (
            select(HelpArticle)
            .options(joinedload(HelpArticle.author))
            .where(where_clause)
        )

        # Sorting — pinned first, then by sort field
        sort_col = getattr(HelpArticle, sort_by, HelpArticle.sort_order)
        if sort_order == "desc":
            stmt = stmt.order_by(HelpArticle.is_pinned.desc(), sort_col.desc())
        else:
            stmt = stmt.order_by(HelpArticle.is_pinned.desc(), sort_col.asc())

        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        articles = list(result.unique().scalars().all())

        return articles, total

    async def update_article(self, article: HelpArticle, **kwargs) -> HelpArticle:
        """Update help article fields."""
        for key, value in kwargs.items():
            if hasattr(article, key) and value is not None:
                setattr(article, key, value)

        # Set published_at when publishing
        if kwargs.get("status") == "published" and article.published_at is None:
            article.published_at = datetime.now(UTC)

        article.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(article)
        return article

    async def delete_article(self, article: HelpArticle) -> None:
        """Delete a help article."""
        await self.db.delete(article)
        await self.db.flush()

    # ---------- View Tracking ----------

    async def track_view(
        self,
        article_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        language: str = "en",
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Track an article view."""
        view = HelpArticleView(
            article_id=article_id,
            user_id=user_id,
            language=language,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(view)

        # Update denormalized count
        stmt = update(HelpArticle).where(HelpArticle.id == article_id).values(
            view_count=HelpArticle.view_count + 1
        )
        await self.db.execute(stmt)
        await self.db.flush()

    # ---------- Feedback ----------

    async def add_feedback(
        self,
        article_id: uuid.UUID,
        user_id: uuid.UUID,
        feedback_type: str,
        feedback_text: str | None = None,
    ) -> HelpArticleFeedback:
        """Add feedback for an article."""
        feedback = HelpArticleFeedback(
            article_id=article_id,
            user_id=user_id,
            feedback_type=feedback_type,
            feedback_text=feedback_text,
        )
        self.db.add(feedback)
        await self.db.flush()
        await self.db.refresh(feedback)

        # Update denormalized counts
        await self._update_feedback_counts(article_id)
        return feedback

    async def _update_feedback_counts(self, article_id: uuid.UUID) -> None:
        """Update denormalized feedback counts on the article."""
        helpful_stmt = select(func.count(HelpArticleFeedback.id)).where(
            and_(
                HelpArticleFeedback.article_id == article_id,
                HelpArticleFeedback.feedback_type == "helpful",
            )
        )
        not_helpful_stmt = select(func.count(HelpArticleFeedback.id)).where(
            and_(
                HelpArticleFeedback.article_id == article_id,
                HelpArticleFeedback.feedback_type == "not_helpful",
            )
        )

        helpful_result = await self.db.execute(helpful_stmt)
        not_helpful_result = await self.db.execute(not_helpful_stmt)

        stmt = (
            update(HelpArticle)
            .where(HelpArticle.id == article_id)
            .values(
                helpful_count=helpful_result.scalar_one(),
                not_helpful_count=not_helpful_result.scalar_one(),
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

    # ---------- Share Tracking ----------

    async def track_share(
        self,
        article_id: uuid.UUID,
        user_id: uuid.UUID,
        share_method: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> HelpArticleShare:
        """Track an article share."""
        share = HelpArticleShare(
            article_id=article_id,
            user_id=user_id,
            share_method=share_method,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(share)
        await self.db.flush()
        await self.db.refresh(share)
        return share

    # ---------- Search ----------

    async def search_articles(
        self,
        query: str,
        language: str = "en",
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[HelpArticle], int]:
        """Search published help articles."""
        search_pattern = f"%{query}%"

        conditions = [HelpArticle.status == "published"]

        if language == "ur":
            conditions.append(
                or_(
                    HelpArticle.title_ur.ilike(search_pattern),
                    HelpArticle.content_ur.ilike(search_pattern),
                )
            )
        else:
            conditions.append(
                or_(
                    HelpArticle.title_en.ilike(search_pattern),
                    HelpArticle.content_en.ilike(search_pattern),
                    HelpArticle.excerpt.ilike(search_pattern),
                )
            )

        where_clause = and_(*conditions)

        # Count
        count_stmt = select(func.count(HelpArticle.id)).where(where_clause)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data
        offset = (page - 1) * limit
        stmt = (
            select(HelpArticle)
            .options(joinedload(HelpArticle.author))
            .where(where_clause)
            .order_by(HelpArticle.view_count.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        articles = list(result.unique().scalars().all())

        return articles, total
