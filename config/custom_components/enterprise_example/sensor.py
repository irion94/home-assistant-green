from __future__ import annotations
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN

async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    add_entities([EnterpriseHelloSensor()])

class EnterpriseHelloSensor(SensorEntity):
    _attr_name = "Enterprise Hello"
    _attr_unique_id = "enterprise_hello_1"
    @property
    def state(self):
        return "world"
    @property
    def icon(self):
        return "mdi:briefcase-account"
