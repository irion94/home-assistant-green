"""Streaming Vosk transcription for real-time speech-to-text.

This module provides streaming STT capabilities, sending interim (partial)
results as audio is being captured, significantly reducing perceived latency.

Key differences from batch transcription:
- Processes audio chunks immediately as they arrive
- Emits partial results for real-time feedback
- Final result available after silence detection
- Confidence scoring for Whisper fallback decision
"""

from __future__ import annotations

import json
import logging
import os
from typing import Callable, Optional

import numpy as np
from vosk import Model, KaldiRecognizer, SetLogLevel

logger = logging.getLogger(__name__)

# Suppress Vosk logging
SetLogLevel(-1)


class StreamingTranscriber:
    """Real-time streaming transcription using Vosk.

    Processes audio chunks as they arrive, emitting partial results
    for immediate feedback in the UI.

    Usage:
        transcriber = StreamingTranscriber(model_path)

        for chunk in audio_chunks:
            partial, is_complete = transcriber.process_chunk(chunk)
            if partial:
                publish_interim(partial)

        final_text, confidence = transcriber.finalize()
    """

    def __init__(
        self,
        model_path: str,
        sample_rate: int = 16000,
        on_partial: Optional[Callable[[str, int], None]] = None
    ):
        """Initialize streaming transcriber.

        Args:
            model_path: Path to Vosk model directory
            sample_rate: Audio sample rate (must match model)
            on_partial: Optional callback invoked on each partial result
                        Signature: on_partial(text: str, sequence: int)
        """
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.on_partial = on_partial

        self._model: Optional[Model] = None
        self._recognizer: Optional[KaldiRecognizer] = None
        self._sequence = 0
        self._last_partial = ""
        self._accumulated_text = []

        logger.info(f"StreamingTranscriber initialized: model={model_path}, rate={sample_rate}")

    def _get_model(self) -> Model:
        """Lazy load Vosk model."""
        if self._model is None:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Vosk model not found: {self.model_path}")

            logger.info(f"Loading Vosk model from {self.model_path}")
            self._model = Model(self.model_path)
            logger.info("Vosk model loaded successfully")

        return self._model

    def _get_recognizer(self) -> KaldiRecognizer:
        """Get or create KaldiRecognizer."""
        if self._recognizer is None:
            model = self._get_model()
            self._recognizer = KaldiRecognizer(model, self.sample_rate)
            self._recognizer.SetWords(True)  # Enable word-level confidence
            logger.debug("Created new KaldiRecognizer")

        return self._recognizer

    def process_chunk(self, audio_chunk: np.ndarray) -> tuple[str, bool]:
        """Process a single audio chunk.

        Args:
            audio_chunk: Audio samples as numpy array (int16)

        Returns:
            Tuple of (text, is_utterance_complete):
            - text: Current partial/complete transcription
            - is_utterance_complete: True if Vosk detected end of utterance
        """
        recognizer = self._get_recognizer()

        # Convert to bytes (Vosk expects raw bytes)
        audio_bytes = audio_chunk.tobytes()

        # Process audio
        if recognizer.AcceptWaveform(audio_bytes):
            # Utterance complete - Vosk detected natural pause
            result = json.loads(recognizer.Result())
            text = result.get('text', '').strip()

            if text:
                self._accumulated_text.append(text)
                logger.debug(f"Utterance complete: '{text}'")

            # Reset partial tracking for next utterance
            self._last_partial = ""

            return text, True
        else:
            # Partial result - speech in progress
            partial_result = json.loads(recognizer.PartialResult())
            partial = partial_result.get('partial', '').strip()

            # Only emit if changed and non-empty
            if partial and partial != self._last_partial:
                self._sequence += 1
                self._last_partial = partial

                # Invoke callback if provided
                if self.on_partial:
                    try:
                        self.on_partial(partial, self._sequence)
                    except Exception as e:
                        logger.error(f"on_partial callback error: {e}")

                logger.debug(f"Partial [{self._sequence}]: '{partial}'")

            return partial, False

    def finalize(self) -> tuple[str, float]:
        """Finalize transcription and get confidence score.

        Call this after all audio has been processed (VAD detected silence).

        Returns:
            Tuple of (final_text, confidence):
            - final_text: Complete transcription
            - confidence: Word-averaged confidence (0.0-1.0)
        """
        recognizer = self._get_recognizer()

        # Get final result
        final_result = json.loads(recognizer.FinalResult())
        final_text = final_result.get('text', '').strip()

        if final_text:
            self._accumulated_text.append(final_text)

        # Combine all accumulated text
        full_text = ' '.join(self._accumulated_text).strip()

        # Calculate confidence from word-level scores
        confidence = self._calculate_confidence(final_result)

        logger.info(
            f"Finalized transcription: text='{full_text[:50]}{'...' if len(full_text) > 50 else ''}', "
            f"confidence={confidence:.2f}, sequences={self._sequence}"
        )

        return full_text, confidence

    def _calculate_confidence(self, result: dict) -> float:
        """Calculate average confidence from word-level scores.

        Args:
            result: Vosk result dict containing 'result' array with word data

        Returns:
            Average confidence (0.0-1.0), defaults to 0.85 if no word data
        """
        words = result.get('result', [])

        if not words:
            # No word-level data, assume medium-high confidence
            return 0.85

        # Average confidence across all words
        confidences = [w.get('conf', 0.85) for w in words]
        avg_confidence = sum(confidences) / len(confidences)

        return avg_confidence

    def reset(self) -> None:
        """Reset transcriber state for new session.

        Call this before starting a new transcription session.
        """
        self._recognizer = None
        self._sequence = 0
        self._last_partial = ""
        self._accumulated_text = []
        logger.debug("StreamingTranscriber reset")

    @property
    def sequence(self) -> int:
        """Current sequence number (increments with each unique partial)."""
        return self._sequence

    @property
    def last_partial(self) -> str:
        """Most recent partial result."""
        return self._last_partial


class StreamingSTTResult:
    """Container for streaming STT results."""

    def __init__(
        self,
        text: str,
        confidence: float,
        engine: str = "vosk",
        sequence_count: int = 0
    ):
        self.text = text
        self.confidence = confidence
        self.engine = engine
        self.sequence_count = sequence_count

    def __repr__(self) -> str:
        return (
            f"StreamingSTTResult(text='{self.text[:30]}...', "
            f"confidence={self.confidence:.2f}, engine={self.engine})"
        )
