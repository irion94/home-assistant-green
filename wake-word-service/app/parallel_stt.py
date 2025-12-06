"""Parallel STT using Vosk and Whisper.

This module runs both STT engines in parallel and compares/merges
results to get the best transcription.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass

import numpy as np

from transcriber import Transcriber
from whisper_transcriber import WhisperTranscriber

logger = logging.getLogger(__name__)


@dataclass
class STTResult:
    """Result from a single STT engine."""
    text: str
    engine: str
    duration: float
    confidence: float = 0.0


@dataclass
class ParallelSTTResult:
    """Combined result from parallel STT."""
    vosk: STTResult
    whisper: STTResult
    selected: STTResult
    selection_reason: str


class ParallelSTT:
    """Run Vosk and Whisper in parallel for comparison."""

    def __init__(self, vosk_model_path: str | None = None, whisper_model_size: str = "base"):
        """Initialize parallel STT.

        Args:
            vosk_model_path: Path to Vosk model directory
            whisper_model_size: Whisper model size ('tiny', 'base', 'small')
        """
        self.vosk = Transcriber(model_path=vosk_model_path)

        # Only initialize Whisper if USE_WHISPER=true (saves ~2GB RAM)
        use_whisper = os.getenv("USE_WHISPER", "false").lower() == "true"
        if use_whisper:
            self.whisper = WhisperTranscriber(model_size=whisper_model_size)
            logger.info("ParallelSTT initialized with Vosk and Whisper")
        else:
            self.whisper = None
            logger.info("ParallelSTT initialized with Vosk only (Whisper disabled)")

        self.executor = ThreadPoolExecutor(max_workers=2)

    def _transcribe_vosk(self, audio_data: np.ndarray, sample_rate: int) -> STTResult:
        """Run Vosk transcription with timing."""
        start = time.time()
        text = self.vosk.transcribe(audio_data, sample_rate)
        duration = time.time() - start

        return STTResult(
            text=text,
            engine="vosk",
            duration=duration
        )

    def _transcribe_whisper(self, audio_data: np.ndarray, sample_rate: int) -> STTResult:
        """Run Whisper transcription with timing."""
        if self.whisper is None:
            # Whisper disabled - return empty result
            return STTResult(
                text="",
                confidence=0.0,
                duration=0.0,
                engine="whisper"
            )

        start = time.time()
        text = self.whisper.transcribe(audio_data, sample_rate)
        duration = time.time() - start

        return STTResult(
            text=text,
            engine="whisper",
            duration=duration
        )

    def transcribe_parallel(self, audio_data: np.ndarray, sample_rate: int = 16000) -> ParallelSTTResult:
        """Run both STT engines in parallel and select best result.

        Args:
            audio_data: Audio samples as numpy array (int16)
            sample_rate: Sample rate of audio

        Returns:
            ParallelSTTResult with both results and selection
        """
        # Check if Whisper is disabled (for performance on edge devices)
        use_whisper = os.getenv("USE_WHISPER", "false").lower() == "true"

        if use_whisper:
            logger.info("Starting parallel transcription (Vosk + Whisper with timeout)")

            # Get timeout from environment (default 6 seconds)
            whisper_timeout = float(os.getenv("WHISPER_TIMEOUT", "6.0"))

            # Submit both tasks to executor
            vosk_future = self.executor.submit(self._transcribe_vosk, audio_data, sample_rate)
            whisper_future = self.executor.submit(self._transcribe_whisper, audio_data, sample_rate)

            # Wait for Vosk first (always fast)
            vosk_result = vosk_future.result()
            logger.info(f"Vosk completed: '{vosk_result.text[:50]}...' ({vosk_result.duration:.2f}s)")

            # Wait for Whisper with timeout
            whisper_start = time.time()
            done, pending = wait([whisper_future], timeout=whisper_timeout)

            if whisper_future in done:
                # Whisper completed within timeout
                whisper_result = whisper_future.result()
                logger.info(f"Whisper completed: '{whisper_result.text[:50]}...' ({whisper_result.duration:.2f}s)")
            else:
                # Whisper timed out - use Vosk result
                elapsed = time.time() - whisper_start
                logger.warning(f"Whisper timeout after {elapsed:.1f}s, using Vosk result")
                # Create dummy result to indicate timeout
                whisper_result = STTResult(
                    text="",
                    confidence=0.0,
                    duration=elapsed,
                    engine="whisper"
                )
                # Note: whisper_future will continue running in background and complete later
        else:
            # Vosk-only mode (faster, more reliable on edge devices)
            logger.info("Starting transcription (Vosk only)")
            vosk_result = self._transcribe_vosk(audio_data, sample_rate)
            # Create dummy Whisper result
            whisper_result = STTResult(
                text="",
                confidence=0.0,
                duration=0.0,
                engine="whisper"
            )

        # Select best result
        selected, reason = self._select_best(vosk_result, whisper_result)

        logger.info(f"Selected: {selected.engine} - {reason}")

        return ParallelSTTResult(
            vosk=vosk_result,
            whisper=whisper_result,
            selected=selected,
            selection_reason=reason
        )

    def _select_best(self, vosk: STTResult, whisper: STTResult) -> tuple[STTResult, str]:
        """Select the best transcription result.

        Selection criteria:
        1. If one is empty, use the other
        2. If similar, prefer Whisper (more accurate)
        3. If very different lengths, prefer longer (more content)

        Args:
            vosk: Vosk transcription result
            whisper: Whisper transcription result

        Returns:
            Tuple of (selected result, reason)
        """
        vosk_len = len(vosk.text.strip())
        whisper_len = len(whisper.text.strip())

        # Handle empty results
        if vosk_len == 0 and whisper_len == 0:
            return vosk, "both empty"

        if vosk_len == 0:
            return whisper, "vosk empty"

        if whisper_len == 0:
            return vosk, "whisper empty"

        # Check speed difference - prefer faster engine if one is much slower
        # This prevents 30+ second Whisper delays
        speed_ratio = whisper.duration / vosk.duration if vosk.duration > 0 else 1.0

        # If Whisper is >3x slower than Vosk, use Vosk (e.g., 34s vs 2s)
        if speed_ratio > 3.0 and vosk_len > 0:
            return vosk, f"whisper too slow ({whisper.duration:.1f}s vs {vosk.duration:.1f}s)"

        # If Vosk is >3x slower than Whisper, use Whisper
        if speed_ratio < 0.33 and whisper_len > 0:
            return whisper, f"vosk too slow ({vosk.duration:.1f}s vs {whisper.duration:.1f}s)"

        # Compare lengths
        length_ratio = min(vosk_len, whisper_len) / max(vosk_len, whisper_len)

        # If similar length (within 30%), prefer Whisper for accuracy
        if length_ratio > 0.7:
            return whisper, "similar length, prefer accuracy"

        # If very different, prefer longer (more content captured)
        if vosk_len > whisper_len:
            return vosk, f"vosk longer ({vosk_len} vs {whisper_len})"
        else:
            return whisper, f"whisper longer ({whisper_len} vs {vosk_len})"

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio using parallel STT, returning best result.

        This is the simple interface matching Vosk transcriber.

        Args:
            audio_data: Audio samples as numpy array (int16)
            sample_rate: Sample rate of audio

        Returns:
            Best transcribed text
        """
        result = self.transcribe_parallel(audio_data, sample_rate)
        return result.selected.text

    def shutdown(self):
        """Clean shutdown of executor."""
        self.executor.shutdown(wait=True)
        logger.info("ParallelSTT executor shut down")
