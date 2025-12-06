"""Default fixtures for the mock backend.

Provides realistic entity and state definitions for testing
without a real home automation system.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.models import EntityInfo, EntityState


def _now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


# =============================================================================
# DEFAULT ENTITIES
# =============================================================================

DEFAULT_ENTITIES: list[EntityInfo] = [
    # Lights
    EntityInfo(
        entity_id="light.living_room",
        domain="light",
        name="Living Room Light",
        area="Living Room",
        supported_features=["brightness", "color", "color_temp"],
    ),
    EntityInfo(
        entity_id="light.kitchen",
        domain="light",
        name="Kitchen Light",
        area="Kitchen",
        supported_features=["brightness", "color", "color_temp"],
    ),
    EntityInfo(
        entity_id="light.bedroom",
        domain="light",
        name="Bedroom Light",
        area="Bedroom",
        supported_features=["brightness", "color", "color_temp"],
    ),
    EntityInfo(
        entity_id="light.desk",
        domain="light",
        name="Desk Lamp",
        area="Office",
        supported_features=["brightness", "color_temp"],
    ),
    EntityInfo(
        entity_id="light.hallway",
        domain="light",
        name="Hallway Light",
        area="Hallway",
        supported_features=["brightness"],
    ),
    EntityInfo(
        entity_id="light.led_strip",
        domain="light",
        name="LED Strip",
        area="Living Room",
        supported_features=["brightness", "color"],
    ),
    # Switches
    EntityInfo(
        entity_id="switch.outlet_1",
        domain="switch",
        name="Smart Outlet 1",
        area="Living Room",
        supported_features=[],
    ),
    EntityInfo(
        entity_id="switch.outlet_2",
        domain="switch",
        name="Smart Outlet 2",
        area="Kitchen",
        supported_features=[],
    ),
    EntityInfo(
        entity_id="switch.fan",
        domain="switch",
        name="Ceiling Fan",
        area="Bedroom",
        supported_features=[],
    ),
    # Climate
    EntityInfo(
        entity_id="climate.thermostat",
        domain="climate",
        name="Thermostat",
        area="Living Room",
        supported_features=["temperature", "hvac_mode"],
        device_class="climate",
    ),
    # Sensors
    EntityInfo(
        entity_id="sensor.outdoor_temperature",
        domain="sensor",
        name="Outdoor Temperature",
        area=None,
        supported_features=[],
        device_class="temperature",
    ),
    EntityInfo(
        entity_id="sensor.indoor_temperature",
        domain="sensor",
        name="Indoor Temperature",
        area="Living Room",
        supported_features=[],
        device_class="temperature",
    ),
    EntityInfo(
        entity_id="sensor.humidity",
        domain="sensor",
        name="Humidity",
        area="Living Room",
        supported_features=[],
        device_class="humidity",
    ),
    EntityInfo(
        entity_id="sensor.motion_living_room",
        domain="sensor",
        name="Living Room Motion",
        area="Living Room",
        supported_features=[],
        device_class="motion",
    ),
    # Media Players
    EntityInfo(
        entity_id="media_player.living_room_tv",
        domain="media_player",
        name="Living Room TV",
        area="Living Room",
        supported_features=["play", "pause", "stop", "volume", "source"],
        device_class="tv",
    ),
    EntityInfo(
        entity_id="media_player.speaker",
        domain="media_player",
        name="Smart Speaker",
        area="Living Room",
        supported_features=["play", "pause", "volume"],
        device_class="speaker",
    ),
    EntityInfo(
        entity_id="media_player.bedroom_tv",
        domain="media_player",
        name="Bedroom TV",
        area="Bedroom",
        supported_features=["play", "pause", "stop", "volume", "source"],
        device_class="tv",
    ),
]


# =============================================================================
# DEFAULT STATES
# =============================================================================

DEFAULT_STATES: dict[str, EntityState] = {
    # Lights - mostly off initially
    "light.living_room": EntityState(
        entity_id="light.living_room",
        state="off",
        attributes={
            "brightness": 0,
            "color_mode": None,
            "friendly_name": "Living Room Light",
        },
        last_changed=_now(),
    ),
    "light.kitchen": EntityState(
        entity_id="light.kitchen",
        state="off",
        attributes={
            "brightness": 0,
            "color_mode": None,
            "friendly_name": "Kitchen Light",
        },
        last_changed=_now(),
    ),
    "light.bedroom": EntityState(
        entity_id="light.bedroom",
        state="off",
        attributes={
            "brightness": 0,
            "color_mode": None,
            "friendly_name": "Bedroom Light",
        },
        last_changed=_now(),
    ),
    "light.desk": EntityState(
        entity_id="light.desk",
        state="on",
        attributes={
            "brightness": 200,
            "color_temp": 370,
            "color_mode": "color_temp",
            "friendly_name": "Desk Lamp",
        },
        last_changed=_now(),
    ),
    "light.hallway": EntityState(
        entity_id="light.hallway",
        state="off",
        attributes={
            "brightness": 0,
            "friendly_name": "Hallway Light",
        },
        last_changed=_now(),
    ),
    "light.led_strip": EntityState(
        entity_id="light.led_strip",
        state="off",
        attributes={
            "brightness": 0,
            "rgb_color": None,
            "friendly_name": "LED Strip",
        },
        last_changed=_now(),
    ),
    # Switches
    "switch.outlet_1": EntityState(
        entity_id="switch.outlet_1",
        state="off",
        attributes={"friendly_name": "Smart Outlet 1"},
        last_changed=_now(),
    ),
    "switch.outlet_2": EntityState(
        entity_id="switch.outlet_2",
        state="on",
        attributes={"friendly_name": "Smart Outlet 2"},
        last_changed=_now(),
    ),
    "switch.fan": EntityState(
        entity_id="switch.fan",
        state="off",
        attributes={"friendly_name": "Ceiling Fan"},
        last_changed=_now(),
    ),
    # Climate
    "climate.thermostat": EntityState(
        entity_id="climate.thermostat",
        state="heat",
        attributes={
            "current_temperature": 21.5,
            "temperature": 22.0,
            "hvac_mode": "heat",
            "hvac_modes": ["off", "heat", "cool", "auto"],
            "friendly_name": "Thermostat",
        },
        last_changed=_now(),
    ),
    # Sensors
    "sensor.outdoor_temperature": EntityState(
        entity_id="sensor.outdoor_temperature",
        state="15.2",
        attributes={
            "unit_of_measurement": "°C",
            "device_class": "temperature",
            "friendly_name": "Outdoor Temperature",
        },
        last_changed=_now(),
    ),
    "sensor.indoor_temperature": EntityState(
        entity_id="sensor.indoor_temperature",
        state="21.5",
        attributes={
            "unit_of_measurement": "°C",
            "device_class": "temperature",
            "friendly_name": "Indoor Temperature",
        },
        last_changed=_now(),
    ),
    "sensor.humidity": EntityState(
        entity_id="sensor.humidity",
        state="45",
        attributes={
            "unit_of_measurement": "%",
            "device_class": "humidity",
            "friendly_name": "Humidity",
        },
        last_changed=_now(),
    ),
    "sensor.motion_living_room": EntityState(
        entity_id="sensor.motion_living_room",
        state="off",
        attributes={
            "device_class": "motion",
            "friendly_name": "Living Room Motion",
        },
        last_changed=_now(),
    ),
    # Media Players
    "media_player.living_room_tv": EntityState(
        entity_id="media_player.living_room_tv",
        state="off",
        attributes={
            "volume_level": 0.5,
            "is_volume_muted": False,
            "source": None,
            "source_list": ["HDMI 1", "HDMI 2", "Netflix", "YouTube"],
            "friendly_name": "Living Room TV",
        },
        last_changed=_now(),
    ),
    "media_player.speaker": EntityState(
        entity_id="media_player.speaker",
        state="idle",
        attributes={
            "volume_level": 0.3,
            "is_volume_muted": False,
            "friendly_name": "Smart Speaker",
        },
        last_changed=_now(),
    ),
    "media_player.bedroom_tv": EntityState(
        entity_id="media_player.bedroom_tv",
        state="off",
        attributes={
            "volume_level": 0.4,
            "is_volume_muted": False,
            "source": None,
            "source_list": ["HDMI 1", "HDMI 2", "Netflix"],
            "friendly_name": "Bedroom TV",
        },
        last_changed=_now(),
    ),
}
