"""Webhook support for Strava activity events."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

WEBHOOK_PATH = f"/api/{DOMAIN}/webhook"


class StravaWebhookView(HomeAssistantView):
    """Handle Strava webhook callbacks."""

    url = WEBHOOK_PATH
    name = f"api:{DOMAIN}:webhook"
    requires_auth = False

    def __init__(self, hass: HomeAssistant, verify_token: str) -> None:
        """Initialize the webhook view."""
        self.hass = hass
        self.verify_token = verify_token

    async def get(self, request: web.Request) -> web.Response:
        """Handle Strava webhook subscription verification."""
        # Strava sends a GET request with hub.mode, hub.verify_token, and hub.challenge
        hub_mode = request.query.get("hub.mode")
        hub_verify_token = request.query.get("hub.verify_token")
        hub_challenge = request.query.get("hub.challenge")

        _LOGGER.debug(
            "Received webhook verification: mode=%s, token=%s",
            hub_mode,
            hub_verify_token,
        )

        if hub_mode == "subscribe" and hub_verify_token == self.verify_token:
            _LOGGER.info("Webhook verification successful")
            return web.json_response({"hub.challenge": hub_challenge})

        _LOGGER.warning("Webhook verification failed")
        return web.Response(status=403)

    async def post(self, request: web.Request) -> web.Response:
        """Handle Strava webhook events."""
        try:
            data = await request.json()
            _LOGGER.debug("Received webhook event: %s", data)

            # Validate webhook signature if present
            # Note: Strava doesn't currently sign webhooks, but this is here for future-proofing

            # Process the event
            aspect_type = data.get("aspect_type")  # "create", "update", "delete"
            object_type = data.get("object_type")  # "activity", "athlete"
            object_id = data.get("object_id")
            owner_id = data.get("owner_id")

            if object_type == "activity" and aspect_type in ("create", "update"):
                _LOGGER.info(
                    "Activity %s %sd by athlete %s",
                    object_id,
                    aspect_type,
                    owner_id,
                )

                # Trigger a sync for this user
                # Find the coordinator for this athlete and request an update
                for entry_id, coordinator in self.hass.data.get(DOMAIN, {}).items():
                    if hasattr(coordinator, "athlete_id") and coordinator.athlete_id == owner_id:
                        _LOGGER.info("Triggering sync for entry %s", entry_id)
                        await coordinator.async_request_refresh()
                        break

            return web.Response(status=200)

        except Exception as err:
            _LOGGER.error("Error processing webhook event: %s", err)
            return web.Response(status=500)


async def async_setup_webhook(
    hass: HomeAssistant,
    verify_token: str,
) -> None:
    """Register the webhook view."""
    webhook_view = StravaWebhookView(hass, verify_token)
    hass.http.register_view(webhook_view)
    _LOGGER.info("Webhook registered at %s", WEBHOOK_PATH)


async def async_unregister_webhook(hass: HomeAssistant) -> None:
    """Unregister the webhook view."""
    # Note: Home Assistant doesn't provide a direct way to unregister views
    # This is a placeholder for cleanup if needed
    _LOGGER.info("Webhook cleanup requested")
