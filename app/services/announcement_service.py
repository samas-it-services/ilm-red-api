"""Feature announcement service for business logic."""

import uuid

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.announcement_repo import AnnouncementRepository
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementListItem,
    AnnouncementListResponse,
    AnnouncementResponse,
    AnnouncementUpdate,
    UnreadCountResponse,
)
from app.schemas.common import create_pagination

logger = structlog.get_logger(__name__)


class AnnouncementService:
    """Service for feature announcement business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AnnouncementRepository(db)

    # ---------- CRUD ----------

    async def create_announcement(
        self,
        data: AnnouncementCreate,
        user: User,
    ) -> AnnouncementResponse:
        """Create a new feature announcement (admin only)."""
        announcement = await self.repo.create(
            title=data.title,
            content=data.content,
            excerpt=data.excerpt,
            featured_image_url=data.featured_image_url,
            status=data.status.value,
            priority=data.priority.value,
            is_featured=data.is_featured,
            is_pinned=data.is_pinned,
        )
        await self.db.commit()

        logger.info(
            "Announcement created",
            announcement_id=str(announcement.id),
            by_user=str(user.id),
        )
        return AnnouncementResponse.model_validate(announcement)

    async def get_announcement(
        self,
        slug: str,
        user: User | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AnnouncementResponse:
        """Get announcement by slug, auto-tracking view."""
        announcement = await self.repo.get_by_slug(slug)
        if not announcement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Announcement not found",
            )

        # Non-published only visible to admins
        if announcement.status != "published":
            if not user or not user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Announcement not found",
                )

        # Auto-track view
        await self.repo.track_view(
            announcement_id=announcement.id,
            user_id=user.id if user else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.db.commit()

        # Refresh to get updated view_count
        announcement = await self.repo.get_by_id(announcement.id)
        return AnnouncementResponse.model_validate(announcement)

    async def get_announcement_by_id(
        self,
        announcement_id: uuid.UUID,
        user: User | None = None,
    ) -> AnnouncementResponse:
        """Get announcement by ID."""
        announcement = await self.repo.get_by_id(announcement_id)
        if not announcement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Announcement not found",
            )

        if announcement.status != "published":
            if not user or not user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Announcement not found",
                )

        return AnnouncementResponse.model_validate(announcement)

    async def list_announcements(
        self,
        user: User | None = None,
        status_filter: str | None = "published",
        priority: str | None = None,
        is_featured: bool | None = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "published_at",
        sort_order: str = "desc",
    ) -> AnnouncementListResponse:
        """List announcements with filtering and pagination."""
        # Non-admins can only see published
        if not user or not user.is_admin:
            status_filter = "published"

        announcements, total = await self.repo.list_announcements(
            status=status_filter,
            priority=priority,
            is_featured=is_featured,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        items = [AnnouncementListItem.model_validate(a) for a in announcements]

        return AnnouncementListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    async def update_announcement(
        self,
        announcement_id: uuid.UUID,
        data: AnnouncementUpdate,
        user: User,
    ) -> AnnouncementResponse:
        """Update a feature announcement (admin only)."""
        announcement = await self.repo.get_by_id(announcement_id)
        if not announcement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Announcement not found",
            )

        update_data = {}
        for field in ["title", "content", "excerpt", "featured_image_url", "is_featured", "is_pinned"]:
            value = getattr(data, field, None)
            if value is not None:
                update_data[field] = value

        if data.status is not None:
            update_data["status"] = data.status.value
        if data.priority is not None:
            update_data["priority"] = data.priority.value

        if update_data:
            announcement = await self.repo.update(announcement, **update_data)

        await self.db.commit()

        logger.info(
            "Announcement updated",
            announcement_id=str(announcement_id),
            by_user=str(user.id),
        )
        return AnnouncementResponse.model_validate(announcement)

    async def delete_announcement(
        self,
        announcement_id: uuid.UUID,
        user: User,
    ) -> None:
        """Delete a feature announcement (admin only)."""
        announcement = await self.repo.get_by_id(announcement_id)
        if not announcement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Announcement not found",
            )

        await self.repo.delete(announcement)
        await self.db.commit()

        logger.info(
            "Announcement deleted",
            announcement_id=str(announcement_id),
            by_user=str(user.id),
        )

    # ---------- Unread Count ----------

    async def get_unread_count(self, user: User) -> UnreadCountResponse:
        """Get the number of unread announcements for the current user."""
        unread_count, total_published = await self.repo.get_unread_count(user.id)
        return UnreadCountResponse(
            unread_count=unread_count,
            total_published=total_published,
        )
