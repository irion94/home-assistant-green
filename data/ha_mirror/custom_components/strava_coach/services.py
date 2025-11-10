"""Services for Strava Coach."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_DATE,
    ATTR_USE_LLM,
    ATTR_WINDOW_DAYS_PARAM,
    DOMAIN,
    SERVICE_GENERATE_SUGGESTION,
    SERVICE_SYNC_NOW,
)
from .coordinator import StravaCoachDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Service schemas
SYNC_NOW_SCHEMA = vol.Schema({})

GENERATE_SUGGESTION_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DATE): cv.string,
        vol.Optional(ATTR_WINDOW_DAYS_PARAM): cv.positive_int,
        vol.Optional(ATTR_USE_LLM): cv.boolean,
    }
)


async def async_setup_services(
    hass: HomeAssistant,
    coordinator: StravaCoachDataUpdateCoordinator,
) -> None:
    """Set up services for Strava Coach."""

    async def handle_sync_now(call: ServiceCall) -> None:
        """Handle sync_now service call."""
        _LOGGER.info("Manual sync requested")

        try:
            await coordinator.async_request_refresh()
            _LOGGER.info("Manual sync completed successfully")

            # Send notification
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Strava Coach Sync",
                    "message": "Manual sync completed successfully",
                    "notification_id": "strava_coach_sync",
                },
            )

        except Exception as err:
            _LOGGER.error("Manual sync failed: %s", err)
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Strava Coach Sync Failed",
                    "message": f"Error during sync: {err}",
                    "notification_id": "strava_coach_sync_error",
                },
            )

    async def handle_generate_suggestion(call: ServiceCall) -> None:
        """Handle generate_suggestion service call."""
        date_str = call.data.get(ATTR_DATE)
        use_llm = call.data.get(ATTR_USE_LLM, False)

        # Parse date or use today
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                _LOGGER.error("Invalid date format: %s", date_str)
                return
        else:
            target_date = datetime.now()

        _LOGGER.info(
            "Generating suggestion for %s (use_llm=%s)",
            target_date.strftime("%Y-%m-%d"),
            use_llm,
        )

        # For now, just trigger a notification with current suggestion
        # In a full implementation, you'd regenerate the suggestion for the specified date

        suggestion_entity_id = f"sensor.strava_coach_{DOMAIN}_suggestion"

        try:
            state = hass.states.get(suggestion_entity_id)
            if state:
                command = state.state
                rationale = state.attributes.get("rationale_short", "No rationale available")

                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "Strava Coach Suggestion",
                        "message": f"**{command}**\n\n{rationale}",
                        "notification_id": "strava_coach_suggestion",
                    },
                )
            else:
                _LOGGER.warning("Suggestion sensor not found")

        except Exception as err:
            _LOGGER.error("Failed to generate suggestion: %s", err)

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC_NOW,
        handle_sync_now,
        schema=SYNC_NOW_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_SUGGESTION,
        handle_generate_suggestion,
        schema=GENERATE_SUGGESTION_SCHEMA,
    )

    _LOGGER.info("Strava Coach services registered")
