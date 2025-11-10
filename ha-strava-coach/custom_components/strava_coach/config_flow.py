"""Config flow for Strava Coach integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_AGGREGATES_ONLY,
    CONF_HISTORY_WINDOW,
    CONF_LLM_API_KEY,
    CONF_LLM_ENABLED,
    CONF_LLM_MODEL,
    CONF_LLM_PROVIDER,
    CONF_SYNC_TIME,
    DEFAULT_AGGREGATES_ONLY,
    DEFAULT_HISTORY_WINDOW,
    DEFAULT_LLM_ENABLED,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_SYNC_TIME,
    DOMAIN,
    OAUTH2_SCOPES,
)

_LOGGER = logging.getLogger(__name__)


class StravaCoachFlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Config flow to handle Strava Coach OAuth2 authentication."""

    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data to include in the authorization request."""
        return {
            "scope": ",".join(OAUTH2_SCOPES),
            "approval_prompt": "auto",
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        # Check if credentials are in configuration.yaml
        if DOMAIN in self.hass.data and "config" in self.hass.data[DOMAIN]:
            config = self.hass.data[DOMAIN]["config"]
            if CONF_CLIENT_ID in config and CONF_CLIENT_SECRET in config:
                # Import credentials to application_credentials
                await async_import_client_credential(
                    self.hass,
                    DOMAIN,
                    ClientCredential(
                        config[CONF_CLIENT_ID],
                        config[CONF_CLIENT_SECRET],
                    ),
                    DOMAIN,
                )
                _LOGGER.info("Imported Strava credentials from configuration.yaml")

        return await super().async_step_user(user_input)

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> FlowResult:
        """Create an entry for Strava Coach after OAuth."""
        # After successful OAuth, ask for additional preferences
        return await self.async_step_preferences()

    async def async_step_preferences(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle preferences step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate sync time format
            sync_time = user_input.get(CONF_SYNC_TIME, DEFAULT_SYNC_TIME)
            try:
                hours, minutes = sync_time.split(":")
                if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
                    errors[CONF_SYNC_TIME] = "invalid_time"
            except (ValueError, AttributeError):
                errors[CONF_SYNC_TIME] = "invalid_time"

            # Validate history window
            history_window = user_input.get(CONF_HISTORY_WINDOW, DEFAULT_HISTORY_WINDOW)
            if not (7 <= history_window <= 365):
                errors[CONF_HISTORY_WINDOW] = "invalid_window"

            if not errors:
                # Store preferences in data
                self.data.update(user_input)

                # If LLM is enabled, move to LLM config
                if user_input.get(CONF_LLM_ENABLED, DEFAULT_LLM_ENABLED):
                    return await self.async_step_llm()

                # Otherwise create the entry
                return self.async_create_entry(
                    title="Strava Coach",
                    data=self.data,
                )

        return self.async_show_form(
            step_id="preferences",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SYNC_TIME, default=DEFAULT_SYNC_TIME): str,
                    vol.Optional(
                        CONF_HISTORY_WINDOW, default=DEFAULT_HISTORY_WINDOW
                    ): vol.All(vol.Coerce(int), vol.Range(min=7, max=365)),
                    vol.Optional(CONF_LLM_ENABLED, default=DEFAULT_LLM_ENABLED): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_llm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle LLM configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Store LLM configuration
            self.data.update(user_input)

            return self.async_create_entry(
                title="Strava Coach",
                data=self.data,
            )

        return self.async_show_form(
            step_id="llm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LLM_PROVIDER, default=DEFAULT_LLM_PROVIDER): str,
                    vol.Required(CONF_LLM_API_KEY): str,
                    vol.Optional(CONF_LLM_MODEL, default=DEFAULT_LLM_MODEL): str,
                    vol.Optional(
                        CONF_AGGREGATES_ONLY, default=DEFAULT_AGGREGATES_ONLY
                    ): bool,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return StravaCoachOptionsFlowHandler(config_entry)


class StravaCoachOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Strava Coach options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate inputs
            sync_time = user_input.get(
                CONF_SYNC_TIME, self.config_entry.data.get(CONF_SYNC_TIME, DEFAULT_SYNC_TIME)
            )
            try:
                hours, minutes = sync_time.split(":")
                if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
                    errors[CONF_SYNC_TIME] = "invalid_time"
            except (ValueError, AttributeError):
                errors[CONF_SYNC_TIME] = "invalid_time"

            if not errors:
                # Update config entry data
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, **user_input},
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SYNC_TIME,
                        default=self.config_entry.data.get(CONF_SYNC_TIME, DEFAULT_SYNC_TIME),
                    ): str,
                    vol.Optional(
                        CONF_HISTORY_WINDOW,
                        default=self.config_entry.data.get(
                            CONF_HISTORY_WINDOW, DEFAULT_HISTORY_WINDOW
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=7, max=365)),
                    vol.Optional(
                        CONF_LLM_ENABLED,
                        default=self.config_entry.data.get(CONF_LLM_ENABLED, DEFAULT_LLM_ENABLED),
                    ): bool,
                    vol.Optional(
                        CONF_LLM_API_KEY,
                        default=self.config_entry.data.get(CONF_LLM_API_KEY, ""),
                    ): str,
                    vol.Optional(
                        CONF_LLM_MODEL,
                        default=self.config_entry.data.get(CONF_LLM_MODEL, DEFAULT_LLM_MODEL),
                    ): str,
                }
            ),
            errors=errors,
        )
