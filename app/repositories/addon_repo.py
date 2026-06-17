"""Addon repository for database operations."""

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.addon import (
    AddonRegistry,
    AddonReview,
    BookClubAddonConfig,
    GlobalAddonConfig,
)


class AddonRepository:
    """Repository for addon database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Marketplace / Registry ---

    async def list_addons(
        self,
        category: str | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[AddonRegistry], int]:
        """List addons with optional filtering and pagination."""
        conditions = []

        if category:
            conditions.append(AddonRegistry.category == category)
        if status:
            conditions.append(AddonRegistry.status == status)
        else:
            # Default to active addons only
            conditions.append(AddonRegistry.status == "active")
        if search:
            pattern = f"%{search}%"
            conditions.append(AddonRegistry.name.ilike(pattern))

        where_clause = and_(*conditions) if conditions else True

        count_stmt = select(func.count(AddonRegistry.id)).where(where_clause)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(AddonRegistry)
            .where(where_clause)
            .order_by(AddonRegistry.download_count.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_addon_by_id(self, addon_id: uuid.UUID) -> AddonRegistry | None:
        """Get addon by ID."""
        stmt = select(AddonRegistry).where(AddonRegistry.id == addon_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_addon_by_slug(self, slug: str) -> AddonRegistry | None:
        """Get addon by slug."""
        stmt = select(AddonRegistry).where(AddonRegistry.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # --- Reviews ---

    async def create_review(
        self,
        addon_id: uuid.UUID,
        user_id: uuid.UUID,
        rating: int,
        title: str | None = None,
        content: str | None = None,
    ) -> AddonReview:
        """Create a new addon review."""
        review = AddonReview(
            addon_id=addon_id,
            user_id=user_id,
            rating=rating,
            title=title,
            content=content,
        )
        self.db.add(review)
        await self.db.flush()
        await self.db.refresh(review)

        # Update addon rating stats
        await self._update_addon_rating_stats(addon_id)
        return review

    async def get_existing_review(
        self, addon_id: uuid.UUID, user_id: uuid.UUID
    ) -> AddonReview | None:
        """Check if user already reviewed this addon."""
        stmt = select(AddonReview).where(
            and_(AddonReview.addon_id == addon_id, AddonReview.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_reviews(
        self, addon_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> tuple[list[AddonReview], int]:
        """List reviews for an addon with pagination."""
        count_stmt = select(func.count(AddonReview.id)).where(
            AddonReview.addon_id == addon_id
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(AddonReview)
            .where(AddonReview.addon_id == addon_id)
            .order_by(AddonReview.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def _update_addon_rating_stats(self, addon_id: uuid.UUID) -> None:
        """Recalculate addon rating and review count."""
        stmt = select(
            func.count(AddonReview.id),
            func.coalesce(func.avg(AddonReview.rating), 0),
        ).where(AddonReview.addon_id == addon_id)
        result = await self.db.execute(stmt)
        row = result.one()
        review_count, avg_rating = row

        addon = await self.get_addon_by_id(addon_id)
        if addon:
            addon.review_count = review_count
            addon.rating = round(float(avg_rating), 2)
            await self.db.flush()

    # --- Global Config ---

    async def get_global_config(self, addon_id: uuid.UUID) -> GlobalAddonConfig | None:
        """Get global config for an addon."""
        stmt = select(GlobalAddonConfig).where(GlobalAddonConfig.addon_id == addon_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_global_configs(self) -> list[GlobalAddonConfig]:
        """List all global addon configurations."""
        stmt = select(GlobalAddonConfig).order_by(GlobalAddonConfig.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_global_config(
        self, addon_id: uuid.UUID, configured_by: uuid.UUID | None = None, **kwargs
    ) -> GlobalAddonConfig:
        """Create or update global config for an addon."""
        config = await self.get_global_config(addon_id)
        if config:
            for key, value in kwargs.items():
                if hasattr(config, key) and value is not None:
                    setattr(config, key, value)
            if configured_by:
                config.configured_by = configured_by
            await self.db.flush()
            await self.db.refresh(config)
        else:
            config = GlobalAddonConfig(
                addon_id=addon_id, configured_by=configured_by, **kwargs
            )
            self.db.add(config)
            await self.db.flush()
            await self.db.refresh(config)
        return config

    # --- Book Club Addon Config ---

    async def get_club_addon_config(
        self, addon_id: uuid.UUID, book_club_id: uuid.UUID
    ) -> BookClubAddonConfig | None:
        """Get club-specific addon config."""
        stmt = select(BookClubAddonConfig).where(
            and_(
                BookClubAddonConfig.addon_id == addon_id,
                BookClubAddonConfig.book_club_id == book_club_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_club_addon_config(
        self,
        addon_id: uuid.UUID,
        book_club_id: uuid.UUID,
        configured_by: uuid.UUID | None = None,
        **kwargs,
    ) -> BookClubAddonConfig:
        """Update club addon config."""
        config = await self.get_club_addon_config(addon_id, book_club_id)
        if not config:
            config = BookClubAddonConfig(
                addon_id=addon_id,
                book_club_id=book_club_id,
                configured_by=configured_by,
                **kwargs,
            )
            self.db.add(config)
            await self.db.flush()
            await self.db.refresh(config)
        else:
            for key, value in kwargs.items():
                if hasattr(config, key) and value is not None:
                    setattr(config, key, value)
            if configured_by:
                config.configured_by = configured_by
            await self.db.flush()
            await self.db.refresh(config)
        return config

    async def install_addon(
        self,
        addon_id: uuid.UUID,
        book_club_id: uuid.UUID,
        configured_by: uuid.UUID | None = None,
        config: dict | None = None,
    ) -> BookClubAddonConfig:
        """Install an addon for a book club (create config entry)."""
        entry = BookClubAddonConfig(
            addon_id=addon_id,
            book_club_id=book_club_id,
            is_available=True,
            is_enabled_by_default=True,
            default_config=config or {},
            configured_by=configured_by,
        )
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)

        # Increment download count
        addon = await self.get_addon_by_id(addon_id)
        if addon:
            addon.download_count += 1
            await self.db.flush()

        return entry

    async def uninstall_addon(
        self, addon_id: uuid.UUID, book_club_id: uuid.UUID
    ) -> bool:
        """Uninstall an addon from a book club (remove config entry)."""
        config = await self.get_club_addon_config(addon_id, book_club_id)
        if config:
            await self.db.delete(config)
            await self.db.flush()
            return True
        return False

    async def list_club_addons(
        self, book_club_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> tuple[list[BookClubAddonConfig], int]:
        """List installed addons for a club."""
        count_stmt = select(func.count(BookClubAddonConfig.id)).where(
            BookClubAddonConfig.book_club_id == book_club_id
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(BookClubAddonConfig)
            .where(BookClubAddonConfig.book_club_id == book_club_id)
            .order_by(BookClubAddonConfig.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def list_available_for_club(
        self, book_club_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> tuple[list[AddonRegistry], int]:
        """List addons available for a club (active, not yet installed)."""
        installed_subq = (
            select(BookClubAddonConfig.addon_id)
            .where(BookClubAddonConfig.book_club_id == book_club_id)
        )

        conditions = [
            AddonRegistry.status == "active",
            AddonRegistry.id.notin_(installed_subq),
        ]

        count_stmt = select(func.count(AddonRegistry.id)).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(AddonRegistry)
            .where(and_(*conditions))
            .order_by(AddonRegistry.download_count.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def count_club_installations(self, addon_id: uuid.UUID) -> int:
        """Count how many clubs have installed a given addon."""
        stmt = select(func.count(BookClubAddonConfig.id)).where(
            BookClubAddonConfig.addon_id == addon_id
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
