"""Gamification Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LogActivityRequest(BaseModel):
    """Request to log an activity."""

    activity_name: str = Field(..., description="Name of the activity")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class LogActivityResponse(BaseModel):
    """Response after logging an activity."""

    points_awarded: int
    new_total_points: int
    rank_changed: bool
    new_rank: str | None = None


class AwardBadgeRequest(BaseModel):
    """Request to award a badge."""

    user_id: uuid.UUID
    badge_name: str
    metadata: dict = Field(default_factory=dict)


class BadgeResponse(BaseModel):
    """Badge response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    display_name: str
    description: str | None = None
    category: str
    icon: str | None = None
    color: str | None = None
    rarity: str
    points_awarded: int


class UserBadgeResponse(BaseModel):
    """User badge response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    badge: BadgeResponse
    earned_at: datetime
    awarded_by: uuid.UUID | None = None


class RankResponse(BaseModel):
    """Rank response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    display_name: str
    description: str | None = None
    level: int
    min_points: int
    color: str | None = None
    icon: str | None = None


class GamificationSummary(BaseModel):
    """User gamification summary."""

    user_id: uuid.UUID
    total_points: int
    current_rank: RankResponse | None = None
    recent_badges: list[UserBadgeResponse] = []
    badges_count: int = 0
    activities_today: int = 0


class ActivityResponse(BaseModel):
    """Activity type response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    display_name: str
    description: str | None = None
    points: int
    is_active: bool


class PointsHistoryResponse(BaseModel):
    """Points history entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    points: int
    reason: str | None = None
    created_at: datetime


class LeaderboardEntry(BaseModel):
    """Leaderboard entry."""

    user_id: uuid.UUID
    username: str
    display_name: str
    avatar_url: str | None = None
    total_points: int
    rank_position: int
    rank_name: str | None = None
