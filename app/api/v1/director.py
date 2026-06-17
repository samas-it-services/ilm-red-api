"""Director dashboard API endpoints.

Provides aggregated metrics and statistics for library directors.
All endpoints require the director_library_operations role.
"""

from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_roles
from app.db.session import get_db
from app.models.billing import AIUsageRecord, BillingTransaction
from app.models.book import Book
from app.models.chat import ChatMessage, ChatSession
from app.models.progress import ReadingProgress
from app.models.user import User

router = APIRouter()
logger = structlog.get_logger(__name__)

# Director role dependency
DirectorUser = Depends(require_roles("director_library_operations", "admin", "super_admin"))


@router.get(
    "/dashboard",
    summary="Director dashboard metrics",
    description="""
Get aggregated metrics for the director dashboard.

**Includes:**
- Total users, active today, new this week/month
- Total books, books uploaded this week/month
- Active chat sessions today
- Reading activity summary

**Requires:** director_library_operations role
    """,
    dependencies=[DirectorUser],
)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get aggregated dashboard metrics."""
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # User metrics
    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    active_users = await db.scalar(
        select(func.count()).select_from(User).where(User.status == "active")
    ) or 0
    active_today = await db.scalar(
        select(func.count()).select_from(User).where(
            User.last_active_at >= today_start,
        )
    ) or 0
    new_users_week = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= week_ago)
    ) or 0
    new_users_month = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= month_ago)
    ) or 0

    # Book metrics
    total_books = await db.scalar(
        select(func.count()).select_from(Book).where(Book.deleted_at.is_(None))
    ) or 0
    books_this_week = await db.scalar(
        select(func.count()).select_from(Book).where(
            Book.created_at >= week_ago,
            Book.deleted_at.is_(None),
        )
    ) or 0
    books_this_month = await db.scalar(
        select(func.count()).select_from(Book).where(
            Book.created_at >= month_ago,
            Book.deleted_at.is_(None),
        )
    ) or 0
    public_books = await db.scalar(
        select(func.count()).select_from(Book).where(
            Book.visibility == "public",
            Book.deleted_at.is_(None),
        )
    ) or 0

    # Chat metrics
    total_chat_sessions = await db.scalar(
        select(func.count()).select_from(ChatSession)
    ) or 0
    chat_sessions_today = await db.scalar(
        select(func.count()).select_from(ChatSession).where(
            ChatSession.created_at >= today_start,
        )
    ) or 0
    total_chat_messages = await db.scalar(
        select(func.count()).select_from(ChatMessage)
    ) or 0

    # Reading activity
    active_readers_today = await db.scalar(
        select(func.count(func.distinct(ReadingProgress.user_id))).where(
            ReadingProgress.last_read_at >= today_start,
        )
    ) or 0

    logger.info("Director dashboard accessed")

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "active_today": active_today,
            "new_this_week": new_users_week,
            "new_this_month": new_users_month,
        },
        "books": {
            "total": total_books,
            "public": public_books,
            "uploaded_this_week": books_this_week,
            "uploaded_this_month": books_this_month,
        },
        "chat": {
            "total_sessions": total_chat_sessions,
            "sessions_today": chat_sessions_today,
            "total_messages": total_chat_messages,
        },
        "reading": {
            "active_readers_today": active_readers_today,
        },
        "generated_at": now.isoformat(),
    }


@router.get(
    "/users/stats",
    summary="User statistics",
    description="""
Get detailed user statistics including growth and activity trends.

**Requires:** director_library_operations role
    """,
    dependencies=[DirectorUser],
)
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
) -> dict:
    """Get user statistics and growth data."""
    now = datetime.now(UTC)
    start_date = now - timedelta(days=days)

    # Total counts by status
    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    active_count = await db.scalar(
        select(func.count()).select_from(User).where(User.status == "active")
    ) or 0
    suspended_count = await db.scalar(
        select(func.count()).select_from(User).where(User.status == "suspended")
    ) or 0

    # Premium vs free users
    premium_count = await db.scalar(
        select(func.count()).select_from(User).where(User.is_premium_user.is_(True))
    ) or 0

    # New user signups in period
    new_signups = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= start_date)
    ) or 0

    # Users with completed onboarding
    onboarded_count = await db.scalar(
        select(func.count()).select_from(User).where(User.onboarding_completed.is_(True))
    ) or 0

    # Users active in the period
    recently_active = await db.scalar(
        select(func.count()).select_from(User).where(User.last_active_at >= start_date)
    ) or 0

    logger.info("Director accessed user stats", days=days)

    return {
        "period_days": days,
        "total_users": total_users,
        "by_status": {
            "active": active_count,
            "suspended": suspended_count,
        },
        "premium_users": premium_count,
        "free_users": total_users - premium_count,
        "new_signups": new_signups,
        "onboarding_completed": onboarded_count,
        "onboarding_rate": round(onboarded_count / total_users * 100, 1) if total_users > 0 else 0,
        "recently_active": recently_active,
        "activity_rate": round(recently_active / total_users * 100, 1) if total_users > 0 else 0,
    }


@router.get(
    "/books/stats",
    summary="Book statistics",
    description="""
Get detailed book statistics including upload trends and category distribution.

