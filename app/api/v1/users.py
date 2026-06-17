"""User endpoints."""

from datetime import UTC, datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser, DBSession, OptionalUser
from app.db.session import get_db
from app.models.book import Book
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import PublicUserResponse, UserResponse, UserUpdate

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get my profile",
    description="""
Get the authenticated user's full profile.

**Includes:**
- Email (private)
- Username and display name
- Avatar URL and bio
- Preferences (theme, language, AI model defaults)
- Account status and creation date

**Example:**
```bash
curl -X GET /v1/users/me \\
  -H "Authorization: Bearer <token>"
```

**Requires:** Bearer token authentication
    """,
)
async def get_current_user_profile(
    current_user: CurrentUser,
) -> UserResponse:
    """Get the current authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update my profile",
    description="""
Update your profile information and preferences.

**Updatable Fields:**
- `display_name` - Your public display name
- `avatar_url` - Profile picture URL
- `bio` - Short biography (max 500 chars)
- `preferences` - Theme, language, AI model defaults
- `extra_data` - Extended profile fields (full_name, city, country, etc.)

**Example:**
```bash
curl -X PATCH /v1/users/me \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{"display_name":"New Name","preferences":{"theme":"dark"},"extra_data":{"full_name":"John Doe","city":"Milpitas"}}'
```

**Preferences Options:**
- `theme`: "light", "dark", or "system"
- `language`: "en", "ar", etc.
- `default_ai_model`: Any supported AI model ID

**Extra Data Fields (future-proof JSON storage):**
- `full_name`: User's full legal name
- `city`: City of residence
- `state_province`: State or province
- `country`: Country of residence
- `date_of_birth`: Date of birth (YYYY-MM-DD)
- Additional custom fields can be added without schema changes

**Requires:** Bearer token authentication
    """,
)
async def update_current_user_profile(
    data: UserUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update the current user's profile."""
    user_repo = UserRepository(db)

    update_data = data.model_dump(exclude_unset=True)

    # Handle nested preferences update
    if "preferences" in update_data and update_data["preferences"]:
        # Merge with existing preferences
        existing_prefs = current_user.preferences or {}
        new_prefs = update_data["preferences"]
        if hasattr(new_prefs, "model_dump"):
            new_prefs = new_prefs.model_dump(exclude_unset=True)
        existing_prefs.update(new_prefs)
        update_data["preferences"] = existing_prefs

    # Handle nested extra_data update
    if "extra_data" in update_data and update_data["extra_data"]:
        # Merge with existing extra_data
        existing_extra = current_user.extra_data or {}
        new_extra = update_data["extra_data"]
        if hasattr(new_extra, "model_dump"):
            new_extra = new_extra.model_dump(exclude_unset=True)
        existing_extra.update(new_extra)
        update_data["extra_data"] = existing_extra

    if update_data:
        user = await user_repo.update(current_user, **update_data)
        logger.info("User profile updated", user_id=str(current_user.id))
        return UserResponse.model_validate(user)

    return UserResponse.model_validate(current_user)


# ============================================================================
# Wave 6: Onboarding Endpoints (must be before /{user_id} routes)
# ============================================================================


@router.get(
    "/me/onboarding",
    summary="Get onboarding status",
    description="""
Get the current user's onboarding status and progress.

**Requires:** Bearer token authentication
    """,
)
async def get_onboarding_status(
    current_user: CurrentUser,
) -> dict:
    """Get the current user's onboarding status."""
    extra_data = current_user.extra_data or {}
    onboarding_data = extra_data.get("onboarding", {})

    return {
        "onboarding_completed": current_user.onboarding_completed,
        "onboarding_completed_at": (
            current_user.onboarding_completed_at.isoformat()
            if current_user.onboarding_completed_at
            else None
        ),
        "onboarding_data": onboarding_data,
    }


@router.post(
    "/me/onboarding/complete",
    summary="Mark onboarding completed",
    description="""
Mark the current user's onboarding as completed.

**Requires:** Bearer token authentication
    """,
)
async def complete_onboarding(
    current_user: CurrentUser,
    db: DBSession,
) -> dict:
    """Mark onboarding as completed."""
    if current_user.onboarding_completed:
        return {
            "message": "Onboarding already completed",
            "onboarding_completed": True,
            "onboarding_completed_at": (
                current_user.onboarding_completed_at.isoformat()
                if current_user.onboarding_completed_at
                else None
            ),
        }

    user_repo = UserRepository(db)
    now = datetime.now(UTC)
    user = await user_repo.update(
        current_user,
        onboarding_completed=True,
        onboarding_completed_at=now,
    )

    logger.info("User completed onboarding", user_id=str(current_user.id))

    return {
        "message": "Onboarding completed successfully",
        "onboarding_completed": True,
        "onboarding_completed_at": now.isoformat(),
    }


