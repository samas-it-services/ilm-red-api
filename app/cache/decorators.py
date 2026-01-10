"""Caching decorators for automatic function result caching.

Provides decorators that automatically cache function results in Redis.
Supports TTL, key prefixes, and automatic cache key generation.
"""

import hashlib
import json
from functools import wraps
from typing import Any, Callable, TypeVar

import structlog

from app.cache.redis_client import RedisCache

logger = structlog.get_logger(__name__)

T = TypeVar("T")


def cache_key(*args, prefix: str = "", **kwargs) -> str:
    """Generate a cache key from function arguments.

    Creates a deterministic hash of the arguments to use as cache key.

    Args:
        *args: Positional arguments
        prefix: Optional key prefix
        **kwargs: Keyword arguments

    Returns:
        Cache key string
    """
    # Serialize arguments to JSON for hashing
    key_data = json.dumps(
        {"args": [str(a) for a in args], "kwargs": {k: str(v) for k, v in sorted(kwargs.items())}},
        sort_keys=True,
    )

    # Create MD5 hash of the arguments
    key_hash = hashlib.md5(key_data.encode()).hexdigest()

    if prefix:
        return f"{prefix}:{key_hash}"
    return key_hash


def cached(
    ttl: int = 300,
    prefix: str = "",
    key_builder: Callable[..., str] | None = None,
    skip_cache_if: Callable[..., bool] | None = None,
):
    """Decorator to cache function results in Redis.

    Automatically caches the return value of async functions.
    Cache keys are generated from function name and arguments.

    Args:
        ttl: Time-to-live in seconds (default 5 minutes)
        prefix: Key prefix for namespacing
        key_builder: Optional custom function to build cache key
        skip_cache_if: Optional function that returns True to skip caching

    Returns:
        Decorated function

    Example:
        @cached(ttl=600, prefix="books")
        async def get_book(book_id: str) -> dict:
            ...

        # Custom key builder
        @cached(
            ttl=300,
            key_builder=lambda user_id, **kw: f"user:{user_id}:profile"
        )
        async def get_user_profile(user_id: str) -> dict:
            ...

        # Skip caching for certain conditions
        @cached(
            ttl=300,
            skip_cache_if=lambda user=None: user and user.is_admin
        )
        async def get_dashboard(user: User | None = None) -> dict:
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Check if we should skip caching
            if skip_cache_if and skip_cache_if(*args, **kwargs):
                return await func(*args, **kwargs)

            # Try to get Redis client
            try:
                redis_client = await RedisCache.get_client()
            except Exception:
                # Redis unavailable, execute function directly
                logger.debug("cache_skip_no_redis", func=func.__name__)
                return await func(*args, **kwargs)

            # Build cache key
            if key_builder:
                cache_key_str = key_builder(*args, **kwargs)
            else:
                # Default key: prefix:func_name:hash(args)
                func_prefix = f"{prefix}:{func.__name__}" if prefix else func.__name__
                cache_key_str = cache_key(*args, prefix=func_prefix, **kwargs)

            # Try to get from cache
            try:
                cached_value = await redis_client.get(cache_key_str)
                if cached_value is not None:
                    logger.debug("cache_hit", key=cache_key_str, func=func.__name__)
                    return json.loads(cached_value)
            except json.JSONDecodeError:
                # Invalid cached value, will refresh
                logger.warning("cache_invalid_json", key=cache_key_str)
            except Exception as e:
                logger.warning("cache_get_error", key=cache_key_str, error=str(e))

            # Execute function
            logger.debug("cache_miss", key=cache_key_str, func=func.__name__)
            result = await func(*args, **kwargs)

            # Cache the result
            try:
                serialized = json.dumps(result, default=str)
                await redis_client.setex(cache_key_str, ttl, serialized)
                logger.debug("cache_set", key=cache_key_str, ttl=ttl)
            except Exception as e:
                logger.warning("cache_set_error", key=cache_key_str, error=str(e))

            return result

        # Attach helper to invalidate cache
        async def invalidate(*args, **kwargs) -> bool:
            """Invalidate the cached value for given arguments."""
            try:
                redis_client = await RedisCache.get_client()
                if key_builder:
                    cache_key_str = key_builder(*args, **kwargs)
                else:
                    func_prefix = f"{prefix}:{func.__name__}" if prefix else func.__name__
                    cache_key_str = cache_key(*args, prefix=func_prefix, **kwargs)

                result = await redis_client.delete(cache_key_str)
                logger.debug("cache_invalidated", key=cache_key_str)
                return result > 0
            except Exception as e:
                logger.warning("cache_invalidate_error", error=str(e))
                return False

        wrapper.invalidate = invalidate  # type: ignore
        wrapper.cache_prefix = prefix  # type: ignore

        return wrapper

    return decorator


def cached_property(ttl: int = 300, prefix: str = ""):
    """Decorator for caching property-like methods on objects.

    Caches based on object ID and method name.

    Args:
        ttl: Time-to-live in seconds
        prefix: Key prefix

    Example:
        class BookService:
            @cached_property(ttl=600, prefix="book")
            async def get_popular_books(self) -> list[dict]:
                ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(self, *args, **kwargs) -> T:
            # Get object identifier if available
            obj_id = getattr(self, "id", None) or id(self)

            # Build cache key
            func_prefix = f"{prefix}:{func.__name__}:{obj_id}" if prefix else f"{func.__name__}:{obj_id}"

            # Use the main cached decorator logic
            @cached(ttl=ttl, prefix=func_prefix)
            async def inner(*a, **kw):
                return await func(self, *a, **kw)

            return await inner(*args, **kwargs)

        return wrapper

    return decorator


class CacheInvalidator:
    """Helper class to invalidate related caches.

    Use this when mutations occur to clear related cached data.

    Example:
        invalidator = CacheInvalidator()

        async def update_book(book_id: str, data: dict):
            # Update book in database
            ...

            # Invalidate related caches
            await invalidator.invalidate_patterns([
                f"books:detail:{book_id}",
                "books:list:*",
                f"books:user:{owner_id}:*",
            ])
    """

    async def invalidate_patterns(self, patterns: list[str]) -> int:
        """Invalidate all keys matching any of the patterns.

        Args:
            patterns: List of key patterns with wildcards

        Returns:
            Total number of keys deleted
        """
        try:
            redis_client = await RedisCache.get_client()
            total_deleted = 0

            for pattern in patterns:
                keys = []
                async for key in redis_client.scan_iter(match=pattern):
                    keys.append(key)

                if keys:
                    deleted = await redis_client.delete(*keys)
                    total_deleted += deleted
                    logger.debug(
                        "cache_pattern_invalidated",
                        pattern=pattern,
                        deleted=deleted,
                    )

            return total_deleted
        except Exception as e:
            logger.warning("cache_invalidate_patterns_error", error=str(e))
            return 0

    async def invalidate_keys(self, keys: list[str]) -> int:
        """Invalidate specific keys.

        Args:
            keys: List of exact cache keys

        Returns:
            Number of keys deleted
        """
        try:
            redis_client = await RedisCache.get_client()
            if keys:
                return await redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning("cache_invalidate_keys_error", error=str(e))
            return 0


# Global cache invalidator instance
cache_invalidator = CacheInvalidator()
