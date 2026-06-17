"""Public Q&A API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.api.v1.deps import CurrentUser, DBSession, OptionalUser
from app.schemas.public_qa import (
    EditHistoryResponse,
    FeedbackRequest,
    FeedbackResponse,
    PromoteToPublicQARequest,
    PublicQAListResponse,
    PublicQAResponse,
    PublicQAUpdate,
    QAStatus,
    VoteRequest,
    VoteResponse,
)
from app.services.public_qa_service import PublicQAService

router = APIRouter()


# Allowed sort fields for defense-in-depth
ALLOWED_SORT_FIELDS = {"created_at", "updated_at", "net_votes", "view_count", "title"}


@router.post(
    "/promote",
    response_model=PublicQAResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Promote chat to public Q&A",
    description="Promote a chat message to a public Q&A entry.",
)
async def promote_to_public_qa(
    request_data: PromoteToPublicQARequest,
    db: DBSession,
    current_user: CurrentUser,
) -> PublicQAResponse:
    """Promote a chat message to a public Q&A entry.

    Creates a new public Q&A from a chat conversation.
    The Q&A starts in draft status by default.
    """
    service = PublicQAService(db)
    return await service.promote_to_public_qa(request_data, current_user)


@router.get(
    "",
    response_model=PublicQAListResponse,
    summary="List public Q&A",
    description="List public Q&A entries with filtering and pagination.",
)
async def list_qa(
    db: DBSession,
    current_user: OptionalUser,
    book_id: UUID | None = Query(None, description="Filter by book ID"),
    category: str | None = Query(None, description="Filter by category"),
    status_filter: QAStatus | None = Query(None, alias="status", description="Filter by status"),
    q: str | None = Query(None, description="Search in title and question"),
    featured: bool | None = Query(None, description="Filter by featured status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
) -> PublicQAListResponse:
    """List public Q&A entries.

    Supports filtering by book, category, status, and search.
    Default sort is by creation date descending.
    """
    from fastapi import HTTPException

    if sort_by not in ALLOWED_SORT_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field. Allowed: {', '.join(sorted(ALLOWED_SORT_FIELDS))}",
        )

    service = PublicQAService(db)
    return await service.list_qa(
        book_id=book_id,
        category=category,
        status=status_filter.value if status_filter else None,
        search_query=q,
        featured=featured,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{qa_id}",
    response_model=PublicQAResponse,
    summary="Get Q&A detail",
    description="Get a specific Q&A entry. Automatically tracks the view.",
)
async def get_qa(
    qa_id: UUID,
    request: Request,
    db: DBSession,
    current_user: OptionalUser,
) -> PublicQAResponse:
    """Get a Q&A entry by ID.

    Automatically tracks the view with deduplication (30-minute window).
    """
    ip_address = request.client.host if request.client else "0.0.0.0"
    user_agent = request.headers.get("User-Agent")

    service = PublicQAService(db)
    return await service.get_qa(
        qa_id=qa_id,
        viewer_id=current_user.id if current_user else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.put(
    "/{qa_id}",
    response_model=PublicQAResponse,
    summary="Update Q&A",
    description="Update a Q&A entry. Creates an edit history record.",
)
async def update_qa(
    qa_id: UUID,
    updates: PublicQAUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> PublicQAResponse:
    """Update a Q&A entry.

    Only the original author or an admin can edit.
    Each edit is tracked in the edit history.
    """
    service = PublicQAService(db)
    return await service.update_qa(qa_id, updates, current_user)


@router.delete(
    "/{qa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Q&A",
    description="Delete a Q&A entry. Only the author or an admin can delete.",
)
async def delete_qa(
    qa_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Delete a Q&A entry.

    Only the original author or an admin can delete.
    This permanently removes the Q&A and all associated data.
    """
    service = PublicQAService(db)
    await service.delete_qa(qa_id, current_user)


@router.post(
    "/{qa_id}/vote",
    response_model=VoteResponse,
    summary="Vote on Q&A",
    description="Vote on a Q&A entry. Supports upvote, downvote, and toggle.",
)
async def vote_on_qa(
    qa_id: UUID,
    vote_request: VoteRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> VoteResponse:
    """Vote on a Q&A entry.

    - Voting the same type again removes the vote (toggle off).
    - Voting a different type changes the vote.
    - A new vote creates a fresh entry.
    """
    service = PublicQAService(db)
    return await service.vote(qa_id, vote_request, current_user)


@router.post(
    "/{qa_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback",
    description="Submit feedback (helpful/not helpful) on a Q&A entry.",
)
async def submit_feedback(
    qa_id: UUID,
    feedback_request: FeedbackRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> FeedbackResponse:
    """Submit feedback on a Q&A entry.

    Each user can only submit feedback once per Q&A entry.
    """
    service = PublicQAService(db)
    return await service.submit_feedback(qa_id, feedback_request, current_user)


@router.get(
    "/{qa_id}/history",
    response_model=EditHistoryResponse,
    summary="Get edit history",
    description="Get the edit history for a Q&A entry.",
)
async def get_edit_history(
    qa_id: UUID,
    db: DBSession,
    current_user: OptionalUser,
) -> EditHistoryResponse:
    """Get the edit history for a Q&A entry.

    Returns all previous versions in reverse chronological order.
    """
    service = PublicQAService(db)
    return await service.get_edit_history(qa_id)
