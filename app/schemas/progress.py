"""Reading progress schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProgressUpdate(BaseModel):
    """Request to update reading progress."""

    current_page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    total_pages: int = Field(..., ge=1, description="Total pages in book")
    reading_time_seconds: int = Field(
        default=0,
        ge=0,
        description="Time spent reading since last update (seconds)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_page": 42,
                "total_pages": 350,
                "reading_time_seconds": 180,
            }
        }
    )


class ProgressResponse(BaseModel):
    """Reading progress response."""

    book_id: UUID
    current_page: int
    total_pages: int
    progress_percent: int
    last_read_at: datetime
    started_at: datetime
    completed_at: datetime | None = None
    reading_time_seconds: int

    model_config = ConfigDict(from_attributes=True)


class RecentRead(BaseModel):
    """Recent read with book info."""

    book_id: UUID
    book_title: str
    book_author: str | None = None
    book_cover_url: str | None = None
    current_page: int
    total_pages: int
    progress_percent: int
    last_read_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReadingStats(BaseModel):
    """User's reading statistics."""

    total_books_started: int
    total_books_completed: int
    total_reading_time_seconds: int
    total_reading_time_formatted: str  # "2h 35m"
    current_streak_days: int
    longest_streak_days: int
    avg_pages_per_day: float

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_books_started": 15,
                "total_books_completed": 7,
                "total_reading_time_seconds": 36000,
                "total_reading_time_formatted": "10h 0m",
                "current_streak_days": 5,
                "longest_streak_days": 12,
                "avg_pages_per_day": 25.5,
            }
        }
    )
