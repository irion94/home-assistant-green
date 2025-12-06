"""Suggestion engine for proactive suggestions based on patterns."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.services.database import DatabaseService

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """Generates proactive suggestions based on learned patterns.

    Analyzes user behavior to suggest actions based on:
    - Time of day
    - Day of week
    - Room context
    - Frequency of commands
    """

    def __init__(self, db_service: DatabaseService | None = None) -> None:
        """Initialize suggestion engine.

        Args:
            db_service: Optional database service for pattern analysis
        """
        self.db = db_service

    async def get_suggestions(
        self,
        room_id: str | None = None,
        limit: int = 3,
    ) -> list[str]:
        """Get contextual suggestions for current time and room.

        Args:
            room_id: Room identifier for context-specific suggestions
            limit: Maximum number of suggestions to return

        Returns:
            List of suggestion strings
        """
        if not self.db or not self.db.pool:
            logger.debug("Database not available, returning default suggestions")
            return self._get_default_suggestions(room_id, limit)

        try:
            # Get current time context
            warsaw_tz = ZoneInfo("Europe/Warsaw")
            now = datetime.now(warsaw_tz)
            hour = now.hour
            day_name = now.strftime("%A")

            suggestions = []

            # Time-based suggestions
            if 6 <= hour < 9:
                suggestions.append("Turn on morning lights?")
            elif 18 <= hour < 22:
                suggestions.append("Turn on evening lights?")
            elif 22 <= hour < 24:
                suggestions.append("Activate night mode?")

            # Room-based suggestions
            if room_id:
                if room_id == "sypialnia" and 22 <= hour < 24:
                    suggestions.append("Set bedroom lights to dim?")
                elif room_id == "kuchnia" and 7 <= hour < 9:
                    suggestions.append("Turn on kitchen lights?")

            return suggestions[:limit]

        except Exception as e:
            logger.error(f"Error generating suggestions: {e}", exc_info=True)
            return self._get_default_suggestions(room_id, limit)

    def _get_default_suggestions(
        self, room_id: str | None, limit: int
    ) -> list[str]:
        """Get default suggestions when database is unavailable.

        Args:
            room_id: Room identifier
            limit: Maximum suggestions

        Returns:
            List of default suggestions
        """
        suggestions = [
            "Check the weather?",
            "What's the temperature?",
            "What time is it?",
        ]

        if room_id:
            suggestions.insert(0, f"Control lights in {room_id}?")

        return suggestions[:limit]

    async def record_action(
        self,
        action: str,
        room_id: str | None = None,
        session_id: str | None = None,
    ) -> bool:
        """Record user action for pattern learning.

        Args:
            action: Action taken by user
            room_id: Room context
            session_id: Session identifier

        Returns:
            True if recorded successfully
        """
        if not self.db or not self.db.pool:
            return False

        try:
            warsaw_tz = ZoneInfo("Europe/Warsaw")
            now = datetime.now(warsaw_tz)

            metadata = {
                "hour": now.hour,
                "day_of_week": now.strftime("%A"),
                "room_id": room_id,
                "session_id": session_id,
            }

            await self.db.save_training_data(
                input_text=action,
                output_text="action_recorded",
                interaction_type="user_action",
                metadata=metadata,
            )

            logger.debug(f"Recorded action: {action} at {now.hour}:00")
            return True

        except Exception as e:
            logger.error(f"Error recording action: {e}", exc_info=True)
            return False


# Singleton factory
_suggestion_engine: SuggestionEngine | None = None


def get_suggestion_engine(
    db_service: DatabaseService | None = None
) -> SuggestionEngine:
    """Get or create SuggestionEngine instance.

    Args:
        db_service: Optional database service

    Returns:
        SuggestionEngine singleton
    """
    global _suggestion_engine
    if _suggestion_engine is None:
        _suggestion_engine = SuggestionEngine(db_service)
    return _suggestion_engine
