"""Application credentials platform for Strava Coach."""

from __future__ import annotations

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant

from .const import OAUTH2_AUTHORIZE, OAUTH2_TOKEN, STRAVA_AUTH_URL, STRAVA_TOKEN_URL


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server for Strava OAuth2."""
    return AuthorizationServer(
        authorize_url=STRAVA_AUTH_URL,
        token_url=STRAVA_TOKEN_URL,
    )


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Return description placeholders for the credentials dialog."""
    return {
        "oauth_url": "https://www.strava.com/settings/api",
        "more_info_url": "https://developers.strava.com/docs/getting-started/",
    }
