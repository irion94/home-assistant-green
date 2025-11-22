"""Ollama LLM client for natural language to Home Assistant plan translation.

This module handles communication with Ollama for command translation.
"""

from __future__ import annotations

import logging

import httpx

from app.models import Config, HAAction, OllamaRequest
from app.services.llm_client import LLMClient, SYSTEM_PROMPT
from app.utils.json_validator import parse_ollama_response, parse_ollama_response_with_confidence

logger = logging.getLogger(__name__)


class OllamaClient(LLMClient):
    """Client for Ollama LLM API."""

    def __init__(self, config: Config) -> None:
        """Initialize Ollama client.

        Args:
            config: Application configuration
        """
        self.base_url = config.ollama_base_url
        self.model = config.ollama_model
        self.timeout = 90.0  # 90 second timeout for LLM requests (RPi5 can be slow)

    async def translate_command(self, command: str) -> HAAction | None:
        """Translate natural language command to Home Assistant action plan.

        Args:
            command: Natural language command from user

        Returns:
            Validated HAAction plan, or None if translation fails
        """
        logger.info(f"Translating command: {command}")

        try:
            # Build Ollama request
            request = OllamaRequest(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": command},
                ],
                stream=False,
                format="json",
            )

            # Call Ollama API
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=request.model_dump(),
                )
                response.raise_for_status()

            # Parse response
            data = response.json()
            logger.debug(f"Ollama response: {data}")

            # Extract message content
            if "choices" not in data or not data["choices"]:
                logger.error("No choices in Ollama response")
                return None

            message_content = data["choices"][0]["message"]["content"]
            logger.debug(f"Message content: {message_content}")

            # Validate and parse JSON
            action = parse_ollama_response(message_content)

            if action:
                logger.info(f"Successfully translated to action: {action.action}")
            else:
                logger.warning("Failed to parse valid action from Ollama response")

            return action

        except httpx.TimeoutException:
            logger.error(f"Timeout calling Ollama (>{self.timeout}s) - model may be loading")
            return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling Ollama: {type(e).__name__}: {e}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error in translate_command: {e}")
            return None

    async def translate_command_with_confidence(self, command: str) -> tuple[HAAction | None, float]:
        """Translate command and return confidence score.

        Args:
            command: Natural language command from user

        Returns:
            Tuple of (HAAction or None, confidence 0.0-1.0)
        """
        logger.info(f"Translating command with confidence: {command}")

        try:
            # Build Ollama request
            request = OllamaRequest(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": command},
                ],
                stream=False,
                format="json",
            )

            # Call Ollama API
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=request.model_dump(),
                )
                response.raise_for_status()

            # Parse response
            data = response.json()
            logger.debug(f"Ollama response: {data}")

            # Extract message content
            if "choices" not in data or not data["choices"]:
                logger.error("No choices in Ollama response")
                return (None, 0.0)

            message_content = data["choices"][0]["message"]["content"]
            logger.debug(f"Message content: {message_content}")

            # Validate and parse JSON with confidence
            action, confidence = parse_ollama_response_with_confidence(message_content)

            if action:
                logger.info(f"Translated to action: {action.action} (confidence={confidence:.2f})")
            else:
                logger.warning("Failed to parse valid action from Ollama response")

            return (action, confidence)

        except httpx.TimeoutException:
            logger.error(f"Timeout calling Ollama (>{self.timeout}s)")
            return (None, 0.0)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling Ollama: {type(e).__name__}: {e}")
            return (None, 0.0)

        except Exception as e:
            logger.error(f"Unexpected error in translate_command_with_confidence: {e}")
            return (None, 0.0)
