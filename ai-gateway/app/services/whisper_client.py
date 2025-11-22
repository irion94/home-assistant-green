"""Whisper transcription service using faster-whisper.

This module handles audio transcription for voice commands using the
faster-whisper library optimized for CPU inference.
"""

from __future__ import annotations

import logging
import math
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

from app.services.stt_client import STTClient

logger = logging.getLogger(__name__)


class WhisperSTTClient(STTClient):
    """Client for Whisper audio transcription."""

    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        """Initialize Whisper client.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            device: Device to run on (cpu, cuda)
            compute_type: Computation type (int8, float16, float32)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: WhisperModel | None = None

        logger.info(
            f"WhisperClient initialized with model={model_size}, "
            f"device={device}, compute_type={compute_type}"
        )

    def _get_model(self) -> WhisperModel:
        """Lazy load Whisper model.

        Returns:
            Initialized WhisperModel
        """
        if self._model is None:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("Whisper model loaded successfully")
        return self._model

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes to text.

        Args:
            audio_bytes: Audio data in WAV format

        Returns:
            Transcribed text

        Raises:
            Exception: If transcription fails
        """
        try:
            # Write audio to temporary file (faster-whisper needs file path)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = Path(tmp_file.name)

            try:
                # Get model (lazy loading)
                model = self._get_model()

                # Transcribe with initial prompt for better Polish recognition
                # The initial prompt provides vocabulary hints to improve accuracy
                initial_prompt = (
                    "Zapal światło w salonie. Zgaś światło w kuchni. "
                    "Zapal lampkę. Zgaś lampę. Włącz światło w sypialni. "
                    "Wyłącz światło. Powiedz cześć. Ustaw jasność."
                )

                segments, info = model.transcribe(
                    str(tmp_path),
                    beam_size=5,
                    language="pl",  # Polish language for transcription
                    vad_filter=True,  # Filter out silence
                    initial_prompt=initial_prompt,  # Vocabulary hints
                )

                # Combine all segments
                text = " ".join(segment.text.strip() for segment in segments)

                logger.info(
                    f"Transcription complete: language={info.language}, "
                    f"probability={info.language_probability:.2f}, "
                    f"text_length={len(text)}"
                )

                return text

            finally:
                # Clean up temporary file
                tmp_path.unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            raise

    async def transcribe_with_confidence(self, audio_bytes: bytes) -> tuple[str, float]:
        """Transcribe audio and return confidence score.

        Args:
            audio_bytes: Audio data in WAV format

        Returns:
            Tuple of (transcribed text, confidence 0.0-1.0)
        """
        try:
            # Write audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = Path(tmp_file.name)

            try:
                # Get model
                model = self._get_model()

                # Transcribe with initial prompt
                initial_prompt = (
                    "Zapal światło w salonie. Zgaś światło w kuchni. "
                    "Zapal lampkę. Zgaś lampę. Włącz światło w sypialni."
                )

                segments, info = model.transcribe(
                    str(tmp_path),
                    beam_size=5,
                    language="pl",
                    vad_filter=True,
                    initial_prompt=initial_prompt,
                )

                # Collect segments and their confidences
                segment_list = list(segments)
                texts = []
                confidences = []

                for segment in segment_list:
                    texts.append(segment.text.strip())
                    # Convert log probability to probability
                    # avg_logprob is typically negative, closer to 0 = higher confidence
                    prob = math.exp(segment.avg_logprob)
                    confidences.append(prob)

                text = " ".join(texts)

                # Calculate weighted average confidence
                if confidences:
                    confidence = sum(confidences) / len(confidences)
                    # Normalize - Whisper probs are often low, scale up
                    confidence = min(1.0, confidence * 2)  # Scale factor
                else:
                    confidence = info.language_probability if text else 0.0

                logger.info(
                    f"Whisper transcription complete: "
                    f"text_length={len(text)}, "
                    f"confidence={confidence:.2f}, "
                    f"segments={len(segment_list)}"
                )

                return (text, confidence)

            finally:
                tmp_path.unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}", exc_info=True)
            return ("", 0.0)


# Keep old alias for backwards compatibility
WhisperClient = WhisperSTTClient
