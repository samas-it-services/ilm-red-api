"""Expert configuration service for business logic."""

import uuid

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.expert_repo import ExpertRepository
from app.schemas.common import create_pagination
from app.schemas.expert import (
    ExpertConfigCreate,
    ExpertConfigListItem,
    ExpertConfigListResponse,
    ExpertConfigResponse,
    ExpertConfigUpdate,
)

logger = structlog.get_logger(__name__)


class ExpertService:
    """Service for expert configuration business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ExpertRepository(db)

    async def create_expert(
        self,
        data: ExpertConfigCreate,
    ) -> ExpertConfigResponse:
        """Create a new expert configuration."""
        expert = await self.repo.create(
            name=data.name,
            category=data.category,
            field=data.field,
            traits=data.traits,
            preferred_model=data.preferred_model,
            preferred_provider=data.preferred_provider,
            system_prompt_template=data.system_prompt_template,
            model_config_data=data.model_config_data,
            is_active=data.is_active,
        )
        await self.db.commit()

        logger.info(
            "Expert configuration created",
            expert_id=str(expert.id),
            name=expert.name,
            category=expert.category,
        )

        return ExpertConfigResponse.model_validate(expert)

    async def get_expert(
        self,
        expert_id: uuid.UUID,
    ) -> ExpertConfigResponse:
        """Get expert configuration by ID."""
        expert = await self.repo.get_by_id(expert_id)

        if not expert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expert configuration not found",
            )

        return ExpertConfigResponse.model_validate(expert)

    async def list_experts(
        self,
        category: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> ExpertConfigListResponse:
        """List expert configurations with filtering and pagination."""
        experts, total = await self.repo.list_experts(
            category=category,
            is_active=is_active,
            page=page,
            limit=limit,
        )

        items = [ExpertConfigListItem.model_validate(e) for e in experts]

        return ExpertConfigListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    async def update_expert(
        self,
        expert_id: uuid.UUID,
        updates: ExpertConfigUpdate,
    ) -> ExpertConfigResponse:
        """Update an expert configuration."""
        expert = await self.repo.get_by_id(expert_id)

        if not expert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expert configuration not found",
            )

        # Build update dict from non-None fields
        update_data = {}
        for field_name in [
            "name",
            "category",
            "field",
            "traits",
            "preferred_model",
            "preferred_provider",
            "system_prompt_template",
            "model_config_data",
            "is_active",
        ]:
            value = getattr(updates, field_name, None)
            if value is not None:
                update_data[field_name] = value

        if update_data:
            expert = await self.repo.update(expert, **update_data)
            await self.db.commit()

        logger.info(
            "Expert configuration updated",
            expert_id=str(expert_id),
        )

        return ExpertConfigResponse.model_validate(expert)

    async def delete_expert(
        self,
        expert_id: uuid.UUID,
    ) -> None:
        """Delete an expert configuration."""
        expert = await self.repo.get_by_id(expert_id)

        if not expert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expert configuration not found",
            )

        await self.repo.delete(expert)
        await self.db.commit()

        logger.info(
            "Expert configuration deleted",
            expert_id=str(expert_id),
        )
