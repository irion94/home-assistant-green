"""
Feedback Backend Abstraction

Provides visual/LED feedback for different platforms:
- PixelRingFeedback: ReSpeaker LED ring (RPi)
- ConsoleFeedback: Emoji output (development)
- NullFeedback: No-op (silent)
"""

import logging
import os
import sys
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Tuple

from .detector import Platform, get_platform

logger = logging.getLogger(__name__)


class FeedbackState(Enum):
    """Visual feedback states."""

    IDLE = "idle"
    WAKE_DETECTED = "wake_detected"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    SUCCESS = "success"
    ERROR = "error"
    MIC_ERROR = "mic_error"


class FeedbackBackend(ABC):
    """Abstract base class for visual feedback backends."""

    @abstractmethod
    def set_state(self, state: FeedbackState) -> None:
        """Set the current feedback state.

        Args:
            state: FeedbackState to display.
        """
        pass

    @abstractmethod
    def set_color(self, r: int, g: int, b: int) -> None:
        """Set a custom RGB color.

        Args:
            r: Red component (0-255).
            g: Green component (0-255).
            b: Blue component (0-255).
        """
        pass

    @abstractmethod
    def set_brightness(self, brightness: int) -> None:
        """Set LED/display brightness.

        Args:
            brightness: Brightness level (0-100).
        """
        pass

    @abstractmethod
    def off(self) -> None:
        """Turn off all feedback indicators."""
        pass

    def cleanup(self) -> None:
        """Cleanup resources."""
        self.off()

    # Convenience methods mapping to states
    def idle(self) -> None:
        self.set_state(FeedbackState.IDLE)

    def wake_detected(self) -> None:
        self.set_state(FeedbackState.WAKE_DETECTED)

    def listening(self) -> None:
        self.set_state(FeedbackState.LISTENING)

    def processing(self) -> None:
        self.set_state(FeedbackState.PROCESSING)

    def speaking(self) -> None:
        self.set_state(FeedbackState.SPEAKING)

    def success(self) -> None:
        self.set_state(FeedbackState.SUCCESS)

    def error(self) -> None:
        self.set_state(FeedbackState.ERROR)

    def mic_error(self) -> None:
        self.set_state(FeedbackState.MIC_ERROR)


class NullFeedback(FeedbackBackend):
    """No-op feedback backend.

    Used when no visual feedback is available or desired.
    """

    def set_state(self, state: FeedbackState) -> None:
        logger.debug(f"Feedback state: {state.value}")

    def set_color(self, r: int, g: int, b: int) -> None:
        pass

    def set_brightness(self, brightness: int) -> None:
        pass

    def off(self) -> None:
        pass


