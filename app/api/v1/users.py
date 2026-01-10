"""User endpoints."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser
from app.db.session import get_db
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

    from uuid import UUID
    user = await user_repo.get_by_id(UUID(user_id))

    if not user or user.status != "active":
        raise HTTPException(status_code=404, detail="User not found")

    return PublicUserResponse.model_validate(user)
