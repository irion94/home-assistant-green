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

# Conversation mode triggers
CONVERSATION_START_KEYWORDS = [
    "let's talk", "lets talk", "talk to me", "let's chat", "lets chat",
    "pogadajmy", "porozmawiajmy", "porozmawiaj ze mną", "pogadaj ze mną",
    "chcę porozmawiać", "chce porozmawiać",
]

CONVERSATION_END_KEYWORDS = [
    "stop", "enough", "that's all", "thats all", "bye", "goodbye", "end conversation",
    "koniec", "wystarczy", "to wszystko", "koniec rozmowy", "pa pa", "do widzenia",
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
        action, _ = self.match_with_confidence(text)
        return action

    def match_with_confidence(self, text: str) -> tuple[HAAction | None, float]:
        """Match text to a home control action with confidence score.

        Args:
            text: Transcribed command text

        Returns:
            Tuple of (HAAction or None, confidence 0.0-1.0)
        """
        from app.models import HAAction

        text_lower = text.lower().strip()
        confidence = 0.0

        # Check for conversation mode triggers first
        conversation_action, conv_confidence = self._detect_conversation_with_confidence(text_lower)
        if conversation_action:
            logger.info(f"Conversation intent matched: {conversation_action} (confidence={conv_confidence:.2f}, text: {text})")
            return (
                HAAction(
                    action=conversation_action,
                    service=None,
                    entity_id=None,
                    data={},
                ),
                conv_confidence,
            )

        # Check for turn on/off commands
        action_type, action_confidence = self._detect_action_with_confidence(text_lower)
        if action_type:
            entity, entity_confidence = self._extract_entity_with_confidence(text_lower)
            if entity:
                service = f"light.turn_{action_type}"
                # Combined confidence = action * entity
                confidence = action_confidence * entity_confidence
                logger.info(f"Intent matched: {service} -> {entity} (confidence={confidence:.2f}, text: {text})")
                return (
                    HAAction(
                        action="call_service",
                        service=service,
                        entity_id=entity,
                        data={},
                    ),
                    confidence,
                )

        # Check for media stop commands
        if any(word in text_lower for word in ["stop media", "zatrzymaj", "stop player", "media stop"]):
            logger.info(f"Media stop intent matched (confidence=1.0)")
            return (
                HAAction(
                    action="call_service",
                    service="media_player.media_stop",
                    entity_id="media_player.living_room_display",
                    data={},
                ),
                1.0,  # Exact match = full confidence
            )

        # Check for TTS commands
        tts_message = self._extract_tts_message(text_lower)
        if tts_message:
            logger.info(f"TTS intent matched: {tts_message} (confidence=0.9)")
            return (
                HAAction(
                    action="call_service",
                    service="tts.speak",
                    entity_id="tts.google_translate_en_com",
                    data={
                        "media_player_entity_id": "media_player.living_room_display",
                        "message": tts_message,
                    },
                ),
                0.9,  # Regex match = high confidence
            )

        logger.debug(f"No intent match for: {text}")
        return (None, 0.0)

    def _detect_conversation(self, text: str) -> str | None:
        """Detect if text contains conversation start/end trigger.

        Returns:
            'conversation_start' or 'conversation_end' or None
        """
        result, _ = self._detect_conversation_with_confidence(text)
        return result

    def _detect_conversation_with_confidence(self, text: str) -> tuple[str | None, float]:
        """Detect conversation trigger with confidence score.

        Returns:
            Tuple of (action or None, confidence 0.0-1.0)
        """
        # Check conversation start keywords (exact match = 1.0)
        for keyword in CONVERSATION_START_KEYWORDS:
            if keyword in text:
                return ("conversation_start", 1.0)

        # Check conversation end keywords (exact match = 1.0)
        for keyword in CONVERSATION_END_KEYWORDS:
            if keyword in text:
                return ("conversation_end", 1.0)

        # Fuzzy match for conversation start
        best_start = process.extractOne(
            text, CONVERSATION_START_KEYWORDS, scorer=fuzz.partial_ratio
        )
        if best_start and best_start[1] >= 85:
            return ("conversation_start", best_start[1] / 100.0)

        # Fuzzy match for conversation end
        best_end = process.extractOne(
            text, CONVERSATION_END_KEYWORDS, scorer=fuzz.partial_ratio
        )
        if best_end and best_end[1] >= 85:
            return ("conversation_end", best_end[1] / 100.0)

        return (None, 0.0)

    def _detect_action(self, text: str) -> str | None:
        """Detect if text contains turn on/off action.

        Returns:
            'on' or 'off' or None
        """
        result, _ = self._detect_action_with_confidence(text)
        return result

    def _detect_action_with_confidence(self, text: str) -> tuple[str | None, float]:
        """Detect turn on/off action with confidence score.

        Returns:
            Tuple of ('on'/'off' or None, confidence 0.0-1.0)
        """
        # Check turn on keywords (exact match = 1.0)
        for keyword in TURN_ON_KEYWORDS:
            if keyword in text:
                return ("on", 1.0)

        # Check turn off keywords (exact match = 1.0)
        for keyword in TURN_OFF_KEYWORDS:
            if keyword in text:
                return ("off", 1.0)

        # Fuzzy match for turn on
        best_on = process.extractOne(
            text, TURN_ON_KEYWORDS, scorer=fuzz.partial_ratio
        )
        if best_on and best_on[1] >= 80:
            return ("on", best_on[1] / 100.0)

        # Fuzzy match for turn off
        best_off = process.extractOne(
            text, TURN_OFF_KEYWORDS, scorer=fuzz.partial_ratio
        )
        if best_off and best_off[1] >= 80:
            return ("off", best_off[1] / 100.0)

        return (None, 0.0)

    def _extract_entity(self, text: str) -> str | None:
        """Extract entity ID from text.

        Returns:
            Entity ID or None
        """
        result, _ = self._extract_entity_with_confidence(text)
        return result

    def _extract_entity_with_confidence(self, text: str) -> tuple[str | None, float]:
        """Extract entity ID from text with confidence score.

        Returns:
            Tuple of (entity_id or None, confidence 0.0-1.0)
        """
        # Check specific room names first (exact match = 1.0)
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
                return (entity_id, 1.0)

        # Fuzzy match room names
        best_match = process.extractOne(
            text, self.room_names, scorer=fuzz.partial_ratio
        )
        if best_match and best_match[1] >= self.threshold:
            return (ROOM_ENTITIES[best_match[0]], best_match[1] / 100.0)

        # Default to living room for generic "lights" commands (lower confidence)
        if any(word in text for word in ["światło", "światła", "light", "lights"]):
            return (ROOM_ENTITIES["salon"], 0.7)  # Default = lower confidence

        return (None, 0.0)

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
