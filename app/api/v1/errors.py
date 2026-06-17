"""Error logging API endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.api.v1.deps import AdminUser, DBSession
from app.schemas.error_log import (
    ErrorLogCreate,
    ErrorLogCreateResponse,
    ErrorLogListResponse,
    ErrorLogResolve,
    ErrorLogResponse,
)
from app.services.error_log_service import ErrorLogService

router = APIRouter()


@router.post(
    "/",
    response_model=ErrorLogCreateResponse,
    status_code=201,
    summary="Log an error",
    description="""
Log a client-side or server-side error for tracking and debugging.

**No authentication required** - allows error logging from any context.

Returns a unique error code (ERR-XXXXX) for reference.
    """,
)
async def log_error(
    data: ErrorLogCreate,
    request: Request,
    db: DBSession,
) -> ErrorLogCreateResponse:
    """Log a new error.

    Automatically captures IP address and user agent from the request.
    Returns an error code for tracking.
    """
    service = ErrorLogService(db)

    # Extract client info from request
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    return await service.log_error(
        error_type=data.error_type,
        error_message=data.error_message,
        stack_trace=data.stack_trace,
        user_id=data.user_id,
        book_id=data.book_id,
        session_id=data.session_id,
        request_data=data.request_data,
        severity=data.severity,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.get(
    "/",
    response_model=ErrorLogListResponse,
    summary="List errors (admin)",
    description="""
List all error logs with filtering and pagination.

**Filters:**
- `severity`: Filter by severity (low, medium, high, critical)
- `resolved`: Filter by resolved status (true/false)
- `error_type`: Filter by error type
- `start_date` / `end_date`: Filter by date range

**Requires:** Admin role
    """,
)
async def list_errors(
    db: DBSession,
    admin_user: AdminUser,
    severity: str | None = Query(None, description="Filter by severity"),
    resolved: bool | None = Query(None, description="Filter by resolved status"),
    error_type: str | None = Query(None, description="Filter by error type"),
    start_date: datetime | None = Query(None, description="Filter by start date (ISO format)"),
    end_date: datetime | None = Query(None, description="Filter by end date (ISO format)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> ErrorLogListResponse:
    """List error logs with optional filtering.

    Errors are sorted by creation date (most recent first).
    """
    service = ErrorLogService(db)
    return await service.list_errors(
        severity=severity,
        resolved=resolved,
        error_type=error_type,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit,
    )


@router.get(
    "/{error_id}",
    response_model=ErrorLogResponse,
    summary="Get error detail (admin)",
    description="Get full details for a specific error log entry.",
)
async def get_error(
    error_id: UUID,
    db: DBSession,
    admin_user: AdminUser,
) -> ErrorLogResponse:
    """Get full details of an error log entry."""
    service = ErrorLogService(db)
    return await service.get_error(error_id)


@router.put(
    "/{error_id}/resolve",
    response_model=ErrorLogResponse,
    summary="Resolve error (admin)",
    description="""
Mark an error as resolved.

Sets resolved=true, records the timestamp and the admin who resolved it.

**Requires:** Admin role
    """,
)
async def resolve_error(
    error_id: UUID,
    db: DBSession,
    admin_user: AdminUser,
    data: ErrorLogResolve | None = None,
) -> ErrorLogResponse:
    """Mark an error as resolved by the current admin."""
    service = ErrorLogService(db)
    return await service.resolve_error(error_id, admin_user)
