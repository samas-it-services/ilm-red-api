"""Addon system Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


# --- Response Schemas ---


class AddonRegistryResponse(BaseModel):
    """Addon marketplace listing response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    version: str
    description: str | None = None
    icon: str | None = None
    author: str | None = None
    author_email: str | None = None
    license: str | None = None
    category: str | None = None
    tags: list[str] = []
    entry_point: str | None = None
    manifest_url: str | None = None
    bundle_url: str | None = None
    config_schema: dict = {}
    permissions: list[str] = []
    is_official: bool = False
    is_free: bool = True
    price: float | None = None
    download_count: int = 0
    rating: float = 0.0
    review_count: int = 0
    status: str
    created_at: datetime
    updated_at: datetime


class AddonReviewResponse(BaseModel):
    """Addon review response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    addon_id: uuid.UUID
    user_id: uuid.UUID
    rating: int
    title: str | None = None
    content: str | None = None
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime


class GlobalAddonConfigResponse(BaseModel):
    """Global addon configuration response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    addon_id: uuid.UUID
    is_available: bool
    is_default_enabled: bool
    is_required: bool
    requires_approval: bool
    max_installations_per_club: int | None = None
    default_config: dict = {}
    notes: str | None = None
    configured_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class BookClubAddonConfigResponse(BaseModel):
    """Per-club addon config response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    addon_id: uuid.UUID
    book_club_id: uuid.UUID
    is_available: bool
    is_enabled_by_default: bool
    can_be_disabled: bool
    default_config: dict = {}
    max_installations: int | None = None
    notes: str | None = None
    configured_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class AddonListResponse(BaseModel):
    """Paginated addon list response."""

    data: list[AddonRegistryResponse]
    pagination: Pagination


# --- Request Schemas ---


class AddonRegistryCreate(BaseModel):
    """Create a new addon in the registry."""

    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=200)
    version: str = Field("1.0.0", max_length=50)
    description: str | None = None
    icon: str | None = None
    author: str | None = None
    author_email: str | None = None
    license: str | None = None
    category: str | None = None
    tags: list[str] = []
    entry_point: str | None = None
    manifest_url: str | None = None
    bundle_url: str | None = None
    config_schema: dict = {}
    permissions: list[str] = []
    is_official: bool = False
    is_free: bool = True
    price: float | None = None


class AddonReviewCreate(BaseModel):
    """Create a review for an addon."""

    rating: int = Field(..., ge=1, le=5)
    title: str | None = Field(None, max_length=200)
    content: str | None = Field(None, max_length=5000)


class AddonInstallRequest(BaseModel):
    """Request to install an addon for a book club."""

    addon_id: uuid.UUID
    config: dict = {}


class AddonConfigUpdate(BaseModel):
    """Update addon configuration for a club."""

    is_available: bool | None = None
    is_enabled_by_default: bool | None = None
    can_be_disabled: bool | None = None
    default_config: dict | None = None
    notes: str | None = None


class GlobalAddonConfigUpdate(BaseModel):
    """Update global addon configuration (admin only)."""

    addon_id: uuid.UUID
    is_available: bool | None = None
    is_default_enabled: bool | None = None
    is_required: bool | None = None
    requires_approval: bool | None = None
    max_installations_per_club: int | None = None
    default_config: dict | None = None
    notes: str | None = None
