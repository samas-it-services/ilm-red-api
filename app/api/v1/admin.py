"""Admin API endpoints for user, book, and system management.

All endpoints require admin or super_admin role.
"""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import AdminUser
from app.db.session import get_db
from app.models.book import Book, Rating
from app.models.chat import ChatMessage, ChatSession
from app.models.rating_flag import RatingFlag
from app.models.user import User
from app.repositories.book_repo import BookRepository
from app.repositories.user_repo import UserRepository
from app.schemas.admin import (
    AdminBookResponse,
    AdminChatMessageResponse,
    AdminChatSessionDetailResponse,
    AdminChatSessionResponse,
    AdminRatingResponse,
    AdminUserResponse,
    AdminUserUpdate,
    BookProcessingRequest,
    BookProcessingResponse,
    PaginatedResponse,
    RatingAnalytics,
    SystemStatsResponse,
)

router = APIRouter()
logger = structlog.get_logger(__name__)


# ============================================================================
# User Management Endpoints
# ============================================================================


@router.get(
    "/users",
    response_model=dict,
    summary="List all users (admin)",
    description="""
List all users with search, filtering, and pagination.

**Filters:**
- `search`: Search by email, username, or display_name
- `status`: Filter by account status (active, suspended, deleted)
- `role`: Filter by role

**Requires:** Admin role
    """,
)
async def list_users(
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(None, description="Search term"),
    status: str | None = Query(None, description="Filter by status"),
    role: str | None = Query(None, description="Filter by role"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> dict:
    """List all users with filtering and pagination."""
    # Build query
    query = select(User)

    # Apply filters
    filters = []
    if search:
        search_term = f"%{search}%"
        filters.append(
            or_(
                User.email.ilike(search_term),
                User.username.ilike(search_term),
                User.display_name.ilike(search_term),
            )
        )
    if status:
        filters.append(User.status == status)
    if role:
        filters.append(User.roles.contains([role]))

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(User.created_at.desc())

    result = await db.execute(query)
    users = result.scalars().all()

    items = [AdminUserResponse.model_validate(u) for u in users]

    logger.info(
        "Admin listed users",
        admin_id=str(admin_user.id),
        total=total,
        page=page,
    )

    return PaginatedResponse.create(items, total, page, page_size).model_dump()


@router.get(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Get user details (admin)",
    description="Get full details for a specific user.",
)
async def get_user(
    user_id: UUID,
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    """Get user details by ID."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return AdminUserResponse.model_validate(user)


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Update user (admin)",
    description="""
Update a user's profile, roles, or status.

**Updatable Fields:**
- `display_name`: User's display name
- `roles`: Array of roles (user, premium, admin, super_admin)
- `status`: Account status (active, suspended, deleted)

**Requires:** Admin role
    """,
)
async def update_user(
    user_id: UUID,
    data: AdminUserUpdate,
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    """Update user as admin."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent modifying super_admin unless you are super_admin
    if "super_admin" in user.roles and "super_admin" not in admin_user.roles:
        raise HTTPException(
            status_code=403,
            detail="Cannot modify super_admin users",
        )

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        user = await user_repo.update(user, **update_data)
        logger.info(
            "Admin updated user",
            admin_id=str(admin_user.id),
            user_id=str(user_id),
            updates=list(update_data.keys()),
        )

    return AdminUserResponse.model_validate(user)


@router.post(
    "/users/{user_id}/disable",
    response_model=AdminUserResponse,
    summary="Disable user account (admin)",
    description="Set user status to 'suspended'.",
)
async def disable_user(
    user_id: UUID,
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    """Disable a user account."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if "super_admin" in user.roles:
        raise HTTPException(
            status_code=403,
            detail="Cannot disable super_admin users",
        )

    user = await user_repo.update(user, status="suspended")
    logger.info(
        "Admin disabled user",
        admin_id=str(admin_user.id),
        user_id=str(user_id),
    )

    return AdminUserResponse.model_validate(user)


# ============================================================================
# Book Management Endpoints
# ============================================================================


@router.get(
    "/books",
    response_model=dict,
    summary="List all books (admin)",
    description="""
List all books with search, filtering, and pagination.

**Filters:**
- `search`: Search by title or author
- `category`: Filter by category
- `owner_id`: Filter by book owner
- `visibility`: Filter by visibility (public, private, friends)
- `has_pages`: Filter by whether pages are generated

**Requires:** Admin role
    """,
)
async def list_books(
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(None, description="Search term"),
    category: str | None = Query(None, description="Category filter"),
    owner_id: UUID | None = Query(None, description="Owner ID filter"),
    visibility: str | None = Query(None, description="Visibility filter"),
    has_pages: bool | None = Query(None, description="Has pages filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> dict:
    """List all books with filtering and pagination."""
    # Build query
    query = select(Book)

    # Apply filters
    filters = []
    if search:
        search_term = f"%{search}%"
        filters.append(
            or_(
                Book.title.ilike(search_term),
                Book.author.ilike(search_term),
            )
        )
    if category:
        filters.append(Book.category == category)
    if owner_id:
        filters.append(Book.owner_id == owner_id)
    if visibility:
        filters.append(Book.visibility == visibility)
    if has_pages is not None:
        if has_pages:
            filters.append(Book.page_count > 0)
        else:
            filters.append(Book.page_count == 0)

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Book.created_at.desc())

    result = await db.execute(query)
    books = result.scalars().all()

    # Enrich with owner info
    items = []
    for book in books:
        item = AdminBookResponse.model_validate(book)
        # Get owner username
        if book.owner_id:
            owner_query = select(User.username).where(User.id == book.owner_id)
            owner_result = await db.execute(owner_query)
            owner_username = owner_result.scalar()
            item.owner_username = owner_username
        # Determine processing status based on page_count
        item.processing_status = "ready" if book.page_count and book.page_count > 0 else "pending"
        items.append(item)

    logger.info(
        "Admin listed books",
        admin_id=str(admin_user.id),
        total=total,
        page=page,
    )

    return PaginatedResponse.create(items, total, page, page_size).model_dump()


@router.get(
    "/books/{book_id}",
    response_model=AdminBookResponse,
    summary="Get book details (admin)",
    description="Get full details for a specific book.",
)
async def get_book(
    book_id: UUID,
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> AdminBookResponse:
    """Get book details by ID."""
    book_repo = BookRepository(db)
    book = await book_repo.get_by_id(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    response = AdminBookResponse.model_validate(book)
    response.processing_status = "ready" if book.pages_count > 0 else "pending"

    # Get owner username
    if book.owner_id:
        owner_query = select(User.username).where(User.id == book.owner_id)
        owner_result = await db.execute(owner_query)
        response.owner_username = owner_result.scalar()

    return response


@router.post(
    "/books/{book_id}/generate-pages",
    response_model=BookProcessingResponse,
    summary="Generate pages for book (admin)",
    description="""
Trigger page generation for a PDF book.

Converts PDF pages to images for in-app viewing.
    """,
)
async def generate_pages(
    book_id: UUID,
    data: BookProcessingRequest,
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> BookProcessingResponse:
    """Trigger page generation for a book."""
    book_repo = BookRepository(db)
    book = await book_repo.get_by_id(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if not book.file_url:
        raise HTTPException(status_code=400, detail="Book has no file")

    if book.pages_count > 0 and not data.force:
        return BookProcessingResponse(
            book_id=book_id,
            action="generate-pages",
            status="completed",
            message=f"Book already has {book.pages_count} pages. Use force=true to regenerate.",
        )

    # TODO: Queue page generation job
    # For now, return queued status
    logger.info(
        "Admin triggered page generation",
        admin_id=str(admin_user.id),
        book_id=str(book_id),
        force=data.force,
    )

    return BookProcessingResponse(
        book_id=book_id,
        action="generate-pages",
        status="queued",
        message="Page generation job queued",
    )


@router.post(
    "/books/{book_id}/generate-thumbnails",
    response_model=BookProcessingResponse,
    summary="Regenerate thumbnails (admin)",
    description="Regenerate page thumbnails for a book.",
)
async def generate_thumbnails(
    book_id: UUID,
    data: BookProcessingRequest,
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> BookProcessingResponse:
    """Trigger thumbnail regeneration for a book."""
    book_repo = BookRepository(db)
    book = await book_repo.get_by_id(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.pages_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Book has no pages. Generate pages first.",
        )

    logger.info(
        "Admin triggered thumbnail generation",
        admin_id=str(admin_user.id),
        book_id=str(book_id),
    )

    return BookProcessingResponse(
        book_id=book_id,
        action="generate-thumbnails",
        status="queued",
        message="Thumbnail generation job queued",
    )


@router.post(
    "/books/{book_id}/process-ai",
    response_model=BookProcessingResponse,
    summary="Process AI embeddings (admin)",
    description="""
Trigger AI processing for a book.

Generates text chunks and embeddings for AI chat functionality.
    """,
)
async def process_ai(
    book_id: UUID,
    data: BookProcessingRequest,
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> BookProcessingResponse:
    """Trigger AI processing for a book."""
    book_repo = BookRepository(db)
    book = await book_repo.get_by_id(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    logger.info(
        "Admin triggered AI processing",
        admin_id=str(admin_user.id),
        book_id=str(book_id),
    )

    return BookProcessingResponse(
        book_id=book_id,
        action="process-ai",
        status="queued",
        message="AI processing job queued",
    )


# ============================================================================
# Chat Session Management Endpoints
# ============================================================================


@router.get(
    "/chats",
    response_model=dict,
    summary="List chat sessions (admin)",
    description="""
List all chat sessions with filtering and pagination.

**Filters:**
- `book_id`: Filter by book
- `user_id`: Filter by user

**Requires:** Admin role
    """,
)
async def list_chats(
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
    book_id: UUID | None = Query(None, description="Book ID filter"),
    user_id: UUID | None = Query(None, description="User ID filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> dict:
    """List all chat sessions with filtering and pagination."""
    # Build query
    query = select(ChatSession)

    filters = []
    if book_id:
        filters.append(ChatSession.book_id == book_id)
    if user_id:
        filters.append(ChatSession.user_id == user_id)

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(ChatSession.created_at.desc())

    result = await db.execute(query)
    sessions = result.scalars().all()

    # Enrich with book and user info
    items = []
    for session in sessions:
        item = AdminChatSessionResponse(
            id=session.id,
            book_id=session.book_id,
            user_id=session.user_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

        # Get book title
        book_query = select(Book.title).where(Book.id == session.book_id)
        book_result = await db.execute(book_query)
        item.book_title = book_result.scalar()

        # Get user username
        user_query = select(User.username).where(User.id == session.user_id)
        user_result = await db.execute(user_query)
        item.user_username = user_result.scalar()

        # Count messages
        msg_count_query = select(func.count()).where(ChatMessage.session_id == session.id)
        msg_count = await db.scalar(msg_count_query) or 0
        item.message_count = msg_count

        items.append(item)

    logger.info(
        "Admin listed chats",
        admin_id=str(admin_user.id),
        total=total,
        page=page,
    )

    return PaginatedResponse.create(items, total, page, page_size).model_dump()


@router.get(
    "/chats/{chat_id}",
    response_model=AdminChatSessionDetailResponse,
    summary="Get chat session details (admin)",
    description="Get full details for a chat session including messages.",
)
async def get_chat(
    chat_id: UUID,
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> AdminChatSessionDetailResponse:
    """Get chat session with messages."""
    query = select(ChatSession).where(ChatSession.id == chat_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Get messages
    msg_query = select(ChatMessage).where(ChatMessage.session_id == chat_id).order_by(ChatMessage.created_at)
    msg_result = await db.execute(msg_query)
    messages = msg_result.scalars().all()

    # Get book title
    book_query = select(Book.title).where(Book.id == session.book_id)
    book_result = await db.execute(book_query)
    book_title = book_result.scalar()

    # Get user username
    user_query = select(User.username).where(User.id == session.user_id)
    user_result = await db.execute(user_query)
    user_username = user_result.scalar()

    return AdminChatSessionDetailResponse(
        id=session.id,
        book_id=session.book_id,
        book_title=book_title,
        user_id=session.user_id,
        user_username=user_username,
        messages=[AdminChatMessageResponse.model_validate(m) for m in messages],
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.delete(
    "/chats/{chat_id}",
    summary="Delete chat session (admin)",
    description="Delete a chat session and all its messages.",
)
async def delete_chat(
    chat_id: UUID,
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a chat session."""
    query = select(ChatSession).where(ChatSession.id == chat_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    await db.delete(session)
    await db.commit()

    logger.info(
        "Admin deleted chat session",
        admin_id=str(admin_user.id),
        chat_id=str(chat_id),
    )

    return {"message": "Chat session deleted", "chat_id": str(chat_id)}


# ============================================================================
# System Statistics Endpoint
# ============================================================================


@router.get(
    "/stats",
    response_model=SystemStatsResponse,
    summary="Get system statistics (admin)",
    description="""
Get system-wide statistics including:
- User counts (total, active, admin)
- Book counts (total, public, private, with pages)
- Chat statistics
- Storage usage

**Requires:** Admin role
    """,
)
async def get_stats(
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> SystemStatsResponse:
    """Get system-wide statistics."""
    # User stats
    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    active_users = await db.scalar(
        select(func.count()).select_from(User).where(User.status == "active")
    ) or 0
    admin_users = await db.scalar(
        select(func.count()).select_from(User).where(
            or_(
                User.roles.contains(["admin"]),
                User.roles.contains(["super_admin"]),
            )
        )
    ) or 0

    # Book stats
    total_books = await db.scalar(select(func.count()).select_from(Book)) or 0
    public_books = await db.scalar(
        select(func.count()).select_from(Book).where(Book.visibility == "public")
    ) or 0
    private_books = total_books - public_books
    books_with_pages = await db.scalar(
        select(func.count()).select_from(Book).where(Book.page_count > 0)
    ) or 0

    # Chat stats
    total_chat_sessions = await db.scalar(select(func.count()).select_from(ChatSession)) or 0
    total_chat_messages = await db.scalar(select(func.count()).select_from(ChatMessage)) or 0

    # Storage (placeholder - would need actual file size calculation)
    storage_used_bytes = 0
    storage_used_formatted = "0 B"

    logger.info(
        "Admin retrieved stats",
        admin_id=str(admin_user.id),
    )

    return SystemStatsResponse(
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        total_books=total_books,
        public_books=public_books,
        private_books=private_books,
        books_with_pages=books_with_pages,
        total_chat_sessions=total_chat_sessions,
        total_chat_messages=total_chat_messages,
        storage_used_bytes=storage_used_bytes,
        storage_used_formatted=storage_used_formatted,
    )


# ============================================================================
# Rating Management Endpoints
# ============================================================================


@router.get(
    "/ratings",
    response_model=dict,
    summary="List all ratings (admin)",
    description="List all ratings system-wide with filtering and pagination.",
)
async def list_ratings(
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
    book_id: UUID | None = Query(None, description="Filter by book"),
    user_id: UUID | None = Query(None, description="Filter by user"),
    flagged_only: bool = Query(False, description="Show only flagged ratings"),
    min_rating: int | None = Query(None, ge=1, le=5),
    max_rating: int | None = Query(None, ge=1, le=5),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    """List all ratings with filtering."""
    # Build query
    query = select(Rating)

    # Apply filters
    filters = []
    if book_id:
        filters.append(Rating.book_id == book_id)
    if user_id:
        filters.append(Rating.user_id == user_id)
    if min_rating:
        filters.append(Rating.rating >= min_rating)
    if max_rating:
        filters.append(Rating.rating <= max_rating)

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Rating.created_at.desc())

    result = await db.execute(query)
    ratings = result.scalars().all()

    # Enrich with book/user info and flag count
    items = []
    for rating in ratings:
        # Get flag count
        flag_count_query = select(func.count()).where(
            and_(
                RatingFlag.rating_id == rating.id,
                RatingFlag.status == "pending",
            )
        )
        flag_count = await db.scalar(flag_count_query) or 0

        # Skip if flagged_only and no flags
        if flagged_only and flag_count == 0:
            continue

        # Get book title
        book_query = select(Book.title).where(Book.id == rating.book_id)
        book_result = await db.execute(book_query)
        book_title = book_result.scalar()

        # Get user username
        user_query = select(User.username).where(User.id == rating.user_id)
        user_result = await db.execute(user_query)
        user_username = user_result.scalar()

        item = AdminRatingResponse(
            id=rating.id,
            book_id=rating.book_id,
            book_title=book_title,
            user_id=rating.user_id,
            user_username=user_username,
            rating=rating.rating,
            review=rating.review,
            flag_count=flag_count,
            is_flagged=flag_count > 0,
            created_at=rating.created_at,
            updated_at=rating.updated_at,
        )
        items.append(item)

    logger.info(
        "Admin listed ratings",
        admin_id=str(admin_user.id),
        total=total,
        page=page,
    )

    return PaginatedResponse.create(items, total, page, page_size).model_dump()


@router.delete(
    "/ratings/{rating_id}",
    summary="Delete rating (admin)",
    description="Delete an inappropriate rating.",
)
async def delete_rating(
    rating_id: UUID,
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a rating."""
    query = select(Rating).where(Rating.id == rating_id)
    result = await db.execute(query)
    rating = result.scalar_one_or_none()

    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found")

    await db.delete(rating)
    await db.commit()

    logger.info(
        "Admin deleted rating",
        admin_id=str(admin_user.id),
        rating_id=str(rating_id),
    )

    return {"message": "Rating deleted", "rating_id": str(rating_id)}


@router.get(
    "/analytics/ratings",
    response_model=RatingAnalytics,
    summary="Get rating analytics (admin)",
    description="Get comprehensive rating statistics and trends.",
)
async def get_rating_analytics(
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> RatingAnalytics:
    """Get rating analytics."""
    # Total ratings and average
    stats_query = select(
        func.count(Rating.id).label("total"),
        func.avg(Rating.rating).label("average"),
    )
    stats_result = await db.execute(stats_query)
    stats = stats_result.one()

    # Distribution
    dist_query = select(
        Rating.rating,
        func.count(Rating.id).label("count"),
    ).group_by(Rating.rating)
    dist_result = await db.execute(dist_query)
    distribution = {str(row[0]): row[1] for row in dist_result.all()}

    # Top rated books (with at least 3 ratings)
    top_books_query = (
        select(
            Book.id,
            Book.title,
            func.avg(Rating.rating).label("avg_rating"),
            func.count(Rating.id).label("rating_count"),
        )
        .join(Rating, Rating.book_id == Book.id)
        .group_by(Book.id, Book.title)
        .having(func.count(Rating.id) >= 3)
        .order_by(func.avg(Rating.rating).desc())
        .limit(10)
    )
    top_books_result = await db.execute(top_books_query)
    top_rated_books = [
        {
            "book_id": str(row[0]),
            "title": row[1],
            "avg_rating": round(float(row[2]), 2),
            "rating_count": row[3],
        }
        for row in top_books_result.all()
    ]

    # Most reviewed books
    most_reviewed_query = (
        select(
            Book.id,
            Book.title,
            func.count(Rating.id).label("review_count"),
            func.avg(Rating.rating).label("avg_rating"),
        )
        .join(Rating, Rating.book_id == Book.id)
        .group_by(Book.id, Book.title)
        .order_by(func.count(Rating.id).desc())
        .limit(10)
    )
    most_reviewed_result = await db.execute(most_reviewed_query)
    most_reviewed_books = [
        {
            "book_id": str(row[0]),
            "title": row[1],
            "review_count": row[2],
            "avg_rating": round(float(row[3]), 2),
        }
        for row in most_reviewed_result.all()
    ]

    # Recent flagged count
    flagged_count = await db.scalar(
        select(func.count()).select_from(RatingFlag).where(RatingFlag.status == "pending")
    ) or 0

    return RatingAnalytics(
        total_ratings=stats.total or 0,
        average_rating=round(float(stats.average), 2) if stats.average else 0.0,
        distribution=distribution,
        top_rated_books=top_rated_books,
        most_reviewed_books=most_reviewed_books,
        recent_flagged_count=flagged_count,
    )
