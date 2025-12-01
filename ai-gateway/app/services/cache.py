"""Redis caching service for performance optimization (Phase 7)."""

import json
import logging
from typing import Optional, Any, Callable
import os

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service with graceful degradation."""

    def __init__(self, redis_url: str = "redis://redis:6379", enabled: bool = True):
        """
        Initialize cache service.

        Args:
            redis_url: Redis connection URL
            enabled: Whether caching is enabled (feature flag)
        """
        self.enabled = enabled and os.getenv("REDIS_ENABLED", "false").lower() == "true"
        self.client = None

        if not self.enabled:
            logger.info("Redis caching DISABLED (feature flag REDIS_ENABLED=false)")
            return

        try:
            import redis
            self.client = redis.from_url(redis_url, decode_responses=True)
            self._test_connection()
        except ImportError:
            logger.warning("Redis library not installed, caching disabled")
            self.enabled = False
        except Exception as e:
            logger.error(f"Redis initialization failed: {e}, caching disabled")
            self.enabled = False

    def _test_connection(self):
        """Test Redis connection."""
        try:
            if self.client:
                self.client.ping()
                logger.info("Redis connection successful")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.enabled = False
            raise

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/disabled
        """
        if not self.enabled or not self.client:
            return None

        try:
            data = self.client.get(key)
            if data:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(data)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error for key '{key}': {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300):
        """
        Set value in cache with TTL (seconds).

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (default: 5 minutes)
        """
        if not self.enabled or not self.client:
            return

        try:
            self.client.setex(key, ttl, json.dumps(value))
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Cache set error for key '{key}': {e}")

    def delete(self, key: str):
        """
        Delete key from cache.

        Args:
            key: Cache key to delete
        """
        if not self.enabled or not self.client:
            return

        try:
            self.client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
        except Exception as e:
            logger.error(f"Cache delete error for key '{key}': {e}")

    def invalidate_pattern(self, pattern: str):
        """
        Invalidate all keys matching pattern.

        Args:
            pattern: Redis key pattern (e.g., "context:*")
        """
        if not self.enabled or not self.client:
            return

        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
                logger.info(f"Cache invalidated: {pattern} ({len(keys)} keys)")
        except Exception as e:
            logger.error(f"Cache invalidate error for pattern '{pattern}': {e}")

    def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable[[], Any],
        ttl: int = 300
    ) -> Any:
        """
        Get from cache or fetch and cache if not found.

        Args:
            key: Cache key
            fetch_fn: Function to call if cache miss
            ttl: Time-to-live in seconds

        Returns:
            Cached or freshly fetched value
        """
        # Try cache first
        cached = self.get(key)
        if cached is not None:
            return cached

        # Fetch fresh data
        value = fetch_fn()
        if value is not None:
            self.set(key, value, ttl)

        return value

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats or empty if disabled
        """
        if not self.enabled or not self.client:
            return {"enabled": False}

        try:
            info = self.client.info("stats")
            return {
                "enabled": True,
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"enabled": True, "error": str(e)}

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage."""
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100


# Singleton instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """
    Get global cache service instance.

    Returns:
        CacheService singleton instance
    """
    global _cache_service
    if _cache_service is None:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        redis_enabled = os.getenv("REDIS_ENABLED", "false").lower() == "true"
        _cache_service = CacheService(redis_url=redis_url, enabled=redis_enabled)
    return _cache_service
