from __future__ import annotations
from homeassistant.core import HomeAssistant
from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    # YAML-based setup (optional if you also implement config_flow)
    hass.states.async_set(f"{DOMAIN}.status", "ok")
    return True

async def async_setup_entry(hass: HomeAssistant, entry):
    # UI config_flow entries (not implemented yet)
    return True
