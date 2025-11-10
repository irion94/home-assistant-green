"""Sensor platform for Strava Coach."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ATL,
    ATTR_COMMAND,
    ATTR_CTL,
    ATTR_MONOTONY,
    ATTR_PARAMS,
    ATTR_RATIONALE,
    ATTR_TSB,
    ATTR_WINDOW_DAYS,
    CONF_HISTORY_WINDOW,
    CONF_LLM_API_KEY,
    CONF_LLM_ENABLED,
    CONF_LLM_MODEL,
    DEFAULT_AGGREGATES_ONLY,
    DEFAULT_HISTORY_WINDOW,
    DEFAULT_LLM_ENABLED,
    DEFAULT_LLM_MODEL,
    DOMAIN,
    SENSOR_FATIGUE,
    SENSOR_FITNESS,
    SENSOR_FORM,
    SENSOR_READINESS,
    SENSOR_SUGGESTION,
)
from .coordinator import StravaCoachDataUpdateCoordinator
from .llm import LLMAdapter, LLMError
from .metrics import suggest_for_date

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Strava Coach sensors from a config entry."""
    coordinator: StravaCoachDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors: list[SensorEntity] = [
        StravaCoachReadinessSensor(coordinator, entry),
        StravaCoachFitnessSensor(coordinator, entry),
        StravaCoachFatigueSensor(coordinator, entry),
        StravaCoachFormSensor(coordinator, entry),
        StravaCoachSuggestionSensor(coordinator, entry),
    ]

    async_add_entities(sensors)


class StravaCoachReadinessSensor(CoordinatorEntity, SensorEntity):
    """Sensor for readiness score (0-100)."""

    _attr_name = "Strava Coach Readiness"
    _attr_icon = "mdi:gauge"
    _attr_native_unit_of_measurement = "%"

    def __init__(
        self,
        coordinator: StravaCoachDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_READINESS}"
        self._entry = entry

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("readiness")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        attrs = {
            ATTR_ATL: self.coordinator.data.get("atl"),
            ATTR_CTL: self.coordinator.data.get("ctl"),
            ATTR_TSB: self.coordinator.data.get("tsb"),
            ATTR_MONOTONY: self.coordinator.data.get("monotony"),
            ATTR_WINDOW_DAYS: self._entry.data.get(CONF_HISTORY_WINDOW, DEFAULT_HISTORY_WINDOW),
        }

        # Add data age information
        if "days_ago" in self.coordinator.data:
            days_ago = self.coordinator.data["days_ago"]
            if days_ago > 0:
                attrs["data_age_days"] = days_ago
                attrs["last_activity_date"] = self.coordinator.data.get("date")

        return attrs


class StravaCoachFitnessSensor(CoordinatorEntity, SensorEntity):
    """Sensor for CTL (Chronic Training Load / Fitness)."""

    _attr_name = "Strava Coach Fitness"
    _attr_icon = "mdi:trending-up"
    _attr_native_unit_of_measurement = "CTL"

    def __init__(
        self,
        coordinator: StravaCoachDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_FITNESS}"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("ctl")


class StravaCoachFatigueSensor(CoordinatorEntity, SensorEntity):
    """Sensor for ATL (Acute Training Load / Fatigue)."""

    _attr_name = "Strava Coach Fatigue"
    _attr_icon = "mdi:tire"
    _attr_native_unit_of_measurement = "ATL"

    def __init__(
        self,
        coordinator: StravaCoachDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_FATIGUE}"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("atl")


class StravaCoachFormSensor(CoordinatorEntity, SensorEntity):
    """Sensor for TSB (Training Stress Balance / Form)."""

    _attr_name = "Strava Coach Form"
    _attr_icon = "mdi:trending-up"
    _attr_native_unit_of_measurement = "TSB"

    def __init__(
        self,
        coordinator: StravaCoachDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_FORM}"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("tsb")


class StravaCoachSuggestionSensor(CoordinatorEntity, SensorEntity):
    """Sensor for today's training suggestion."""

    _attr_name = "Strava Coach Today Suggestion"
    _attr_icon = "mdi:clipboard-text"

    def __init__(
        self,
        coordinator: StravaCoachDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_SUGGESTION}"
        self._entry = entry
        self._suggestion: dict[str, Any] | None = None

    async def async_update(self) -> None:
        """Update the sensor."""
        await super().async_update()

        # Generate suggestion using rules or LLM
        if self.coordinator.data:
            self._suggestion = await self._generate_suggestion()

    async def _generate_suggestion(self) -> dict[str, Any]:
        """Generate suggestion using LLM or rules."""
        metrics = self.coordinator.data

        # Check if LLM is enabled
        llm_enabled = self._entry.data.get(CONF_LLM_ENABLED, DEFAULT_LLM_ENABLED)

        if llm_enabled:
            try:
                api_key = self._entry.data.get(CONF_LLM_API_KEY)
                model = self._entry.data.get(CONF_LLM_MODEL, DEFAULT_LLM_MODEL)

                if not api_key:
                    _LOGGER.warning("LLM enabled but no API key configured")
                else:
                    adapter = LLMAdapter(
                        api_key=api_key,
                        model=model,
                        aggregates_only=DEFAULT_AGGREGATES_ONLY,
                    )

                    # Add date and day_of_week to metrics
                    today = datetime.now()
                    metrics_with_date = {
                        **metrics,
                        "date": today.strftime("%Y-%m-%d"),
                        "day_of_week": today.strftime("%A"),
                        "recent_load_7d": metrics.get("atl", 0.0) * 7,  # Approximate
                    }

                    suggestion = await adapter.generate_suggestion(metrics_with_date)
                    _LOGGER.info("Generated LLM suggestion: %s", suggestion)
                    return suggestion

            except (LLMError, Exception) as err:
                _LOGGER.warning("LLM suggestion failed, falling back to rules: %s", err)

        # Fallback to rules-based suggestion
        today = datetime.now()
        metrics_dict = {
            "readiness": metrics.get("readiness", 50.0),
            "tsb": metrics.get("tsb", 0.0),
            "atl": metrics.get("atl", 0.0),
            "ctl": metrics.get("ctl", 0.0),
            "rest_days": metrics.get("rest_days", 0),
            "recent_load_7d": metrics.get("atl", 0.0) * 7,  # Approximate
        }

        rule_suggestion = suggest_for_date(today, metrics_dict)

        return {
            "command": rule_suggestion.command,
            "params": rule_suggestion.params,
            "rationale_short": rule_suggestion.rationale_short,
        }

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if not self._suggestion:
            return None
        return self._suggestion.get("command")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if not self._suggestion:
            return {}

        return {
            ATTR_COMMAND: self._suggestion.get("command"),
            ATTR_PARAMS: self._suggestion.get("params", {}),
            ATTR_RATIONALE: self._suggestion.get("rationale_short"),
        }
