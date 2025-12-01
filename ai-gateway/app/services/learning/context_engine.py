"""Context engine for managing conversation history and preferences."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.services.database import DatabaseService
from app.services.cache import CacheService, get_cache_service

logger = logging.getLogger(__name__)


class ContextEngine:
    """Manages conversation context and user preferences.

    Provides:
    - Recent conversation history
    - User preferences by category
    - Room-specific context
    - Pattern learning integration
    - Redis caching for performance (Phase 7)
    """

    def __init__(
        self,
        db_service: DatabaseService,
        cache_service: Optional[CacheService] = None
    ) -> None:
        """Initialize context engine.

        Args:
            db_service: Database service for persistence
            cache_service: Optional cache service (defaults to singleton)
        """
        self.db = db_service
        self.cache = cache_service or get_cache_service()

    async def get_context(
        self,
        session_id: str,
        room_id: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Build context from conversation history and preferences.

        Phase 7: Uses Redis caching to reduce DB query latency from 200ms to <10ms.

        Args:
            session_id: Session ID for history lookup
            room_id: Optional room ID for room-specific context
            limit: Maximum number of recent messages to include

        Returns:
            Context dict with history, preferences, room context
        """
        # Phase 7: Try cache first
        cache_key = f"context:{session_id}:{room_id or 'default'}:{limit}"
        cached_context = self.cache.get(cache_key)
        if cached_context:
            logger.debug(f"Context cache HIT for session {session_id}")
            return cached_context

        # Cache miss - fetch from database
        context: dict[str, Any] = {
            "conversation_history": [],
            "preferences": {},
            "room_context": {},
            "metadata": {"session_id": session_id},
        }

        if not self.db or not self.db.pool:
            logger.warning("Database not available for context retrieval")
            return context

        try:
            # 1. Recent conversation history
            history = await self.db.get_conversation_history(
                session_id=session_id, limit=limit
            )
            context["conversation_history"] = history

            # 2. User preferences
            try:
                prefs = await self.db.get_preferences_by_category("user")
                context["preferences"] = prefs
            except Exception as e:
                logger.warning(f"Failed to load preferences: {e}")

            # 3. Room context (if available)
            if room_id:
                context["room_context"] = {
                    "room_id": room_id,
                    "metadata": {},
                }

            logger.info(
                f"Built context for session {session_id}: "
                f"{len(history)} messages, {len(prefs)} preferences"
            )

            # Phase 7: Cache the context (5 minute TTL)
            import os
            ttl = int(os.getenv("REDIS_CACHE_TTL", "300"))
            self.cache.set(cache_key, context, ttl=ttl)

            return context

        except Exception as e:
            logger.error(f"Error building context: {e}", exc_info=True)
            return context

    async def learn_pattern(
        self,
        user_input: str,
        intent: str,
        session_id: str,
        language: str | None = None,
    ) -> bool:
        """Learn command pattern from user interaction.

        Stores successful command patterns for future reference.
        Phase 7: Invalidates related caches after learning.

        Args:
            user_input: User's original input
            intent: Extracted intent or action taken
            session_id: Session identifier
            language: Detected language (pl/en)

        Returns:
            True if pattern was saved successfully
        """
        if not self.db or not self.db.pool:
            logger.warning("Database not available for pattern learning")
            return False

        try:
            await self.db.save_training_data(
                input_text=user_input,
                output_text=intent,
                interaction_type="command_pattern",
                language=language,
                metadata={"session_id": session_id},
            )
            logger.info(f"Learned pattern: {user_input[:50]} → {intent[:50]}")

            # Phase 7: Invalidate related caches since context changed
            self.cache.invalidate_pattern(f"context:{session_id}:*")

            return True

        except Exception as e:
            logger.error(f"Error saving pattern: {e}", exc_info=True)
            return False

    async def get_recent_patterns(
        self, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get recently learned command patterns.

        Args:
            limit: Maximum number of patterns to return

        Returns:
            List of pattern dicts
        """
        if not self.db or not self.db.pool:
            return []

        try:
            stats = await self.db.get_training_stats()
            logger.info(f"Training stats: {stats}")
            return []  # Could be extended to return actual patterns

        except Exception as e:
            logger.error(f"Error retrieving patterns: {e}", exc_info=True)
            return []


# Singleton factory
_context_engine: ContextEngine | None = None


def get_context_engine(db_service: DatabaseService) -> ContextEngine:
    """Get or create ContextEngine instance.

    Args:
        db_service: Database service

    Returns:
        ContextEngine singleton
    """
    global _context_engine
    if _context_engine is None:
        _context_engine = ContextEngine(db_service)
    return _context_engine
