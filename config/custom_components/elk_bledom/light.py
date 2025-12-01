"""ELK-BLEDOM Light platform."""
from __future__ import annotations

import logging
from typing import Any

from bleak import BleakClient
from bleak.exc import BleakError

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CHARACTERISTIC_UUID,
    CMD_POWER_OFF,
    CMD_POWER_ON,
    DOMAIN,
    SERVICE_UUID,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ELK-BLEDOM light from config entry."""
    address = config_entry.data["address"]
    name = config_entry.data.get("name", "ELK-BLEDOM Light")

    async_add_entities([ElkBledomLight(address, name)], True)


class ElkBledomLight(LightEntity):
    """Representation of an ELK-BLEDOM LED controller."""

    def __init__(self, address: str, name: str) -> None:
        """Initialize the light."""
        self._address = address
        self._attr_name = name
        self._attr_unique_id = f"elk_bledom_{address.replace(':', '')}"
        self._attr_color_mode = ColorMode.RGB
        self._attr_supported_color_modes = {ColorMode.RGB}
        self._is_on = False
        self._brightness = 255
        self._rgb_color = (255, 255, 255)
        self._client: BleakClient | None = None

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._is_on

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return self._brightness

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        """Return the RGB color value."""
        return self._rgb_color

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        try:
            # Update brightness if provided
            if ATTR_BRIGHTNESS in kwargs:
                self._brightness = kwargs[ATTR_BRIGHTNESS]

            # Update color if provided
            if ATTR_RGB_COLOR in kwargs:
                self._rgb_color = kwargs[ATTR_RGB_COLOR]

            # Build command
            if ATTR_RGB_COLOR in kwargs or ATTR_BRIGHTNESS in kwargs:
                # RGB color command: 7E 00 05 03 RR GG BB 00 EF
                r, g, b = self._rgb_color
                brightness_factor = self._brightness / 255
                r = int(r * brightness_factor)
                g = int(g * brightness_factor)
                b = int(b * brightness_factor)
                command = bytearray([0x7E, 0x00, 0x05, 0x03, r, g, b, 0x00, 0xEF])
            else:
                # Simple power on
                command = CMD_POWER_ON

            await self._send_command(command)
            self._is_on = True
            self.async_write_ha_state()

        except Exception as e:
            _LOGGER.error("Failed to turn on light: %s", e)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        try:
            await self._send_command(CMD_POWER_OFF)
            self._is_on = False
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Failed to turn off light: %s", e)

    async def _send_command(self, command: bytearray) -> None:
        """Send command to the device."""
        try:
            async with BleakClient(self._address) as client:
                await client.write_gatt_char(
                    CHARACTERISTIC_UUID,
                    command,
                    response=False,
                )
                _LOGGER.debug("Sent command to %s: %s", self._address, command.hex())
        except BleakError as e:
            _LOGGER.error("BLE communication error: %s", e)
            raise
        except Exception as e:
            _LOGGER.error("Unexpected error sending command: %s", e)
            raise

    async def async_update(self) -> None:
        """Update the light state."""
        # ELK-BLEDOM doesn't support reading state, so we maintain local state
        pass
