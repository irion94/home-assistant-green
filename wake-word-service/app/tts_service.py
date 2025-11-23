"""Local TTS service using Coqui TTS.

This module handles text-to-speech synthesis locally using Coqui TTS,
generating audio that can be played on Nest Hub or other speakers.
"""

from __future__ import annotations

import io
import logging
import os
import re
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# TTS Models
TTS_MODEL_VITS_POLISH = "tts_models/pl/mai_female/vits"  # Fast, good quality
TTS_MODEL_XTTS_V2 = "tts_models/multilingual/multi-dataset/xtts_v2"  # Slow, best quality

# Backwards compatibility
TTS_MODEL_POLISH = TTS_MODEL_VITS_POLISH
TTS_MODEL_ENGLISH = "tts_models/en/ljspeech/tacotron2-DDC"

# Routing threshold
SHORT_RESPONSE_WORDS = 15  # Use fast VITS for responses under this


class TTSService:
    """Local text-to-speech service using Coqui TTS with smart routing."""

    def __init__(self, model_name: str | None = None, use_gpu: bool = False, enable_xtts: bool = True):
        """Initialize TTS service.

        Args:
            model_name: TTS model to use for fast responses. If None, uses Polish VITS.
            use_gpu: Whether to use GPU acceleration (not available on Pi).
            enable_xtts: Enable XTTS v2 for long responses (requires more storage).
        """
        self.fast_model_name = model_name or TTS_MODEL_VITS_POLISH
        self.slow_model_name = TTS_MODEL_XTTS_V2
        self.use_gpu = use_gpu
        self.enable_xtts = enable_xtts
        self._fast_tts = None  # VITS - fast
        self._slow_tts = None  # XTTS - quality
        self._models_dir = Path("/app/models/tts")
        # Audio output device (default: ReSpeaker output with ALSA plugin for format conversion)
        self.output_device = os.getenv("AUDIO_OUTPUT_DEVICE", "plughw:2,0")
        # Word threshold for routing
        self.short_threshold = int(os.getenv("TTS_SHORT_RESPONSE_LIMIT", str(SHORT_RESPONSE_WORDS)))

        logger.info(
            f"TTSService initialized: fast={self.fast_model_name}, "
            f"xtts_enabled={enable_xtts}, threshold={self.short_threshold} words, "
            f"output={self.output_device}"
        )

    def _normalize_text_for_tts(self, text: str, language: str = "pl") -> str:
        """Normalize text for better TTS pronunciation.

        Converts units, symbols, and abbreviations to spoken forms.

        Args:
            text: Text to normalize
            language: Language code ('pl' or 'en')

        Returns:
            Normalized text ready for TTS
        """
        if language == "pl":
            # Polish unit replacements
            replacements = [
                # Temperature
                (r'(\d+)\s*°C', r'\1 stopni Celsjusza'),
                (r'(\d+)\s*°F', r'\1 stopni Fahrenheita'),
                (r'(\d+)\s*°', r'\1 stopni'),
                # Speed
                (r'(\d+)\s*km/h', r'\1 kilometrów na godzinę'),
                (r'(\d+)\s*m/s', r'\1 metrów na sekundę'),
                (r'(\d+)\s*mph', r'\1 mil na godzinę'),
                # Distance
                (r'(\d+)\s*km', r'\1 kilometrów'),
                (r'(\d+)\s*m\b', r'\1 metrów'),
                (r'(\d+)\s*cm', r'\1 centymetrów'),
                (r'(\d+)\s*mm', r'\1 milimetrów'),
                # Weight
                (r'(\d+)\s*kg', r'\1 kilogramów'),
                (r'(\d+)\s*g\b', r'\1 gramów'),
                (r'(\d+)\s*mg', r'\1 miligramów'),
                # Pressure
                (r'(\d+)\s*hPa', r'\1 hektopaskali'),
                (r'(\d+)\s*Pa', r'\1 paskali'),
                # Percentage
                (r'(\d+)\s*%', r'\1 procent'),
                # Time
                (r'(\d+)\s*h\b', r'\1 godzin'),
                (r'(\d+)\s*min', r'\1 minut'),
                (r'(\d+)\s*s\b', r'\1 sekund'),
                # Other symbols
                (r'&', ' i '),
                (r'\+', ' plus '),
                (r'=', ' równa się '),
            ]
        else:
            # English unit replacements
            replacements = [
                # Temperature
                (r'(\d+)\s*°C', r'\1 degrees Celsius'),
                (r'(\d+)\s*°F', r'\1 degrees Fahrenheit'),
                (r'(\d+)\s*°', r'\1 degrees'),
                # Speed
                (r'(\d+)\s*km/h', r'\1 kilometers per hour'),
                (r'(\d+)\s*m/s', r'\1 meters per second'),
                (r'(\d+)\s*mph', r'\1 miles per hour'),
                # Distance
                (r'(\d+)\s*km', r'\1 kilometers'),
                (r'(\d+)\s*m\b', r'\1 meters'),
                (r'(\d+)\s*cm', r'\1 centimeters'),
                (r'(\d+)\s*mm', r'\1 millimeters'),
                # Weight
                (r'(\d+)\s*kg', r'\1 kilograms'),
                (r'(\d+)\s*g\b', r'\1 grams'),
                (r'(\d+)\s*mg', r'\1 milligrams'),
                # Pressure
                (r'(\d+)\s*hPa', r'\1 hectopascals'),
                (r'(\d+)\s*Pa', r'\1 pascals'),
                # Percentage
                (r'(\d+)\s*%', r'\1 percent'),
                # Time
                (r'(\d+)\s*h\b', r'\1 hours'),
                (r'(\d+)\s*min', r'\1 minutes'),
                (r'(\d+)\s*s\b', r'\1 seconds'),
                # Other symbols
                (r'&', ' and '),
                (r'\+', ' plus '),
                (r'=', ' equals '),
            ]

        # Apply all replacements
        result = text
        for pattern, replacement in replacements:
            result = re.sub(pattern, replacement, result)

        # Clean up multiple spaces
        result = re.sub(r'\s+', ' ', result).strip()

        if result != text:
            logger.debug(f"Text normalized: '{text[:50]}...' -> '{result[:50]}...'")

        return result

    # Backwards compatibility
    @property
    def model_name(self):
        return self.fast_model_name

    @property
    def _tts(self):
        return self._fast_tts

    @_tts.setter
    def _tts(self, value):
        self._fast_tts = value

    def _get_tts(self):
        """Lazy load fast TTS model (VITS).

        Returns:
            Initialized TTS model
        """
        if self._fast_tts is None:
            try:
                from TTS.api import TTS

                logger.info(f"Loading fast TTS model: {self.fast_model_name}")

                # Create models directory
                self._models_dir.mkdir(parents=True, exist_ok=True)

                # Initialize TTS with model
                self._fast_tts = TTS(self.fast_model_name, progress_bar=False)

                # Move to GPU if available and requested
                if self.use_gpu:
                    self._fast_tts.to("cuda")

                logger.info("Fast TTS model loaded successfully")

            except Exception as e:
                logger.error(f"Failed to load fast TTS model: {e}")
                raise

        return self._fast_tts

    def _get_slow_tts(self):
        """Lazy load slow TTS model (XTTS v2).

        Returns:
            Initialized TTS model or None if disabled
        """
        if not self.enable_xtts:
            return None

        if self._slow_tts is None:
            try:
                from TTS.api import TTS

                logger.info(f"Loading slow TTS model: {self.slow_model_name}")

                # Create models directory
                self._models_dir.mkdir(parents=True, exist_ok=True)

                # Initialize XTTS - requires speaker wav for voice cloning
                self._slow_tts = TTS(self.slow_model_name, progress_bar=False)

                # Move to GPU if available and requested
                if self.use_gpu:
                    self._slow_tts.to("cuda")

                logger.info("Slow TTS model (XTTS v2) loaded successfully")

            except Exception as e:
                logger.error(f"Failed to load slow TTS model: {e}")
                # Don't raise - fall back to fast model
                self.enable_xtts = False
                return None

        return self._slow_tts

    def _should_use_xtts(self, text: str) -> bool:
        """Determine if XTTS should be used based on text length.

        Args:
            text: Text to synthesize

        Returns:
            True if should use XTTS, False for VITS
        """
        if not self.enable_xtts:
            return False

        word_count = len(text.split())
        return word_count > self.short_threshold

    def synthesize(self, text: str, language: str = "pl") -> bytes:
        """Synthesize speech from text.

        Args:
            text: Text to convert to speech
            language: Language code ('pl' or 'en')

        Returns:
            Audio data as WAV bytes
        """
        try:
            tts = self._get_tts()

            # Normalize text for better pronunciation
            normalized_text = self._normalize_text_for_tts(text, language)

            # Generate to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            try:
                # Generate speech
                logger.info(f"Synthesizing: '{normalized_text[:50]}...' ({language})")
                tts.tts_to_file(text=normalized_text, file_path=tmp_path)

                # Read generated audio
                with open(tmp_path, "rb") as f:
                    wav_bytes = f.read()

                logger.info(f"TTS complete: {len(wav_bytes)} bytes")
                return wav_bytes

            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}", exc_info=True)
            raise

    def synthesize_to_file(self, text: str, output_path: str, language: str = "pl") -> str:
        """Synthesize speech and save to file.

        Args:
            text: Text to convert to speech
            output_path: Path to save WAV file
            language: Language code ('pl' or 'en')

        Returns:
            Path to saved file
        """
        try:
            tts = self._get_tts()

            logger.info(f"Synthesizing to file: {output_path}")
            tts.tts_to_file(text=text, file_path=output_path)

            logger.info(f"TTS saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"TTS synthesis to file failed: {e}", exc_info=True)
            raise

    def get_available_models(self) -> list:
        """Get list of available TTS models.

        Returns:
            List of model names
        """
        try:
            from TTS.api import TTS
            return TTS.list_models()
        except Exception as e:
            logger.error(f"Failed to get model list: {e}")
            return []

    def detect_language(self, text: str) -> str:
        """Detect language from text.

        Args:
            text: Text to analyze

        Returns:
            Language code ('pl' or 'en')
        """
        # Check for Polish diacritical characters
        polish_chars = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")
        if any(char in polish_chars for char in text):
            return "pl"
        return "en"

    def speak(self, text: str, language: str | None = None) -> bool:
        """Synthesize and play speech directly on Pi with smart routing.

        Uses VITS for short responses (fast) and XTTS for long responses (quality).

        Args:
            text: Text to speak
            language: Language code ('pl' or 'en'), auto-detected if None

        Returns:
            True if successful, False otherwise
        """
        try:
            # Auto-detect language if not specified
            if language is None:
                language = self.detect_language(text)

            # Determine which model to use
            use_xtts = self._should_use_xtts(text)
            word_count = len(text.split())

            if use_xtts:
                logger.info(f"Using XTTS v2 for long response ({word_count} words)")
                wav_bytes = self._synthesize_xtts(text, language)
            else:
                logger.info(f"Using VITS for short response ({word_count} words)")
                wav_bytes = self.synthesize(text, language)

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(wav_bytes)
                tmp_path = tmp_file.name

            try:
                # Play using aplay (ALSA) on specified output device
                model_type = "XTTS" if use_xtts else "VITS"
                logger.info(f"Playing {model_type} audio on {self.output_device}: {len(wav_bytes)} bytes")
                result = subprocess.run(
                    ["aplay", "-D", self.output_device, "-q", tmp_path],
                    capture_output=True,
                    timeout=120  # XTTS can generate longer audio
                )

                if result.returncode != 0:
                    logger.error(f"aplay failed: {result.stderr.decode()}")
                    return False

                logger.info("TTS playback complete")
                return True

            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except subprocess.TimeoutExpired:
            logger.error("TTS playback timed out")
            return False
        except Exception as e:
            logger.error(f"TTS speak failed: {e}", exc_info=True)
            return False

    def _synthesize_xtts(self, text: str, language: str = "pl") -> bytes:
        """Synthesize speech using XTTS v2.

        Args:
            text: Text to convert to speech
            language: Language code

        Returns:
            Audio data as WAV bytes
        """
        try:
            tts = self._get_slow_tts()
            if tts is None:
                # Fall back to fast model
                logger.warning("XTTS not available, falling back to VITS")
                return self.synthesize(text, language)

            # Normalize text for better pronunciation
            normalized_text = self._normalize_text_for_tts(text, language)

            # Generate to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            try:
                logger.info(f"XTTS synthesizing: '{normalized_text[:50]}...' ({language})")

                # XTTS requires speaker_wav for voice cloning
                # For now, use default speaker if available
                tts.tts_to_file(
                    text=normalized_text,
                    file_path=tmp_path,
                    language=language,
                )

                # Read generated audio
                with open(tmp_path, "rb") as f:
                    wav_bytes = f.read()

                logger.info(f"XTTS complete: {len(wav_bytes)} bytes")
                return wav_bytes

            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"XTTS synthesis failed: {e}", exc_info=True)
            # Fall back to fast model
            logger.warning("Falling back to VITS")
            return self.synthesize(text, language)

    def get_word_count(self, text: str) -> int:
        """Get word count for duration estimation.

        Args:
            text: Text to count words

        Returns:
            Number of words
        """
        return len(text.split())
