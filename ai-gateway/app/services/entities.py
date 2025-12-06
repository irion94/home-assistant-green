"""Centralized entity mappings for Home Assistant devices.

This module provides a single source of truth for all entity mappings,
room names, and device configurations used throughout the AI Gateway.

Configuration is loaded from config/entities.yaml by default.
Hardcoded fallbacks are provided for backward compatibility.

Usage:
    from app.services.entities import ENTITY_MAPPING, ROOM_ENTITIES, get_entity_id

    # Get entity ID from friendly name
    entity_id = get_entity_id("living room")

    # Get room entity
    entity_id = ROOM_ENTITIES.get("salon")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION LOADING
# =============================================================================
# Try to load from YAML config file first, fall back to hardcoded values

try:
    from app.services.config_loader import get_entity_config

    _config = get_entity_config()
    _use_config = True
    logger.info("Entity mappings loaded from YAML configuration")
except Exception as e:
    logger.warning(f"Failed to load YAML config, using hardcoded values: {e}")
    _use_config = False
    _config = None


# =============================================================================
# ENTITY MAPPING
# =============================================================================
# Maps friendly names (English/Polish) to Home Assistant entity IDs
# Used by LLM clients to translate natural language to entity references

if _use_config and _config is not None:
    ENTITY_MAPPING: dict[str, str] = _config.entity_mapping
else:
    ENTITY_MAPPING = {
        # All lights
        "all lights": "all",
        "all": "all",
        "everything": "all",
        "wszystko": "all",
        "wszystkie": "all",
        "wszystkie światła": "all",
        "wszędzie": "all",
        # Living room / Salon
        "living room": "light.yeelight_color_0x80156a9",
        "living room lights": "light.yeelight_color_0x80156a9",
        "salon": "light.yeelight_color_0x80156a9",
        "salonie": "light.yeelight_color_0x80156a9",
        "lights": "light.yeelight_color_0x80156a9",
        "the lights": "light.yeelight_color_0x80156a9",
        "światło": "light.yeelight_color_0x80156a9",
        "światła": "light.yeelight_color_0x80156a9",
        # Kitchen / Kuchnia
        "kitchen": "light.yeelight_color_0x49c27e1",
        "kitchen lights": "light.yeelight_color_0x49c27e1",
        "kuchnia": "light.yeelight_color_0x49c27e1",
        "kuchni": "light.yeelight_color_0x49c27e1",
        # Bedroom / Sypialnia
        "bedroom": "light.yeelight_color_0x80147dd",
        "bedroom lights": "light.yeelight_color_0x80147dd",
        "sypialnia": "light.yeelight_color_0x80147dd",
        "sypialni": "light.yeelight_color_0x80147dd",
        # Lamp 1 / Lampa 1
        "lamp 1": "light.yeelight_color_0x801498b",
        "lampa 1": "light.yeelight_color_0x801498b",
        "lampę 1": "light.yeelight_color_0x801498b",
        # Lamp 2 / Lampa 2
        "lamp 2": "light.yeelight_color_0x8015154",
        "lampa 2": "light.yeelight_color_0x8015154",
        "lampę 2": "light.yeelight_color_0x8015154",
        # Desk / Biurko
        "desk": "light.yeelight_lamp15_0x1b37d19d_ambilight",
        "desk lamp": "light.yeelight_lamp15_0x1b37d19d_ambilight",
        "biurko": "light.yeelight_lamp15_0x1b37d19d_ambilight",
        "biurku": "light.yeelight_lamp15_0x1b37d19d_ambilight",
        "lampka": "light.yeelight_lamp15_0x1b37d19d_ambilight",
        "lampkę": "light.yeelight_lamp15_0x1b37d19d_ambilight",
        # Desk Ambient
        "ambient": "light.yeelight_lamp15_0x1b37d19d",
        "ambilight": "light.yeelight_lamp15_0x1b37d19d",
        "biurko ambient": "light.yeelight_lamp15_0x1b37d19d",
        # LED Strip
        "led strip": "light.elk_bledom_led",
        "led": "light.elk_bledom_led",
        "taśma": "light.elk_bledom_led",
        "taśma led": "light.elk_bledom_led",
        "taśmę": "light.elk_bledom_led",
        "taśmę led": "light.elk_bledom_led",
        "elk": "light.elk_bledom_led",
        # LED Scripts
        "led red": "script.elk_led_red",
        "led green": "script.elk_led_green",
        "led blue": "script.elk_led_blue",
        "led white": "script.elk_led_white",
        "led yellow": "script.elk_led_yellow",
        "led purple": "script.elk_led_purple",
        "led cyan": "script.elk_led_cyan",
        "led orange": "script.elk_led_orange",
        "led pink": "script.elk_led_pink",
        "taśma czerwona": "script.elk_led_red",
        "taśma zielona": "script.elk_led_green",
        "taśma niebieska": "script.elk_led_blue",
        "taśma biała": "script.elk_led_white",
        "taśma żółta": "script.elk_led_yellow",
        "taśma fioletowa": "script.elk_led_purple",
        # Media players
        "nest hub": "media_player.living_room_display",
        "speaker": "media_player.living_room_display",
        "głośnik": "media_player.living_room_display",
        "living room tv": "media_player.telewizor_w_salonie",
        "telewizor": "media_player.telewizor_w_salonie",
        "telewizor salon": "media_player.telewizor_w_salonie",
        "tv salon": "media_player.telewizor_w_salonie",
        "tv": "media_player.telewizor_w_salonie",
        "bedroom tv": "media_player.telewizor_w_sypialni",
        "telewizor sypialnia": "media_player.telewizor_w_sypialni",
        "tv sypialnia": "media_player.telewizor_w_sypialni",
    }


# =============================================================================
# ROOM ENTITIES (Simplified)
# =============================================================================
# Simplified room name to entity mapping for LLM function calling tools

if _use_config and _config is not None:
    ROOM_ENTITIES: dict[str, str] = _config.room_entities
else:
    ROOM_ENTITIES = {
        "salon": "light.yeelight_color_0x80156a9",
        "kuchnia": "light.yeelight_color_0x49c27e1",
        "sypialnia": "light.yeelight_color_0x80147dd",
        "biurko": "light.yeelight_lamp15_0x1b37d19d_ambilight",
        "all": "all",
    }

# Human-readable room names for responses
if _use_config and _config is not None:
    ROOM_NAMES: dict[str, str] = _config.room_names
else:
    ROOM_NAMES = {
        "salon": "living room",
        "kuchnia": "kitchen",
        "sypialnia": "bedroom",
        "biurko": "desk",
        "all": "all lights",
    }


# =============================================================================
# ALL LIGHTS LIST
# =============================================================================
# Complete list of all controllable light entities

if _use_config and _config is not None:
    ALL_LIGHT_ENTITIES: list[str] = _config.all_lights
else:
    ALL_LIGHT_ENTITIES = [
        "light.yeelight_color_0x80156a9",  # salon
        "light.yeelight_color_0x49c27e1",  # kuchnia
        "light.yeelight_color_0x80147dd",  # sypialnia
        "light.yeelight_lamp15_0x1b37d19d_ambilight",  # biurko
        "light.yeelight_lamp15_0x1b37d19d",  # biurko ambient
        "light.yeelight_color_0x801498b",  # lamp 1
        "light.yeelight_color_0x8015154",  # lamp 2
    ]


# =============================================================================
# SENSOR ENTITIES
# =============================================================================
# Maps sensor types to possible Home Assistant entity IDs

if _use_config and _config is not None:
    SENSOR_ENTITIES: dict[str, list[str]] = _config.sensor_entities
else:
    SENSOR_ENTITIES = {
        "temperature_outside": [
            "sensor.outside_temperature",
            "sensor.outdoor_temperature",
            "sensor.weather_temperature",
            "weather.home",
        ],
        "temperature_inside": [
            "sensor.indoor_temperature",
            "sensor.living_room_temperature",
            "sensor.temperature",
        ],
        "humidity": [
            "sensor.outdoor_humidity",
            "sensor.humidity",
            "sensor.living_room_humidity",
        ],
        "weather": [
            "weather.home",
            "weather.forecast_home",
        ],
    }


# =============================================================================
# ACTION KEYWORDS
# =============================================================================
# Keywords for intent matching (English and Polish, including common misrecognitions)

if _use_config and _config is not None:
    TURN_ON_KEYWORDS: list[str] = _config.keywords.get("turn_on", [])
    TURN_OFF_KEYWORDS: list[str] = _config.keywords.get("turn_off", [])
    CONVERSATION_START_KEYWORDS: list[str] = _config.keywords.get("conversation_start", [])
    CONVERSATION_END_KEYWORDS: list[str] = _config.keywords.get("conversation_end", [])
    INTERRUPT_KEYWORDS: list[str] = _config.keywords.get("interrupt", [])
else:
    TURN_ON_KEYWORDS = [
        "zapal", "włącz", "włacz", "wlacz", "zaświeć", "włącz się",
        "turn on", "switch on", "light up",
        "zapadł", "zaball", "zaopal", "za pal", "za pan",
    ]

    TURN_OFF_KEYWORDS = [
        "zgaś", "wyłącz", "wylacz", "gaś", "wyłącz się",
        "turn off", "switch off",
        "zgaść", "sgas", "z gaś",
    ]

    CONVERSATION_START_KEYWORDS = [
        "let's talk", "lets talk", "talk to me", "let's chat", "lets chat",
        "pogadajmy", "porozmawiajmy", "porozmawiaj ze mną", "pogadaj ze mną",
        "chcę porozmawiać", "chce porozmawiać",
    ]

    CONVERSATION_END_KEYWORDS = [
        "bye", "goodbye", "stop", "end", "that's all", "thats all", "thank you",
        "pa", "do widzenia", "koniec", "zakończ", "kończymy", "to wszystko",
        "dzięki", "dziękuję",
    ]

    INTERRUPT_KEYWORDS = [
        "stop", "przerwij", "cicho", "cisza",
    ]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_entity_id(friendly_name: str) -> str | None:
    """Get entity ID from friendly name.

    Args:
        friendly_name: Human-readable name (English or Polish)

    Returns:
        Home Assistant entity ID or None if not found
    """
    return ENTITY_MAPPING.get(friendly_name.lower().strip())


def get_room_entity(room_name: str) -> str | None:
    """Get entity ID from room name.

    Args:
        room_name: Canonical room name

    Returns:
        Home Assistant entity ID or None if not found
    """
    return ROOM_ENTITIES.get(room_name.lower().strip())


def get_room_display_name(room_key: str) -> str:
    """Get human-readable room name for responses.

    Args:
        room_key: Room key (e.g., "salon", "kuchnia")

    Returns:
        Human-readable name (e.g., "living room", "kitchen")
    """
    return ROOM_NAMES.get(room_key.lower().strip(), room_key)


def get_all_light_entities() -> list[str]:
    """Get list of all controllable light entity IDs.

    Returns:
        List of entity IDs for all lights
    """
    return ALL_LIGHT_ENTITIES.copy()


def reload_config() -> None:
    """Reload entity configuration from YAML file.

    Updates all module-level variables with new configuration.
    """
    global ENTITY_MAPPING, ROOM_ENTITIES, ROOM_NAMES, ALL_LIGHT_ENTITIES
    global SENSOR_ENTITIES, TURN_ON_KEYWORDS, TURN_OFF_KEYWORDS
    global CONVERSATION_START_KEYWORDS, CONVERSATION_END_KEYWORDS, INTERRUPT_KEYWORDS
    global _config, _use_config

    try:
        from app.services.config_loader import reload_entity_config

        _config = reload_entity_config()
        _use_config = True

        ENTITY_MAPPING = _config.entity_mapping
        ROOM_ENTITIES = _config.room_entities
        ROOM_NAMES = _config.room_names
        ALL_LIGHT_ENTITIES = _config.all_lights
        SENSOR_ENTITIES = _config.sensor_entities
        TURN_ON_KEYWORDS = _config.keywords.get("turn_on", [])
        TURN_OFF_KEYWORDS = _config.keywords.get("turn_off", [])
        CONVERSATION_START_KEYWORDS = _config.keywords.get("conversation_start", [])
        CONVERSATION_END_KEYWORDS = _config.keywords.get("conversation_end", [])
        INTERRUPT_KEYWORDS = _config.keywords.get("interrupt", [])

        logger.info("Entity configuration reloaded from YAML")
    except Exception as e:
        logger.error(f"Failed to reload entity configuration: {e}")
