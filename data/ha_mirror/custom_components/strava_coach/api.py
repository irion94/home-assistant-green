"""Strava API client with rate limiting and token refresh."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

from .const import (
    STRAVA_API_BASE,
    STRAVA_RATE_LIMIT_15MIN,
    STRAVA_RATE_LIMIT_DAILY,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class RateLimitTracker:
    """Track rate limit usage for Strava API."""

    short_term: deque[datetime]  # 15-minute window
    daily: deque[datetime]  # Daily window

    def __init__(self) -> None:
        """Initialize rate limit tracker."""
        self.short_term = deque()
        self.daily = deque()

    def _clean_old_requests(self, window: deque[datetime], duration: timedelta) -> None:
        """Remove requests older than the window duration."""
        cutoff = datetime.now() - duration
        while window and window[0] < cutoff:
            window.popleft()

    def can_make_request(self) -> bool:
        """Check if we can make a request without exceeding limits."""
        now = datetime.now()

        # Clean old requests
        self._clean_old_requests(self.short_term, timedelta(minutes=15))
        self._clean_old_requests(self.daily, timedelta(days=1))

        # Check limits
        if len(self.short_term) >= STRAVA_RATE_LIMIT_15MIN:
            _LOGGER.warning("15-minute rate limit reached")
            return False

        if len(self.daily) >= STRAVA_RATE_LIMIT_DAILY:
            _LOGGER.warning("Daily rate limit reached")
            return False

        return True

    def record_request(self) -> None:
        """Record a request to both trackers."""
        now = datetime.now()
        self.short_term.append(now)
        self.daily.append(now)

    def time_until_next_slot(self) -> float:
        """Calculate seconds until next available request slot."""
        self._clean_old_requests(self.short_term, timedelta(minutes=15))
        self._clean_old_requests(self.daily, timedelta(days=1))

        if len(self.short_term) >= STRAVA_RATE_LIMIT_15MIN:
            # Wait until oldest request in 15-min window expires
            oldest = self.short_term[0]
            wait_until = oldest + timedelta(minutes=15)
            return (wait_until - datetime.now()).total_seconds()

        if len(self.daily) >= STRAVA_RATE_LIMIT_DAILY:
            # Wait until oldest request in daily window expires
            oldest = self.daily[0]
            wait_until = oldest + timedelta(days=1)
            return (wait_until - datetime.now()).total_seconds()

        return 0


class StravaAPIClient:
    """Strava API client with OAuth2 and rate limiting."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: OAuth2Session,
    ) -> None:
        """Initialize the Strava API client."""
        self.hass = hass
        self.oauth_session = session
        self.rate_limiter = RateLimitTracker()
        self._lock = asyncio.Lock()

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make a rate-limited request to the Strava API."""
        async with self._lock:
            # Wait if rate limit is exceeded
            if not self.rate_limiter.can_make_request():
                wait_time = self.rate_limiter.time_until_next_slot()
                _LOGGER.info("Rate limit reached, waiting %.1f seconds", wait_time)
                await asyncio.sleep(wait_time)

            url = f"{STRAVA_API_BASE}/{endpoint.lstrip('/')}"

            # Ensure we have a valid token
            await self.oauth_session.async_ensure_token_valid()

            headers = {
                "Authorization": f"Bearer {self.oauth_session.token['access_token']}",
            }

            max_retries = 3
            retry_delay = 1.0

            for attempt in range(max_retries):
                try:
                    async with aiohttp.ClientSession() as client:
                        async with client.request(
                            method, url, headers=headers, **kwargs
                        ) as response:
                            # Record successful request
                            self.rate_limiter.record_request()

                            if response.status == 429:
                                # Rate limit hit despite our tracking
                                _LOGGER.warning("Strava API rate limit exceeded")
                                await asyncio.sleep(60)  # Wait 1 minute
                                continue

                            if response.status == 401:
                                # Unauthorized - token may be invalid
                                _LOGGER.error("Strava API unauthorized")
                                raise StravaAPIError("Unauthorized")

                            response.raise_for_status()
                            return await response.json()

                except aiohttp.ClientError as err:
                    _LOGGER.warning(
                        "Request failed (attempt %d/%d): %s",
                        attempt + 1,
                        max_retries,
                        err,
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (2**attempt))
                    else:
                        raise StravaAPIError(f"Request failed after {max_retries} attempts") from err

            raise StravaAPIError("Request failed")

    async def get_athlete(self) -> dict[str, Any]:
        """Get the authenticated athlete's profile."""
        return await self._request("GET", "/athlete")  # type: ignore[return-value]

    async def get_activities(
        self,
        before: int | None = None,
        after: int | None = None,
        page: int = 1,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """Get athlete's activities.

        Args:
            before: Unix timestamp to get activities before
            after: Unix timestamp to get activities after
            page: Page number
            per_page: Number of activities per page (max 200)

        Returns:
            List of activity summaries
        """
        params: dict[str, Any] = {
            "page": page,
            "per_page": min(per_page, 200),
        }
        if before is not None:
            params["before"] = before
        if after is not None:
            params["after"] = after

        return await self._request("GET", "/athlete/activities", params=params)  # type: ignore[return-value]

    async def get_activity(self, activity_id: int) -> dict[str, Any]:
        """Get detailed information about a specific activity.

        Args:
            activity_id: Strava activity ID

        Returns:
            Detailed activity data
        """
        return await self._request("GET", f"/activities/{activity_id}")  # type: ignore[return-value]

    async def get_activity_streams(
        self,
        activity_id: int,
        keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get activity streams (time series data).

        Args:
            activity_id: Strava activity ID
            keys: Stream types to request (e.g., ["time", "heartrate", "watts"])

        Returns:
            Activity stream data
        """
        if keys is None:
            keys = ["time", "heartrate", "watts", "altitude", "distance"]

        params = {"keys": ",".join(keys), "key_by_type": "true"}

        return await self._request(  # type: ignore[return-value]
            "GET", f"/activities/{activity_id}/streams", params=params
        )


class StravaAPIError(Exception):
    """Exception raised for Strava API errors."""

    pass
