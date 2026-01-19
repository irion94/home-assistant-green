"""
PyAudio Audio Playback Backend

Cross-platform audio playback using PyAudio.
Works on macOS, Linux, and Raspberry Pi.
"""

import io
import logging
import os
import threading
import wave
from pathlib import Path
from typing import Optional, Union

import pyaudio

from .playback import PlaybackBackend

logger = logging.getLogger(__name__)


class PyAudioPlayback(PlaybackBackend):
    """PyAudio-based audio playback backend.

    Provides cross-platform audio output without system dependencies.
    """

    def __init__(self, device_index: Optional[int] = None, volume: float = 1.0):
        """Initialize PyAudio playback.

        Args:
            device_index: Output device index. None for default.
            volume: Initial volume (0.0 to 1.0).
        """
        self._device_index = device_index
        self._volume = volume
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._playing = False
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()
        self._playback_thread: Optional[threading.Thread] = None

        logger.info(f"PyAudioPlayback initialized: device_index={device_index}")

    def _ensure_pyaudio(self) -> pyaudio.PyAudio:
        """Ensure PyAudio is initialized."""
        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()
        return self._pyaudio

    def _find_output_device(self) -> Optional[int]:
        """Find a suitable output device.

        Returns:
            Device index or None for default.
        """
        if self._device_index is not None:
            return self._device_index

        pa = self._ensure_pyaudio()

        # Try to find preferred output device
        env_pref = os.getenv("AUDIO_OUTPUT_DEVICE_PREFERENCE", "")
        if env_pref:
            prefs = [p.strip().lower() for p in env_pref.split(",")]

            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info.get("maxOutputChannels", 0) > 0:
                    name = info.get("name", "").lower()
                    for pref in prefs:
                        if pref in name:
                            logger.info(f"Selected output device: {info.get('name')}")
                            return i

        # Use default output device
        try:
            default_info = pa.get_default_output_device_info()
            return default_info.get("index")
        except IOError:
            return None

    def play_file(self, path: Union[str, Path], blocking: bool = True) -> bool:
        """Play an audio file using PyAudio."""
        path = Path(path)

        if not path.exists():
            logger.error(f"Audio file not found: {path}")
            return False

        try:
            with open(path, "rb") as f:
                data = f.read()
            return self.play_bytes(data, blocking=blocking)

        except Exception as e:
            logger.error(f"Failed to play file: {e}")
            return False

    def play_bytes(self, data: bytes, sample_rate: int = 44100, blocking: bool = True) -> bool:
        """Play WAV audio data using PyAudio."""
        try:
            # Parse WAV data
            wav_io = io.BytesIO(data)
            with wave.open(wav_io, "rb") as wf:
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                rate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())

            if blocking:
                return self._play_blocking(frames, channels, sample_width, rate)
            else:
                self._playback_thread = threading.Thread(
                    target=self._play_blocking,
                    args=(frames, channels, sample_width, rate),
                    daemon=True,
                )
                self._playback_thread.start()
                return True

        except wave.Error as e:
            logger.error(f"Invalid WAV data: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to play audio bytes: {e}")
            return False

    def _play_blocking(
        self,
        frames: bytes,
        channels: int,
        sample_width: int,
        rate: int
    ) -> bool:
        """Play audio data in blocking mode."""
        pa = self._ensure_pyaudio()
        device_index = self._find_output_device()

        try:
            with self._lock:
                self._stop_flag.clear()
                self._playing = True

            # Get format from sample width
            format_map = {
                1: pyaudio.paInt8,
                2: pyaudio.paInt16,
                4: pyaudio.paInt32,
            }
            pa_format = format_map.get(sample_width, pyaudio.paInt16)

            # Open stream
            stream = pa.open(
                format=pa_format,
                channels=channels,
                rate=rate,
                output=True,
                output_device_index=device_index,
            )

            try:
                # Apply volume
                if self._volume != 1.0:
                    import numpy as np
                    audio = np.frombuffer(frames, dtype=np.int16)
                    audio = (audio * self._volume).astype(np.int16)
                    frames = audio.tobytes()

                # Write in chunks to allow stopping
                chunk_size = 4096
                for i in range(0, len(frames), chunk_size):
                    if self._stop_flag.is_set():
                        logger.debug("Playback stopped")
                        break
                    chunk = frames[i:i + chunk_size]
                    stream.write(chunk)

                return True

            finally:
                stream.stop_stream()
                stream.close()

        except Exception as e:
            logger.error(f"Playback error: {e}")
            return False

        finally:
            with self._lock:
                self._playing = False

    def stop(self) -> None:
        """Stop any currently playing audio."""
        self._stop_flag.set()

        if self._playback_thread is not None:
            self._playback_thread.join(timeout=1)
            self._playback_thread = None

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        with self._lock:
            return self._playing

    def set_volume(self, volume: float) -> None:
        """Set playback volume."""
        self._volume = max(0.0, min(1.0, volume))
        logger.debug(f"Volume set to: {self._volume}")

    def get_output_device(self) -> Optional[str]:
        """Get the current output device name."""
        if self._device_index is None:
            return "default"

        try:
            pa = self._ensure_pyaudio()
            info = pa.get_device_info_by_index(self._device_index)
            return info.get("name", f"Device {self._device_index}")
        except Exception:
            return f"Device {self._device_index}"

    def cleanup(self) -> None:
        """Cleanup resources."""
        self.stop()

        if self._pyaudio is not None:
            try:
                self._pyaudio.terminate()
            except Exception as e:
                logger.error(f"Error terminating PyAudio: {e}")
            finally:
                self._pyaudio = None

    def list_output_devices(self) -> list:
        """List available output devices.

        Returns:
            List of (index, name) tuples.
        """
        pa = self._ensure_pyaudio()
        devices = []

        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info.get("maxOutputChannels", 0) > 0:
                devices.append((i, info.get("name", f"Device {i}")))

        return devices
