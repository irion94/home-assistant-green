"""
PyAudio Audio Backend

Cross-platform audio input using PyAudio.
Works on macOS, Linux, and Raspberry Pi.
"""

import logging
import os
from collections import deque
from typing import Callable, List, Optional

import numpy as np
import pyaudio

from .audio_backend import AudioBackend, AudioDevice
from .detector import Platform, get_platform

logger = logging.getLogger(__name__)

# Default device preferences per platform
DEFAULT_PREFERENCES = {
    Platform.RPI: ["ReSpeaker", "USB Audio", "seeed"],
    Platform.LINUX: ["USB Audio", "pulse", "default"],
    Platform.MACOS: ["Built-in Microphone", "MacBook", "USB"],
}


class PyAudioBackend(AudioBackend):
    """PyAudio-based audio input backend.

    Provides cross-platform audio capture with automatic device detection
    and preference-based device selection.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1280,
        gain: float = 2.0,
    ):
        """Initialize PyAudio backend.

        Args:
            sample_rate: Default sample rate in Hz.
            channels: Default number of input channels.
            chunk_size: Default frames per buffer.
            gain: Software gain multiplier for audio.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.gain = gain

        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._selected_device: Optional[AudioDevice] = None
        self._buffer: deque = deque(maxlen=100)
        self._platform = get_platform()

        # Get preferences from environment or use platform defaults
        env_prefs = os.getenv("AUDIO_DEVICE_PREFERENCE", "")
        if env_prefs:
            self._preferences = [p.strip() for p in env_prefs.split(",") if p.strip()]
        else:
            self._preferences = DEFAULT_PREFERENCES.get(self._platform, [])

        logger.info(
            f"PyAudioBackend initialized: platform={self._platform.value}, "
            f"preferences={self._preferences}, gain={self.gain}"
        )

    def _ensure_pyaudio(self) -> pyaudio.PyAudio:
        """Ensure PyAudio is initialized.

        Returns:
            PyAudio instance.
        """
        if self._pyaudio is None:
            logger.debug("Initializing PyAudio")
            self._pyaudio = pyaudio.PyAudio()
        return self._pyaudio

    def enumerate_devices(self) -> List[AudioDevice]:
        """List all available audio input devices."""
        pa = self._ensure_pyaudio()
        devices = []

        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            max_input = info.get("maxInputChannels", 0)

            # Only include devices with input capability
            if max_input > 0:
                host_api_info = pa.get_host_api_info_by_index(info.get("hostApi", 0))
                device = AudioDevice(
                    index=i,
                    name=info.get("name", f"Device {i}"),
                    max_input_channels=max_input,
                    default_sample_rate=info.get("defaultSampleRate", 44100),
                    host_api=host_api_info.get("name", "Unknown"),
                )
                devices.append(device)
                logger.debug(f"Found input device: {device}")

        return devices

    def select_device(
        self,
        preferences: Optional[List[str]] = None,
        fallback_to_default: bool = True
    ) -> Optional[AudioDevice]:
        """Select an audio device based on preferences."""
        devices = self.enumerate_devices()

        if not devices:
            logger.error("No audio input devices found")
            return None

        # Use provided preferences or instance defaults
        prefs = preferences or self._preferences

        # Try to match preferences in order
        for pref in prefs:
            pref_lower = pref.lower()
            for device in devices:
                if pref_lower in device.name.lower():
                    logger.info(f"Selected device by preference '{pref}': {device}")
                    self._selected_device = device
                    return device

        # Fallback to default device
        if fallback_to_default:
            pa = self._ensure_pyaudio()
            try:
                default_idx = pa.get_default_input_device_info().get("index")
                for device in devices:
                    if device.index == default_idx:
                        logger.info(f"Using default input device: {device}")
                        self._selected_device = device
                        return device
            except IOError:
                pass

            # Last resort: use first available device
            if devices:
                logger.warning(f"Using first available device: {devices[0]}")
                self._selected_device = devices[0]
                return devices[0]

        logger.error("No suitable audio device found")
        return None

    def open_stream(
        self,
        device: Optional[AudioDevice] = None,
        sample_rate: int = None,
        channels: int = None,
        chunk_size: int = None,
    ) -> None:
        """Open audio stream for the specified device."""
        pa = self._ensure_pyaudio()

        # Use provided values or defaults
        rate = sample_rate or self.sample_rate
        ch = channels or self.channels
        chunk = chunk_size or self.chunk_size

        # Select device if not provided
        if device is None:
            device = self._selected_device or self.select_device()

        if device is None:
            raise RuntimeError("No audio device available")

        # Validate channel count
        if ch > device.max_input_channels:
            logger.warning(
                f"Requested {ch} channels but device supports {device.max_input_channels}. "
                f"Using {device.max_input_channels} channels."
            )
            ch = device.max_input_channels

        logger.info(
            f"Opening audio stream: device={device.name}, "
            f"rate={rate}, channels={ch}, chunk={chunk}"
        )

        try:
            self._stream = pa.open(
                format=pyaudio.paInt16,
                channels=ch,
                rate=rate,
                input=True,
                input_device_index=device.index,
                frames_per_buffer=chunk,
                stream_callback=None,  # Blocking mode
            )
            self._selected_device = device
            self.channels = ch
            self.sample_rate = rate
            self.chunk_size = chunk
            logger.info("Audio stream opened successfully")

        except Exception as e:
            logger.error(f"Failed to open audio stream: {e}")
            raise

    def close_stream(self) -> None:
        """Close the audio stream."""
        if self._stream is not None:
            try:
                if self._stream.is_active():
                    self._stream.stop_stream()
                self._stream.close()
                logger.info("Audio stream closed")
            except Exception as e:
                logger.error(f"Error closing stream: {e}")
            finally:
                self._stream = None

        if self._pyaudio is not None:
            try:
                self._pyaudio.terminate()
            except Exception as e:
                logger.error(f"Error terminating PyAudio: {e}")
            finally:
                self._pyaudio = None

    def read_chunk(self) -> Optional[np.ndarray]:
        """Read a single chunk of audio data."""
        if not self.is_active():
            return None

        try:
            data = self._stream.read(self.chunk_size, exception_on_overflow=False)
            audio = np.frombuffer(data, dtype=np.int16)

            # Handle multi-channel audio
            if self.channels > 1:
                audio = audio.reshape(-1, self.channels)
                # Use first channel (raw mic)
                audio = audio[:, 0]

            # Apply software gain
            if self.gain != 1.0:
                audio = np.clip(
                    audio.astype(np.float32) * self.gain,
                    -32768,
                    32767
                ).astype(np.int16)

            # Store in buffer
            self._buffer.append(audio.copy())

            return audio

        except Exception as e:
            logger.error(f"Error reading audio chunk: {e}")
            return None

    def is_active(self) -> bool:
        """Check if the audio stream is currently active."""
        return self._stream is not None and self._stream.is_active()

    def get_selected_device(self) -> Optional[AudioDevice]:
        """Get the currently selected device."""
        return self._selected_device

    def record(
        self,
        duration: float,
        stop_check: Optional[Callable[[], bool]] = None,
        silence_threshold: int = 1000,
        silence_chunks_to_stop: int = 12,
        min_speech_chunks: int = 8,
    ) -> np.ndarray:
        """Record audio with voice activity detection (VAD)."""
        logger.info(f"Recording (max {duration}s, VAD enabled)")

        max_chunks = int(duration * self.sample_rate / self.chunk_size)
        recorded_chunks = []

        consecutive_silence = 0
        speech_detected = False
        speech_chunks = 0

        try:
            for _ in range(max_chunks):
                if stop_check and stop_check():
                    logger.info("Recording interrupted by stop signal")
                    break

                chunk = self.read_chunk()
                if chunk is None:
                    continue

                recorded_chunks.append(chunk)

                # Calculate audio energy for VAD
                energy = np.mean(np.abs(chunk))

                if energy > silence_threshold:
                    speech_detected = True
                    speech_chunks += 1
                    consecutive_silence = 0
                else:
                    consecutive_silence += 1

                # Stop if we've had speech and now have enough silence
                if speech_detected and speech_chunks >= min_speech_chunks:
                    if consecutive_silence >= silence_chunks_to_stop:
                        logger.info(f"VAD: Speech ended after {len(recorded_chunks)} chunks")
                        break

            if recorded_chunks:
                audio = np.concatenate(recorded_chunks)
                logger.info(f"Recorded {len(audio)} samples ({len(audio)/self.sample_rate:.2f}s)")
                return audio
            else:
                logger.warning("No audio data recorded")
                return np.array([], dtype=np.int16)

        except Exception as e:
            logger.error(f"Error during recording: {e}")
            return np.array([], dtype=np.int16)

    def record_streaming(
        self,
        duration: float,
        on_chunk: Callable[[np.ndarray], None],
        stop_check: Optional[Callable[[], bool]] = None,
        silence_threshold: int = 1000,
        silence_chunks_to_stop: int = 12,
        min_speech_chunks: int = 8,
    ) -> np.ndarray:
        """Record audio with streaming callback for real-time STT."""
        logger.info(f"Recording with streaming (max {duration}s, VAD enabled)")

        max_chunks = int(duration * self.sample_rate / self.chunk_size)
        recorded_chunks = []

        consecutive_silence = 0
        speech_detected = False
        speech_chunks = 0

        try:
            for _ in range(max_chunks):
                if stop_check and stop_check():
                    logger.info("Streaming recording interrupted by stop signal")
                    break

                chunk = self.read_chunk()
                if chunk is None:
                    continue

                recorded_chunks.append(chunk)

                # Invoke streaming callback
                try:
                    on_chunk(chunk)
                except Exception as e:
                    logger.error(f"on_chunk callback error: {e}")

                # Calculate audio energy for VAD
                energy = np.mean(np.abs(chunk))

                if energy > silence_threshold:
                    speech_detected = True
                    speech_chunks += 1
                    consecutive_silence = 0
                else:
                    consecutive_silence += 1

                # Stop if we've had speech and now have enough silence
                if speech_detected and speech_chunks >= min_speech_chunks:
                    if consecutive_silence >= silence_chunks_to_stop:
                        logger.info(
                            f"Streaming VAD: Speech ended after {len(recorded_chunks)} chunks "
                            f"({len(recorded_chunks) * self.chunk_size / self.sample_rate:.2f}s)"
                        )
                        break

            if recorded_chunks:
                audio = np.concatenate(recorded_chunks)
                logger.info(
                    f"Streaming recording complete: {len(audio)} samples "
                    f"({len(audio)/self.sample_rate:.2f}s)"
                )
                return audio
            else:
                logger.warning("No audio data recorded in streaming mode")
                return np.array([], dtype=np.int16)

        except Exception as e:
            logger.error(f"Error during streaming recording: {e}")
            return np.array([], dtype=np.int16)

    def get_device_info(self) -> dict:
        """Get information about the selected audio device."""
        if self._selected_device is None:
            return {}

        return {
            "index": self._selected_device.index,
            "name": self._selected_device.name,
            "max_input_channels": self._selected_device.max_input_channels,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "chunk_size": self.chunk_size,
            "gain": self.gain,
            "platform": self._platform.value,
        }


