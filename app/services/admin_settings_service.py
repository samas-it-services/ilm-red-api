"""Admin settings service for business logic."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_settings_repo import AdminSettingsRepository
from app.schemas.admin_settings import (
    AdminSettingResponse,
    MysticalMessageResponse,
    MysticalMessageStats,
)


class AdminSettingsService:
    """Service for admin settings operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AdminSettingsRepository(db)

    async def get_all_settings(self) -> list[AdminSettingResponse]:
        """Get all settings."""
        settings = await self.repo.get_all()
        return [AdminSettingResponse.model_validate(s) for s in settings]

    async def get_setting(self, key: str) -> AdminSettingResponse | None:
        """Get a setting by key."""
        setting = await self.repo.get_by_key(key)
        if setting:
            return AdminSettingResponse.model_validate(setting)
        return None

    async def upsert_setting(
        self,
        key: str,
        value: dict,
        description: str | None = None,
        updated_by: uuid.UUID | None = None,
    ) -> AdminSettingResponse:
        """Create or update a setting."""
        setting = await self.repo.upsert(key, value, description, updated_by)
        return AdminSettingResponse.model_validate(setting)

    async def get_mystical_messages(self) -> list[MysticalMessageResponse]:
        """Get active mystical messages."""
        messages = await self.repo.get_mystical_messages()
        return [MysticalMessageResponse.model_validate(m) for m in messages]

    async def get_mystical_message_stats(self) -> MysticalMessageStats:
        """Get mystical message statistics."""
        stats = await self.repo.get_mystical_message_stats()
        return MysticalMessageStats(**stats)
