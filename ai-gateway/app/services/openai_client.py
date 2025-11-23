"""OpenAI GPT client for natural language to Home Assistant plan translation.

This module handles communication with OpenAI's API for command translation.
"""

from __future__ import annotations

import logging

import httpx

from app.models import Config, HAAction
from app.services.llm_client import LLMClient, SYSTEM_PROMPT
from app.utils.json_validator import parse_ollama_response, parse_ollama_response_with_confidence

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

    async def translate_command_dynamic(
        self, command: str, entities: list[dict]
    ) -> tuple[HAAction | None, float]:
        """Translate command using dynamic entity list.

        Args:
            command: Natural language command from user
            entities: List of entity dicts with 'entity_id', 'domain', 'name'

        Returns:
            Tuple of (HAAction or None, confidence 0.0-1.0)
        """
        logger.info(f"Translating with dynamic entities via OpenAI: {command}")

        # Build dynamic entity prompt
        entity_prompt = self._build_entity_prompt(entities)

        dynamic_prompt = f"""You are a Home Assistant command translator. Convert natural language to JSON actions.

CRITICAL RULES:
1. ONLY return valid JSON - no explanations
2. Match the user's intent to the best matching entity
3. Be tolerant of speech recognition errors and alternate names
4. Return {{"action":"none","confidence":0.0}} if you cannot match

AVAILABLE ENTITIES:
{entity_prompt}

POLISH COLOR MAPPING:
- "czerwony" → [255, 0, 0], "niebieski" → [0, 0, 255], "zielony" → [0, 255, 0]
- "żółty" → [255, 255, 0], "biały" → [255, 255, 255], "pomarańczowy" → [255, 165, 0]
- "fioletowy" → [128, 0, 128], "różowy" → [255, 192, 203], "turkusowy" → [0, 255, 255]

COLOR TEMPERATURE: "ciepłe" → 2700K, "neutralne" → 4000K, "zimne" → 6500K

SUPPORTED ACTIONS:
- Turn on: {{"action":"call_service","service":"<domain>.turn_on","entity_id":"<entity_id>","data":{{}},"confidence":0.95}}
- Turn off: {{"action":"call_service","service":"<domain>.turn_off","entity_id":"<entity_id>","data":{{}},"confidence":0.95}}
- Set brightness (50%=128, 100%=255): {{"action":"call_service","service":"light.turn_on","entity_id":"<entity_id>","data":{{"brightness":128}},"confidence":0.9}}
- Set color (RGB): {{"action":"call_service","service":"light.turn_on","entity_id":"<entity_id>","data":{{"rgb_color":[255,0,0]}},"confidence":0.9}}
- Set color temperature: {{"action":"call_service","service":"light.turn_on","entity_id":"<entity_id>","data":{{"color_temp_kelvin":2700}},"confidence":0.9}}
- Transition: {{"action":"call_service","service":"light.turn_on","entity_id":"<entity_id>","data":{{"brightness":255,"transition":5}},"confidence":0.9}}
- Media control: {{"action":"call_service","service":"media_player.<action>","entity_id":"<entity_id>","data":{{}},"confidence":0.9}}
- Create scene/mood: {{"action":"create_scene","actions":[...list of call_service actions...],"confidence":0.85}}

Special entity "all" controls all devices in a domain (e.g., entity_id: "all" for all lights).

CONFIDENCE SCORING:
- 0.9-1.0: Clear match, exact entity name
- 0.7-0.89: Good match, similar name
- 0.5-0.69: Ambiguous, best guess
- Below 0.5: Very uncertain

Return ONLY the JSON object."""

        try:
            request_body = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": dynamic_prompt},
                    {"role": "user", "content": command},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
                "max_tokens": 200,
            }

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

            data = response.json()
            logger.debug(f"Dynamic OpenAI response: {data}")

            if "choices" not in data or not data["choices"]:
                logger.error("No choices in OpenAI response")
                return (None, 0.0)

            message_content = data["choices"][0]["message"]["content"]
            logger.debug(f"Dynamic message content: {message_content}")

            action, confidence = parse_ollama_response_with_confidence(message_content)

            # Validate entity_id exists in provided entities (unless "all")
            if action and action.entity_id and action.entity_id != "all":
                valid_ids = {e["entity_id"] for e in entities}
                if action.entity_id not in valid_ids:
                    logger.warning(f"OpenAI returned invalid entity_id: {action.entity_id}")
                    confidence = min(confidence * 0.5, 0.3)

            if action:
                logger.info(f"Dynamic translated: {action.action} -> {action.entity_id} (conf={confidence:.2f})")
            else:
                logger.warning("Failed to parse dynamic action from OpenAI")

            return (action, confidence)

        except httpx.TimeoutException:
            logger.error(f"Timeout in dynamic translate (>{self.timeout}s)")
            return (None, 0.0)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in dynamic translate: {e.response.status_code}")
            return (None, 0.0)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error in dynamic translate: {type(e).__name__}: {e}")
            return (None, 0.0)

        except Exception as e:
            logger.error(f"Unexpected error in translate_command_dynamic: {e}")
            return (None, 0.0)

    def _build_entity_prompt(self, entities: list[dict]) -> str:
        """Build entity list formatted for LLM prompt.

        Args:
            entities: List of entity dicts

        Returns:
            Formatted string for prompt
        """
        if not entities:
            return "No entities available."

        # Group by domain
        by_domain: dict[str, list[str]] = {}
        for e in entities:
            domain = e.get("domain", "unknown")
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(f'- "{e.get("name", "")}" → {e.get("entity_id", "")}')

        # Build sections
        lines = []
        domain_order = ["light", "switch", "media_player", "climate", "cover", "fan"]

        for domain in domain_order:
            if domain in by_domain:
                lines.append(f"{domain.upper()}S:")
                lines.extend(by_domain[domain])
                lines.append("")
                del by_domain[domain]

        # Remaining domains
        for domain, items in sorted(by_domain.items()):
            lines.append(f"{domain.upper()}S:")
            lines.extend(items)
            lines.append("")

        return "\n".join(lines)
