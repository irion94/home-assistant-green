"""
Platform Detection Module

Detects the current runtime environment:
- macOS (Darwin)
- Linux (generic x86_64/aarch64)
- Raspberry Pi (Linux with /proc/device-tree/model)

Can be overridden via PLATFORM environment variable.
"""

import logging
import os
import platform
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Supported platforms for wake-word service."""

    MACOS = "macos"
    LINUX = "linux"
    RPI = "rpi"  # Raspberry Pi (any version)

    @property
    def is_linux(self) -> bool:
        """Check if platform is any Linux variant."""
        return self in (Platform.LINUX, Platform.RPI)

    @property
    def supports_alsa(self) -> bool:
        """Check if platform supports ALSA audio."""
        return self.is_linux

    @property
    def supports_pixel_ring(self) -> bool:
        """Check if platform supports ReSpeaker pixel ring LEDs."""
        return self == Platform.RPI


def _detect_raspberry_pi() -> bool:
    """Detect if running on Raspberry Pi.

    Checks /proc/device-tree/model which contains the Pi model string.

    Returns:
        True if running on Raspberry Pi, False otherwise.
    """
    model_path = Path("/proc/device-tree/model")

    if not model_path.exists():
        return False

    try:
        model = model_path.read_text().lower()
        is_rpi = "raspberry pi" in model
        if is_rpi:
            logger.info(f"Detected Raspberry Pi: {model.strip()}")
        return is_rpi
    except (IOError, OSError) as e:
        logger.debug(f"Could not read device-tree model: {e}")
        return False


def _detect_platform_auto() -> Platform:
    """Auto-detect the current platform.

    Returns:
        Detected Platform enum value.
    """
    system = platform.system().lower()

    if system == "darwin":
        logger.info("Detected platform: macOS")
        return Platform.MACOS

    if system == "linux":
        if _detect_raspberry_pi():
            return Platform.RPI
        logger.info("Detected platform: Linux (generic)")
        return Platform.LINUX

    # Fallback to generic Linux for unknown systems
    logger.warning(f"Unknown system '{system}', defaulting to Linux")
    return Platform.LINUX


def detect_platform(override: Optional[str] = None) -> Platform:
    """Detect or override the current platform.

    Args:
        override: Manual platform override. Valid values:
            - "auto": Auto-detect (default)
            - "macos": Force macOS mode
            - "linux": Force generic Linux mode
            - "rpi": Force Raspberry Pi mode

    Returns:
        Platform enum value.

    Raises:
        ValueError: If override value is invalid.
    """
    # Check environment variable first
    env_platform = os.getenv("PLATFORM", "").lower().strip()
    effective_override = override or env_platform

    if not effective_override or effective_override == "auto":
        return _detect_platform_auto()

    # Map override strings to Platform enum
    override_map = {
        "macos": Platform.MACOS,
        "darwin": Platform.MACOS,
        "linux": Platform.LINUX,
        "rpi": Platform.RPI,
        "raspberry": Platform.RPI,
        "raspberrypi": Platform.RPI,
    }

    if effective_override in override_map:
        detected = override_map[effective_override]
        logger.info(f"Platform override: {detected.value}")
        return detected

    valid_options = list(override_map.keys()) + ["auto"]
    raise ValueError(
        f"Invalid platform override '{effective_override}'. "
        f"Valid options: {', '.join(valid_options)}"
    )


@lru_cache(maxsize=1)
def get_platform() -> Platform:
    """Get the current platform (cached).

    This function caches the result for performance.
    Use detect_platform() directly if you need to bypass the cache.

    Returns:
        Platform enum value.
    """
    return detect_platform()


def get_platform_info() -> dict:
    """Get detailed platform information for diagnostics.

    Returns:
        Dictionary with platform details.
    """
    current = get_platform()

    info = {
        "platform": current.value,
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "supports_alsa": current.supports_alsa,
        "supports_pixel_ring": current.supports_pixel_ring,
    }

    # Add Pi-specific info
    if current == Platform.RPI:
        model_path = Path("/proc/device-tree/model")
        if model_path.exists():
            try:
                info["rpi_model"] = model_path.read_text().strip().rstrip("\x00")
            except (IOError, OSError):
                pass

    return info