@router.put(
    "/me/onboarding",
    summary="Save partial onboarding data",
    description="""
Save partial onboarding progress data. This allows the frontend to persist
onboarding state across sessions without marking it as complete.

**Requires:** Bearer token authentication
    """,
)
async def save_onboarding_data(
    data: dict,
    current_user: CurrentUser,
    db: DBSession,
) -> dict:
    """Save partial onboarding data."""
    user_repo = UserRepository(db)

    # Merge onboarding data into extra_data
    existing_extra = current_user.extra_data or {}
    existing_onboarding = existing_extra.get("onboarding", {})
    existing_onboarding.update(data)
    existing_extra["onboarding"] = existing_onboarding

    await user_repo.update(current_user, extra_data=existing_extra)

    logger.info("User saved onboarding data", user_id=str(current_user.id))

    return {
        "message": "Onboarding data saved",
        "onboarding_data": existing_onboarding,
    }


@router.get(
    "/{user_id}",
    response_model=PublicUserResponse,
    summary="Get user profile (public)",
    description="""
Get a user's **public** profile by their ID.

**Includes:** Display name, avatar, bio, join date, public books count
**Excludes:** Email, preferences, private data

**Use Case:** Viewing other users' profiles, social features, author pages

**Example:**
```bash
curl -X GET /v1/users/550e8400-e29b-41d4-a716-446655440000
```

**Note:** No authentication required for public profiles.
    """,
    responses={
        404: {"description": "User not found or account inactive"},
    },
)
async def get_user_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> PublicUserResponse:
    """Get a user's public profile."""
    user_repo = UserRepository(db)

    user = await user_repo.get_by_id(UUID(user_id))

    if not user or user.status != "active":
        raise HTTPException(status_code=404, detail="User not found")

    return PublicUserResponse.model_validate(user)


# ============================================================================
# Wave 6: Public Profile + Onboarding Endpoints
# ============================================================================


@router.get(
    "/{user_id}/public-profile",
    summary="Get user public profile with stats",
    description="""
Get a user's public profile including statistics like book count and activity.

**Includes:** Username, avatar, bio, public book count, join date
**Excludes:** Email, preferences, private data

**Note:** Authentication is optional. Authenticated users may see more details.
    """,
)
async def get_user_public_profile(
    user_id: UUID,
    db: DBSession,
    current_user: OptionalUser = None,
) -> dict:
    """Get a user's public profile with statistics."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user or user.status != "active":
        raise HTTPException(status_code=404, detail="User not found")

    # Count public books
    public_books_count = await db.scalar(
        select(func.count()).select_from(Book).where(
            Book.owner_id == user.id,
            Book.visibility == "public",
            Book.deleted_at.is_(None),
        )
    ) or 0

    # Count total books (only if viewing own profile)
    total_books_count = None
    if current_user and current_user.id == user.id:
        total_books_count = await db.scalar(
            select(func.count()).select_from(Book).where(
                Book.owner_id == user.id,
                Book.deleted_at.is_(None),
            )
        ) or 0

    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "public_books_count": public_books_count,
        "total_books_count": total_books_count,
        "is_premium": user.is_premium,
    }


@router.get(
    "/{user_id}/public-books",
    summary="Get user's public books",
    description="""
Get a paginated list of a user's public books.

**Note:** Authentication is optional.
    """,
)
async def get_user_public_books(
    user_id: UUID,
    db: DBSession,
    current_user: OptionalUser = None,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> dict:
    """Get a user's public books."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user or user.status != "active":
        raise HTTPException(status_code=404, detail="User not found")

    query = select(Book).where(
        Book.owner_id == user.id,
        Book.visibility == "public",
        Book.deleted_at.is_(None),
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Book.created_at.desc())

    result = await db.execute(query)
    books = result.scalars().all()

    items = [
        {
            "id": str(book.id),
            "title": book.title,
            "author": book.author,
            "description": book.description,
            "category": book.category,
            "cover_url": book.cover_url,
            "page_count": book.page_count,
            "created_at": book.created_at.isoformat() if book.created_at else None,
        }
        for book in books
    ]

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get(
    "/{user_id}/public-activity",
    summary="Get user's public activity",
    description="""
Get a user's recent public activity (books added, ratings, etc.).

**Note:** Authentication is optional.
    """,
)
async def get_user_public_activity(
    user_id: UUID,
    db: DBSession,
    current_user: OptionalUser = None,
    limit: int = Query(20, ge=1, le=50, description="Number of activities"),
) -> dict:
    """Get a user's public activity feed."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user or user.status != "active":
        raise HTTPException(status_code=404, detail="User not found")

    # Get recent public books as activity
    recent_books_query = (
        select(Book)
        .where(
            Book.owner_id == user.id,
            Book.visibility == "public",
            Book.deleted_at.is_(None),
        )
        .order_by(Book.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(recent_books_query)
    recent_books = result.scalars().all()

    activities = [
        {
            "type": "book_added",
            "book_id": str(book.id),
            "title": book.title,
            "category": book.category,
            "timestamp": book.created_at.isoformat() if book.created_at else None,
        }
        for book in recent_books
    ]

    return {
        "user_id": str(user.id),
        "activities": activities,
        "total": len(activities),
    }
