"""
Platform Abstraction Layer for Wake-Word Service

Provides cross-platform support for:
- macOS (development)
- Linux (generic)
- Raspberry Pi (with ReSpeaker support)

Usage:
    from app.platform import get_platform, Platform
    from app.platform import get_audio_backend, get_playback_backend, get_feedback_backend

    platform = get_platform()
    audio = get_audio_backend()
    playback = get_playback_backend()
    feedback = get_feedback_backend()
"""

import logging
import os
from typing import Optional

from .detector import Platform, detect_platform, get_platform, get_platform_info
from .audio_backend import AudioBackend, AudioDevice
from .audio_pyaudio import PyAudioBackend, get_audio_backend
from .playback import PlaybackBackend
from .playback_alsa import ALSAPlayback, is_alsa_available
from .playback_pyaudio import PyAudioPlayback
from .feedback_backend import (
    FeedbackBackend,
    FeedbackState,
    NullFeedback,
    ConsoleFeedback,
    PixelRingFeedback,
    get_feedback_backend,
)

logger = logging.getLogger(__name__)


def get_playback_backend(
    device: Optional[str] = None,
    force_pyaudio: bool = False,
) -> PlaybackBackend:
    """Factory function to create appropriate playback backend.

    Selection order:
    1. If force_pyaudio=True, use PyAudioPlayback
    2. If PLAYBACK_BACKEND env is set, use that backend
    3. On Linux (including RPi), prefer ALSA
    4. On macOS, use PyAudio
    5. Fallback to PyAudio if ALSA not available

    Args:
        device: Output device name (for ALSA) or index (for PyAudio).
        force_pyaudio: Force PyAudio backend.

    Returns:
        Appropriate PlaybackBackend instance.
    """
    env_backend = os.getenv("PLAYBACK_BACKEND", "auto").lower()

    if force_pyaudio or env_backend == "pyaudio":
        logger.info("Using PyAudioPlayback (forced)")
        return PyAudioPlayback()

    if env_backend == "alsa":
        if is_alsa_available():
            logger.info("Using ALSAPlayback (forced)")
            return ALSAPlayback(device=device)
        else:
            logger.warning("ALSA not available, falling back to PyAudio")
            return PyAudioPlayback()

    # Auto-detect
    platform = get_platform()

    if platform.supports_alsa and is_alsa_available():
        device = device or os.getenv("AUDIO_OUTPUT_DEVICE")
        logger.info(f"Using ALSAPlayback: device={device}")
        return ALSAPlayback(device=device)

    logger.info("Using PyAudioPlayback")
    return PyAudioPlayback()


__all__ = [
    # Platform detection
    "Platform",
    "detect_platform",
    "get_platform",
    "get_platform_info",
    # Audio input
    "AudioBackend",
    "AudioDevice",
    "PyAudioBackend",
    "get_audio_backend",
    # Audio output
    "PlaybackBackend",
    "ALSAPlayback",
    "PyAudioPlayback",
    "get_playback_backend",
    "is_alsa_available",
    # Feedback
    "FeedbackBackend",
    "FeedbackState",
    "NullFeedback",
    "ConsoleFeedback",
    "PixelRingFeedback",
    "get_feedback_backend",
]
