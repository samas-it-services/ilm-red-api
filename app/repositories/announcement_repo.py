"""Feature announcement repository for database operations."""

import re
import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.announcement import FeatureAnnouncement, FeatureAnnouncementView


def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from a title."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug


class AnnouncementRepository:
    """Repository for feature announcement database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Slug Helpers ----------

    async def _ensure_unique_slug(
        self,
        slug: str,
        exclude_id: uuid.UUID | None = None,
    ) -> str:
        """Ensure slug is unique, appending a suffix if necessary."""
        base_slug = slug
        counter = 1
        while True:
            stmt = select(func.count(FeatureAnnouncement.id)).where(
                FeatureAnnouncement.slug == slug
            )
            if exclude_id:
                stmt = stmt.where(FeatureAnnouncement.id != exclude_id)
            result = await self.db.execute(stmt)
            if result.scalar_one() == 0:
                return slug
            slug = f"{base_slug}-{counter}"
            counter += 1

    # ---------- Announcement CRUD ----------

    async def create(
        self,
        title: str,
        content: str,
        excerpt: str | None = None,
        featured_image_url: str | None = None,
        status: str = "draft",
        priority: str = "normal",
        is_featured: bool = False,
        is_pinned: bool = False,
    ) -> FeatureAnnouncement:
        """Create a new feature announcement."""
        slug = generate_slug(title)
        slug = await self._ensure_unique_slug(slug)

        published_at = datetime.now(UTC) if status == "published" else None

        announcement = FeatureAnnouncement(
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt,
            featured_image_url=featured_image_url,
            status=status,
            priority=priority,
            is_featured=is_featured,
            is_pinned=is_pinned,
            published_at=published_at,
        )
        self.db.add(announcement)
        await self.db.flush()
        await self.db.refresh(announcement)
        return announcement

    async def get_by_id(self, announcement_id: uuid.UUID) -> FeatureAnnouncement | None:
        """Get announcement by ID."""
        stmt = select(FeatureAnnouncement).where(
            FeatureAnnouncement.id == announcement_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> FeatureAnnouncement | None:
        """Get announcement by slug."""
        stmt = select(FeatureAnnouncement).where(FeatureAnnouncement.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_announcements(
        self,
        status: str | None = None,
        priority: str | None = None,
        is_featured: bool | None = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "published_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> tuple[list[FeatureAnnouncement], int]:
        """List announcements with filtering and pagination."""
        base_conditions = []

        if status:
            base_conditions.append(FeatureAnnouncement.status == status)

        if priority:
            base_conditions.append(FeatureAnnouncement.priority == priority)

        if is_featured is not None:
            base_conditions.append(FeatureAnnouncement.is_featured == is_featured)

        where_clause = and_(*base_conditions) if base_conditions else True

        # Count query
        count_stmt = select(func.count(FeatureAnnouncement.id)).where(where_clause)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        stmt = select(FeatureAnnouncement).where(where_clause)

        # Sorting — pinned first, then by sort field
        sort_column = getattr(FeatureAnnouncement, sort_by, FeatureAnnouncement.published_at)
        if sort_order == "desc":
            stmt = stmt.order_by(
                FeatureAnnouncement.is_pinned.desc(),
                sort_column.desc(),
            )
        else:
            stmt = stmt.order_by(
                FeatureAnnouncement.is_pinned.desc(),
                sort_column.asc(),
            )

        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        announcements = list(result.scalars().all())

        return announcements, total

    async def update(self, announcement: FeatureAnnouncement, **kwargs) -> FeatureAnnouncement:
        """Update announcement fields."""
        for key, value in kwargs.items():
            if hasattr(announcement, key) and value is not None:
                setattr(announcement, key, value)

        # Set published_at when publishing
        if kwargs.get("status") == "published" and announcement.published_at is None:
            announcement.published_at = datetime.now(UTC)

        announcement.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(announcement)
        return announcement

    async def delete(self, announcement: FeatureAnnouncement) -> None:
        """Delete an announcement."""
        await self.db.delete(announcement)
        await self.db.flush()

    # ---------- View Tracking ----------

    async def track_view(
        self,
        announcement_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Track an announcement view."""
        view = FeatureAnnouncementView(
            announcement_id=announcement_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(view)

        # Update denormalized count
        stmt = (
            update(FeatureAnnouncement)
            .where(FeatureAnnouncement.id == announcement_id)
            .values(view_count=FeatureAnnouncement.view_count + 1)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def has_user_viewed(
        self,
        announcement_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Check if a user has viewed an announcement."""
        stmt = select(func.count(FeatureAnnouncementView.id)).where(
            and_(
                FeatureAnnouncementView.announcement_id == announcement_id,
                FeatureAnnouncementView.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one() > 0

    async def get_unread_count(self, user_id: uuid.UUID) -> tuple[int, int]:
        """Get count of unread published announcements for a user.

        Returns:
            Tuple of (unread_count, total_published)
        """
        # Total published announcements
        total_stmt = select(func.count(FeatureAnnouncement.id)).where(
            FeatureAnnouncement.status == "published"
        )
        total_result = await self.db.execute(total_stmt)
        total_published = total_result.scalar_one()

        # Viewed announcement IDs for this user
        viewed_stmt = select(FeatureAnnouncementView.announcement_id).where(
            FeatureAnnouncementView.user_id == user_id
        ).distinct()

        # Unread = published announcements not in user's views
        unread_stmt = select(func.count(FeatureAnnouncement.id)).where(
            and_(
                FeatureAnnouncement.status == "published",
                FeatureAnnouncement.id.not_in(viewed_stmt),
            )
        )
        unread_result = await self.db.execute(unread_stmt)
        unread_count = unread_result.scalar_one()

        return unread_count, total_published
