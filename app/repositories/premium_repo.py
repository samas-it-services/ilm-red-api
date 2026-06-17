"""Premium repository for database operations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.premium import (
    PremiumFeature,
    PremiumRequest,
    StripePaymentIntent,
    UserPremiumSubscription,
    UserUploadLimit,
)


class PremiumRepository:
    """Repository for premium-related database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Premium Request Operations
    # ========================================================================

    async def create_request(
        self,
        user_id: uuid.UUID,
        name: str,
        email: str,
        organization: str | None = None,
        user_type: str | None = None,
        current_usage: str | None = None,
        interested_features: list[str] | None = None,
        use_case: str | None = None,
        team_size: str | None = None,
        budget: str | None = None,
        timeline: str | None = None,
        additional_notes: str | None = None,
    ) -> PremiumRequest:
        """Create a new premium request.

        Args:
            user_id: Requesting user's ID
            name: Contact name
            email: Contact email
            organization: Organization name
            user_type: Type of user
            current_usage: Current platform usage description
            interested_features: List of interested premium features
            use_case: Primary use case
            team_size: Team size
            budget: Budget range
            timeline: Upgrade timeline
            additional_notes: Extra notes

        Returns:
            Created premium request
        """
        request = PremiumRequest(
            user_id=user_id,
            name=name,
            email=email,
            organization=organization,
            user_type=user_type,
            current_usage=current_usage,
            interested_features=interested_features,
            use_case=use_case,
            team_size=team_size,
            budget=budget,
            timeline=timeline,
            additional_notes=additional_notes,
        )
        self.db.add(request)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def get_request_by_id(self, request_id: uuid.UUID) -> PremiumRequest | None:
        """Get a premium request by ID."""
        stmt = select(PremiumRequest).where(PremiumRequest.id == request_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_request(self, user_id: uuid.UUID) -> PremiumRequest | None:
        """Get the most recent premium request for a user."""
        stmt = (
            select(PremiumRequest)
            .where(PremiumRequest.user_id == user_id)
            .order_by(PremiumRequest.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_request(
        self,
        request: PremiumRequest,
        **kwargs,
    ) -> PremiumRequest:
        """Update a premium request with the given fields.

        Args:
            request: The premium request to update
            **kwargs: Fields to update

        Returns:
            Updated premium request
        """
        for key, value in kwargs.items():
            if hasattr(request, key) and value is not None:
                setattr(request, key, value)
        request.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def list_requests(
        self,
        status: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[PremiumRequest], int]:
        """List premium requests with optional status filter and pagination.

        Args:
            status: Filter by status
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (requests list, total count)
        """
        conditions = []
        if status:
            conditions.append(PremiumRequest.status == status)

        where_clause = and_(*conditions) if conditions else True

        # Count query
        count_stmt = select(func.count(PremiumRequest.id)).where(where_clause)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        offset = (page - 1) * limit
        stmt = (
            select(PremiumRequest)
            .where(where_clause)
            .order_by(PremiumRequest.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        requests = list(result.scalars().all())

        return requests, total

    async def approve_request(
        self,
        request: PremiumRequest,
        admin_id: uuid.UUID,
        admin_notes: str | None = None,
    ) -> PremiumRequest:
        """Approve a premium request.

        Args:
            request: The premium request to approve
            admin_id: Admin user ID
            admin_notes: Optional admin notes

        Returns:
            Updated premium request
        """
        request.status = "approved"
        request.reviewed_by = admin_id
        request.reviewed_at = datetime.now(UTC)
        request.admin_notes = admin_notes
        request.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def reject_request(
        self,
        request: PremiumRequest,
        admin_id: uuid.UUID,
        admin_notes: str,
    ) -> PremiumRequest:
        """Reject a premium request.

        Args:
            request: The premium request to reject
            admin_id: Admin user ID
            admin_notes: Rejection reason

        Returns:
            Updated premium request
        """
        request.status = "rejected"
        request.reviewed_by = admin_id
        request.reviewed_at = datetime.now(UTC)
        request.admin_notes = admin_notes
        request.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(request)
        return request

    async def get_request_stats(self) -> dict:
        """Get statistics about premium requests.

        Returns:
            Dictionary with request counts by status
        """
        # Total count
        total_stmt = select(func.count(PremiumRequest.id))
        total_result = await self.db.execute(total_stmt)
        total = total_result.scalar_one()

        # Count by status
        status_stmt = select(
            PremiumRequest.status,
            func.count(PremiumRequest.id).label("count"),
        ).group_by(PremiumRequest.status)

        status_result = await self.db.execute(status_stmt)
        status_counts = {row[0]: row[1] for row in status_result.all()}

        return {
            "total": total,
            "pending": status_counts.get("pending", 0),
            "approved": status_counts.get("approved", 0),
            "rejected": status_counts.get("rejected", 0),
            "in_review": status_counts.get("in_review", 0),
        }

    # ========================================================================
    # Premium Feature Operations
    # ========================================================================

    async def list_features(self, active_only: bool = True) -> list[PremiumFeature]:
        """List premium features.

        Args:
            active_only: If True, only return active features

        Returns:
            List of premium features
        """
        stmt = select(PremiumFeature)
        if active_only:
            stmt = stmt.where(PremiumFeature.is_active == True)  # noqa: E712
        stmt = stmt.order_by(PremiumFeature.name)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ========================================================================
    # Subscription Operations
    # ========================================================================

    async def create_subscription(
        self,
        user_id: uuid.UUID,
        subscription_type: str,
        start_date: datetime,
        end_date: datetime | None = None,
        granted_by: uuid.UUID | None = None,
    ) -> UserPremiumSubscription:
        """Create a premium subscription for a user.

        Args:
            user_id: User ID
            subscription_type: Subscription type (premium/enterprise)
            start_date: Subscription start date
            end_date: Optional end date
            granted_by: Admin who granted the subscription

        Returns:
            Created subscription
        """
        subscription = UserPremiumSubscription(
            user_id=user_id,
            subscription_type=subscription_type,
            start_date=start_date,
            end_date=end_date,
            granted_by=granted_by,
        )
        self.db.add(subscription)
        await self.db.flush()
        await self.db.refresh(subscription)
        return subscription

    async def get_active_subscription(
        self, user_id: uuid.UUID
    ) -> UserPremiumSubscription | None:
        """Get user's active subscription."""
        stmt = select(UserPremiumSubscription).where(
            and_(
                UserPremiumSubscription.user_id == user_id,
                UserPremiumSubscription.is_active == True,  # noqa: E712
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ========================================================================
    # Upload Limit Operations
    # ========================================================================

    async def get_or_create_upload_limits(
        self, user_id: uuid.UUID
    ) -> UserUploadLimit:
        """Get or create user upload limits.

        Args:
            user_id: User ID

        Returns:
            User upload limits
        """
        stmt = select(UserUploadLimit).where(UserUploadLimit.user_id == user_id)
        result = await self.db.execute(stmt)
        limits = result.scalar_one_or_none()

        if not limits:
            limits = UserUploadLimit(user_id=user_id)
            self.db.add(limits)
            await self.db.flush()
            await self.db.refresh(limits)

        return limits

    async def upgrade_upload_limits(
        self,
        user_id: uuid.UUID,
        max_file_size_mb: int = 500,
        total_storage_mb: int = 5000,
        monthly_upload_count: int = 200,
    ) -> UserUploadLimit:
        """Upgrade user upload limits to premium.

        Args:
            user_id: User ID
            max_file_size_mb: Max file size in MB
            total_storage_mb: Total storage in MB
            monthly_upload_count: Monthly upload limit

        Returns:
            Updated upload limits
        """
        limits = await self.get_or_create_upload_limits(user_id)
        limits.is_premium = True
        limits.max_file_size_mb = max_file_size_mb
        limits.total_storage_mb = total_storage_mb
        limits.monthly_upload_count = monthly_upload_count
        limits.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(limits)
        return limits
