"""Centralized entity mappings for Home Assistant devices.

This module provides a single source of truth for all entity mappings,
room names, and device configurations used throughout the AI Gateway.
"""

from __future__ import annotations

# =============================================================================
# ENTITY MAPPING
# =============================================================================
# Maps friendly names (English/Polish) to Home Assistant entity IDs
# Used by LLM clients to translate natural language to entity references

ENTITY_MAPPING: dict[str, str] = {
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
    # Desk / Biurko (main light is _ambilight entity in HA)
    "desk": "light.yeelight_lamp15_0x1b37d19d_ambilight",
    "desk lamp": "light.yeelight_lamp15_0x1b37d19d_ambilight",
    "biurko": "light.yeelight_lamp15_0x1b37d19d_ambilight",
    "biurku": "light.yeelight_lamp15_0x1b37d19d_ambilight",  # Polish locative
    "lampka": "light.yeelight_lamp15_0x1b37d19d_ambilight",
    "lampkę": "light.yeelight_lamp15_0x1b37d19d_ambilight",  # Polish accusative
    # Desk Ambient (background light)
    "ambient": "light.yeelight_lamp15_0x1b37d19d",
    "ambilight": "light.yeelight_lamp15_0x1b37d19d",
    "biurko ambient": "light.yeelight_lamp15_0x1b37d19d",
    # LED Strip / Taśma LED
    "led strip": "light.elk_bledom_led",
    "led": "light.elk_bledom_led",
    "taśma": "light.elk_bledom_led",
    "taśma led": "light.elk_bledom_led",
    "taśmę": "light.elk_bledom_led",  # Polish accusative
    "taśmę led": "light.elk_bledom_led",
    "elk": "light.elk_bledom_led",
    # LED Strip Color Scripts
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
    "głośnik": "media_player.living_room_display",  # Polish: speaker
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
# Uses canonical room names only

ROOM_ENTITIES: dict[str, str] = {
    "salon": "light.yeelight_color_0x80156a9",
    "kuchnia": "light.yeelight_color_0x49c27e1",
    "sypialnia": "light.yeelight_color_0x80147dd",
    "biurko": "light.yeelight_lamp15_0x1b37d19d_ambilight",
    "all": "all",
}

# Human-readable room names for responses
ROOM_NAMES: dict[str, str] = {
    "salon": "living room",
    "kuchnia": "kitchen",
    "sypialnia": "bedroom",
    "biurko": "desk",
    "all": "all lights",
}

# =============================================================================
# SENSOR ENTITIES
# =============================================================================
# Maps sensor types to possible Home Assistant entity IDs
# Multiple options provided for flexibility in different HA setups

SENSOR_ENTITIES: dict[str, list[str]] = {
    "temperature_outside": [
        "sensor.outside_temperature",
        "sensor.outdoor_temperature",
        "sensor.weather_temperature",
        "weather.home",  # Weather integration
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

TURN_ON_KEYWORDS: list[str] = [
    "zapal", "włącz", "włacz", "wlacz", "zaświeć", "włącz się",
    "turn on", "switch on", "light up",
    # Common misrecognitions
    "zapadł", "zaball", "zaopal", "za pal", "za pan",
]

TURN_OFF_KEYWORDS: list[str] = [
    "zgaś", "wyłącz", "wylacz", "gaś", "wyłącz się",
    "turn off", "switch off",
    # Common misrecognitions
    "zgaść", "sgas", "z gaś",
]

# =============================================================================
# CONVERSATION KEYWORDS
# =============================================================================
# Keywords for conversation mode control

CONVERSATION_START_KEYWORDS: list[str] = [
    "let's talk", "lets talk", "talk to me", "let's chat", "lets chat",
    "pogadajmy", "porozmawiajmy", "porozmawiaj ze mną", "pogadaj ze mną",
    "chcę porozmawiać", "chce porozmawiać",
]

CONVERSATION_END_KEYWORDS: list[str] = [
    "bye", "goodbye", "stop", "end", "that's all", "thats all", "thank you",
    "pa", "do widzenia", "koniec", "zakończ", "kończymy", "to wszystko",
    "dzięki", "dziękuję",
]

INTERRUPT_KEYWORDS: list[str] = [
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