class ConsoleFeedback(FeedbackBackend):
    """Console-based feedback using emoji.

    Useful for development and debugging without LED hardware.
    """

    # Emoji mapping for states
    STATE_EMOJI = {
        FeedbackState.IDLE: "⚫",  # Black circle
        FeedbackState.WAKE_DETECTED: "💡",  # Light bulb
        FeedbackState.LISTENING: "🎤",  # Microphone
        FeedbackState.PROCESSING: "🔄",  # Processing
        FeedbackState.SPEAKING: "🔊",  # Speaker
        FeedbackState.SUCCESS: "✅",  # Check mark
        FeedbackState.ERROR: "❌",  # X mark
        FeedbackState.MIC_ERROR: "🚫🎤",  # No mic
    }

    def __init__(self, show_timestamps: bool = False):
        """Initialize console feedback.

        Args:
            show_timestamps: Include timestamps in output.
        """
        self._show_timestamps = show_timestamps
        self._current_state: Optional[FeedbackState] = None

    def set_state(self, state: FeedbackState) -> None:
        if state == self._current_state:
            return

        self._current_state = state
        emoji = self.STATE_EMOJI.get(state, "❓")

        if self._show_timestamps:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {emoji} {state.value}", file=sys.stderr)
        else:
            print(f"{emoji} {state.value}", file=sys.stderr)

    def set_color(self, r: int, g: int, b: int) -> None:
        # ANSI color approximation
        print(f"🎨 RGB({r}, {g}, {b})", file=sys.stderr)

    def set_brightness(self, brightness: int) -> None:
        bars = "█" * (brightness // 10)
        print(f"☀️ Brightness: {bars} ({brightness}%)", file=sys.stderr)

    def off(self) -> None:
        self._current_state = None
        print("⚫ off", file=sys.stderr)


class PixelRingFeedback(FeedbackBackend):
    """ReSpeaker Pixel Ring LED feedback.

    Uses the pixel_ring library to control ReSpeaker LED ring.
    Only works on Raspberry Pi with ReSpeaker HAT/USB array.
    """

    def __init__(self, brightness: int = 20):
        """Initialize Pixel Ring feedback.

        Args:
            brightness: Initial LED brightness (0-31).
        """
        self._brightness = brightness
        self._pixel_ring = None
        self._available = False

        try:
            from pixel_ring import pixel_ring
            self._pixel_ring = pixel_ring
            self._pixel_ring.set_brightness(brightness)
            self._pixel_ring.off()
            self._available = True
            logger.info(f"PixelRing initialized (brightness={brightness})")
        except ImportError:
            logger.warning("pixel_ring library not available")
        except Exception as e:
            logger.error(f"Failed to initialize PixelRing: {e}")

    @property
    def available(self) -> bool:
        """Check if pixel ring is available."""
        return self._available

    def set_state(self, state: FeedbackState) -> None:
        if not self._available:
            return

        try:
            if state == FeedbackState.IDLE:
                self._pixel_ring.off()
            elif state == FeedbackState.WAKE_DETECTED:
                self._pixel_ring.wakeup()
            elif state == FeedbackState.LISTENING:
                self._pixel_ring.listen()
            elif state == FeedbackState.PROCESSING:
                self._pixel_ring.think()
            elif state == FeedbackState.SPEAKING:
                self._pixel_ring.speak()
            elif state == FeedbackState.SUCCESS:
                self._pixel_ring.set_color(0, 255, 0)  # Green
                time.sleep(0.5)
                self._pixel_ring.off()
            elif state == FeedbackState.ERROR:
                self._pixel_ring.set_color(255, 0, 0)  # Red
                time.sleep(0.5)
                self._pixel_ring.off()
            elif state == FeedbackState.MIC_ERROR:
                # Blinking red pattern
                for _ in range(3):
                    self._pixel_ring.set_color(255, 0, 0)
                    time.sleep(0.2)
                    self._pixel_ring.off()
                    time.sleep(0.2)
        except Exception as e:
            logger.error(f"PixelRing error ({state.value}): {e}")

    def set_color(self, r: int, g: int, b: int) -> None:
        if not self._available:
            return

        try:
            self._pixel_ring.set_color(r, g, b)
        except Exception as e:
            logger.error(f"PixelRing set_color error: {e}")

    def set_brightness(self, brightness: int) -> None:
        self._brightness = max(0, min(31, brightness * 31 // 100))

        if not self._available:
            return

        try:
            self._pixel_ring.set_brightness(self._brightness)
        except Exception as e:
            logger.error(f"PixelRing set_brightness error: {e}")

    def off(self) -> None:
        if not self._available:
            return

        try:
            self._pixel_ring.off()
        except Exception as e:
            logger.error(f"PixelRing off error: {e}")


def get_feedback_backend(
    force_console: bool = False,
    force_null: bool = False,
) -> FeedbackBackend:
    """Factory function to create appropriate feedback backend.

    Selection order:
    1. If force_null=True, return NullFeedback
    2. If force_console=True or FEEDBACK_CONSOLE env is set, return ConsoleFeedback
    3. On RPi, try PixelRingFeedback
    4. On other platforms, return ConsoleFeedback if interactive, else NullFeedback

    Args:
        force_console: Force console feedback (emoji).
        force_null: Force no feedback.

    Returns:
        Appropriate FeedbackBackend instance.
    """
    if force_null:
        logger.info("Using NullFeedback (forced)")
        return NullFeedback()

    # Check environment variable
    env_console = os.getenv("FEEDBACK_CONSOLE", "").lower() in ("true", "1", "yes")

    if force_console or env_console:
        logger.info("Using ConsoleFeedback")
        return ConsoleFeedback(show_timestamps=True)

    platform = get_platform()

    if platform == Platform.RPI:
        # Try pixel ring on RPi
        feedback = PixelRingFeedback()
        if feedback.available:
            logger.info("Using PixelRingFeedback")
            return feedback
        else:
            logger.warning("PixelRing not available, falling back to ConsoleFeedback")
            return ConsoleFeedback(show_timestamps=True)

    # Non-RPi platforms: console if interactive, null otherwise
    if sys.stdout.isatty():
        logger.info("Using ConsoleFeedback (interactive terminal)")
        return ConsoleFeedback(show_timestamps=True)

    logger.info("Using NullFeedback (non-interactive)")
    return NullFeedback()
