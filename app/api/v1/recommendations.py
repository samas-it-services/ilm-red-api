"""Recommendations API endpoints."""

from fastapi import APIRouter, Query

from app.api.v1.deps import CurrentUser, DBSession
from app.schemas.recommendation import RecommendedBook
from app.services.recommendation_service import RecommendationService

router = APIRouter()


@router.get(
    "/for-you",
    response_model=list[RecommendedBook],
    summary="Get personalized recommendations",
    description="""
Get personalized book recommendations based on your reading history.

**Recommendation Algorithm:**
1. Books in categories you've been reading (40% weight)
2. Top-rated books you haven't read (30% weight)
3. Recently added popular books (30% weight)

**Note:** Recommendations are personalized based on your reading progress and preferences.
    """,
)
async def get_recommendations(
    current_user: CurrentUser,
    db: DBSession,
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations"),
) -> list[RecommendedBook]:
    """Get personalized recommendations."""
    service = RecommendationService(db)
    return await service.get_recommendations(current_user.id, limit)
