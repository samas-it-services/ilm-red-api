"""Blog API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, Request, status

from app.api.v1.deps import AdminUser, CurrentUser, DBSession, OptionalUser
from app.schemas.blog import (
    BlogCategoryResponse,
    BlogCommentCreate,
    BlogCommentListResponse,
    BlogCommentResponse,
    BlogPostCreate,
    BlogPostListResponse,
    BlogPostResponse,
    BlogPostUpdate,
    BlogTagResponse,
)
from app.services.blog_service import BlogService

router = APIRouter()


# ---------- Blog Post CRUD ----------


@router.post(
    "/posts",
    response_model=BlogPostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a blog post",
    description="Create a new blog post. Requires authentication.",
)
async def create_post(
    data: BlogPostCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> BlogPostResponse:
    """Create a new blog post.

    - **title**: Post title (required)
    - **content**: Post content in markdown (required)
    - **status**: draft, published, or archived (default: draft)
    - **category_ids**: List of category UUIDs to associate
    - **tag_ids**: List of tag UUIDs to associate
    """
    service = BlogService(db)
    return await service.create_post(data, current_user)


@router.get(
    "/posts",
    response_model=BlogPostListResponse,
    summary="List blog posts",
    description="List blog posts with optional filtering and pagination.",
)
async def list_posts(
    db: DBSession,
    current_user: OptionalUser,
    category: str | None = Query(None, description="Filter by category slug"),
    tag: str | None = Query(None, description="Filter by tag slug"),
    q: str | None = Query(None, description="Search in title and content"),
    is_featured: bool | None = Query(None, description="Filter featured posts"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
    sort_by: str = Query("published_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
) -> BlogPostListResponse:
    """List blog posts with filtering.

    Published posts are visible to everyone.
    Draft/archived posts are only visible to admins.
    """
    service = BlogService(db)
    return await service.list_posts(
        user=current_user,
        category_slug=category,
        tag_slug=tag,
        search_query=q,
        is_featured=is_featured,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/posts/{slug}",
    response_model=BlogPostResponse,
    summary="Get blog post by slug",
    description="Get a single blog post by its URL slug. Automatically tracks the view.",
)
async def get_post(
    slug: str,
    request: Request,
    db: DBSession,
    current_user: OptionalUser,
) -> BlogPostResponse:
    """Get a blog post by slug.

    Automatically tracks the view for analytics.
    """
    service = BlogService(db)
    return await service.get_post(
        slug=slug,
        user=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )


@router.put(
    "/posts/{post_id}",
    response_model=BlogPostResponse,
    summary="Update a blog post",
    description="Update a blog post. Only the author or an admin can update.",
)
async def update_post(
    post_id: UUID,
    data: BlogPostUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> BlogPostResponse:
    """Update a blog post.

    Only the post author or an admin can update.
    """
    service = BlogService(db)
    return await service.update_post(post_id, data, current_user)


@router.delete(
    "/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a blog post",
    description="Delete a blog post. Only the author or an admin can delete.",
)
async def delete_post(
    post_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Delete a blog post.

    Only the post author or an admin can delete.
    """
    service = BlogService(db)
    await service.delete_post(post_id, current_user)


# ---------- Like Endpoints ----------


@router.post(
    "/posts/{post_id}/like",
    status_code=status.HTTP_201_CREATED,
    summary="Like a blog post",
    description="Like a blog post. Idempotent — liking again has no effect.",
)
async def like_post(
    post_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Like a blog post."""
    service = BlogService(db)
    return await service.like_post(post_id, current_user)


@router.delete(
    "/posts/{post_id}/like",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unlike a blog post",
    description="Remove your like from a blog post.",
)
async def unlike_post(
    post_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Remove your like from a blog post."""
    service = BlogService(db)
    await service.unlike_post(post_id, current_user)


# ---------- Comment Endpoints ----------


@router.post(
    "/posts/{post_id}/comments",
    response_model=BlogCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment",
    description="Add a comment to a published blog post. Supports threaded replies.",
)
async def create_comment(
    post_id: UUID,
    data: BlogCommentCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> BlogCommentResponse:
    """Add a comment to a blog post.

    - **content**: Comment text (required)
    - **parent_id**: Parent comment UUID for threaded replies (optional)
    """
    service = BlogService(db)
    return await service.create_comment(post_id, data, current_user)


@router.get(
    "/posts/{post_id}/comments",
    response_model=BlogCommentListResponse,
    summary="Get post comments",
    description="Get all approved comments for a blog post with pagination.",
)
async def get_comments(
    post_id: UUID,
    db: DBSession,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> BlogCommentListResponse:
    """Get all approved comments for a blog post."""
    service = BlogService(db)
    return await service.get_comments(post_id, page, limit)


# ---------- Category & Tag Endpoints ----------


@router.get(
    "/categories",
    response_model=list[BlogCategoryResponse],
    summary="Get blog categories",
    description="Get all active blog categories.",
)
async def get_categories(
    db: DBSession,
) -> list[BlogCategoryResponse]:
    """Get all active blog categories."""
    service = BlogService(db)
    return await service.get_categories()


@router.get(
    "/tags",
    response_model=list[BlogTagResponse],
    summary="Get blog tags",
    description="Get all blog tags.",
)
async def get_tags(
    db: DBSession,
) -> list[BlogTagResponse]:
    """Get all blog tags."""
    service = BlogService(db)
    return await service.get_tags()
