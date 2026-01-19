"""
Audio Backend Abstract Interface

Defines the contract for audio input backends.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AudioDevice:
    """Represents an audio input device."""

    index: int
    name: str
    max_input_channels: int
    default_sample_rate: float
    host_api: str

    def __str__(self) -> str:
        return f"[{self.index}] {self.name} ({self.max_input_channels}ch, {int(self.default_sample_rate)}Hz)"


class AudioBackend(ABC):
    """Abstract base class for audio input backends."""

    @abstractmethod
    def enumerate_devices(self) -> List[AudioDevice]:
        """List all available audio input devices.

        Returns:
            List of AudioDevice objects.
        """
        pass

    @abstractmethod
    def select_device(
        self,
        preferences: Optional[List[str]] = None,
        fallback_to_default: bool = True
    ) -> Optional[AudioDevice]:
        """Select an audio device based on preferences.

        Args:
            preferences: List of device name patterns to match (case-insensitive).
                         Matched in order of preference.
            fallback_to_default: If True, return default device when no preference matches.

        Returns:
            Selected AudioDevice or None if no suitable device found.
        """
        pass

    @abstractmethod
    def open_stream(
        self,
        device: Optional[AudioDevice] = None,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1280,
    ) -> None:
        """Open audio stream for the specified device.

        Args:
            device: Device to use. If None, uses auto-selected device.
            sample_rate: Sample rate in Hz.
            channels: Number of input channels.
            chunk_size: Frames per buffer.
        """
        pass

    @abstractmethod
    def close_stream(self) -> None:
        """Close the audio stream."""
        pass

    @abstractmethod
    def read_chunk(self) -> Optional[np.ndarray]:
        """Read a single chunk of audio data.

        Returns:
            Numpy array with audio data (mono, int16) or None on error.
        """
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """Check if the audio stream is currently active.

        Returns:
            True if stream is open and active.
        """
        pass

    @abstractmethod
    def get_selected_device(self) -> Optional[AudioDevice]:
        """Get the currently selected device.

        Returns:
            AudioDevice if a device is selected, None otherwise.
        """
        pass

    def record(
        self,
        duration: float,
        stop_check: Optional[Callable[[], bool]] = None,
        silence_threshold: int = 1000,
        silence_chunks_to_stop: int = 12,
        min_speech_chunks: int = 8,
    ) -> np.ndarray:
        """Record audio with voice activity detection (VAD).

        Default implementation using read_chunk().
        Can be overridden for platform-specific optimizations.

        Args:
            duration: Maximum recording duration in seconds.
            stop_check: Optional callable that returns True to stop recording.
            silence_threshold: Audio level below this is considered silence.
            silence_chunks_to_stop: Consecutive silent chunks to end recording.
            min_speech_chunks: Minimum speech chunks before allowing stop.

        Returns:
            Numpy array with recorded audio (mono, int16).
        """
        # This is a default implementation - subclasses may override
        raise NotImplementedError("Subclass should implement record()")

    def record_streaming(
        self,
        duration: float,
        on_chunk: Callable[[np.ndarray], None],
        stop_check: Optional[Callable[[], bool]] = None,
        silence_threshold: int = 1000,
        silence_chunks_to_stop: int = 12,
        min_speech_chunks: int = 8,
    ) -> np.ndarray:
        """Record audio with streaming callback for real-time STT.

        Default implementation using read_chunk().
        Can be overridden for platform-specific optimizations.

        Args:
            duration: Maximum recording duration in seconds.
            on_chunk: Callback invoked with each audio chunk.
            stop_check: Optional callable that returns True to stop recording.
            silence_threshold: Audio level below this is considered silence.
            silence_chunks_to_stop: Consecutive silent chunks to end recording.
            min_speech_chunks: Minimum speech chunks before allowing stop.

        Returns:
            Numpy array with recorded audio (mono, int16).
        """
        # This is a default implementation - subclasses may override
        raise NotImplementedError("Subclass should implement record_streaming()")
