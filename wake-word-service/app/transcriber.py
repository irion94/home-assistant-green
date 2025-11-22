"""Vosk transcription for local speech-to-text.

This module handles audio transcription using Vosk directly in the
wake-word service for lower latency.
"""

from __future__ import annotations

import io
import json
import logging
import os
import tempfile
import wave
import zipfile
from pathlib import Path

import httpx
import numpy as np
from vosk import Model, KaldiRecognizer, SetLogLevel

logger = logging.getLogger(__name__)

# Suppress Vosk logging
SetLogLevel(-1)

# Polish model URL (only Polish model available)
VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-pl-0.22.zip"
VOSK_MODEL_NAME = "vosk-model-small-pl-0.22"


class Transcriber:
    """Local Vosk transcription for wake-word service."""

    def __init__(self, model_path: str | None = None):
        """Initialize transcriber.

        Args:
            model_path: Path to Vosk model directory. If None, downloads default Polish model.
        """
        self.model_path = model_path or self._get_default_model_path()
        self._model: Model | None = None

        logger.info(f"Transcriber initialized with model_path={self.model_path}")

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

            # Create WAV in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data.tobytes())

            wav_buffer.seek(0)

            # Read back and transcribe
            with wave.open(wav_buffer, "rb") as wf:
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
                    f"Transcription complete: "
                    f"text='{text[:50]}{'...' if len(text) > 50 else ''}', "
                    f"length={len(text)}"
                )

                return text

        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            return ""
