"""Admin settings repository for database operations."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_settings import AdminSetting, MysticalMessage


class AdminSettingsRepository:
    """Repository for admin settings database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[AdminSetting]:
        """Get all settings."""
        stmt = select(AdminSetting).order_by(AdminSetting.setting_key)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_key(self, key: str) -> AdminSetting | None:
        """Get setting by key."""
        stmt = select(AdminSetting).where(AdminSetting.setting_key == key)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        key: str,
        value: dict,
        description: str | None = None,
        updated_by: uuid.UUID | None = None,
    ) -> AdminSetting:
        """Create or update a setting."""
        existing = await self.get_by_key(key)
        if existing:
            existing.setting_value = value
            if description is not None:
                existing.description = description
            existing.updated_by = updated_by
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            setting = AdminSetting(
                setting_key=key,
                setting_value=value,
                description=description,
                updated_by=updated_by,
            )
            self.db.add(setting)
            await self.db.flush()
            await self.db.refresh(setting)
            return setting

    # Mystical messages
    async def get_mystical_messages(self, active_only: bool = True) -> list[MysticalMessage]:
        """Get mystical messages."""
        stmt = select(MysticalMessage)
        if active_only:
            stmt = stmt.where(MysticalMessage.is_active.is_(True))
        stmt = stmt.order_by(MysticalMessage.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_mystical_message_stats(self) -> dict:
        """Get stats for mystical messages."""
        total_stmt = select(func.count()).select_from(MysticalMessage)
        active_stmt = select(func.count()).select_from(MysticalMessage).where(
            MysticalMessage.is_active.is_(True)
        )
        categories_stmt = (
            select(MysticalMessage.category)
            .where(MysticalMessage.category.isnot(None))
            .distinct()
        )

        total = (await self.db.execute(total_stmt)).scalar() or 0
        active = (await self.db.execute(active_stmt)).scalar() or 0
        categories_result = await self.db.execute(categories_stmt)
        categories = [r[0] for r in categories_result.all()]

        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "categories": categories,
        }
