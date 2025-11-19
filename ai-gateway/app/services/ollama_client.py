"""Ollama LLM client for natural language to Home Assistant plan translation.

This module handles communication with Ollama and includes sophisticated
system prompt engineering to ensure JSON-only, deterministic responses.
"""

from __future__ import annotations

import logging

import httpx

from app.models import Config, HAAction, OllamaRequest
from app.utils.json_validator import parse_ollama_response

logger = logging.getLogger(__name__)

# Entity mapping: friendly names -> Home Assistant entity IDs
ENTITY_MAPPING = {
    "living room": "light.living_room_main",
    "living room lights": "light.living_room_main",
    "salon": "light.living_room_main",  # Polish
    "kitchen": "light.kitchen",
    "kitchen lights": "light.kitchen",
    "kuchnia": "light.kitchen",  # Polish
    "bedroom": "light.bedroom",
    "bedroom lights": "light.bedroom",
    "sypialnia": "light.bedroom",  # Polish
}

# System prompt for Ollama - forces JSON-only responses
SYSTEM_PROMPT = """You are a Home Assistant command translator. Your ONLY job is to convert natural language commands into JSON action plans.

CRITICAL RULES:
1. You MUST respond with ONLY valid JSON - no explanations, no additional text
2. Accept commands in both English and Polish
3. Use the entity mapping below to translate friendly names to entity IDs
4. If you receive multiple instructions, choose the PRIMARY action only
5. If you cannot understand the command or map it to an entity, return {"action":"none"}

ENTITY MAPPING:
- "living room" / "salon" → light.living_room_main
- "kitchen" / "kuchnia" → light.kitchen
- "bedroom" / "sypialnia" → light.bedroom

SUPPORTED ACTIONS:
- Turn on lights: {"action":"call_service","service":"light.turn_on","entity_id":"<entity>","data":{}}
- Turn off lights: {"action":"call_service","service":"light.turn_off","entity_id":"<entity>","data":{}}
- Set brightness: {"action":"call_service","service":"light.turn_on","entity_id":"<entity>","data":{"brightness":255}}
- Unknown/unsupported: {"action":"none"}

RESPONSE FORMAT (STRICTLY JSON ONLY):
{"action":"call_service","service":"light.turn_on","entity_id":"light.living_room_main","data":{}}

EXAMPLES:
Input: "Turn on living room lights"
Output: {"action":"call_service","service":"light.turn_on","entity_id":"light.living_room_main","data":{}}

Input: "Wyłącz światło w kuchni"
Output: {"action":"call_service","service":"light.turn_off","entity_id":"light.kitchen","data":{}}

Input: "Set bedroom to 50% brightness"
Output: {"action":"call_service","service":"light.turn_on","entity_id":"light.bedroom","data":{"brightness":128}}

Input: "What's the weather?"
Output: {"action":"none"}

Remember: ONLY return the JSON object, nothing else."""


class OllamaClient:
    """Client for Ollama LLM API."""

    def __init__(self, config: Config) -> None:
        """Initialize Ollama client.

        Args:
            config: Application configuration
        """
        self.base_url = config.ollama_base_url
        self.model = config.ollama_model
        self.timeout = 30.0  # 30 second timeout for LLM requests

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

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling Ollama: {e}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error in translate_command: {e}")
            return None
