"""Vosk transcription service for fast speech-to-text.

This module handles audio transcription using Vosk, which is optimized
for fast CPU inference with good accuracy for Polish.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import wave
import zipfile
from pathlib import Path

import httpx
from vosk import Model, KaldiRecognizer, SetLogLevel

from app.services.stt_client import STTClient

logger = logging.getLogger(__name__)

# Suppress Vosk logging
SetLogLevel(-1)

# Polish model URL (small model for speed)
VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-pl-0.22.zip"
VOSK_MODEL_NAME = "vosk-model-small-pl-0.22"


class VoskSTTClient(STTClient):
    """Client for Vosk audio transcription."""

    def __init__(self, model_path: str | None = None):
        """Initialize Vosk client.

        Args:
            model_path: Path to Vosk model directory. If None, downloads default Polish model.
        """
        self.model_path = model_path or self._get_default_model_path()
        self._model: Model | None = None

        logger.info(f"VoskSTTClient initialized with model_path={self.model_path}")

    def _get_default_model_path(self) -> str:
        """Get default model path, downloading if necessary."""
        # Default to /app/models/vosk in container
        models_dir = Path("/app/models/vosk")
        if not models_dir.exists():
            # Fallback to temp directory
            models_dir = Path(tempfile.gettempdir()) / "vosk_models"

        model_dir = models_dir / VOSK_MODEL_NAME

        if not model_dir.exists():
            self._download_model(models_dir)

        return str(model_dir)

    def _download_model(self, models_dir: Path) -> None:
        """Download and extract Vosk Polish model.

        Args:
            models_dir: Directory to store models
        """
        logger.info(f"Downloading Vosk Polish model to {models_dir}")

        models_dir.mkdir(parents=True, exist_ok=True)
        zip_path = models_dir / f"{VOSK_MODEL_NAME}.zip"

        # Download model
        with httpx.Client(timeout=300.0) as client:
            response = client.get(VOSK_MODEL_URL, follow_redirects=True)
            response.raise_for_status()

            with open(zip_path, "wb") as f:
                f.write(response.content)

        logger.info(f"Downloaded model ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")

        # Extract model
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(models_dir)

        # Clean up zip
        zip_path.unlink()

        logger.info(f"Extracted model to {models_dir / VOSK_MODEL_NAME}")

    def _get_model(self) -> Model:
        """Lazy load Vosk model.

        Returns:
            Initialized Vosk Model
        """
        if self._model is None:
            logger.info(f"Loading Vosk model from {self.model_path}")

            if not os.path.exists(self.model_path):
                # Try to download
                models_dir = Path(self.model_path).parent
                self._download_model(models_dir)

            self._model = Model(self.model_path)
            logger.info("Vosk model loaded successfully")

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
            # Write to temp file to read with wave module
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = Path(tmp_file.name)

            try:
                # Get model
                model = self._get_model()

                # Read WAV file
                with wave.open(str(tmp_path), "rb") as wf:
                    if wf.getnchannels() != 1:
                        raise ValueError("Audio must be mono")

                    sample_rate = wf.getframerate()

                    # Create recognizer
                    rec = KaldiRecognizer(model, sample_rate)
                    rec.SetWords(True)

                    # Process audio in chunks
                    results = []
                    while True:
                        data = wf.readframes(4000)
                        if len(data) == 0:
                            break
                        if rec.AcceptWaveform(data):
                            result = json.loads(rec.Result())
                            if result.get("text"):
                                results.append(result["text"])

                    # Get final result
                    final_result = json.loads(rec.FinalResult())
                    if final_result.get("text"):
                        results.append(final_result["text"])

                    text = " ".join(results).strip()

                    logger.info(
                        f"Vosk transcription complete: "
                        f"text_length={len(text)}, "
                        f"sample_rate={sample_rate}"
                    )

                    return text

            finally:
                # Clean up
                tmp_path.unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Vosk transcription failed: {e}", exc_info=True)
            raise

    async def transcribe_with_confidence(self, audio_bytes: bytes) -> tuple[str, float]:
        """Transcribe audio and return confidence score.

        Args:
            audio_bytes: Audio data in WAV format

        Returns:
            Tuple of (transcribed text, confidence 0.0-1.0)
        """
        try:
            # Write to temp file to read with wave module
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = Path(tmp_file.name)

            try:
                # Get model
                model = self._get_model()

                # Read WAV file
                with wave.open(str(tmp_path), "rb") as wf:
                    if wf.getnchannels() != 1:
                        raise ValueError("Audio must be mono")

                    sample_rate = wf.getframerate()

                    # Create recognizer with word confidence
                    rec = KaldiRecognizer(model, sample_rate)
                    rec.SetWords(True)

                    # Process audio in chunks
                    results = []
                    all_confidences = []

                    while True:
                        data = wf.readframes(4000)
                        if len(data) == 0:
                            break
                        if rec.AcceptWaveform(data):
                            result = json.loads(rec.Result())
                            if result.get("text"):
                                results.append(result["text"])
                            # Extract word confidences
                            for word_info in result.get("result", []):
                                if "conf" in word_info:
                                    all_confidences.append(word_info["conf"])

                    # Get final result
                    final_result = json.loads(rec.FinalResult())
                    if final_result.get("text"):
                        results.append(final_result["text"])
                    # Extract final word confidences
                    for word_info in final_result.get("result", []):
                        if "conf" in word_info:
                            all_confidences.append(word_info["conf"])

                    text = " ".join(results).strip()

                    # Calculate average confidence
                    if all_confidences:
                        confidence = sum(all_confidences) / len(all_confidences)
                    else:
                        confidence = 0.7 if text else 0.0  # Default if no word scores

                    logger.info(
                        f"Vosk transcription complete: "
                        f"text_length={len(text)}, "
                        f"confidence={confidence:.2f}, "
                        f"words={len(all_confidences)}"
                    )

                    return (text, confidence)

            finally:
                # Clean up
                tmp_path.unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"Vosk transcription failed: {e}", exc_info=True)
            return ("", 0.0)
