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
