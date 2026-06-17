"""Expert configuration repository for database operations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expert import ExpertConfiguration


class ExpertRepository:
    """Repository for ExpertConfiguration database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        name: str,
        category: str,
        field: str | None = None,
        traits: list | None = None,
        preferred_model: str | None = None,
        preferred_provider: str | None = None,
        system_prompt_template: str | None = None,
        model_config_data: dict | None = None,
        is_active: bool = True,
    ) -> ExpertConfiguration:
        """Create a new expert configuration."""
        expert = ExpertConfiguration(
            name=name,
            category=category,
            field=field,
            traits=traits or [],
            preferred_model=preferred_model,
            preferred_provider=preferred_provider,
            system_prompt_template=system_prompt_template,
            model_config_data=model_config_data or {},
            is_active=is_active,
        )
        self.db.add(expert)
        await self.db.flush()
        await self.db.refresh(expert)
        return expert

    async def get_by_id(self, expert_id: uuid.UUID) -> ExpertConfiguration | None:
        """Get expert configuration by ID."""
        stmt = select(ExpertConfiguration).where(ExpertConfiguration.id == expert_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_experts(
        self,
        category: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[ExpertConfiguration], int]:
        """List expert configurations with filtering and pagination.

        Args:
            category: Filter by category
            is_active: Filter by active status
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (experts list, total count)
        """
        conditions = []

        if category:
            conditions.append(ExpertConfiguration.category == category)

        if is_active is not None:
            conditions.append(ExpertConfiguration.is_active == is_active)

        # Count query
        count_stmt = select(func.count(ExpertConfiguration.id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        stmt = select(ExpertConfiguration)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(ExpertConfiguration.created_at.desc())

        # Pagination
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        experts = list(result.scalars().all())

        return experts, total

    async def update(
        self,
        expert: ExpertConfiguration,
        **kwargs,
    ) -> ExpertConfiguration:
        """Update expert configuration fields."""
        for key, value in kwargs.items():
            if hasattr(expert, key) and value is not None:
                setattr(expert, key, value)

        expert.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(expert)
        return expert

    async def delete(self, expert: ExpertConfiguration) -> None:
        """Delete an expert configuration."""
        await self.db.delete(expert)
        await self.db.flush()
