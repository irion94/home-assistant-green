"""Auto-learning pattern matcher from successful LLM matches.

Learns new patterns from high-confidence LLM translations
to improve pattern matcher over time.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import HAAction

logger = logging.getLogger(__name__)

# Default path for learned patterns
DEFAULT_PATTERNS_FILE = "/app/data/learned_patterns.json"


@dataclass
class LearnedPattern:
    """A pattern learned from LLM match."""

    pattern: str  # Normalized text pattern
    entity_id: str
    service: str
    confidence: float  # Original LLM confidence
    learned_at: float  # Timestamp
    match_count: int = 0  # Times this pattern was used


class PatternLearner:
    """Learns patterns from successful LLM matches.

    When LLM matches a command with high confidence,
    save the pattern for future fast matching.
    """

    def __init__(
        self,
        patterns_file: str = DEFAULT_PATTERNS_FILE,
        min_confidence: float = 0.85,
        max_patterns: int = 500,
    ):
        """Initialize pattern learner.

        Args:
            patterns_file: Path to persist learned patterns
            min_confidence: Minimum confidence to learn from
            max_patterns: Maximum patterns to store
        """
        self._patterns_file = Path(patterns_file)
        self._min_confidence = min_confidence
        self._max_patterns = max_patterns
        self._patterns: dict[str, LearnedPattern] = {}
        self._load_patterns()

    def _normalize_pattern(self, text: str) -> str:
        """Normalize text for pattern matching.

        Args:
            text: Input text

        Returns:
            Normalized text with extra whitespace removed, lowercase
        """
        # Remove extra whitespace, lowercase
        normalized = " ".join(text.lower().split())
        # Remove common filler words that don't affect intent
        fillers = ["please", "can you", "could you", "would you", "proszę"]
        for filler in fillers:
            normalized = normalized.replace(filler, "").strip()
        return " ".join(normalized.split())

    def _load_patterns(self) -> None:
        """Load learned patterns from file."""
        if not self._patterns_file.exists():
            logger.info(f"No learned patterns file at {self._patterns_file}")
            return

        try:
            with open(self._patterns_file) as f:
                data = json.load(f)

            for key, pattern_data in data.items():
                self._patterns[key] = LearnedPattern(**pattern_data)

            logger.info(f"Loaded {len(self._patterns)} learned patterns")

        except Exception as e:
            logger.error(f"Error loading learned patterns: {e}")

    def _save_patterns(self) -> None:
        """Save learned patterns to file."""
        try:
            # Ensure directory exists
            self._patterns_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert to JSON-serializable format
            data = {key: asdict(pattern) for key, pattern in self._patterns.items()}

            with open(self._patterns_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self._patterns)} learned patterns")

        except Exception as e:
            logger.error(f"Error saving learned patterns: {e}")

    def learn(self, text: str, action: HAAction, confidence: float) -> bool:
        """Learn a pattern from successful LLM match.

        Args:
            text: Original command text
            action: Successful action
            confidence: LLM confidence score

        Returns:
            True if pattern was learned, False otherwise
        """
        if confidence < self._min_confidence:
            logger.debug(f"Confidence {confidence:.2f} below threshold {self._min_confidence}")
            return False

        if not action.entity_id or not action.service:
            logger.debug("Action missing entity_id or service, skipping learn")
            return False

        pattern = self._normalize_pattern(text)

        if not pattern:
            return False

        # Check if we already have this exact pattern
        if pattern in self._patterns:
            # Update existing pattern's confidence if higher
            existing = self._patterns[pattern]
            if confidence > existing.confidence:
                existing.confidence = confidence
                existing.learned_at = time.time()
                self._save_patterns()
                logger.debug(f"Updated pattern confidence: {pattern[:50]}...")
            return False

        # Add new pattern
        self._patterns[pattern] = LearnedPattern(
            pattern=pattern,
            entity_id=action.entity_id,
            service=action.service,
            confidence=confidence,
            learned_at=time.time(),
            match_count=0,
        )

        # Enforce max patterns (remove least used, oldest)
        while len(self._patterns) > self._max_patterns:
            # Find least valuable pattern (low match count, old)
            worst_key = min(
                self._patterns.keys(),
                key=lambda k: (
                    self._patterns[k].match_count,
                    -self._patterns[k].learned_at,
                ),
            )
            del self._patterns[worst_key]
            logger.debug(f"Evicted pattern: {worst_key[:50]}...")

        self._save_patterns()
        logger.info(f"Learned pattern: '{pattern[:50]}...' → {action.entity_id}")
        return True

    def match(self, text: str) -> tuple[str, str, float] | None:
        """Match text against learned patterns.

        Args:
            text: Command text

        Returns:
            Tuple of (entity_id, service, confidence) if matched, None otherwise
        """
        pattern = self._normalize_pattern(text)

        if pattern in self._patterns:
            learned = self._patterns[pattern]
            learned.match_count += 1
            self._save_patterns()

            logger.info(
                f"Learned pattern match: '{pattern[:50]}...' → {learned.entity_id} "
                f"(matches={learned.match_count})"
            )

            return (learned.entity_id, learned.service, learned.confidence)

        # Try fuzzy matching for similar patterns
        for key, learned in self._patterns.items():
            # Simple similarity: check if all words in learned pattern are in text
            pattern_words = set(key.split())
            text_words = set(pattern.split())

            if pattern_words and pattern_words.issubset(text_words):
                # All pattern words found in text
                learned.match_count += 1
                self._save_patterns()

                # Lower confidence for fuzzy match
                adjusted_confidence = learned.confidence * 0.85

                logger.info(
                    f"Fuzzy pattern match: '{pattern[:50]}...' ≈ '{key[:50]}...' → "
                    f"{learned.entity_id} (conf={adjusted_confidence:.2f})"
                )

                return (learned.entity_id, learned.service, adjusted_confidence)

        return None

    def clear(self) -> None:
        """Clear all learned patterns."""
        self._patterns.clear()
        if self._patterns_file.exists():
            self._patterns_file.unlink()
        logger.info("Cleared all learned patterns")

    def stats(self) -> dict:
        """Get learner statistics."""
        if not self._patterns:
            return {
                "total_patterns": 0,
                "max_patterns": self._max_patterns,
                "min_confidence": self._min_confidence,
            }

        return {
            "total_patterns": len(self._patterns),
            "max_patterns": self._max_patterns,
            "min_confidence": self._min_confidence,
            "total_matches": sum(p.match_count for p in self._patterns.values()),
            "most_used": max(
                self._patterns.items(),
                key=lambda x: x[1].match_count,
                default=(None, None),
            )[0],
        }


# Singleton instance
_pattern_learner: PatternLearner | None = None


def get_pattern_learner() -> PatternLearner:
    """Get or create singleton pattern learner instance."""
    global _pattern_learner
    if _pattern_learner is None:
        _pattern_learner = PatternLearner()
    return _pattern_learner
