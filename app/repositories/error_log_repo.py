"""Error log repository for database operations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.error_log import ErrorLog


class ErrorLogRepository:
    """Repository for error log database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _generate_error_code(self) -> str:
        """Generate the next sequential error code (ERR-XXXXX)."""
        stmt = select(func.count(ErrorLog.id))
        result = await self.db.execute(stmt)
        count = result.scalar_one() or 0
        return f"ERR-{count + 1:05d}"

    async def create(
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
    ) -> ErrorLog:
        """Create a new error log entry.

        Args:
            error_type: Type/class of the error
            error_message: Human-readable error message
            stack_trace: Optional stack trace
            user_id: Optional user ID
            book_id: Optional book ID
            session_id: Optional session ID
            request_data: Optional request context
            severity: Error severity (low/medium/high/critical)
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            Created error log entry
        """
        error_code = await self._generate_error_code()

        error_log = ErrorLog(
            error_code=error_code,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            user_id=user_id,
            book_id=book_id,
            session_id=session_id,
            request_data=request_data or {},
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(error_log)
        await self.db.flush()
        await self.db.refresh(error_log)
        return error_log

    async def get_by_id(self, error_id: uuid.UUID) -> ErrorLog | None:
        """Get error log by ID."""
        stmt = select(ErrorLog).where(ErrorLog.id == error_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_error_code(self, error_code: str) -> ErrorLog | None:
        """Get error log by error code."""
        stmt = select(ErrorLog).where(ErrorLog.error_code == error_code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_errors(
        self,
        severity: str | None = None,
        resolved: bool | None = None,
        error_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[ErrorLog], int]:
        """List error logs with filtering and pagination.

        Args:
            severity: Filter by severity level
            resolved: Filter by resolution status
            error_type: Filter by error type
            start_date: Filter errors after this date
            end_date: Filter errors before this date
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (error_logs list, total count)
        """
        conditions = []

        if severity:
            conditions.append(ErrorLog.severity == severity)
        if resolved is not None:
            conditions.append(ErrorLog.resolved == resolved)
        if error_type:
            conditions.append(ErrorLog.error_type == error_type)
        if start_date:
            conditions.append(ErrorLog.created_at >= start_date)
        if end_date:
            conditions.append(ErrorLog.created_at <= end_date)

        # Count query
        where_clause = and_(*conditions) if conditions else True
        count_stmt = select(func.count(ErrorLog.id)).where(where_clause)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        offset = (page - 1) * limit
        stmt = (
            select(ErrorLog)
            .where(where_clause)
            .order_by(ErrorLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        error_logs = list(result.scalars().all())

        return error_logs, total

    async def resolve(
        self,
        error_log: ErrorLog,
        resolved_by: uuid.UUID,
    ) -> ErrorLog:
        """Mark an error log as resolved.

        Args:
            error_log: The error log to resolve
            resolved_by: ID of the admin resolving the error

        Returns:
            Updated error log
        """
        error_log.resolved = True
        error_log.resolved_at = datetime.now(UTC)
        error_log.resolved_by = resolved_by
        await self.db.flush()
        await self.db.refresh(error_log)
        return error_log
