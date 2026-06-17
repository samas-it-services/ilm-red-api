"""Help/Documentation service for business logic."""

import uuid

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.help_repo import HelpRepository
from app.schemas.common import create_pagination
from app.schemas.help import (
    AuthorBrief,
    HelpArticleCreate,
    HelpArticleListItem,
    HelpArticleListResponse,
    HelpArticleResponse,
    HelpArticleUpdate,
    HelpCategoryCreate,
    HelpCategoryListResponse,
    HelpCategoryResponse,
    HelpFeedbackCreate,
    HelpFeedbackResponse,
    HelpScreenshotResponse,
    HelpShareCreate,
    HelpShareResponse,
    HelpViewCreate,
)

logger = structlog.get_logger(__name__)


class HelpService:
    """Service for help/documentation business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = HelpRepository(db)

    # ---------- Category Operations ----------

    async def get_categories(self) -> HelpCategoryListResponse:
        """Get all active help categories with article counts."""
        categories = await self.repo.get_categories(active_only=True)

        items = []
        for cat in categories:
            count = await self.repo.get_article_count_by_category(cat.id)
            items.append(
                HelpCategoryResponse(
                    id=cat.id,
                    name=cat.name,
                    slug=cat.slug,
                    description=cat.description,
                    icon=cat.icon,
                    color=cat.color,
                    sort_order=cat.sort_order,
                    is_active=cat.is_active,
                    article_count=count,
                )
            )

        return HelpCategoryListResponse(data=items)

    async def create_category(
        self,
        data: HelpCategoryCreate,
        user: User,
    ) -> HelpCategoryResponse:
        """Create a new help category (admin only)."""
        category = await self.repo.create_category(
            name=data.name,
            slug=data.slug,
            description=data.description,
            icon=data.icon,
            color=data.color,
            sort_order=data.sort_order,
            is_active=data.is_active,
        )
        await self.db.commit()
        logger.info("Help category created", category_id=str(category.id))

        count = await self.repo.get_article_count_by_category(category.id)
        return HelpCategoryResponse(
            id=category.id,
            name=category.name,
            slug=category.slug,
            description=category.description,
            icon=category.icon,
            color=category.color,
            sort_order=category.sort_order,
            is_active=category.is_active,
            article_count=count,
        )

    # ---------- Article Operations ----------

    async def create_article(
        self,
        data: HelpArticleCreate,
        author: User,
    ) -> HelpArticleResponse:
        """Create a new help article (admin only)."""
        # Verify category exists
        category = await self.repo.get_category_by_id(data.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

        article = await self.repo.create_article(
            author_id=author.id,
            category_id=data.category_id,
            title_en=data.title_en,
            content_en=data.content_en,
            title_ur=data.title_ur,
            content_ur=data.content_ur,
            excerpt=data.excerpt,
            tags=data.tags,
            sort_order=data.sort_order,
            is_featured=data.is_featured,
            is_pinned=data.is_pinned,
            status=data.status.value,
            visibility=data.visibility.value,
        )
        await self.db.commit()

        # Reload with relationships
        article = await self.repo.get_article_by_id(article.id)
        logger.info("Help article created", article_id=str(article.id))
        return self._article_to_response(article)

    async def get_article(
        self,
        slug: str,
        user: User | None = None,
    ) -> HelpArticleResponse:
        """Get a help article by slug."""
        article = await self.repo.get_article_by_slug(slug)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Help article not found",
            )

        # Non-published articles only visible to admin
        if article.status != "published":
            if not user or not user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Help article not found",
                )

        return self._article_to_response(article)

    async def get_article_by_id(
        self,
        article_id: uuid.UUID,
        user: User | None = None,
    ) -> HelpArticleResponse:
        """Get a help article by ID."""
        article = await self.repo.get_article_by_id(article_id)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Help article not found",
            )

        if article.status != "published":
            if not user or not user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Help article not found",
                )

        return self._article_to_response(article)

    async def list_articles(
        self,
        user: User | None = None,
        category_id: uuid.UUID | None = None,
        status_filter: str | None = "published",
        search_query: str | None = None,
        is_featured: bool | None = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "sort_order",
        sort_order: str = "asc",
    ) -> HelpArticleListResponse:
        """List help articles with filtering and pagination."""
        # Non-admins can only see published articles
        if not user or not user.is_admin:
            status_filter = "published"

        articles, total = await self.repo.list_articles(
            category_id=category_id,
            status=status_filter,
            search_query=search_query,
            is_featured=is_featured,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        items = [self._article_to_list_item(a) for a in articles]

        return HelpArticleListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    async def update_article(
        self,
        article_id: uuid.UUID,
        data: HelpArticleUpdate,
        user: User,
    ) -> HelpArticleResponse:
        """Update a help article (admin only)."""
        article = await self.repo.get_article_by_id(article_id)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Help article not found",
            )

        # Verify new category if changing
        if data.category_id:
            category = await self.repo.get_category_by_id(data.category_id)
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found",
                )

        update_data = {}
        for field in [
            "category_id", "title_en", "content_en", "title_ur", "content_ur",
            "excerpt", "tags", "sort_order", "is_featured", "is_pinned",
        ]:
            value = getattr(data, field, None)
            if value is not None:
                update_data[field] = value

        if data.status is not None:
            update_data["status"] = data.status.value
        if data.visibility is not None:
            update_data["visibility"] = data.visibility.value

        if update_data:
            article = await self.repo.update_article(article, **update_data)

        await self.db.commit()

        article = await self.repo.get_article_by_id(article.id)
        logger.info("Help article updated", article_id=str(article_id))
        return self._article_to_response(article)

    async def delete_article(
        self,
        article_id: uuid.UUID,
        user: User,
    ) -> None:
        """Delete a help article (admin only)."""
        article = await self.repo.get_article_by_id(article_id)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Help article not found",
            )

        await self.repo.delete_article(article)
        await self.db.commit()
        logger.info("Help article deleted", article_id=str(article_id), by_user=str(user.id))

    # ---------- Search ----------

    async def search_articles(
        self,
        query: str,
        language: str = "en",
        page: int = 1,
        limit: int = 20,
    ) -> HelpArticleListResponse:
        """Search published help articles."""
        articles, total = await self.repo.search_articles(
            query=query,
            language=language,
            page=page,
            limit=limit,
        )

        items = [self._article_to_list_item(a) for a in articles]

        return HelpArticleListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    # ---------- View Tracking ----------

    async def track_view(
        self,
        article_id: uuid.UUID,
        user: User | None = None,
        view_data: HelpViewCreate | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Track an article view."""
        article = await self.repo.get_article_by_id(article_id)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Help article not found",
            )

        language = view_data.language if view_data else "en"

        await self.repo.track_view(
            article_id=article_id,
            user_id=user.id if user else None,
            language=language,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.db.commit()

    # ---------- Feedback ----------

    async def add_feedback(
        self,
        article_id: uuid.UUID,
        data: HelpFeedbackCreate,
        user: User,
    ) -> HelpFeedbackResponse:
        """Add feedback for an article."""
        article = await self.repo.get_article_by_id(article_id)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Help article not found",
            )

        feedback = await self.repo.add_feedback(
            article_id=article_id,
            user_id=user.id,
            feedback_type=data.feedback_type.value,
            feedback_text=data.feedback_text,
        )
        await self.db.commit()
        return HelpFeedbackResponse.model_validate(feedback)

    # ---------- Share Tracking ----------

    async def track_share(
        self,
        article_id: uuid.UUID,
        data: HelpShareCreate,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> HelpShareResponse:
        """Track an article share."""
        article = await self.repo.get_article_by_id(article_id)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Help article not found",
            )

        share = await self.repo.track_share(
            article_id=article_id,
            user_id=user.id,
            share_method=data.share_method,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.db.commit()
        return HelpShareResponse.model_validate(share)

    # ---------- Converters ----------

    def _article_to_response(self, article) -> HelpArticleResponse:
        """Convert HelpArticle model to response schema."""
        screenshots = [
            HelpScreenshotResponse(
                id=s.id,
                image_url=s.image_url,
                alt_text=s.alt_text,
                caption=s.caption,
                sort_order=s.sort_order,
            )
            for s in article.screenshots
        ]

        return HelpArticleResponse(
            id=article.id,
            category_id=article.category_id,
            slug=article.slug,
            status=article.status,
            title_en=article.title_en,
            content_en=article.content_en,
            title_ur=article.title_ur,
            content_ur=article.content_ur,
            excerpt=article.excerpt,
            tags=article.tags,
            sort_order=article.sort_order,
            is_featured=article.is_featured,
            is_pinned=article.is_pinned,
            view_count=article.view_count,
            helpful_count=article.helpful_count,
            not_helpful_count=article.not_helpful_count,
            visibility=article.visibility,
            published_at=article.published_at,
            author=AuthorBrief(
                id=article.author.id,
                username=article.author.username,
                display_name=article.author.display_name,
                avatar_url=article.author.avatar_url,
            ),
            screenshots=screenshots,
            created_at=article.created_at,
            updated_at=article.updated_at,
        )

    def _article_to_list_item(self, article) -> HelpArticleListItem:
        """Convert HelpArticle model to list item schema."""
        return HelpArticleListItem(
            id=article.id,
            category_id=article.category_id,
            slug=article.slug,
            status=article.status,
            title_en=article.title_en,
            title_ur=article.title_ur,
            excerpt=article.excerpt,
            tags=article.tags,
            sort_order=article.sort_order,
            is_featured=article.is_featured,
            is_pinned=article.is_pinned,
            view_count=article.view_count,
            helpful_count=article.helpful_count,
            not_helpful_count=article.not_helpful_count,
            published_at=article.published_at,
            author=AuthorBrief(
                id=article.author.id,
                username=article.author.username,
                display_name=article.author.display_name,
                avatar_url=article.author.avatar_url,
            ),
            created_at=article.created_at,
        )
