"""User endpoints."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserResponse, UserUpdate, PublicUserResponse
from app.api.v1.deps import CurrentUser

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: CurrentUser,
) -> UserResponse:
    """Get the current authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
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

    if update_data:
        user = await user_repo.update(current_user, **update_data)
        logger.info("User profile updated", user_id=str(current_user.id))
        return UserResponse.model_validate(user)

    return UserResponse.model_validate(current_user)


@router.get("/{user_id}", response_model=PublicUserResponse)
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
