"""Suggestion system API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.v1.deps import AdminUser, CurrentUser, DBSession
from app.schemas.suggestion import (
    SuggestionConfigResponse,
    SuggestionConfigUpdate,
    SuggestionCreate,
    SuggestionFeedbackCreate,
    SuggestionFeedbackResponse,
    SuggestionListResponse,
    SuggestionNotificationListResponse,
    SuggestionNotificationResponse,
    SuggestionResponse,
    SystemConfigResponse,
    SystemConfigUpdate,
)
from app.services.suggestion_service import SuggestionService

router = APIRouter()


# --- User Suggestion Endpoints ---


@router.post(
    "",
    response_model=SuggestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit suggestion",
    description="Submit a new suggestion. Subject to daily usage limits.",
)
async def submit_suggestion(
    data: SuggestionCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> SuggestionResponse:
    """Submit a new suggestion.

    The suggestion will be queued for AI and/or admin response.
    Daily limits apply based on user or system configuration.
    """
    service = SuggestionService(db)
    return await service.submit_suggestion(current_user, data)


@router.get(
    "",
    response_model=SuggestionListResponse,
    summary="List my suggestions",
    description="List the current user's suggestions with pagination.",
)
async def list_my_suggestions(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> SuggestionListResponse:
    """List the current user's suggestions."""
    service = SuggestionService(db)
    return await service.list_user_suggestions(current_user, page, limit)


@router.get(
    "/notifications",
    response_model=SuggestionNotificationListResponse,
    summary="Get notifications",
    description="Get the current user's suggestion-related notifications.",
)
async def get_notifications(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> SuggestionNotificationListResponse:
    """Get suggestion-related notifications for the current user."""
    service = SuggestionService(db)
    return await service.get_notifications(current_user, page, limit)


@router.get(
    "/config",
    response_model=SuggestionConfigResponse,
    summary="Get my suggestion config",
    description="Get the current user's suggestion configuration.",
)
async def get_my_config(
    db: DBSession,
    current_user: CurrentUser,
) -> SuggestionConfigResponse:
    """Get the current user's suggestion configuration.

    Creates a default configuration if one does not exist.
    """
    service = SuggestionService(db)
    return await service.get_user_config(current_user)


@router.put(
    "/config",
    response_model=SuggestionConfigResponse,
    summary="Update my suggestion config",
    description="Update the current user's suggestion configuration.",
)
async def update_my_config(
    updates: SuggestionConfigUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> SuggestionConfigResponse:
    """Update the current user's suggestion configuration."""
    service = SuggestionService(db)
    return await service.update_user_config(current_user, updates)


@router.get(
    "/admin/all",
    response_model=SuggestionListResponse,
    summary="List all suggestions (admin)",
    description="List all suggestions across all users. Admin only.",
)
async def list_all_suggestions(
    db: DBSession,
    current_user: AdminUser,
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    priority: str | None = Query(None, description="Filter by priority"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> SuggestionListResponse:
    """List all suggestions for admin review.

    Requires admin role. Supports filtering by status and priority.
    """
    service = SuggestionService(db)
    return await service.list_all_suggestions(
        status_filter=status_filter,
        priority_filter=priority,
        page=page,
        limit=limit,
    )


@router.put(
    "/admin/config",
    response_model=SystemConfigResponse,
    summary="Update system config (admin)",
    description="Update the system-wide suggestion configuration. Admin only.",
)
async def update_system_config(
    updates: SystemConfigUpdate,
    db: DBSession,
    current_user: AdminUser,
) -> SystemConfigResponse:
    """Update the system-wide suggestion configuration.

    Requires admin role. Controls global settings like enabled/disabled,
    default AI model, and daily limits.
    """
    service = SuggestionService(db)
    return await service.update_system_config(updates)


@router.get(
    "/{suggestion_id}",
    response_model=SuggestionResponse,
    summary="Get suggestion detail",
    description="Get detailed information about a specific suggestion.",
)
async def get_suggestion(
    suggestion_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> SuggestionResponse:
    """Get suggestion details by ID.

    Users can only view their own suggestions unless they are admins.
    """
    service = SuggestionService(db)
    return await service.get_suggestion(suggestion_id, current_user)


@router.post(
    "/{suggestion_id}/feedback",
    response_model=SuggestionFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback",
    description="Submit feedback on a suggestion response.",
)
async def submit_feedback(
    suggestion_id: UUID,
    data: SuggestionFeedbackCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> SuggestionFeedbackResponse:
    """Submit feedback on a suggestion response.

    Only the suggestion owner can provide feedback.
    """
    service = SuggestionService(db)
    return await service.submit_feedback(suggestion_id, current_user, data)


@router.put(
    "/notifications/{notification_id}/read",
    response_model=SuggestionNotificationResponse,
    summary="Mark notification read",
    description="Mark a suggestion notification as read.",
)
async def mark_notification_read(
    notification_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> SuggestionNotificationResponse:
    """Mark a notification as read.

    Users can only mark their own notifications as read.
    """
    service = SuggestionService(db)
    return await service.mark_notification_read(notification_id, current_user)
