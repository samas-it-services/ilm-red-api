"""Suggestion repository for database operations."""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.suggestion import (
    SuggestionConfig,
    SuggestionFeedback,
    SuggestionNotification,
    SuggestionSystemConfig,
    UserSuggestion,
    UserSuggestionUsage,
)


class SuggestionRepository:
    """Repository for suggestion database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # --- UserSuggestion CRUD ---

    async def create_suggestion(
        self,
        user_id: uuid.UUID,
        suggestion_text: str,
        category: str | None = None,
    ) -> UserSuggestion:
        """Create a new user suggestion."""
        suggestion = UserSuggestion(
            user_id=user_id,
            suggestion_text=suggestion_text,
            category=category,
            status="pending",
            priority="medium",
        )
        self.db.add(suggestion)
        await self.db.flush()
        await self.db.refresh(suggestion)
        return suggestion

    async def get_suggestion_by_id(
        self,
        suggestion_id: uuid.UUID,
    ) -> UserSuggestion | None:
        """Get suggestion by ID."""
        stmt = select(UserSuggestion).where(UserSuggestion.id == suggestion_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_user_suggestions(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[UserSuggestion], int]:
        """List suggestions for a specific user with pagination."""
        conditions = [UserSuggestion.user_id == user_id]

        # Count
        count_stmt = select(func.count(UserSuggestion.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data
        offset = (page - 1) * limit
        stmt = (
            select(UserSuggestion)
            .where(and_(*conditions))
            .order_by(UserSuggestion.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        suggestions = list(result.scalars().all())

        return suggestions, total

    async def list_all_suggestions(
        self,
        status_filter: str | None = None,
        priority_filter: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[UserSuggestion], int]:
        """List all suggestions (admin view) with filtering and pagination."""
        conditions = []

        if status_filter:
            conditions.append(UserSuggestion.status == status_filter)
        if priority_filter:
            conditions.append(UserSuggestion.priority == priority_filter)

        # Count
        count_stmt = select(func.count(UserSuggestion.id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data
        offset = (page - 1) * limit
        stmt = select(UserSuggestion).order_by(UserSuggestion.created_at.desc())
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        suggestions = list(result.scalars().all())

        return suggestions, total

    async def update_suggestion(
        self,
        suggestion: UserSuggestion,
        **kwargs,
    ) -> UserSuggestion:
        """Update suggestion fields."""
        for key, value in kwargs.items():
            if hasattr(suggestion, key) and value is not None:
                setattr(suggestion, key, value)

        suggestion.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(suggestion)
        return suggestion

    # --- SuggestionFeedback ---

    async def create_feedback(
        self,
        suggestion_id: uuid.UUID,
        user_id: uuid.UUID,
        feedback_type: str,
        rating: int | None = None,
        feedback_text: str | None = None,
    ) -> SuggestionFeedback:
        """Create feedback for a suggestion."""
        feedback = SuggestionFeedback(
            suggestion_id=suggestion_id,
            user_id=user_id,
            feedback_type=feedback_type,
            rating=rating,
            feedback_text=feedback_text,
        )
        self.db.add(feedback)
        await self.db.flush()
        await self.db.refresh(feedback)
        return feedback

    # --- SuggestionNotification ---

    async def get_notifications(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[SuggestionNotification], int]:
        """Get notifications for a user with pagination."""
        conditions = [SuggestionNotification.user_id == user_id]

        # Count
        count_stmt = select(func.count(SuggestionNotification.id)).where(
            and_(*conditions)
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data
        offset = (page - 1) * limit
        stmt = (
            select(SuggestionNotification)
            .where(and_(*conditions))
            .order_by(SuggestionNotification.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        notifications = list(result.scalars().all())

        return notifications, total

    async def get_notification_by_id(
        self,
        notification_id: uuid.UUID,
    ) -> SuggestionNotification | None:
        """Get notification by ID."""
        stmt = select(SuggestionNotification).where(
            SuggestionNotification.id == notification_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_notification_read(
        self,
        notification: SuggestionNotification,
    ) -> SuggestionNotification:
        """Mark a notification as read."""
        notification.is_read = True
        await self.db.flush()
        await self.db.refresh(notification)
        return notification

    # --- SuggestionConfig (per-user) ---

    async def get_user_config(
        self,
        user_id: uuid.UUID,
    ) -> SuggestionConfig | None:
        """Get user's suggestion configuration."""
        stmt = select(SuggestionConfig).where(SuggestionConfig.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_user_config(
        self,
        user_id: uuid.UUID,
        **kwargs,
    ) -> SuggestionConfig:
        """Create or update user's suggestion configuration."""
        config = await self.get_user_config(user_id)

        if config:
            for key, value in kwargs.items():
                if hasattr(config, key) and value is not None:
                    setattr(config, key, value)
            config.updated_at = datetime.now(UTC)
        else:
            config = SuggestionConfig(
                user_id=user_id,
                **{k: v for k, v in kwargs.items() if v is not None},
            )
            self.db.add(config)

        await self.db.flush()
        await self.db.refresh(config)
        return config

    # --- SuggestionSystemConfig ---

    async def get_system_config(self) -> SuggestionSystemConfig | None:
        """Get the system suggestion configuration."""
        stmt = select(SuggestionSystemConfig).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_system_config(
        self,
        **kwargs,
    ) -> SuggestionSystemConfig:
        """Create or update system suggestion configuration."""
        config = await self.get_system_config()

        if config:
            for key, value in kwargs.items():
                if hasattr(config, key) and value is not None:
                    setattr(config, key, value)
            config.updated_at = datetime.now(UTC)
        else:
            config = SuggestionSystemConfig(
                **{k: v for k, v in kwargs.items() if v is not None},
            )
            self.db.add(config)

        await self.db.flush()
        await self.db.refresh(config)
        return config

    # --- UserSuggestionUsage ---

    async def get_daily_usage(
        self,
        user_id: uuid.UUID,
        usage_date: date,
    ) -> UserSuggestionUsage | None:
        """Get user's suggestion usage for a specific date."""
        stmt = select(UserSuggestionUsage).where(
            and_(
                UserSuggestionUsage.user_id == user_id,
                UserSuggestionUsage.date == usage_date,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_usage(
        self,
        user_id: uuid.UUID,
        usage_date: date,
    ) -> UserSuggestionUsage:
        """Increment daily usage counter for a user."""
        usage = await self.get_daily_usage(user_id, usage_date)

        if usage:
            usage.usage_count += 1
            usage.updated_at = datetime.now(UTC)
        else:
            usage = UserSuggestionUsage(
                user_id=user_id,
                date=usage_date,
                usage_count=1,
            )
            self.db.add(usage)

        await self.db.flush()
        await self.db.refresh(usage)
        return usage
