"""
Audio Playback Abstract Interface

Defines the contract for audio output backends.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


class PlaybackBackend(ABC):
    """Abstract base class for audio playback backends."""

    @abstractmethod
    def play_file(self, path: Union[str, Path], blocking: bool = True) -> bool:
        """Play an audio file.

        Args:
            path: Path to audio file (WAV, MP3, etc.).
            blocking: If True, wait for playback to complete.

        Returns:
            True if playback started successfully.
        """
        pass

    @abstractmethod
    def play_bytes(self, data: bytes, sample_rate: int = 44100, blocking: bool = True) -> bool:
        """Play raw audio data.

        Args:
            data: WAV audio data as bytes.
            sample_rate: Sample rate (used if not WAV format).
            blocking: If True, wait for playback to complete.

        Returns:
            True if playback started successfully.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop any currently playing audio."""
        pass

    @abstractmethod
    def is_playing(self) -> bool:
        """Check if audio is currently playing.

        Returns:
            True if audio is playing.
        """
        pass

    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """Set playback volume.

        Args:
            volume: Volume level from 0.0 to 1.0.
        """
        pass

    def get_output_device(self) -> Optional[str]:
        """Get the current output device name.

        Returns:
            Device name or None if using default.
        """
        return None

    def cleanup(self) -> None:
        """Cleanup any resources.

        Called when the backend is no longer needed.
        """
        pass
