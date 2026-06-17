"""Error log service for business logic."""

import uuid
from datetime import datetime

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.error_log_repo import ErrorLogRepository
from app.schemas.common import create_pagination
from app.schemas.error_log import (
    ErrorLogCreateResponse,
    ErrorLogListResponse,
    ErrorLogResponse,
)

logger = structlog.get_logger(__name__)


class ErrorLogService:
    """Service for error logging business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ErrorLogRepository(db)

    async def log_error(
        self,
        error_type: str,
        error_message: str,
        stack_trace: str | None = None,
        user_id: uuid.UUID | None = None,
        book_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        request_data: dict | None = None,
        severity: str = "medium",
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ErrorLogCreateResponse:
        """Log a new error.

        Args:
            error_type: Type/class of the error
            error_message: Human-readable error message
            stack_trace: Optional stack trace
            user_id: Optional user ID
            book_id: Optional book ID
            session_id: Optional session ID
            request_data: Optional request context
            severity: Error severity
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Error log creation response with error code
        """
        error_log = await self.repo.create(
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            user_id=user_id,
            book_id=book_id,
            session_id=session_id,
            request_data=request_data,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info(
            "Error logged",
            error_code=error_log.error_code,
            error_type=error_type,
            severity=severity,
            user_id=str(user_id) if user_id else None,
        )

        return ErrorLogCreateResponse(
            error_code=error_log.error_code,
            id=error_log.id,
        )

    async def list_errors(
        self,
        severity: str | None = None,
        resolved: bool | None = None,
        error_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> ErrorLogListResponse:
        """List error logs with filtering and pagination.

        Args:
            severity: Filter by severity
            resolved: Filter by resolved status
            error_type: Filter by error type
            start_date: Filter by start date
            end_date: Filter by end date
            page: Page number
            limit: Items per page

        Returns:
            Paginated error log list
        """
        error_logs, total = await self.repo.list_errors(
            severity=severity,
            resolved=resolved,
            error_type=error_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            limit=limit,
        )

        return ErrorLogListResponse(
            data=[ErrorLogResponse.model_validate(e) for e in error_logs],
            pagination=create_pagination(page, limit, total),
        )

    async def get_error(self, error_id: uuid.UUID) -> ErrorLogResponse:
        """Get a single error log by ID.

        Args:
            error_id: Error log UUID

        Returns:
            Error log response

        Raises:
            HTTPException: If error not found
        """
        error_log = await self.repo.get_by_id(error_id)

        if not error_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Error log not found",
            )

        return ErrorLogResponse.model_validate(error_log)

    async def resolve_error(
        self,
        error_id: uuid.UUID,
        admin_user: User,
    ) -> ErrorLogResponse:
        """Mark an error as resolved.

        Args:
            error_id: Error log UUID
            admin_user: Admin user performing the resolution

        Returns:
            Updated error log response

        Raises:
            HTTPException: If error not found or already resolved
        """
        error_log = await self.repo.get_by_id(error_id)

        if not error_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Error log not found",
            )

        if error_log.resolved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error is already resolved",
            )

        error_log = await self.repo.resolve(error_log, admin_user.id)

        logger.info(
            "Error resolved",
            error_code=error_log.error_code,
            resolved_by=str(admin_user.id),
        )

        return ErrorLogResponse.model_validate(error_log)
