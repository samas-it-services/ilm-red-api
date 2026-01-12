"""Recommendation schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RecommendedBook(BaseModel):
    """Recommended book with reasoning."""

    book_id: UUID
    title: str
    author: str | None
    category: str
    cover_url: str | None
    average_rating: float | None
    ratings_count: int
    reason: str  # Why this book was recommended

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "book_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Introduction to Fiqh",
                "author": "Sheikh Ahmad",
                "category": "fiqh",
                "cover_url": "https://example.com/cover.jpg",
                "average_rating": 4.5,
                "ratings_count": 12,
                "reason": "Based on your interest in Islamic jurisprudence",
            }
        }
    )
