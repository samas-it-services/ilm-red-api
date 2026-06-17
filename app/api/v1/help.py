"""Help/Documentation API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.api.v1.deps import AdminUser, CurrentUser, DBSession, OptionalUser
from app.schemas.help import (
    HelpArticleCreate,
    HelpArticleListResponse,
    HelpArticleResponse,
    HelpArticleUpdate,
    HelpCategoryCreate,
    HelpCategoryListResponse,
    HelpCategoryResponse,
    HelpFeedbackCreate,
    HelpFeedbackResponse,
    HelpShareCreate,
    HelpShareResponse,
    HelpViewCreate,
)
from app.services.help_service import HelpService

router = APIRouter()


# ---------- Category Endpoints ----------


@router.get(
    "/categories",
    response_model=HelpCategoryListResponse,
    summary="Get help categories",
    description="Get all active help categories with article counts.",
)
async def get_categories(
    db: DBSession,
) -> HelpCategoryListResponse:
    """Get all active help categories with article counts."""
    service = HelpService(db)
    return await service.get_categories()


@router.post(
    "/categories",
    response_model=HelpCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create help category (admin)",
    description="Create a new help category. Requires admin role.",
)
async def create_category(
    data: HelpCategoryCreate,
    db: DBSession,
    current_user: AdminUser,
) -> HelpCategoryResponse:
    """Create a new help category (admin only)."""
    service = HelpService(db)
    return await service.create_category(data, current_user)


# ---------- Article Endpoints ----------


@router.get(
    "/articles",
    response_model=HelpArticleListResponse,
    summary="List help articles",
    description="List help articles with optional filtering and pagination.",
)
async def list_articles(
    db: DBSession,
    current_user: OptionalUser,
    category_id: UUID | None = Query(None, description="Filter by category ID"),
    q: str | None = Query(None, description="Search query"),
    is_featured: bool | None = Query(None, description="Filter featured articles"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
    sort_by: str = Query("sort_order", description="Sort field"),
    sort_order: str = Query("asc", description="Sort order (asc/desc)"),
) -> HelpArticleListResponse:
    """List help articles.

    Published articles visible to everyone. Draft/archived only to admins.
    """
    service = HelpService(db)
    return await service.list_articles(
        user=current_user,
        category_id=category_id,
        search_query=q,
        is_featured=is_featured,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/articles/search",
    response_model=HelpArticleListResponse,
    summary="Search help articles",
    description="Full-text search across published help articles.",
)
async def search_articles(
    db: DBSession,
    q: str = Query(..., min_length=1, description="Search query"),
    language: str = Query("en", description="Language to search (en or ur)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> HelpArticleListResponse:
    """Search published help articles by title and content."""
    service = HelpService(db)
    return await service.search_articles(
        query=q,
        language=language,
        page=page,
        limit=limit,
    )


@router.get(
    "/articles/{slug}",
    response_model=HelpArticleResponse,
    summary="Get help article by slug",
    description="Get a help article by its URL slug.",
)
async def get_article(
    slug: str,
    db: DBSession,
    current_user: OptionalUser,
) -> HelpArticleResponse:
    """Get a help article by slug."""
    service = HelpService(db)
    return await service.get_article(slug, current_user)


@router.post(
    "/articles",
    response_model=HelpArticleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create help article (admin)",
    description="Create a new help article. Requires admin role.",
)
async def create_article(
    data: HelpArticleCreate,
    db: DBSession,
    current_user: AdminUser,
) -> HelpArticleResponse:
    """Create a new help article (admin only).

    - **category_id**: Category UUID (required)
    - **title_en**: English title (required)
    - **content_en**: English content in markdown (required)
    - **title_ur**: Urdu title (optional)
    - **content_ur**: Urdu content (optional)
    """
    service = HelpService(db)
    return await service.create_article(data, current_user)


@router.put(
    "/articles/{article_id}",
    response_model=HelpArticleResponse,
    summary="Update help article (admin)",
    description="Update a help article. Requires admin role.",
)
async def update_article(
    article_id: UUID,
    data: HelpArticleUpdate,
    db: DBSession,
    current_user: AdminUser,
) -> HelpArticleResponse:
    """Update a help article (admin only)."""
    service = HelpService(db)
    return await service.update_article(article_id, data, current_user)


@router.delete(
    "/articles/{article_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete help article (admin)",
    description="Delete a help article. Requires admin role.",
)
async def delete_article(
    article_id: UUID,
    db: DBSession,
    current_user: AdminUser,
) -> None:
    """Delete a help article (admin only)."""
    service = HelpService(db)
    await service.delete_article(article_id, current_user)


# ---------- View Tracking ----------


@router.post(
    "/articles/{article_id}/view",
    status_code=status.HTTP_201_CREATED,
    summary="Track article view",
    description="Track a view for a help article.",
)
async def track_view(
    article_id: UUID,
    request: Request,
    db: DBSession,
    current_user: OptionalUser,
    data: HelpViewCreate | None = None,
) -> dict:
    """Track an article view for analytics."""
    service = HelpService(db)
    await service.track_view(
        article_id=article_id,
        user=current_user,
        view_data=data,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    return {"message": "View tracked"}


# ---------- Feedback ----------


@router.post(
    "/articles/{article_id}/feedback",
    response_model=HelpFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit article feedback",
    description="Submit helpful/not_helpful feedback for an article.",
)
async def submit_feedback(
    article_id: UUID,
    data: HelpFeedbackCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> HelpFeedbackResponse:
    """Submit feedback for a help article.

    - **feedback_type**: helpful or not_helpful
    - **feedback_text**: Optional additional feedback text
    """
    service = HelpService(db)
    return await service.add_feedback(article_id, data, current_user)


# ---------- Share Tracking ----------


@router.post(
    "/articles/{article_id}/share",
    response_model=HelpShareResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Track article share",
    description="Track when a user shares a help article.",
)
async def track_share(
    article_id: UUID,
    data: HelpShareCreate,
    request: Request,
    db: DBSession,
    current_user: CurrentUser,
) -> HelpShareResponse:
    """Track an article share.

    - **share_method**: How the article was shared (link, email, social)
    """
    service = HelpService(db)
    return await service.track_share(
        article_id=article_id,
        data=data,
        user=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
