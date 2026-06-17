"""User issues and feature requests API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.v1.deps import AdminUser, CurrentUser, DBSession
from app.schemas.issue import (
    IssueCreate,
    IssueListResponse,
    IssueResponse,
    IssueResponseCreate,
    IssueResponseListResponse,
    IssueResponseResponse,
    IssueStatusUpdate,
    IssueUpdate,
)
from app.services.issue_service import IssueService

router = APIRouter()


# User-facing endpoints


@router.post(
    "",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an issue",
    description="Submit a new issue, bug report, or feature request.",
)
async def create_issue(
    data: IssueCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> IssueResponse:
    """Create a new issue.

    - **title**: Brief summary of the issue
    - **description**: Detailed description
    - **issue_type**: bug, feature_request, question, technical_issue, or account_issue
    - **priority**: low, medium, high, or urgent
    - **book_id**: Optional related book
    - **session_id**: Optional related chat session
    """
    service = IssueService(db)
    return await service.create_issue(current_user, data)


@router.get(
    "",
    response_model=IssueListResponse,
    summary="List my issues",
    description="List issues submitted by the current user.",
)
async def list_my_issues(
    db: DBSession,
    current_user: CurrentUser,
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    issue_type: str | None = Query(None, description="Filter by issue type"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> IssueListResponse:
    """List the current user's issues with optional filtering."""
    service = IssueService(db)
    return await service.list_user_issues(
        user=current_user,
        status_filter=status_filter,
        issue_type=issue_type,
        page=page,
        limit=limit,
    )


@router.get(
    "/admin/all",
    response_model=IssueListResponse,
    summary="List all issues (admin)",
    description="List all user issues with filtering. Admin only.",
)
async def list_all_issues(
    db: DBSession,
    admin_user: AdminUser,
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    issue_type: str | None = Query(None, description="Filter by issue type"),
    priority: str | None = Query(None, description="Filter by priority"),
    q: str | None = Query(None, description="Search in title"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> IssueListResponse:
    """List all issues across all users (admin only).

    Supports filtering by status, type, priority, and search query.
    """
    service = IssueService(db)
    return await service.list_all_issues(
        status_filter=status_filter,
        issue_type=issue_type,
        priority=priority,
        search_query=q,
        page=page,
        limit=limit,
    )


@router.get(
    "/{issue_id}",
    response_model=IssueResponse,
    summary="Get issue detail",
    description="Get detailed information about a specific issue.",
)
async def get_issue(
    issue_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> IssueResponse:
    """Get issue details by ID.

    Regular users can only view their own issues.
    Admins can view any issue.
    """
    service = IssueService(db)
    return await service.get_issue(issue_id, current_user)


@router.put(
    "/{issue_id}",
    response_model=IssueResponse,
    summary="Update issue",
    description="Update an existing issue.",
)
async def update_issue(
    issue_id: UUID,
    data: IssueUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> IssueResponse:
    """Update an issue.

    Regular users can update title, description, type, and priority of their own issues.
    Admins can update any issue including status.
    """
    service = IssueService(db)
    return await service.update_issue(issue_id, current_user, data)


@router.put(
    "/admin/{issue_id}/status",
    response_model=IssueResponse,
    summary="Update issue status (admin)",
    description="Update the status of an issue. Admin only.",
)
async def update_issue_status(
    issue_id: UUID,
    data: IssueStatusUpdate,
    db: DBSession,
    admin_user: AdminUser,
) -> IssueResponse:
    """Update issue status (admin only).

    Set the status to: open, in_progress, resolved, or closed.
    """
    service = IssueService(db)
    return await service.update_issue_status(issue_id, data)


@router.get(
    "/{issue_id}/responses",
    response_model=IssueResponseListResponse,
    summary="List issue responses",
    description="List all responses for a specific issue.",
)
async def list_issue_responses(
    issue_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, alias="page_size", description="Items per page"),
) -> IssueResponseListResponse:
    """List responses for an issue.

    Regular users only see non-internal responses for their own issues.
    Admins see all responses including internal notes.
    """
    service = IssueService(db)
    return await service.list_responses(issue_id, current_user, page, limit)


@router.post(
    "/{issue_id}/responses",
    response_model=IssueResponseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add response to issue",
    description="Add a response or comment to an issue.",
)
async def add_issue_response(
    issue_id: UUID,
    data: IssueResponseCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> IssueResponseResponse:
    """Add a response to an issue.

    - Regular users can respond to their own issues (no internal notes).
    - Admins can respond to any issue and create internal notes.
    """
    service = IssueService(db)
    return await service.add_response(issue_id, current_user, data)
