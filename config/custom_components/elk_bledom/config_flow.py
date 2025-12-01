"""Config flow for ELK-BLEDOM integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import DEVICE_NAME_PATTERNS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ElkBledomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ELK-BLEDOM."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            name = user_input.get(CONF_NAME, f"ELK-BLEDOM {address[-5:]}")

            # Create unique ID from MAC address
            unique_id = address.replace(":", "").lower()
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=name,
                data={
                    CONF_ADDRESS: address,
                    CONF_NAME: name,
                },
            )

        # Discover BLE devices
        current_addresses = bluetooth.async_discovered_service_info(self.hass)
        discovered_devices = {}

        for service_info in current_addresses:
            if service_info.name:
                for pattern in DEVICE_NAME_PATTERNS:
                    if pattern in service_info.name:
                        discovered_devices[service_info.address] = service_info.name
                        break

        self._discovered_devices = discovered_devices

        if not discovered_devices:
            return self.async_abort(reason="no_devices_found")

        # Build schema with discovered devices
        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(
                    {
                        addr: f"{name} ({addr})"
                        for addr, name in discovered_devices.items()
                    }
                ),
                vol.Optional(CONF_NAME): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle bluetooth discovery."""
        address = discovery_info.address
        name = discovery_info.name or "ELK-BLEDOM"

        # Create unique ID from MAC address
        unique_id = address.replace(":", "").lower()
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        self.context["title_placeholders"] = {"name": name}

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm bluetooth discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=self.context["title_placeholders"]["name"],
                data={
                    CONF_ADDRESS: self.context["bluetooth_address"],
                    CONF_NAME: self.context["title_placeholders"]["name"],
                },
            )

        return self.async_show_form(step_id="bluetooth_confirm")
