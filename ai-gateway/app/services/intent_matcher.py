"""Fast intent matching using RapidFuzz for common home control commands.

This module provides sub-millisecond intent recognition for common commands,
falling back to LLM for complex or unrecognized inputs.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from rapidfuzz import fuzz, process

if TYPE_CHECKING:
    from app.models import HAAction

logger = logging.getLogger(__name__)

# Entity mappings for rooms/devices
ROOM_ENTITIES = {
    # Living room / Salon
    "salon": "light.yeelight_color_0x80156a9",
    "salonie": "light.yeelight_color_0x80156a9",
    "living room": "light.yeelight_color_0x80156a9",
    "światło": "light.yeelight_color_0x80156a9",
    "światła": "light.yeelight_color_0x80156a9",
    "lights": "light.yeelight_color_0x80156a9",
    # Kitchen / Kuchnia
    "kuchnia": "light.yeelight_color_0x49c27e1",
    "kuchni": "light.yeelight_color_0x49c27e1",
    "kitchen": "light.yeelight_color_0x49c27e1",
    # Bedroom / Sypialnia
    "sypialnia": "light.yeelight_color_0x80147dd",
    "sypialni": "light.yeelight_color_0x80147dd",
    "bedroom": "light.yeelight_color_0x80147dd",
    # Lamps
    "lampa 1": "light.yeelight_color_0x801498b",
    "lampę 1": "light.yeelight_color_0x801498b",
    "lamp 1": "light.yeelight_color_0x801498b",
    "lampa 2": "light.yeelight_color_0x8015154",
    "lampę 2": "light.yeelight_color_0x8015154",
    "lamp 2": "light.yeelight_color_0x8015154",
    # Desk lamp
    "lampka": "light.yeelight_lamp15_0x1b37d19d",
    "lampkę": "light.yeelight_lamp15_0x1b37d19d",
    "desk lamp": "light.yeelight_lamp15_0x1b37d19d",
    "lampa 15": "light.yeelight_lamp15_0x1b37d19d",
    # Ambilight
    "ambilight": "light.yeelight_lamp15_0x1b37d19d_ambilight",
    "ambient": "light.yeelight_lamp15_0x1b37d19d_ambilight",
}

# Action keywords
TURN_ON_KEYWORDS = [
    "zapal", "włącz", "włacz", "wlacz", "zaświeć", "włącz się",
    "turn on", "switch on", "light up",
    # Common misrecognitions
    "zapadł", "zaball", "zaopal", "za pal", "za pan",
]

TURN_OFF_KEYWORDS = [
    "zgaś", "wyłącz", "wylacz", "gaś", "wyłącz się",
    "turn off", "switch off",
    # Common misrecognitions
    "zgaść", "sgas", "z gaś",
]


class IntentMatcher:
    """Fast pattern-based intent matcher using fuzzy string matching."""

    def __init__(self, threshold: int = 65):
        """Initialize intent matcher.

        Args:
            threshold: Minimum fuzzy match score (0-100) to accept a match
        """
        self.threshold = threshold
        self.room_names = list(ROOM_ENTITIES.keys())
        logger.info(f"IntentMatcher initialized with threshold={threshold}")

    def match(self, text: str) -> HAAction | None:
        """Match text to a home control action.

        Args:
            text: Transcribed command text

        Returns:
            HAAction if matched, None otherwise
        """
        from app.models import HAAction

        text_lower = text.lower().strip()

        # Check for turn on/off commands
        action_type = self._detect_action(text_lower)
        if action_type:
            entity = self._extract_entity(text_lower)
            if entity:
                service = f"light.turn_{action_type}"
                logger.info(f"Intent matched: {service} -> {entity} (text: {text})")
                return HAAction(
                    action="call_service",
                    service=service,
                    entity_id=entity,
                    data={},
                )

        # Check for TTS commands
        tts_message = self._extract_tts_message(text_lower)
        if tts_message:
            logger.info(f"TTS intent matched: {tts_message}")
            return HAAction(
                action="call_service",
                service="tts.speak",
                entity_id="tts.google_translate_en_com",
                data={
                    "media_player_entity_id": "media_player.living_room_display",
                    "message": tts_message,
                },
            )

        logger.debug(f"No intent match for: {text}")
        return None

    def _detect_action(self, text: str) -> str | None:
        """Detect if text contains turn on/off action.

        Returns:
            'on' or 'off' or None
        """
        # Check turn on keywords
        for keyword in TURN_ON_KEYWORDS:
            if keyword in text:
                return "on"

        # Check turn off keywords
        for keyword in TURN_OFF_KEYWORDS:
            if keyword in text:
                return "off"

        # Fuzzy match for turn on
        best_on = process.extractOne(
            text, TURN_ON_KEYWORDS, scorer=fuzz.partial_ratio
        )
        if best_on and best_on[1] >= 80:
            return "on"

        # Fuzzy match for turn off
        best_off = process.extractOne(
            text, TURN_OFF_KEYWORDS, scorer=fuzz.partial_ratio
        )
        if best_off and best_off[1] >= 80:
            return "off"

        return None

    def _extract_entity(self, text: str) -> str | None:
        """Extract entity ID from text.

        Returns:
            Entity ID or None
        """
        # Check specific room names first (before generic "światło")
        # Order matters - check specific rooms before defaulting
        specific_rooms = [
            # Polish locative forms (most specific)
            ("sypialni", "light.yeelight_color_0x80147dd"),
            ("kuchni", "light.yeelight_color_0x49c27e1"),
            ("salonie", "light.yeelight_color_0x80156a9"),
            # Polish nominative
            ("sypialnia", "light.yeelight_color_0x80147dd"),
            ("kuchnia", "light.yeelight_color_0x49c27e1"),
            ("salon", "light.yeelight_color_0x80156a9"),
            # English
            ("bedroom", "light.yeelight_color_0x80147dd"),
            ("kitchen", "light.yeelight_color_0x49c27e1"),
            ("living room", "light.yeelight_color_0x80156a9"),
            # Lamps
            ("lampka", "light.yeelight_lamp15_0x1b37d19d"),
            ("lampkę", "light.yeelight_lamp15_0x1b37d19d"),
            ("lamp 1", "light.yeelight_color_0x801498b"),
            ("lampa 1", "light.yeelight_color_0x801498b"),
            ("lamp 2", "light.yeelight_color_0x8015154"),
            ("lampa 2", "light.yeelight_color_0x8015154"),
            ("ambilight", "light.yeelight_lamp15_0x1b37d19d_ambilight"),
        ]

        for room_name, entity_id in specific_rooms:
            if room_name in text:
                return entity_id

        # Fuzzy match room names
        best_match = process.extractOne(
            text, self.room_names, scorer=fuzz.partial_ratio
        )
        if best_match and best_match[1] >= self.threshold:
            return ROOM_ENTITIES[best_match[0]]

        # Default to living room for generic "lights" commands
        if any(word in text for word in ["światło", "światła", "light", "lights"]):
            return ROOM_ENTITIES["salon"]

        return None

    def _extract_tts_message(self, text: str) -> str | None:
        """Extract TTS message from text.

        Returns:
            Message to speak or None
        """
        # Polish patterns
        polish_patterns = [
            r"powiedz[:\s]+(.+)",
            r"mów[:\s]+(.+)",
            r"powiedz że (.+)",
        ]

        # English patterns
        english_patterns = [
            r"say[:\s]+(.+)",
            r"speak[:\s]+(.+)",
            r"tell me (.+)",
        ]

        for pattern in polish_patterns + english_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                message = match.group(1).strip()
                # Clean up the message
                message = message.rstrip(".")
                if len(message) > 2:  # Minimum message length
                    return message

        return None


# Global instance
_intent_matcher: IntentMatcher | None = None


def get_intent_matcher() -> IntentMatcher:
    """Get or create global IntentMatcher instance.

    Returns:
        IntentMatcher instance
    """
    global _intent_matcher
    if _intent_matcher is None:
        _intent_matcher = IntentMatcher(threshold=65)
    return _intent_matcher
