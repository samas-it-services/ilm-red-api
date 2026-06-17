"""Suggestion service for business logic."""

import uuid
from datetime import UTC, date, datetime

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.suggestion_repo import SuggestionRepository
from app.schemas.common import create_pagination
from app.schemas.suggestion import (
    SuggestionConfigResponse,
    SuggestionConfigUpdate,
    SuggestionCreate,
    SuggestionFeedbackCreate,
    SuggestionFeedbackResponse,
    SuggestionListItem,
    SuggestionListResponse,
    SuggestionNotificationListResponse,
    SuggestionNotificationResponse,
    SuggestionResponse,
    SystemConfigResponse,
    SystemConfigUpdate,
)

logger = structlog.get_logger(__name__)


class SuggestionService:
    """Service for suggestion system business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SuggestionRepository(db)

    async def submit_suggestion(
        self,
        user: User,
        data: SuggestionCreate,
    ) -> SuggestionResponse:
        """Submit a new suggestion.

        Checks daily usage limits before creating the suggestion.
        """
        # Check daily usage limit
        today = datetime.now(UTC).date()
        usage = await self.repo.get_daily_usage(user.id, today)
        current_count = usage.usage_count if usage else 0

        # Get user config or system config for limit
        user_config = await self.repo.get_user_config(user.id)
        daily_limit = user_config.daily_limit if user_config else 5

        # Check system config for override
        system_config = await self.repo.get_system_config()
        if system_config and not system_config.system_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Suggestion system is currently disabled",
            )

        if current_count >= daily_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily suggestion limit reached ({daily_limit})",
            )

        # Create suggestion
        suggestion = await self.repo.create_suggestion(
            user_id=user.id,
            suggestion_text=data.suggestion_text,
            category=data.category,
        )

        # Increment usage
        await self.repo.increment_usage(user.id, today)

        await self.db.commit()

        logger.info(
            "Suggestion submitted",
            suggestion_id=str(suggestion.id),
            user_id=str(user.id),
        )

        return SuggestionResponse.model_validate(suggestion)

    async def get_suggestion(
        self,
        suggestion_id: uuid.UUID,
        user: User,
    ) -> SuggestionResponse:
        """Get suggestion by ID. Users can only view their own suggestions."""
        suggestion = await self.repo.get_suggestion_by_id(suggestion_id)

        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suggestion not found",
            )

        if suggestion.user_id != user.id and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        return SuggestionResponse.model_validate(suggestion)

    async def list_user_suggestions(
        self,
        user: User,
        page: int = 1,
        limit: int = 20,
    ) -> SuggestionListResponse:
        """List current user's suggestions."""
        suggestions, total = await self.repo.list_user_suggestions(
            user_id=user.id,
            page=page,
            limit=limit,
        )

        items = [SuggestionListItem.model_validate(s) for s in suggestions]

        return SuggestionListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    async def list_all_suggestions(
        self,
        status_filter: str | None = None,
        priority_filter: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> SuggestionListResponse:
        """List all suggestions (admin view)."""
        suggestions, total = await self.repo.list_all_suggestions(
            status_filter=status_filter,
            priority_filter=priority_filter,
            page=page,
            limit=limit,
        )

        items = [SuggestionListItem.model_validate(s) for s in suggestions]

        return SuggestionListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    async def submit_feedback(
        self,
        suggestion_id: uuid.UUID,
        user: User,
        data: SuggestionFeedbackCreate,
    ) -> SuggestionFeedbackResponse:
        """Submit feedback on a suggestion response."""
        suggestion = await self.repo.get_suggestion_by_id(suggestion_id)

        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suggestion not found",
            )

        if suggestion.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only provide feedback on your own suggestions",
            )

        feedback = await self.repo.create_feedback(
            suggestion_id=suggestion_id,
            user_id=user.id,
            feedback_type=data.feedback_type,
            rating=data.rating,
            feedback_text=data.feedback_text,
        )

        await self.db.commit()

        logger.info(
            "Suggestion feedback submitted",
            suggestion_id=str(suggestion_id),
            user_id=str(user.id),
            feedback_type=data.feedback_type,
        )

        return SuggestionFeedbackResponse.model_validate(feedback)

    async def get_notifications(
        self,
        user: User,
        page: int = 1,
        limit: int = 20,
    ) -> SuggestionNotificationListResponse:
        """Get user's suggestion notifications."""
        notifications, total = await self.repo.get_notifications(
            user_id=user.id,
            page=page,
            limit=limit,
        )

        items = [SuggestionNotificationResponse.model_validate(n) for n in notifications]

        return SuggestionNotificationListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    async def mark_notification_read(
        self,
        notification_id: uuid.UUID,
        user: User,
    ) -> SuggestionNotificationResponse:
        """Mark a notification as read."""
        notification = await self.repo.get_notification_by_id(notification_id)

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )

        if notification.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        notification = await self.repo.mark_notification_read(notification)
        await self.db.commit()

        return SuggestionNotificationResponse.model_validate(notification)

    async def get_user_config(
        self,
        user: User,
    ) -> SuggestionConfigResponse:
        """Get user's suggestion configuration. Creates default if not exists."""
        config = await self.repo.get_user_config(user.id)

        if not config:
            config = await self.repo.upsert_user_config(user_id=user.id)
            await self.db.commit()

        return SuggestionConfigResponse.model_validate(config)

    async def update_user_config(
        self,
        user: User,
        updates: SuggestionConfigUpdate,
    ) -> SuggestionConfigResponse:
        """Update user's suggestion configuration."""
        update_data = {}
        if updates.is_enabled is not None:
            update_data["is_enabled"] = updates.is_enabled
        if updates.ai_model is not None:
            update_data["ai_model"] = updates.ai_model
        if updates.daily_limit is not None:
            update_data["daily_limit"] = updates.daily_limit

        config = await self.repo.upsert_user_config(
            user_id=user.id,
            **update_data,
        )
        await self.db.commit()

        logger.info(
            "Suggestion config updated",
            user_id=str(user.id),
        )

        return SuggestionConfigResponse.model_validate(config)

    async def update_system_config(
        self,
        updates: SystemConfigUpdate,
    ) -> SystemConfigResponse:
        """Update system-wide suggestion configuration. Admin only."""
        update_data = {}
        if updates.system_enabled is not None:
            update_data["system_enabled"] = updates.system_enabled
        if updates.default_ai_model is not None:
            update_data["default_ai_model"] = updates.default_ai_model
        if updates.default_daily_limit is not None:
            update_data["default_daily_limit"] = updates.default_daily_limit
        if updates.available_models is not None:
            update_data["available_models"] = updates.available_models

        config = await self.repo.upsert_system_config(**update_data)
        await self.db.commit()

        logger.info("System suggestion config updated")

        return SystemConfigResponse.model_validate(config)
