"""Abstract LLM client and factory for multi-provider support.

This module provides an abstraction layer for LLM providers (Ollama, OpenAI)
allowing switching between them via environment configuration.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Config, HAAction

logger = logging.getLogger(__name__)

# Entity mapping: friendly names -> Home Assistant entity IDs
ENTITY_MAPPING = {
    # Living room / Salon
    "living room": "light.yeelight_color_0x80156a9",
    "living room lights": "light.yeelight_color_0x80156a9",
    "salon": "light.yeelight_color_0x80156a9",
    "salonie": "light.yeelight_color_0x80156a9",  # Polish locative
    "lights": "light.yeelight_color_0x80156a9",  # Default to living room
    "the lights": "light.yeelight_color_0x80156a9",
    "światło": "light.yeelight_color_0x80156a9",  # Polish: light
    "światła": "light.yeelight_color_0x80156a9",  # Polish: lights
    # Kitchen / Kuchnia
    "kitchen": "light.yeelight_color_0x49c27e1",
    "kitchen lights": "light.yeelight_color_0x49c27e1",
    "kuchnia": "light.yeelight_color_0x49c27e1",
    "kuchni": "light.yeelight_color_0x49c27e1",  # Polish locative
    # Bedroom / Sypialnia
    "bedroom": "light.yeelight_color_0x80147dd",
    "bedroom lights": "light.yeelight_color_0x80147dd",
    "sypialnia": "light.yeelight_color_0x80147dd",
    "sypialni": "light.yeelight_color_0x80147dd",  # Polish locative
    # Lamp 1 / Lampa 1
    "lamp 1": "light.yeelight_color_0x801498b",
    "lampa 1": "light.yeelight_color_0x801498b",
    "lampę 1": "light.yeelight_color_0x801498b",  # Polish accusative
    # Lamp 2 / Lampa 2
    "lamp 2": "light.yeelight_color_0x8015154",
    "lampa 2": "light.yeelight_color_0x8015154",
    "lampę 2": "light.yeelight_color_0x8015154",  # Polish accusative
    # Yeelight Lamp15 (desk lamp / lampka biurkowa)
    "desk lamp": "light.yeelight_lamp15_0x1b37d19d",
    "lamp 15": "light.yeelight_lamp15_0x1b37d19d",
    "lampa 15": "light.yeelight_lamp15_0x1b37d19d",
    "lampka": "light.yeelight_lamp15_0x1b37d19d",
    "lampka biurkowa": "light.yeelight_lamp15_0x1b37d19d",
    # Yeelight Lamp15 Ambilight
    "ambilight": "light.yeelight_lamp15_0x1b37d19d_ambilight",
    "ambient light": "light.yeelight_lamp15_0x1b37d19d_ambilight",
    "ambient": "light.yeelight_lamp15_0x1b37d19d_ambilight",
    # Media players
    "nest hub": "media_player.living_room_display",
    "speaker": "media_player.living_room_display",
    "głośnik": "media_player.living_room_display",  # Polish: speaker
    "living room tv": "media_player.telewizor_w_salonie",
    "telewizor": "media_player.telewizor_w_salonie",
    "tv": "media_player.telewizor_w_salonie",
    "bedroom tv": "media_player.telewizor_w_sypialni_2",
}

# System prompt for LLMs - forces JSON-only responses
SYSTEM_PROMPT = """You are a Home Assistant command translator. Your ONLY job is to convert natural language commands into JSON action plans.

CRITICAL RULES:
1. You MUST respond with ONLY valid JSON - no explanations, no additional text
2. Accept commands in both English and Polish
3. Use the entity mapping below to translate friendly names to entity IDs
4. If you receive multiple instructions, choose the PRIMARY action only
5. If you cannot understand the command or map it to an entity, return {"action":"none"}
6. Be tolerant of speech recognition errors and misspellings:
   - "zapal", "zapadł", "zaball", "zaopal" = turn ON
   - "zgaś", "zgaść", "sgas", "wyłącz" = turn OFF
   - "salonie", "salenie", "sanonie" = salon (living room)

ENTITY MAPPING:
LIGHTS:
- "living room" / "salon" / "lights" / "światło" → light.yeelight_color_0x80156a9
- "kitchen" / "kuchnia" → light.yeelight_color_0x49c27e1
- "bedroom" / "sypialnia" → light.yeelight_color_0x80147dd
- "lamp 1" / "lampa 1" → light.yeelight_color_0x801498b
- "lamp 2" / "lampa 2" → light.yeelight_color_0x8015154
- "desk lamp" / "lampka" / "lamp 15" → light.yeelight_lamp15_0x1b37d19d
- "ambilight" / "ambient" → light.yeelight_lamp15_0x1b37d19d_ambilight

MEDIA PLAYERS:
- "nest hub" / "speaker" / "głośnik" → media_player.living_room_display
- "tv" / "telewizor" → media_player.telewizor_w_salonie
- "bedroom tv" → media_player.telewizor_w_sypialni_2

SUPPORTED ACTIONS:
- Turn on lights: {"action":"call_service","service":"light.turn_on","entity_id":"<entity>","data":{}}
- Turn off lights: {"action":"call_service","service":"light.turn_off","entity_id":"<entity>","data":{}}
- Set brightness: {"action":"call_service","service":"light.turn_on","entity_id":"<entity>","data":{"brightness":255}}
- Say/speak text (TTS): {"action":"call_service","service":"tts.speak","entity_id":"tts.google_translate_en_com","data":{"media_player_entity_id":"media_player.living_room_display","message":"<text to speak>"}}
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

Input: "Say hello"
Output: {"action":"call_service","service":"tts.speak","entity_id":"tts.google_translate_en_com","data":{"media_player_entity_id":"media_player.living_room_display","message":"Hello"}}

Input: "Powiedz cześć"
Output: {"action":"call_service","service":"tts.speak","entity_id":"tts.google_translate_en_com","data":{"media_player_entity_id":"media_player.living_room_display","message":"Cześć"}}

Input: "Turn on the desk lamp"
Output: {"action":"call_service","service":"light.turn_on","entity_id":"light.yeelight_lamp15_0x1b37d19d","data":{}}

Input: "Zapal lampkę"
Output: {"action":"call_service","service":"light.turn_on","entity_id":"light.yeelight_lamp15_0x1b37d19d","data":{}}

Remember: ONLY return the JSON object, nothing else."""


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def translate_command(self, command: str) -> HAAction | None:
        """Translate natural language command to Home Assistant action plan.

        Args:
            command: Natural language command from user

        Returns:
            Validated HAAction plan, or None if translation fails
        """
        pass


def get_llm_client(config: Config) -> LLMClient:
    """Factory function to get appropriate LLM client based on configuration.

    Args:
        config: Application configuration

    Returns:
        LLMClient instance (OllamaClient or OpenAIClient)

    Raises:
        ValueError: If unknown provider specified
    """
    provider = config.llm_provider.lower()

    if provider == "ollama":
        from app.services.ollama_client import OllamaClient
        logger.info(f"Using Ollama LLM provider with model: {config.ollama_model}")
        return OllamaClient(config)

    elif provider == "openai":
        from app.services.openai_client import OpenAIClient
        logger.info(f"Using OpenAI LLM provider with model: {config.openai_model}")
        return OpenAIClient(config)

    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Supported: ollama, openai")