def get_audio_backend(
    sample_rate: int = 16000,
    channels: int = None,
    chunk_size: int = 1280,
    gain: float = None,
) -> PyAudioBackend:
    """Factory function to create an audio backend.

    Reads configuration from environment variables:
    - AUDIO_INPUT_CHANNELS: Number of input channels (default: platform-specific)
    - AUDIO_DEVICE_PREFERENCE: Comma-separated device preferences
    - SAMPLE_RATE: Sample rate in Hz
    - CHUNK_SIZE: Frames per buffer

    Args:
        sample_rate: Sample rate in Hz.
        channels: Number of input channels (auto-detected if None).
        chunk_size: Frames per buffer.
        gain: Software gain multiplier.

    Returns:
        Configured PyAudioBackend instance.
    """
    platform = get_platform()

    # Read from environment with sensible defaults per platform
    env_channels = os.getenv("AUDIO_INPUT_CHANNELS")
    if channels is None:
        if env_channels:
            channels = int(env_channels)
        elif platform == Platform.RPI:
            channels = 6  # ReSpeaker 4 Mic Array
        else:
            channels = 1  # Most USB mics

    env_rate = os.getenv("SAMPLE_RATE")
    if env_rate:
        sample_rate = int(env_rate)

    env_chunk = os.getenv("CHUNK_SIZE")
    if env_chunk:
        chunk_size = int(env_chunk)

    if gain is None:
        gain = 2.0  # Default gain boost

    return PyAudioBackend(
        sample_rate=sample_rate,
        channels=channels,
        chunk_size=chunk_size,
        gain=gain,
    )
