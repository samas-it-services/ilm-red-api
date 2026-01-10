"""Redis client for caching.

Provides async Redis client with connection pooling and graceful shutdown.
"""

from typing import Any

import redis.asyncio as redis
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class RedisCache:
    """Async Redis client singleton with connection management."""

    _client: redis.Redis | None = None
    _pool: redis.ConnectionPool | None = None

    @classmethod
    async def get_client(cls) -> redis.Redis:
        """Get or create Redis client.

        Uses connection pooling for efficient connection reuse.
        Lazy initialization - only connects when first used.

        Returns:
            Async Redis client
        """
        if cls._client is None:
            try:
                cls._pool = redis.ConnectionPool.from_url(
                    str(settings.redis_url),
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=10,
                )
                cls._client = redis.Redis(connection_pool=cls._pool)

                # Test connection
                await cls._client.ping()
                logger.info(
                    "redis_connected",
                    url=str(settings.redis_url).replace(
                        settings.redis_url.password or "", "***"
                    ) if settings.redis_url.password else str(settings.redis_url),
                )
            except Exception as e:
                logger.error("redis_connection_failed", error=str(e))
                # Return None client that will be handled gracefully
                cls._client = None
                raise

        return cls._client

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection and cleanup."""
        if cls._client:
            await cls._client.close()
            cls._client = None
            logger.info("redis_disconnected")

        if cls._pool:
            await cls._pool.disconnect()
            cls._pool = None

    @classmethod
    def is_connected(cls) -> bool:
        """Check if Redis client is connected."""
        return cls._client is not None


async def get_redis_client() -> redis.Redis | None:
    """Dependency to get Redis client.

    Returns None if Redis is not available, allowing graceful degradation.

    Returns:
        Redis client or None if unavailable
    """
    try:
        return await RedisCache.get_client()
    except Exception:
        return None


class CacheService:
    """High-level caching service with common operations."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def get(self, key: str) -> str | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.warning("cache_get_error", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: int = 300,
    ) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default 5 minutes)

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.redis.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.warning("cache_set_error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.warning("cache_delete_error", key=key, error=str(e))
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "books:*")

        Returns:
            Number of keys deleted
        """
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.warning("cache_delete_pattern_error", pattern=pattern, error=str(e))
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.warning("cache_exists_error", key=key, error=str(e))
            return False

    async def get_many(self, keys: list[str]) -> dict[str, str | None]:
        """Get multiple values from cache.

        Args:
            keys: List of cache keys

        Returns:
            Dict mapping keys to values (None for missing)
        """
        try:
            values = await self.redis.mget(keys)
            return dict(zip(keys, values, strict=False))
        except Exception as e:
            logger.warning("cache_get_many_error", keys=keys, error=str(e))
            return {k: None for k in keys}

    async def set_many(
        self,
        mapping: dict[str, str],
        ttl: int = 300,
    ) -> bool:
        """Set multiple values in cache.

        Args:
            mapping: Dict of key-value pairs
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        try:
            pipe = self.redis.pipeline()
            for key, value in mapping.items():
                pipe.setex(key, ttl, value)
            await pipe.execute()
            return True
        except Exception as e:
            logger.warning("cache_set_many_error", error=str(e))
            return False

    async def increment(self, key: str, amount: int = 1) -> int | None:
        """Increment a counter in cache.

        Args:
            key: Cache key
            amount: Amount to increment

        Returns:
            New value or None on error
        """
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.warning("cache_increment_error", key=key, error=str(e))
            return None

    async def get_stats(self) -> dict[str, Any]:
        """Get Redis server statistics.

        Returns:
            Dict with cache statistics
        """
        try:
            info = await self.redis.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "used_memory_peak": info.get("used_memory_peak_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_connections_received": info.get("total_connections_received", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0),
                ),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            }
        except Exception as e:
            logger.warning("cache_stats_error", error=str(e))
            return {"connected": False, "error": str(e)}

    @staticmethod
    def _calculate_hit_rate(hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage."""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)
