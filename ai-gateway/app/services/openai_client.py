"""OpenAI GPT client for natural language to Home Assistant plan translation.

This module handles communication with OpenAI's API for command translation.
"""

from __future__ import annotations

import logging

import httpx

from app.models import Config, HAAction
from app.services.llm_client import LLMClient, SYSTEM_PROMPT
from app.utils.json_validator import parse_ollama_response

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    """Client for OpenAI GPT API."""

    def __init__(self, config: Config) -> None:
        """Initialize OpenAI client.

        Args:
            config: Application configuration
        """
        self.api_key = config.openai_api_key
        self.model = config.openai_model
        self.base_url = "https://api.openai.com/v1"
        self.timeout = 30.0  # OpenAI is typically faster than local Ollama

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")

    async def translate_command(self, command: str) -> HAAction | None:
        """Translate natural language command to Home Assistant action plan.

        Args:
            command: Natural language command from user

        Returns:
            Validated HAAction plan, or None if translation fails
        """
        logger.info(f"Translating command via OpenAI: {command}")

        try:
            # Build OpenAI request
            request_body = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": command},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,  # Low temperature for deterministic responses
                "max_tokens": 200,
            }

            # Call OpenAI API
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_body,
                )
                response.raise_for_status()

            # Parse response
            data = response.json()
            logger.debug(f"OpenAI response: {data}")

            # Extract message content
            if "choices" not in data or not data["choices"]:
                logger.error("No choices in OpenAI response")
                return None

            message_content = data["choices"][0]["message"]["content"]
            logger.debug(f"Message content: {message_content}")

            # Validate and parse JSON
            action = parse_ollama_response(message_content)

            if action:
                logger.info(f"Successfully translated to action: {action.action}")
            else:
                logger.warning("Failed to parse valid action from OpenAI response")

            return action

        except httpx.TimeoutException:
            logger.error(f"Timeout calling OpenAI (>{self.timeout}s)")
            return None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from OpenAI: {e.response.status_code} - {e.response.text}")
            return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling OpenAI: {type(e).__name__}: {e}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error in translate_command: {e}")
            return None
