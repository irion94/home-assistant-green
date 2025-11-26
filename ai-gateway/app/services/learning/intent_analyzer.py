"""Intent analyzer for smart overlay behavior."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """Analyzes AI responses to determine overlay behavior.

    Detects questions, confirmations, and other patterns to decide
    whether voice overlay should stay open or close.
    """

    # Question patterns (keep overlay open)
    QUESTION_PATTERNS = [
        r"\?$",  # Ends with question mark
        r"^(what|which|how|when|where|why|who|whose|whom)",  # Question words (EN)
        r"(would you like|do you want|should I|shall I|can I)",  # Confirmation requests (EN)
        r"^(co|który|jak|kiedy|gdzie|dlaczego|kto|czyj)",  # Question words (PL)
        r"(czy chcesz|czy chciałbyś|czy mam|powinienem)",  # Confirmation requests (PL)
        r"(tell me|let me know|wybierz|wybierasz)",  # Requests for information
    ]

    # Confirmation patterns (can close overlay)
    CONFIRMATION_PATTERNS = [
        r"^(ok|done|completed|finished|ready|gotowe|zrobione)",
        r"(turned on|turned off|włączone|wyłączone|włączyłem|wyłączyłem)",
        r"(wszystko gotowe|to wszystko|nic więcej)",
        r"^(świetnie|dobrze|ok|okej|super)",
    ]

    # Error patterns (keep overlay open)
    ERROR_PATTERNS = [
        r"(error|failed|nie udało się|błąd|problem|issue)",
        r"(sorry|przepraszam|przykro mi|unfortunately)",
        r"(couldn't|nie mogłem|nie mogę|unable)",
    ]

    def should_keep_overlay_open(self, assistant_response: str) -> bool:
        """Determine if overlay should stay open based on response.

        Args:
            assistant_response: AI assistant's response text

        Returns:
            True if overlay should stay open, False if it can close
        """
        response_lower = assistant_response.lower().strip()

        # Empty responses should close
        if not response_lower:
            return False

        # Check for errors (keep open)
        for pattern in self.ERROR_PATTERNS:
            if re.search(pattern, response_lower, re.IGNORECASE):
                logger.debug(f"Error pattern matched: {pattern}")
                return True

        # Check for questions (keep open)
        for pattern in self.QUESTION_PATTERNS:
            if re.search(pattern, response_lower, re.IGNORECASE):
                logger.debug(f"Question pattern matched: {pattern}")
                return True

        # Check for confirmations (can close)
        for pattern in self.CONFIRMATION_PATTERNS:
            if re.search(pattern, response_lower, re.IGNORECASE):
                logger.debug(f"Confirmation pattern matched: {pattern}")
                return False

        # Default: keep open if uncertain
        logger.debug("No clear pattern matched, defaulting to keep open")
        return True

    def get_intent_type(self, assistant_response: str) -> str:
        """Classify response intent type.

        Args:
            assistant_response: AI assistant's response text

        Returns:
            Intent type: 'question', 'confirmation', 'error', or 'unknown'
        """
        response_lower = assistant_response.lower().strip()

        # Check error first
        for pattern in self.ERROR_PATTERNS:
            if re.search(pattern, response_lower, re.IGNORECASE):
                return "error"

        # Check question
        for pattern in self.QUESTION_PATTERNS:
            if re.search(pattern, response_lower, re.IGNORECASE):
                return "question"

        # Check confirmation
        for pattern in self.CONFIRMATION_PATTERNS:
            if re.search(pattern, response_lower, re.IGNORECASE):
                return "confirmation"

        return "unknown"


# Singleton instance
_intent_analyzer: IntentAnalyzer | None = None


def get_intent_analyzer() -> IntentAnalyzer:
    """Get or create IntentAnalyzer instance.

    Returns:
        IntentAnalyzer singleton
    """
    global _intent_analyzer
    if _intent_analyzer is None:
        _intent_analyzer = IntentAnalyzer()
    return _intent_analyzer