**Requires:** director_library_operations role
    """,
    dependencies=[DirectorUser],
)
async def get_book_stats(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
) -> dict:
    """Get book statistics."""
    now = datetime.now(UTC)
    start_date = now - timedelta(days=days)

    # Total books
    total_books = await db.scalar(
        select(func.count()).select_from(Book).where(Book.deleted_at.is_(None))
    ) or 0

    # Books uploaded in period
    uploaded_in_period = await db.scalar(
        select(func.count()).select_from(Book).where(
            Book.created_at >= start_date,
            Book.deleted_at.is_(None),
        )
    ) or 0

    # By visibility
    public_count = await db.scalar(
        select(func.count()).select_from(Book).where(
            Book.visibility == "public",
            Book.deleted_at.is_(None),
        )
    ) or 0
    private_count = await db.scalar(
        select(func.count()).select_from(Book).where(
            Book.visibility == "private",
            Book.deleted_at.is_(None),
        )
    ) or 0

    # By status
    ready_count = await db.scalar(
        select(func.count()).select_from(Book).where(
            Book.status == "ready",
            Book.deleted_at.is_(None),
        )
    ) or 0
    processing_count = await db.scalar(
        select(func.count()).select_from(Book).where(
            Book.status == "processing",
            Book.deleted_at.is_(None),
        )
    ) or 0
    failed_count = await db.scalar(
        select(func.count()).select_from(Book).where(
            Book.status == "failed",
            Book.deleted_at.is_(None),
        )
    ) or 0

    # Category distribution
    category_query = (
        select(Book.category, func.count(Book.id).label("count"))
        .where(Book.deleted_at.is_(None))
        .group_by(Book.category)
        .order_by(func.count(Book.id).desc())
    )
    category_result = await db.execute(category_query)
    categories = {row[0]: row[1] for row in category_result.all()}

    # Top uploaders
    top_uploaders_query = (
        select(
            User.id,
            User.username,
            func.count(Book.id).label("book_count"),
        )
        .join(Book, Book.owner_id == User.id)
        .where(Book.deleted_at.is_(None))
        .group_by(User.id, User.username)
        .order_by(func.count(Book.id).desc())
        .limit(10)
    )
    top_uploaders_result = await db.execute(top_uploaders_query)
    top_uploaders = [
        {
            "user_id": str(row[0]),
            "username": row[1],
            "book_count": row[2],
        }
        for row in top_uploaders_result.all()
    ]

    logger.info("Director accessed book stats", days=days)

    return {
        "period_days": days,
        "total_books": total_books,
        "uploaded_in_period": uploaded_in_period,
        "by_visibility": {
            "public": public_count,
            "private": private_count,
        },
        "by_status": {
            "ready": ready_count,
            "processing": processing_count,
            "failed": failed_count,
        },
        "by_category": categories,
        "top_uploaders": top_uploaders,
    }


@router.get(
    "/usage/stats",
    summary="AI usage statistics",
    description="""
Get AI usage statistics including token consumption and cost trends.

**Requires:** director_library_operations role
    """,
    dependencies=[DirectorUser],
)
async def get_usage_stats(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
) -> dict:
    """Get AI usage statistics."""
    now = datetime.now(UTC)
    start_date = now - timedelta(days=days)

    # Total AI usage records in period
    total_usage_records = await db.scalar(
        select(func.count()).select_from(AIUsageRecord).where(
            AIUsageRecord.created_at >= start_date,
        )
    ) or 0

    # Total tokens used in period
    token_stats = await db.execute(
        select(
            func.sum(AIUsageRecord.prompt_tokens).label("total_prompt"),
            func.sum(AIUsageRecord.completion_tokens).label("total_completion"),
            func.sum(AIUsageRecord.total_tokens).label("total_tokens"),
            func.sum(AIUsageRecord.ai_cost_usd).label("total_cost"),
            func.sum(AIUsageRecord.billed_cost_usd).label("total_billed"),
        ).where(AIUsageRecord.created_at >= start_date)
    )
    token_row = token_stats.one()

    # Usage by model
    model_usage_query = (
        select(
            AIUsageRecord.ai_model,
            func.count(AIUsageRecord.id).label("request_count"),
            func.sum(AIUsageRecord.total_tokens).label("total_tokens"),
            func.sum(AIUsageRecord.ai_cost_usd).label("total_cost"),
        )
        .where(AIUsageRecord.created_at >= start_date)
        .group_by(AIUsageRecord.ai_model)
        .order_by(func.sum(AIUsageRecord.total_tokens).desc())
    )
    model_result = await db.execute(model_usage_query)
    usage_by_model = [
        {
            "model": row[0],
            "request_count": row[1],
            "total_tokens": row[2] or 0,
            "total_cost_usd": float(row[3]) if row[3] else 0.0,
        }
        for row in model_result.all()
    ]

    # Unique users who used AI in period
    unique_ai_users = await db.scalar(
        select(func.count(func.distinct(AIUsageRecord.user_id))).where(
            AIUsageRecord.created_at >= start_date,
        )
    ) or 0

    # Billing transactions in period
    total_billing_transactions = await db.scalar(
        select(func.count()).select_from(BillingTransaction).where(
            BillingTransaction.created_at >= start_date,
        )
    ) or 0

    logger.info("Director accessed usage stats", days=days)

    return {
        "period_days": days,
        "total_usage_records": total_usage_records,
        "tokens": {
            "prompt_tokens": token_row.total_prompt or 0,
            "completion_tokens": token_row.total_completion or 0,
            "total_tokens": token_row.total_tokens or 0,
        },
        "cost": {
            "total_ai_cost_usd": float(token_row.total_cost) if token_row.total_cost else 0.0,
            "total_billed_usd": float(token_row.total_billed) if token_row.total_billed else 0.0,
        },
        "usage_by_model": usage_by_model,
        "unique_ai_users": unique_ai_users,
        "total_billing_transactions": total_billing_transactions,
    }
