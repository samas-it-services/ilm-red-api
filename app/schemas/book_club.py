"""Book club Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserBrief(BaseModel):
    """Brief user info for responses."""
    id: uuid.UUID
    username: str
    display_name: str
    avatar_url: str | None = None


class BookClubCreate(BaseModel):
    """Create book club request."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    tagline: str | None = None
    visibility: str = Field("public", pattern="^(public|private|invite_only)$")
    max_members: int = Field(100, ge=2, le=10000)


class BookClubUpdate(BaseModel):
    """Update book club request."""
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    tagline: str | None = None
    visibility: str | None = Field(None, pattern="^(public|private|invite_only)$")
    max_members: int | None = Field(None, ge=2, le=10000)
    welcome_message: str | None = None
    settings: dict | None = None


class BookClubResponse(BaseModel):
    """Book club response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    tagline: str | None = None
    cover_image_url: str | None = None
    cover_thumbnail_url: str | None = None
    owner_id: uuid.UUID
    visibility: str
    member_count: int = 0
    max_members: int
    is_premium_only: bool
    created_at: datetime
    updated_at: datetime


class BookClubMemberResponse(BaseModel):
    """Club member response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    role: str
    custom_title: str | None = None
    joined_at: datetime


class BookClubDiscussionCreate(BaseModel):
    """Create discussion request."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    book_id: uuid.UUID | None = None
    tags: list[str] = []


class BookClubDiscussionResponse(BaseModel):
    """Discussion response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content: str
    author_id: uuid.UUID
    book_id: uuid.UUID | None = None
    tags: list[str] = []
    is_pinned: bool
    is_locked: bool
    replies_count: int
    likes_count: int
    created_at: datetime
    updated_at: datetime


class DiscussionReplyCreate(BaseModel):
    """Create reply request."""
    content: str = Field(..., min_length=1)
    parent_reply_id: uuid.UUID | None = None


class DiscussionReplyResponse(BaseModel):
    """Reply response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content: str
    author_id: uuid.UUID
    parent_reply_id: uuid.UUID | None = None
    likes_count: int
    created_at: datetime


class BookClubInviteCreate(BaseModel):
    """Create invite request."""
    title: str | None = None
    max_uses: int | None = None
    expires_in_days: int | None = Field(None, ge=1, le=365)


class BookClubInviteResponse(BaseModel):
    """Invite response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invite_code: str
    invite_url: str | None = None
    title: str | None = None
    max_uses: int | None = None
    current_uses: int
    is_active: bool
    expires_at: datetime | None = None
    created_at: datetime


class BookClubChallengeCreate(BaseModel):
    """Create challenge request."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    challenge_type: str = "reading"
    target_value: int = Field(1, ge=1)
    target_unit: str = "books"
    reward_points: int = Field(0, ge=0)
    start_date: datetime | None = None
    end_date: datetime | None = None


class BookClubChallengeResponse(BaseModel):
    """Challenge response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    challenge_type: str
    target_value: int
    target_unit: str
    reward_points: int
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_active: bool
    created_at: datetime


class NominationCreate(BaseModel):
    """Create nomination request."""
    book_id: uuid.UUID
    nomination_text: str | None = None


class NominationResponse(BaseModel):
    """Nomination response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    book_id: uuid.UUID
    nominated_by: uuid.UUID
    nomination_text: str | None = None
    votes_count: int
    status: str
    created_at: datetime


class BookClubActivityResponse(BaseModel):
    """Activity feed entry response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_type: str
    activity_data: dict
    user_id: uuid.UUID | None = None
    created_at: datetime


class BookClubStatsResponse(BaseModel):
    """Club statistics response."""
    member_count: int
    book_count: int
    discussion_count: int
    active_challenges: int
