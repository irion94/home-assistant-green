"""Whisper transcription for local speech-to-text.

This module handles audio transcription using faster-whisper for
high-accuracy speech recognition, running in parallel with Vosk.
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
import wave
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Local Whisper transcription for wake-word service."""

    def __init__(self, model_size: str | None = None, device: str = "cpu"):
        """Initialize Whisper transcriber.

        Args:
            model_size: Whisper model size ('tiny', 'base', 'small').
                       Defaults to 'base' for good accuracy/speed balance.
            device: Device to run on ('cpu' or 'cuda')
        """
        self.model_size = model_size or os.getenv("WHISPER_MODEL_SIZE", "base")
        self.device = device
        self.compute_type = "int8" if device == "cpu" else "float16"
        self._model: WhisperModel | None = None

        # Model storage path
        self.model_path = Path("/app/models/whisper")
        self.model_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"WhisperTranscriber initialized: model={self.model_size}, "
            f"device={self.device}, compute_type={self.compute_type}"
        )

    def _get_model(self) -> WhisperModel:
        """Lazy load Whisper model.

        Returns:
            Initialized WhisperModel
        """
        if self._model is None:
            logger.info(f"Loading Whisper model '{self.model_size}'...")

            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=str(self.model_path)
            )

            logger.info("Whisper model loaded successfully")

        return self._model

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio data to text.

        Args:
            audio_data: Audio samples as numpy array (int16)
            sample_rate: Sample rate of audio

        Returns:
            Transcribed text
        """
        try:
            # Get model
            model = self._get_model()

            # Convert int16 to float32 for Whisper
            if audio_data.dtype == np.int16:
                audio_float = audio_data.astype(np.float32) / 32768.0
            else:
                audio_float = audio_data.astype(np.float32)

            # Transcribe - disable VAD since audio_capture already has VAD
            segments, info = model.transcribe(
                audio_float,
                language="pl",  # Polish
                task="transcribe",
                beam_size=5,
                vad_filter=False  # Disabled - audio_capture handles VAD
            )

            # Collect all segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            text = " ".join(text_parts).strip()

            logger.info(
                f"Whisper transcription complete: "
                f"text='{text[:50]}{'...' if len(text) > 50 else ''}', "
                f"length={len(text)}, "
                f"language={info.language}, "
                f"probability={info.language_probability:.2f}"
            )

            return text

        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}", exc_info=True)
            return ""

    def transcribe_with_timing(self, audio_data: np.ndarray, sample_rate: int = 16000) -> tuple[str, float]:
        """Transcribe audio and return timing info.

        Args:
            audio_data: Audio samples as numpy array (int16)
            sample_rate: Sample rate of audio

        Returns:
            Tuple of (transcribed text, duration in seconds)
        """
        import time
        start = time.time()
        text = self.transcribe(audio_data, sample_rate)
        duration = time.time() - start
        return text, duration
