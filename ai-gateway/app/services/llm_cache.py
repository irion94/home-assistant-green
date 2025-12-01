"""LLM result caching for repeated commands.

Caches recent LLM translations to speed up repeated commands.
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import HAAction

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cached LLM result."""

    action: HAAction
    confidence: float
    timestamp: float


class LLMCache:
    """LRU cache for LLM translation results.

    Speeds up repeated commands by caching recent results.
    """

    def __init__(self, max_size: int = 100, ttl_seconds: int = 1800):
        """Initialize cache.

        Args:
            max_size: Maximum number of entries to cache
            ttl_seconds: Time-to-live for cache entries (default 30 minutes)
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds

    def _normalize_key(self, text: str) -> str:
        """Normalize text for cache key.

        Args:
            text: Input text

        Returns:
            Normalized lowercase text with extra whitespace removed
        """
        return " ".join(text.lower().split())

    def get(self, text: str) -> tuple[HAAction, float] | None:
        """Get cached result for text.

        Args:
            text: Command text

        Returns:
            Tuple of (HAAction, confidence) if cached and valid, None otherwise
        """
        key = self._normalize_key(text)

        if key not in self._cache:
            logger.info(f"LLM cache miss: {key[:50]}... (cache size={len(self._cache)})")
            return None

        entry = self._cache[key]

        # Check if expired
        if time.time() - entry.timestamp > self._ttl:
            del self._cache[key]
            logger.debug(f"Cache entry expired: {key[:50]}...")
            return None

        # Move to end (LRU)
        self._cache.move_to_end(key)
        logger.info(f"Cache hit: {key[:50]}... (conf={entry.confidence:.2f})")

        return (entry.action, entry.confidence)

    def put(self, text: str, action: HAAction, confidence: float) -> None:
        """Cache a result.

        Args:
            text: Command text
            action: Translated action
            confidence: Confidence score
        """
        key = self._normalize_key(text)

        # Remove if exists (to update timestamp)
        if key in self._cache:
            del self._cache[key]

        # Add new entry
        self._cache[key] = CacheEntry(
            action=action,
            confidence=confidence,
            timestamp=time.time(),
        )

        # Enforce max size (remove oldest)
        while len(self._cache) > self._max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug(f"Cache evicted: {oldest_key[:50]}...")

        logger.info(f"LLM cache stored: {key[:50]}... (conf={confidence:.2f}, total={len(self._cache)})")

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("LLM cache cleared")

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)

    def stats(self) -> dict:
        """Get cache statistics."""
        now = time.time()
        valid_entries = sum(
            1 for e in self._cache.values() if now - e.timestamp <= self._ttl
        )
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "max_size": self._max_size,
            "ttl_seconds": self._ttl,
        }


# Singleton instance
_llm_cache: LLMCache | None = None


def get_llm_cache() -> LLMCache:
    """Get or create singleton LLM cache instance."""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache()
    return _llm_cache
