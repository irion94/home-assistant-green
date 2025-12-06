"""Abstract STT client and factory for multi-provider support.

This module provides an abstraction layer for STT providers (Whisper, Vosk)
allowing switching between them via environment configuration.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Config

logger = logging.getLogger(__name__)


class STTClient(ABC):
    """Abstract base class for STT clients."""

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes to text.

        Args:
            audio_bytes: Audio data in WAV format

        Returns:
            Transcribed text

        Raises:
            Exception: If transcription fails
        """
        pass

    async def transcribe_with_confidence(self, audio_bytes: bytes) -> tuple[str, float]:
        """Transcribe audio and return confidence score.

        Args:
            audio_bytes: Audio data in WAV format

        Returns:
            Tuple of (transcribed text, confidence 0.0-1.0)
        """
        # Default implementation - subclasses can override
        text = await self.transcribe(audio_bytes)
        return (text, 0.7 if text else 0.0)


def get_stt_client(config: Config) -> STTClient:
    """Factory function to get appropriate STT client based on configuration.

    Args:
        config: Application configuration

    Returns:
        STTClient instance (WhisperClient or VoskClient)

    Raises:
        ValueError: If unknown provider specified
    """
    provider = config.stt_provider.lower()

    if provider == "whisper":
        from app.services.whisper_client import WhisperSTTClient
        logger.info("Using Whisper STT provider")
        return WhisperSTTClient(
            model_size=config.whisper_model,
            device="cpu",
            compute_type="int8",
        )

    elif provider == "vosk":
        from app.services.vosk_client import VoskSTTClient
        logger.info("Using Vosk STT provider")
        return VoskSTTClient(model_path=config.vosk_model_path)

    else:
        raise ValueError(f"Unknown STT provider: {provider}. Supported: whisper, vosk")


def get_stt_pipeline(config: Config):
    """Factory function to get STT pipeline with Vosk -> Whisper fallback.

    Args:
        config: Application configuration

    Returns:
        STTPipeline instance
    """
    from app.services.pipeline import STTPipeline
    from app.services.vosk_client import VoskSTTClient
    from app.services.whisper_client import WhisperSTTClient

    logger.info(
        f"Creating STT pipeline (Vosk -> Whisper, confidence threshold: "
        f"{config.stt_confidence_threshold})"
    )

    vosk_client = VoskSTTClient(model_path=config.vosk_model_path)
    whisper_client = WhisperSTTClient(
        model_size=config.whisper_model,
        device="cpu",
        compute_type="int8",
    )

    return STTPipeline(
        vosk_client=vosk_client,
        whisper_client=whisper_client,
        confidence_threshold=config.stt_confidence_threshold,
    )
