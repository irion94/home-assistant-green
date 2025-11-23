"""
Audio and LED Feedback Module
Provides audio and visual feedback for wake-word detection events
"""

import os
import logging
import subprocess
import time
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import pixel_ring for LED control
try:
    from pixel_ring import pixel_ring
    PIXEL_RING_AVAILABLE = True
except ImportError:
    PIXEL_RING_AVAILABLE = False
    logger.warning("pixel_ring not available - LED feedback disabled")


class AudioFeedback:
    """Audio and LED feedback system"""

    def __init__(self, enabled: bool = True):
        """
        Initialize audio and LED feedback

        Args:
            enabled: Whether feedback is enabled
        """
        self.enabled = enabled
        self.sounds_dir = Path("/app/sounds")
        self.volume = float(os.getenv("BEEP_VOLUME", "0.8"))
        self.led_enabled = PIXEL_RING_AVAILABLE

        # Initialize LEDs
        if self.led_enabled:
            try:
                pixel_ring.set_brightness(20)  # Set moderate brightness
                pixel_ring.off()
                logger.info("LED feedback initialized")
            except Exception as e:
                logger.error(f"Failed to initialize LEDs: {e}")
                self.led_enabled = False

        logger.info(f"Audio feedback initialized (enabled: {self.enabled}, LED: {self.led_enabled})")

    def idle(self):
        """Set idle state - LEDs off"""
        if self.led_enabled:
            try:
                pixel_ring.off()
            except Exception as e:
                logger.error(f"LED error (idle): {e}")

    def play_wake_detected(self):
        """Play sound and show LED when wake word is detected"""
        # LED feedback - blue wakeup animation
        if self.led_enabled:
            try:
                pixel_ring.wakeup()
            except Exception as e:
                logger.error(f"LED error (wake): {e}")

        # Audio feedback
        if not self.enabled:
            return

        sound_file = self.sounds_dir / "wake_detected.wav"
        self._play_sound(sound_file, "wake detected")

    def play_listening(self):
        """Play sound and show LED when starting to listen for command"""
        # LED feedback - blue listening/thinking animation
        if self.led_enabled:
            try:
                pixel_ring.listen()
            except Exception as e:
                logger.error(f"LED error (listen): {e}")

        # Audio feedback
        if not self.enabled:
            return

        sound_file = self.sounds_dir / "listening.wav"
        self._play_sound(sound_file, "listening")

    def processing(self):
        """Show LED for processing state"""
        if self.led_enabled:
            try:
                pixel_ring.think()  # Green spinning animation
            except Exception as e:
                logger.error(f"LED error (processing): {e}")

    def speaking(self):
        """Show LED for TTS speaking state"""
        if self.led_enabled:
            try:
                pixel_ring.speak()  # Blue pulsing animation
            except Exception as e:
                logger.error(f"LED error (speaking): {e}")

    def play_success(self):
        """Play sound and show LED when command succeeds"""
        # LED feedback - green flash then off
        if self.led_enabled:
            try:
                pixel_ring.set_color(0, 255, 0)  # Green
                time.sleep(0.5)
                pixel_ring.off()
            except Exception as e:
                logger.error(f"LED error (success): {e}")

        # Audio feedback
        if not self.enabled:
            return

        sound_file = self.sounds_dir / "success.wav"
        self._play_sound(sound_file, "success")

    def play_error(self):
        """Play sound and show LED when command fails"""
        # LED feedback - red flash then off
        if self.led_enabled:
            try:
                pixel_ring.set_color(255, 0, 0)  # Red
                time.sleep(0.5)
                pixel_ring.off()
            except Exception as e:
                logger.error(f"LED error (error): {e}")

        # Audio feedback
        if not self.enabled:
            return

        sound_file = self.sounds_dir / "error.wav"
        self._play_sound(sound_file, "error")

    def mic_error(self):
        """Show LED pattern for microphone error - blinking red"""
        if self.led_enabled:
            try:
                for _ in range(3):
                    pixel_ring.set_color(255, 0, 0)  # Red
                    time.sleep(0.2)
                    pixel_ring.off()
                    time.sleep(0.2)
            except Exception as e:
                logger.error(f"LED error (mic_error): {e}")

    def _play_sound(self, sound_file: Path, description: str):
        """
        Play a sound file using aplay

        Args:
            sound_file: Path to WAV file
            description: Description for logging
        """
        if not sound_file.exists():
            logger.warning(f"Sound file not found: {sound_file}")
            return

        try:
            # Use aplay to play the sound
            subprocess.run(
                ["aplay", "-q", str(sound_file)],
                check=True,
                timeout=5,
                capture_output=True
            )
            logger.debug(f"Played {description} sound")

        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout playing {description} sound")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error playing {description} sound: {e}")
        except Exception as e:
            logger.error(f"Unexpected error playing sound: {e}")

    def cleanup(self):
        """Cleanup LED state"""
        if self.led_enabled:
            try:
                pixel_ring.off()
            except Exception as e:
                logger.error(f"LED cleanup error: {e}")
