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
    "living room": "light.yeelight_color_0x80156a9",
    "living room lights": "light.yeelight_color_0x80156a9",
    "salon": "light.yeelight_color_0x80156a9",  # Polish
    "lights": "light.yeelight_color_0x80156a9",  # Default to living room
    "the lights": "light.yeelight_color_0x80156a9",
    "kitchen": "light.yeelight_color_0x49c27e1",
    "kitchen lights": "light.yeelight_color_0x49c27e1",
    "kuchnia": "light.yeelight_color_0x49c27e1",  # Polish
    "bedroom": "light.yeelight_color_0x80147dd",
    "bedroom lights": "light.yeelight_color_0x80147dd",
    "sypialnia": "light.yeelight_color_0x80147dd",  # Polish
    "lamp 1": "light.yeelight_color_0x801498b",
    "lampa 1": "light.yeelight_color_0x801498b",
    "lamp 2": "light.yeelight_color_0x8015154",
    "lampa 2": "light.yeelight_color_0x8015154",
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
- "living room" / "salon" / "lights" / "the lights" → light.yeelight_color_0x80156a9
- "kitchen" / "kuchnia" → light.yeelight_color_0x49c27e1
- "bedroom" / "sypialnia" → light.yeelight_color_0x80147dd
- "lamp 1" / "lampa 1" → light.yeelight_color_0x801498b
- "lamp 2" / "lampa 2" → light.yeelight_color_0x8015154

SUPPORTED ACTIONS:
- Turn on lights: {"action":"call_service","service":"light.turn_on","entity_id":"<entity>","data":{}}
- Turn off lights: {"action":"call_service","service":"light.turn_off","entity_id":"<entity>","data":{}}
- Set brightness: {"action":"call_service","service":"light.turn_on","entity_id":"<entity>","data":{"brightness":255}}
- Unknown/unsupported: {"action":"none"}

RESPONSE FORMAT (STRICTLY JSON ONLY):
{"action":"call_service","service":"light.turn_on","entity_id":"light.yeelight_color_0x80156a9","data":{}}

EXAMPLES:
Input: "Turn on living room lights"
Output: {"action":"call_service","service":"light.turn_on","entity_id":"light.yeelight_color_0x80156a9","data":{}}

Input: "Turn on the lights"
Output: {"action":"call_service","service":"light.turn_on","entity_id":"light.yeelight_color_0x80156a9","data":{}}

Input: "Wyłącz światło w kuchni"
Output: {"action":"call_service","service":"light.turn_off","entity_id":"light.yeelight_color_0x49c27e1","data":{}}

Input: "Set bedroom to 50% brightness"
Output: {"action":"call_service","service":"light.turn_on","entity_id":"light.yeelight_color_0x80147dd","data":{"brightness":128}}

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
