"""Addon service for business logic."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.addon_repo import AddonRepository
from app.schemas.addon import (
    AddonConfigUpdate,
    AddonInstallRequest,
    AddonListResponse,
    AddonRegistryResponse,
    AddonReviewCreate,
    AddonReviewResponse,
    BookClubAddonConfigResponse,
    GlobalAddonConfigResponse,
    GlobalAddonConfigUpdate,
)
from app.schemas.common import PaginatedResponse, create_pagination


class AddonService:
    """Service for addon operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AddonRepository(db)

    # --- Marketplace ---

    async def list_marketplace(
        self,
        category: str | None = None,
        status_filter: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> AddonListResponse:
        """List addons in the marketplace with filters and pagination."""
        addons, total = await self.repo.list_addons(
            category=category, status=status_filter, search=search, page=page, limit=limit,
        )
        return AddonListResponse(
            data=[AddonRegistryResponse.model_validate(a) for a in addons],
            pagination=create_pagination(page, limit, total),
        )

    async def get_addon_detail(self, addon_id: uuid.UUID) -> AddonRegistryResponse:
        """Get detailed info for a single addon."""
        addon = await self.repo.get_addon_by_id(addon_id)
        if not addon:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Addon not found")
        return AddonRegistryResponse.model_validate(addon)

    # --- Reviews ---

    async def create_review(
        self, addon_id: uuid.UUID, data: AddonReviewCreate, user: User
    ) -> AddonReviewResponse:
        """Create a review for an addon. One review per user per addon."""
        addon = await self.repo.get_addon_by_id(addon_id)
        if not addon:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Addon not found")

        existing = await self.repo.get_existing_review(addon_id, user.id)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already reviewed this addon")

        review = await self.repo.create_review(
            addon_id=addon_id,
            user_id=user.id,
            rating=data.rating,
            title=data.title,
            content=data.content,
        )
        await self.db.commit()
        return AddonReviewResponse.model_validate(review)

    async def list_reviews(
        self, addon_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> PaginatedResponse[AddonReviewResponse]:
        """List reviews for an addon."""
        addon = await self.repo.get_addon_by_id(addon_id)
        if not addon:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Addon not found")

        reviews, total = await self.repo.list_reviews(addon_id, page, limit)
        return PaginatedResponse(
            data=[AddonReviewResponse.model_validate(r) for r in reviews],
            pagination=create_pagination(page, limit, total),
        )

    # --- Club Installation ---

    async def install_addon_for_club(
        self, club_id: uuid.UUID, data: AddonInstallRequest, user: User
    ) -> BookClubAddonConfigResponse:
        """Install an addon for a book club.

        Validates:
        - Addon exists and is active
        - Not already installed
        - Global max installations not exceeded
        """
        addon = await self.repo.get_addon_by_id(data.addon_id)
        if not addon:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Addon not found")
        if addon.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Addon is not active")

        # Check if already installed
        existing = await self.repo.get_club_addon_config(data.addon_id, club_id)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Addon is already installed for this club")

        # Check global config max installations
        global_config = await self.repo.get_global_config(data.addon_id)
        if global_config and global_config.max_installations_per_club is not None:
            current_count = await self.repo.count_club_installations(data.addon_id)
            if current_count >= global_config.max_installations_per_club:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Maximum installations reached for this addon",
                )

        entry = await self.repo.install_addon(
            addon_id=data.addon_id,
            book_club_id=club_id,
            configured_by=user.id,
            config=data.config,
        )
        await self.db.commit()
        return BookClubAddonConfigResponse.model_validate(entry)

    async def uninstall_addon_from_club(
        self, club_id: uuid.UUID, addon_id: uuid.UUID, user: User
    ) -> None:
        """Uninstall an addon from a book club."""
        removed = await self.repo.uninstall_addon(addon_id, club_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Addon is not installed for this club",
            )
        await self.db.commit()

    async def update_club_addon_config(
        self,
        club_id: uuid.UUID,
        addon_id: uuid.UUID,
        data: AddonConfigUpdate,
        user: User,
    ) -> BookClubAddonConfigResponse:
        """Update addon config for a club."""
        existing = await self.repo.get_club_addon_config(addon_id, club_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Addon is not installed for this club",
            )

        config = await self.repo.update_club_addon_config(
            addon_id=addon_id,
            book_club_id=club_id,
            configured_by=user.id,
            **data.model_dump(exclude_unset=True),
        )
        await self.db.commit()
        return BookClubAddonConfigResponse.model_validate(config)

    async def list_club_addons(
        self, club_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> PaginatedResponse[BookClubAddonConfigResponse]:
        """List installed addons for a club."""
        configs, total = await self.repo.list_club_addons(club_id, page, limit)
        return PaginatedResponse(
            data=[BookClubAddonConfigResponse.model_validate(c) for c in configs],
            pagination=create_pagination(page, limit, total),
        )

    async def list_available_for_club(
        self, club_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> AddonListResponse:
        """List addons available for installation in a club."""
        addons, total = await self.repo.list_available_for_club(club_id, page, limit)
        return AddonListResponse(
            data=[AddonRegistryResponse.model_validate(a) for a in addons],
            pagination=create_pagination(page, limit, total),
        )

    # --- Admin: Global Config ---

    async def get_global_config(self, addon_id: uuid.UUID) -> GlobalAddonConfigResponse:
        """Get global config for an addon (admin only)."""
        config = await self.repo.get_global_config(addon_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Global config not found for this addon",
            )
        return GlobalAddonConfigResponse.model_validate(config)

    async def update_global_config(
        self, data: GlobalAddonConfigUpdate, user: User
    ) -> GlobalAddonConfigResponse:
        """Create or update global addon config (admin only)."""
        addon = await self.repo.get_addon_by_id(data.addon_id)
        if not addon:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Addon not found")

        config = await self.repo.update_global_config(
            addon_id=data.addon_id,
            configured_by=user.id,
            **data.model_dump(exclude={"addon_id"}, exclude_unset=True),
        )
        await self.db.commit()
        return GlobalAddonConfigResponse.model_validate(config)
