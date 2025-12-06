"""STT pipeline executor for cascading speech-to-text.

Runs fast STT (Vosk) first, falls back to accurate STT (Whisper) if confidence low.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.stt_client import STTClient

logger = logging.getLogger(__name__)


@dataclass
class STTResult:
    """Result from STT with confidence score."""

    text: str
    confidence: float  # 0.0 to 1.0
    source: str  # "vosk" or "whisper"
    latency_ms: float


class STTPipeline:
    """Cascading STT pipeline.

    Runs Vosk (fast) first, falls back to Whisper (accurate) if confidence too low.
    """

    def __init__(
        self,
        vosk_client: STTClient,
        whisper_client: STTClient,
        confidence_threshold: float = 0.7,
    ):
        """Initialize STT pipeline.

        Args:
            vosk_client: Fast Vosk STT client
            whisper_client: Accurate Whisper STT client
            confidence_threshold: Minimum confidence to accept Vosk result
        """
        self.vosk_client = vosk_client
        self.whisper_client = whisper_client
        self.confidence_threshold = confidence_threshold

    async def transcribe(self, audio_bytes: bytes) -> STTResult:
        """Transcribe audio through pipeline.

        Tries Vosk first, falls back to Whisper if confidence is low.

        Args:
            audio_bytes: Audio data in WAV format

        Returns:
            STTResult with text and confidence
        """
        # Run Vosk first (fast)
        vosk_result = await self._run_vosk(audio_bytes)

        # If Vosk is confident enough, use it
        if vosk_result.text and vosk_result.confidence >= self.confidence_threshold:
            logger.info(
                f"STT Pipeline: Vosk accepted "
                f"(confidence={vosk_result.confidence:.2f}, latency={vosk_result.latency_ms:.0f}ms)"
            )
            return vosk_result

        # Otherwise, run Whisper
        logger.info(
            f"STT Pipeline: Vosk confidence too low ({vosk_result.confidence:.2f}), "
            f"running Whisper fallback"
        )
        whisper_result = await self._run_whisper(audio_bytes)

        # Compare results
        if whisper_result.text and whisper_result.confidence > vosk_result.confidence:
            logger.info(
                f"STT Pipeline: Whisper result used "
                f"(confidence={whisper_result.confidence:.2f}, latency={whisper_result.latency_ms:.0f}ms)"
            )
            return whisper_result

        # Return Vosk if Whisper didn't improve
        if vosk_result.text:
            logger.info(
                f"STT Pipeline: Using Vosk result (Whisper didn't improve) "
                f"(confidence={vosk_result.confidence:.2f})"
            )
            return vosk_result

        # Return whatever we got from Whisper
        return whisper_result

    async def _run_vosk(self, audio_bytes: bytes) -> STTResult:
        """Run Vosk transcription.

        Args:
            audio_bytes: Audio data

        Returns:
            STTResult from Vosk
        """
        start = time.perf_counter()

        try:
            text, confidence = await self.vosk_client.transcribe_with_confidence(audio_bytes)
            latency = (time.perf_counter() - start) * 1000

            return STTResult(
                text=text,
                confidence=confidence,
                source="vosk",
                latency_ms=latency,
            )
        except Exception as e:
            logger.error(f"Vosk error: {e}")
            latency = (time.perf_counter() - start) * 1000
            return STTResult(
                text="",
                confidence=0.0,
                source="vosk",
                latency_ms=latency,
            )

    async def _run_whisper(self, audio_bytes: bytes) -> STTResult:
        """Run Whisper transcription.

        Args:
            audio_bytes: Audio data

        Returns:
            STTResult from Whisper
        """
        start = time.perf_counter()

        try:
            text, confidence = await self.whisper_client.transcribe_with_confidence(audio_bytes)
            latency = (time.perf_counter() - start) * 1000

            return STTResult(
                text=text,
                confidence=confidence,
                source="whisper",
                latency_ms=latency,
            )
        except Exception as e:
            logger.error(f"Whisper error: {e}")
            latency = (time.perf_counter() - start) * 1000
            return STTResult(
                text="",
                confidence=0.0,
                source="whisper",
                latency_ms=latency,
            )
