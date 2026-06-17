"""Premium service for business logic."""

import uuid
from datetime import UTC, datetime

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.premium_repo import PremiumRepository
from app.schemas.common import create_pagination
from app.schemas.premium import (
    PremiumFeatureResponse,
    PremiumRequestApprove,
    PremiumRequestCreate,
    PremiumRequestListResponse,
    PremiumRequestReject,
    PremiumRequestResponse,
    PremiumRequestStats,
    PremiumRequestUpdate,
)

logger = structlog.get_logger(__name__)


class PremiumService:
    """Service for premium-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PremiumRepository(db)

    # ========================================================================
    # Premium Request Operations
    # ========================================================================

    async def submit_request(
        self,
        data: PremiumRequestCreate,
        user: User,
    ) -> PremiumRequestResponse:
        """Submit a premium request.

        Checks if user already has a pending request before creating a new one.

        Args:
            data: Premium request data
            user: Current authenticated user

        Returns:
            Created premium request response

        Raises:
            HTTPException: If user already has a pending/in_review request
        """
        # Check for existing pending request
        existing = await self.repo.get_user_request(user.id)
        if existing and existing.status in ("pending", "in_review"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have a pending premium request. Please wait for review or update your existing request.",
            )

        request = await self.repo.create_request(
            user_id=user.id,
            name=data.name,
            email=data.email,
            organization=data.organization,
            user_type=data.user_type,
            current_usage=data.current_usage,
            interested_features=data.interested_features,
            use_case=data.use_case,
            team_size=data.team_size,
            budget=data.budget,
            timeline=data.timeline,
            additional_notes=data.additional_notes,
        )

        logger.info(
            "Premium request submitted",
            user_id=str(user.id),
            request_id=str(request.id),
        )

        return PremiumRequestResponse.model_validate(request)

    async def get_my_request(self, user: User) -> PremiumRequestResponse:
        """Get the current user's most recent premium request.

        Args:
            user: Current authenticated user

        Returns:
            Premium request response

        Raises:
            HTTPException: If no request found
        """
        request = await self.repo.get_user_request(user.id)

        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No premium request found",
            )

        return PremiumRequestResponse.model_validate(request)

    async def update_request(
        self,
        request_id: uuid.UUID,
        data: PremiumRequestUpdate,
        user: User,
    ) -> PremiumRequestResponse:
        """Update a premium request (owner only, before review).

        Args:
            request_id: Premium request ID
            data: Update data
            user: Current authenticated user

        Returns:
            Updated premium request response

        Raises:
            HTTPException: If not found, not owner, or already reviewed
        """
        request = await self.repo.get_request_by_id(request_id)

        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Premium request not found",
            )

        if request.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own requests",
            )

        if request.status not in ("pending", "in_review"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update request with status '{request.status}'",
            )

        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            request = await self.repo.update_request(request, **update_data)

        logger.info(
            "Premium request updated",
            user_id=str(user.id),
            request_id=str(request_id),
            updated_fields=list(update_data.keys()),
        )

        return PremiumRequestResponse.model_validate(request)

    # ========================================================================
    # Premium Feature Operations
    # ========================================================================

    async def list_features(self) -> list[PremiumFeatureResponse]:
        """List all active premium features.

        Returns:
            List of premium feature responses
        """
        features = await self.repo.list_features(active_only=True)
        return [PremiumFeatureResponse.model_validate(f) for f in features]

    # ========================================================================
    # Admin Operations
    # ========================================================================

    async def list_all_requests(
        self,
        status_filter: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> PremiumRequestListResponse:
        """List all premium requests (admin).

        Args:
            status_filter: Optional status filter
            page: Page number
            limit: Items per page

        Returns:
            Paginated premium request list
        """
        requests, total = await self.repo.list_requests(
            status=status_filter,
            page=page,
            limit=limit,
        )

        return PremiumRequestListResponse(
            data=[PremiumRequestResponse.model_validate(r) for r in requests],
            pagination=create_pagination(page, limit, total),
        )

    async def approve_request(
        self,
        request_id: uuid.UUID,
        data: PremiumRequestApprove,
        admin_user: User,
    ) -> PremiumRequestResponse:
        """Approve a premium request.

        Creates a subscription and upgrades upload limits for the user.

        Args:
            request_id: Premium request ID
            data: Approval data
            admin_user: Admin performing the approval

        Returns:
            Updated premium request response

        Raises:
            HTTPException: If not found or not in approvable state
        """
        request = await self.repo.get_request_by_id(request_id)

        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Premium request not found",
            )

        if request.status not in ("pending", "in_review"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve request with status '{request.status}'",
            )

        # Approve the request
        request = await self.repo.approve_request(
            request=request,
            admin_id=admin_user.id,
            admin_notes=data.admin_notes,
        )

        # Create subscription for the user
        await self.repo.create_subscription(
            user_id=request.user_id,
            subscription_type=data.subscription_type,
            start_date=datetime.now(UTC),
            granted_by=admin_user.id,
        )

        # Upgrade upload limits
        await self.repo.upgrade_upload_limits(request.user_id)

        logger.info(
            "Premium request approved",
            request_id=str(request_id),
            user_id=str(request.user_id),
            admin_id=str(admin_user.id),
            subscription_type=data.subscription_type,
        )

        return PremiumRequestResponse.model_validate(request)

    async def reject_request(
        self,
        request_id: uuid.UUID,
        data: PremiumRequestReject,
        admin_user: User,
    ) -> PremiumRequestResponse:
        """Reject a premium request.

        Args:
            request_id: Premium request ID
            data: Rejection data with reason
            admin_user: Admin performing the rejection

        Returns:
            Updated premium request response

        Raises:
            HTTPException: If not found or not in rejectable state
        """
        request = await self.repo.get_request_by_id(request_id)

        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Premium request not found",
            )

        if request.status not in ("pending", "in_review"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject request with status '{request.status}'",
            )

        request = await self.repo.reject_request(
            request=request,
            admin_id=admin_user.id,
            admin_notes=data.admin_notes,
        )

        logger.info(
            "Premium request rejected",
            request_id=str(request_id),
            user_id=str(request.user_id),
            admin_id=str(admin_user.id),
        )

        return PremiumRequestResponse.model_validate(request)

    async def get_stats(self) -> PremiumRequestStats:
        """Get premium request statistics.

        Returns:
            Premium request stats
        """
        stats = await self.repo.get_request_stats()

        total = stats["total"]
        approved = stats["approved"]
        rejected = stats["rejected"]
        decided = approved + rejected

        approval_rate = (approved / decided * 100) if decided > 0 else 0.0

        return PremiumRequestStats(
            total_requests=total,
            pending_requests=stats["pending"],
            approved_requests=approved,
            rejected_requests=rejected,
            in_review_requests=stats["in_review"],
            approval_rate=round(approval_rate, 1),
        )
