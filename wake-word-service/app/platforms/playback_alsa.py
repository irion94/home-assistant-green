"""
ALSA Audio Playback Backend

Uses aplay command for audio playback on Linux systems.
"""

import logging
import os
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Optional, Union

from .playback import PlaybackBackend

logger = logging.getLogger(__name__)


class ALSAPlayback(PlaybackBackend):
    """ALSA-based audio playback using aplay.

    Works on Linux systems with ALSA support.
    """

    def __init__(self, device: Optional[str] = None, volume: float = 1.0):
        """Initialize ALSA playback.

        Args:
            device: ALSA device name (e.g., "plughw:2,0"). None for default.
            volume: Initial volume (0.0 to 1.0).
        """
        self._device = device or os.getenv("AUDIO_OUTPUT_DEVICE", "default")
        self._volume = volume
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

        logger.info(f"ALSAPlayback initialized: device={self._device}")

    def play_file(self, path: Union[str, Path], blocking: bool = True) -> bool:
        """Play an audio file using aplay."""
        path = Path(path)

        if not path.exists():
            logger.error(f"Audio file not found: {path}")
            return False

        try:
            cmd = ["aplay"]

            # Add device if not default
            if self._device and self._device != "default":
                cmd.extend(["-D", self._device])

            # Add quiet flag
            cmd.append("-q")

            # Add file path
            cmd.append(str(path))

            logger.debug(f"Playing: {' '.join(cmd)}")

            with self._lock:
                if blocking:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=120,
                    )
                    if result.returncode != 0:
                        logger.error(f"aplay failed: {result.stderr.decode()}")
                        return False
                else:
                    self._process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                    )

            return True

        except subprocess.TimeoutExpired:
            logger.error("Playback timed out")
            return False
        except FileNotFoundError:
            logger.error("aplay command not found - ALSA utils not installed?")
            return False
        except Exception as e:
            logger.error(f"Playback failed: {e}")
            return False

    def play_bytes(self, data: bytes, sample_rate: int = 44100, blocking: bool = True) -> bool:
        """Play raw audio data using aplay."""
        try:
            # Write to temp file and play
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name

            try:
                return self.play_file(tmp_path, blocking=blocking)
            finally:
                # Cleanup temp file (only if blocking, otherwise defer)
                if blocking:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass

        except Exception as e:
            logger.error(f"Failed to play audio bytes: {e}")
            return False

    def stop(self) -> None:
        """Stop any currently playing audio."""
        with self._lock:
            if self._process is not None:
                try:
                    self._process.terminate()
                    self._process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                except Exception as e:
                    logger.error(f"Error stopping playback: {e}")
                finally:
                    self._process = None

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        with self._lock:
            if self._process is None:
                return False
            return self._process.poll() is None

    def set_volume(self, volume: float) -> None:
        """Set playback volume.

        Note: ALSA volume control via amixer is system-wide.
        This sets the instance volume for reference but actual
        system volume control would require amixer commands.
        """
        self._volume = max(0.0, min(1.0, volume))
        logger.debug(f"Volume set to: {self._volume}")

        # Optional: Control system volume via amixer
        # subprocess.run(["amixer", "set", "Master", f"{int(self._volume * 100)}%"])

    def get_output_device(self) -> Optional[str]:
        """Get the current output device name."""
        return self._device

    def cleanup(self) -> None:
        """Cleanup resources."""
        self.stop()


def is_alsa_available() -> bool:
    """Check if ALSA is available on this system.

    Returns:
        True if aplay command is available.
    """
    try:
        result = subprocess.run(
            ["which", "aplay"],
            capture_output=True,
        )
        return result.returncode == 0
    except Exception:
        return False
