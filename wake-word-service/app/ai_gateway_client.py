"""
AI Gateway Client
HTTP client for communicating with AI Gateway service
"""

import os
import logging
import io
import wave
import numpy as np
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AIGatewayClient:
    """Client for AI Gateway API"""

    def __init__(self, base_url: str = "http://host.docker.internal:8080"):
        """
        Initialize AI Gateway client

        Args:
            base_url: Base URL of AI Gateway service
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = int(os.getenv("REQUEST_TIMEOUT", "120"))  # 120s for Whisper + Ollama

        logger.info(f"AI Gateway client initialized: {self.base_url}")

    def process_voice_command(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000
    ) -> Optional[Dict[str, Any]]:
        """
        Send voice command to AI Gateway for processing

        Args:
            audio_data: Audio data as numpy array (mono, int16)
            sample_rate: Sample rate in Hz

        Returns:
            Response dict or None on error
        """
        try:
            # Convert numpy array to WAV bytes
            wav_bytes = self._audio_to_wav_bytes(audio_data, sample_rate)

            # Send audio to /voice endpoint for transcription and processing
            logger.info(f"Sending audio to AI Gateway /voice endpoint ({len(wav_bytes)} bytes)")

            response = self._send_voice_command(wav_bytes)

            return response

        except Exception as e:
            logger.error(f"Error processing voice command: {e}")
            return None

    def _send_voice_command(self, wav_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Send audio file to AI Gateway /voice endpoint

        Args:
            wav_bytes: Audio data in WAV format

        Returns:
            Response dict or None on error
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/voice",
                    files={"audio": ("command.wav", wav_bytes, "audio/wav")}
                )

                response.raise_for_status()
                result = response.json()

                logger.info(f"AI Gateway response: status={result.get('status')}, "
                           f"message={result.get('message')}")

                return result

        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error sending voice command: {e}")
            return None

    def _send_text_command(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Send text command to AI Gateway /ask endpoint

        Args:
            text: Command text

        Returns:
            Response dict or None on error
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/ask",
                    json={"text": text},
                    headers={"Content-Type": "application/json"}
                )

                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return None

    def send_conversation_voice(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        session_id: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """
        Send voice to conversation endpoint

        Args:
            audio_data: Audio data as numpy array (mono, int16)
            sample_rate: Sample rate in Hz
            session_id: Conversation session ID

        Returns:
            Response dict or None on error
        """
        try:
            wav_bytes = self._audio_to_wav_bytes(audio_data, sample_rate)

            logger.info(f"Sending conversation voice ({len(wav_bytes)} bytes, session={session_id})")

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/conversation/voice",
                    files={"audio": ("conversation.wav", wav_bytes, "audio/wav")},
                    params={"session_id": session_id}
                )

                response.raise_for_status()
                result = response.json()

                logger.info(f"Conversation response: status={result.get('status')}")
                return result

        except httpx.HTTPError as e:
            logger.error(f"HTTP error in conversation: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in conversation: {e}")
            return None

    def end_conversation(self, session_id: str = "default") -> Optional[Dict[str, Any]]:
        """
        End conversation session

        Args:
            session_id: Conversation session ID

        Returns:
            Response dict or None on error
        """
        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(
                    f"{self.base_url}/conversation",
                    json={
                        "text": "",
                        "session_id": session_id,
                        "end_session": True
                    },
                    headers={"Content-Type": "application/json"}
                )

                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error ending conversation: {e}")
            return None

    def _audio_to_wav_bytes(self, audio_data: np.ndarray, sample_rate: int) -> bytes:
        """
        Convert numpy audio array to WAV file bytes

        Args:
            audio_data: Audio data (mono, int16)
            sample_rate: Sample rate in Hz

        Returns:
            WAV file as bytes
        """
        wav_buffer = io.BytesIO()

        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        return wav_buffer.getvalue()

    def health_check(self) -> bool:
        """
        Check if AI Gateway is accessible

        Returns:
            True if healthy, False otherwise
        """
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/health")
                response.raise_for_status()

                data = response.json()
                return data.get("status") == "healthy"

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def stop_media(self) -> bool:
        """
        Stop media playback on Nest Hub

        Returns:
            True if successful, False otherwise
        """
        try:
            with httpx.Client(timeout=5) as client:
                response = client.post(
                    f"{self.base_url}/ask",
                    json={"text": "stop media player living room display"},
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                logger.info("Stopped media playback")
                return True

        except Exception as e:
            logger.error(f"Failed to stop media: {e}")
            return False
