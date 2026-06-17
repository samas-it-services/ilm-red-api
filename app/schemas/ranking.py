"""Ranking system schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


class UserBrief(BaseModel):
    """Brief user information for embedding in ranking responses."""

    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


# Response Schemas


class RankingContextResponse(BaseModel):
    """Ranking context response."""

    id: UUID
    name: str
    type: str
    entity_id: UUID | None = None
    settings: dict = {}
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRankingResponse(BaseModel):
    """User ranking within a context."""

    id: UUID
    user_id: UUID
    context_id: UUID
    rank_position: int
    total_points: int
    percentile: float | None = None
    rank_id: UUID | None = None
    books_uploaded: int = 0
    books_reviewed: int = 0
    badges_earned_count: int = 0
    last_activity_at: datetime | None = None
    calculated_at: datetime
    user: UserBrief | None = None

    model_config = ConfigDict(from_attributes=True)


class LeaderboardEntry(BaseModel):
    """Single entry in a leaderboard."""

    rank_position: int
    total_points: int
    percentile: float | None = None
    books_uploaded: int = 0
    books_reviewed: int = 0
    badges_earned_count: int = 0
    last_activity_at: datetime | None = None
    user: UserBrief

    model_config = ConfigDict(from_attributes=True)


class LeaderboardResponse(BaseModel):
    """Paginated leaderboard response."""

    data: list[LeaderboardEntry]
    pagination: Pagination
    context: RankingContextResponse | None = None


class PointsHistoryEntry(BaseModel):
    """Single points history entry."""

    id: UUID
    source: str
    source_id: UUID | None = None
    points: int
    reason: str | None = None
    metadata: dict = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PointsHistoryResponse(BaseModel):
    """Paginated points history response."""

    data: list[PointsHistoryEntry]
    pagination: Pagination


class UserRankingSummary(BaseModel):
    """Summary of user rankings across all contexts."""

    user_id: UUID
    rankings: list[UserRankingResponse]


class RankingRefreshResponse(BaseModel):
    """Response after refreshing rankings for a context."""

    context_id: UUID
    users_recalculated: int
    message: str = "Rankings recalculated successfully"
