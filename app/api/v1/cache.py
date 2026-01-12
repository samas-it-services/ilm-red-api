"""Cache management API endpoints.

Admin-only endpoints for monitoring and managing the Redis cache.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.deps import get_current_user
from app.cache.redis_client import CacheService, RedisCache
from app.models.user import User

router = APIRouter()


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""

    connected: bool
    used_memory: str | None = None
    used_memory_peak: str | None = None
    connected_clients: int | None = None
    total_connections_received: int | None = None
    keyspace_hits: int | None = None
    keyspace_misses: int | None = None
    hit_rate: float | None = None
    uptime_in_seconds: int | None = None
    error: str | None = None


class CacheInvalidateRequest(BaseModel):
    """Request model for cache invalidation."""

    pattern: str = Field(
        ...,
        description="Key pattern to invalidate (supports wildcards, e.g., 'books:*')",
        examples=["books:*", "users:profile:*"],
    )


class CacheInvalidateResponse(BaseModel):
    """Response model for cache invalidation."""

    pattern: str
    keys_deleted: int


class CacheKeyDeleteRequest(BaseModel):
    """Request model for deleting specific cache keys."""

    keys: list[str] = Field(
        ...,
        description="List of exact cache keys to delete",
        min_length=1,
        max_length=100,
    )


class CacheKeyDeleteResponse(BaseModel):
    """Response model for cache key deletion."""

    keys_deleted: int
    keys_requested: int


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require admin role."""
    if not current_user.roles or "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def get_cache_service() -> CacheService | None:
    """Dependency to get cache service."""
    try:
        redis_client = await RedisCache.get_client()
        return CacheService(redis_client)
    except Exception:
        return None


@router.get(
    "/stats",
    response_model=CacheStatsResponse,
    summary="Get cache statistics",
    description="Returns Redis cache statistics including memory usage, hit rate, and connection info.",
)
async def get_cache_stats(
    current_user: User = Depends(require_admin),
    cache_service: CacheService | None = Depends(get_cache_service),
) -> CacheStatsResponse:
    """Get Redis cache statistics (admin only)."""
    if cache_service is None:
        return CacheStatsResponse(connected=False, error="Redis not available")

    stats = await cache_service.get_stats()
    return CacheStatsResponse(**stats)


@router.post(
    "/invalidate",
    response_model=CacheInvalidateResponse,
    summary="Invalidate cache by pattern",
    description="Delete all cache keys matching the given pattern. Use '*' as wildcard.",
)
async def invalidate_cache(
    request: CacheInvalidateRequest,
    current_user: User = Depends(require_admin),
    cache_service: CacheService | None = Depends(get_cache_service),
) -> CacheInvalidateResponse:
    """Invalidate cache keys by pattern (admin only)."""
    if cache_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not available",
        )

    deleted = await cache_service.delete_pattern(request.pattern)
    return CacheInvalidateResponse(
        pattern=request.pattern,
        keys_deleted=deleted,
    )


@router.delete(
    "/keys",
    response_model=CacheKeyDeleteResponse,
    summary="Delete specific cache keys",
    description="Delete specific cache keys by their exact names.",
)
async def delete_cache_keys(
    request: CacheKeyDeleteRequest,
    current_user: User = Depends(require_admin),
    cache_service: CacheService | None = Depends(get_cache_service),
) -> CacheKeyDeleteResponse:
    """Delete specific cache keys (admin only)."""
    if cache_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not available",
        )

    deleted = 0
    for key in request.keys:
        if await cache_service.delete(key):
            deleted += 1

    return CacheKeyDeleteResponse(
        keys_deleted=deleted,
        keys_requested=len(request.keys),
    )


@router.get(
    "/health",
    summary="Check cache health",
    description="Simple health check for Redis connectivity.",
)
async def cache_health() -> dict[str, Any]:
    """Check if Redis cache is healthy."""
    try:
        redis_client = await RedisCache.get_client()
        await redis_client.ping()
        return {"status": "healthy", "connected": True}
    except Exception as e:
        return {"status": "unhealthy", "connected": False, "error": str(e)}


@router.post(
    "/flush",
    summary="Flush entire cache",
    description="Delete ALL keys from the cache. Use with caution!",
)
async def flush_cache(
    confirm: bool = False,
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Flush entire cache (admin only, requires confirmation)."""
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add ?confirm=true to confirm cache flush",
        )

    try:
        redis_client = await RedisCache.get_client()
        await redis_client.flushdb()
        return {"status": "flushed", "message": "All cache keys deleted"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis error: {str(e)}",
        )


@router.post(
    "/hydrate",
    summary="Hydrate (warm) cache with popular queries",
    description="Pre-populate cache with frequently accessed data to improve performance.",
)
async def hydrate_cache(
    current_user: User = Depends(require_admin),
    cache_service: CacheService | None = Depends(get_cache_service),
) -> dict[str, Any]:
    """Warm up cache with popular queries (admin only)."""
    from app.db.session import get_db

    if cache_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis not available",
        )

    # Get database session
    from app.main import app

    db_dependency = app.dependency_overrides.get(get_db, get_db)
    db = await anext(db_dependency())

    try:
        cached_count = 0

        # Hydrate popular categories
        popular_categories = ["quran", "hadith", "fiqh", "seerah", "tafsir"]

        for category in popular_categories:
            # This will trigger caching in search.py
            from app.api.v1.search import search_books

            # Simulate search for each category (this populates cache)
            await search_books(
                db=db,
                current_user=None,
                q=None,
                category=category,
                limit=20,
            )
            cached_count += 1

        # Hydrate general search (top books)
        await search_books(
            db=db,
            current_user=None,
            q=None,
            category=None,
            limit=50,
        )
        cached_count += 1

        return {
            "status": "hydrated",
            "message": f"Cache warmed with {cached_count} popular queries",
            "categories": popular_categories,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache hydration failed: {str(e)}",
        )
    finally:
        await db.close()
