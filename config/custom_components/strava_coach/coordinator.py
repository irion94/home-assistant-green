"""DataUpdateCoordinator for Strava Coach."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import (
    OAuth2Session,
    async_get_config_entry_implementation,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import StravaAPIClient
from .const import (
    CONF_HISTORY_WINDOW,
    DEFAULT_ATL_DAYS,
    DEFAULT_CTL_DAYS,
    DEFAULT_HISTORY_WINDOW,
    DOMAIN,
    UPDATE_INTERVAL,
)
from .db import Activity, DailyMetrics, SyncState, get_session
from .metrics import (
    calculate_atl_ctl_tsb,
    calculate_readiness,
    calculate_training_load,
)

_LOGGER = logging.getLogger(__name__)


class StravaCoachDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Strava Coach data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self.athlete_id: int | None = None
        self._api_client: StravaAPIClient | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Strava and compute metrics."""
        try:
            # Initialize API client if not already done
            if self._api_client is None:
                await self._initialize_api_client()

            # Sync activities from Strava
            await self._sync_activities()

            # Compute daily metrics
            await self._compute_metrics()

            # Get today's metrics
            today_metrics = await self._get_today_metrics()

            return today_metrics

        except Exception as err:
            _LOGGER.error("Error updating Strava Coach data: %s", err)
            raise UpdateFailed(f"Error updating data: {err}") from err

    async def _initialize_api_client(self) -> None:
        """Initialize the Strava API client with OAuth session."""
        implementation = await async_get_config_entry_implementation(self.hass, self.entry)

        session = OAuth2Session(self.hass, self.entry, implementation)

        self._api_client = StravaAPIClient(self.hass, session)

        # Get athlete info to store athlete_id
        athlete = await self._api_client.get_athlete()
        self.athlete_id = athlete["id"]
        _LOGGER.info("Initialized API client for athlete %s", self.athlete_id)

    async def _sync_activities(self) -> None:
        """Sync recent activities from Strava."""
        if not self._api_client or not self.athlete_id:
            raise UpdateFailed("API client not initialized")

        history_window = self.entry.data.get(CONF_HISTORY_WINDOW, DEFAULT_HISTORY_WINDOW)

        # Calculate sync window
        now = datetime.now()
        after_timestamp = int((now - timedelta(days=history_window)).timestamp())

        _LOGGER.debug("Syncing activities after %s", datetime.fromtimestamp(after_timestamp))

        # Fetch activities from Strava
        activities = await self._api_client.get_activities(after=after_timestamp, per_page=200)

        _LOGGER.info("Fetched %d activities from Strava", len(activities))

        # Store activities in database
        def _store_activities() -> None:
            with get_session() as session:
                for activity_data in activities:
                    # Check if activity already exists
                    existing = (
                        session.query(Activity)
                        .filter_by(id=activity_data["id"])
                        .first()
                    )

                    # Calculate training load
                    training_load = calculate_training_load(activity_data)

                    if existing:
                        # Update existing
                        existing.training_load = training_load
                        existing.synced_at = datetime.utcnow()
                    else:
                        # Create new activity
                        activity = Activity(
                            id=activity_data["id"],
                            athlete_id=self.athlete_id,
                            name=activity_data.get("name", "Untitled"),
                            sport_type=activity_data.get("sport_type", "Workout"),
                            start_date=datetime.fromisoformat(
                                activity_data["start_date"].replace("Z", "+00:00")
                            ),
                            start_date_local=datetime.fromisoformat(
                                activity_data["start_date_local"]
                            ),
                            timezone=activity_data.get("timezone"),
                            moving_time=activity_data.get("moving_time", 0),
                            elapsed_time=activity_data.get("elapsed_time", 0),
                            distance=activity_data.get("distance", 0.0),
                            total_elevation_gain=activity_data.get("total_elevation_gain"),
                            average_heartrate=activity_data.get("average_heartrate"),
                            max_heartrate=activity_data.get("max_heartrate"),
                            average_watts=activity_data.get("average_watts"),
                            weighted_average_watts=activity_data.get("weighted_average_watts"),
                            kilojoules=activity_data.get("kilojoules"),
                            training_load=training_load,
                        )
                        session.add(activity)

                # Update sync state
                sync_state = (
                    session.query(SyncState)
                    .filter_by(athlete_id=self.athlete_id)
                    .first()
                )

                if not sync_state:
                    sync_state = SyncState(athlete_id=self.athlete_id)
                    session.add(sync_state)

                sync_state.last_sync_at = datetime.utcnow()
                sync_state.total_activities = len(activities)

        await self.hass.async_add_executor_job(_store_activities)

    async def _compute_metrics(self) -> None:
        """Compute daily metrics from activities."""
        if not self.athlete_id:
            return

        def _compute() -> None:
            with get_session() as session:
                # Get all activities for this athlete
                activities = (
                    session.query(Activity)
                    .filter_by(athlete_id=self.athlete_id)
                    .order_by(Activity.start_date)
                    .all()
                )

                if not activities:
                    _LOGGER.warning("No activities found for athlete %s", self.athlete_id)
                    return

                # Group activities by date and sum training load
                daily_loads: dict[datetime, float] = {}
                for activity in activities:
                    date = activity.start_date_local.date()
                    date_dt = datetime.combine(date, datetime.min.time())
                    daily_loads[date_dt] = daily_loads.get(date_dt, 0.0) + (
                        activity.training_load or 0.0
                    )

                # Convert to sorted list
                load_list = sorted(daily_loads.items(), key=lambda x: x[0])

                # Calculate ATL/CTL/TSB
                fitness_metrics = calculate_atl_ctl_tsb(
                    load_list, atl_days=DEFAULT_ATL_DAYS, ctl_days=DEFAULT_CTL_DAYS
                )

                # Store metrics in database
                for date, metrics in fitness_metrics.items():
                    # Calculate rest days
                    rest_days = 0
                    check_date = date - timedelta(days=1)
                    while check_date not in daily_loads and rest_days < 7:
                        rest_days += 1
                        check_date -= timedelta(days=1)

                    # Calculate readiness
                    readiness = calculate_readiness(
                        tsb=metrics.tsb,
                        monotony=metrics.monotony,
                        rest_days=rest_days,
                        atl=metrics.atl,
                        ctl=metrics.ctl,
                    )

                    # Check if metrics already exist
                    existing = (
                        session.query(DailyMetrics)
                        .filter_by(athlete_id=self.athlete_id, date=date)
                        .first()
                    )

                    if existing:
                        # Update
                        existing.atl = metrics.atl
                        existing.ctl = metrics.ctl
                        existing.tsb = metrics.tsb
                        existing.monotony = metrics.monotony
                        existing.readiness = readiness
                        existing.rest_days = rest_days
                        existing.computed_at = datetime.utcnow()
                    else:
                        # Create new
                        daily_metric = DailyMetrics(
                            athlete_id=self.athlete_id,
                            date=date,
                            atl=metrics.atl,
                            ctl=metrics.ctl,
                            tsb=metrics.tsb,
                            monotony=metrics.monotony,
                            readiness=readiness,
                            rest_days=rest_days,
                        )
                        session.add(daily_metric)

                _LOGGER.info("Computed metrics for %d days", len(fitness_metrics))

        await self.hass.async_add_executor_job(_compute)

    async def _get_today_metrics(self) -> dict[str, Any]:
        """Get today's metrics from database, or most recent if today unavailable."""
        if not self.athlete_id:
            return {}

        def _get() -> dict[str, Any]:
            with get_session() as session:
                today = datetime.now().date()
                today_dt = datetime.combine(today, datetime.min.time())

                # Try to get today's metrics first
                metrics = (
                    session.query(DailyMetrics)
                    .filter_by(athlete_id=self.athlete_id, date=today_dt)
                    .first()
                )

                # If no metrics for today, get the most recent available
                if not metrics:
                    _LOGGER.info("No metrics for today, fetching most recent available")
                    metrics = (
                        session.query(DailyMetrics)
                        .filter_by(athlete_id=self.athlete_id)
                        .order_by(DailyMetrics.date.desc())
                        .first()
                    )

                if not metrics:
                    _LOGGER.warning("No metrics found for athlete %s", self.athlete_id)
                    return {}

                # Calculate days since these metrics
                days_ago = (today - metrics.date.date()).days
                metric_date_str = metrics.date.strftime("%Y-%m-%d")

                if days_ago > 0:
                    _LOGGER.info(
                        "Showing metrics from %s (%d days ago)",
                        metric_date_str,
                        days_ago,
                    )

                return {
                    "readiness": metrics.readiness,
                    "atl": metrics.atl,
                    "ctl": metrics.ctl,
                    "tsb": metrics.tsb,
                    "monotony": metrics.monotony,
                    "rest_days": metrics.rest_days,
                    "date": metrics.date,
                    "days_ago": days_ago,  # Add this so UI can show age
                }

        return await self.hass.async_add_executor_job(_get)

    async def async_shutdown(self) -> None:
        """Cleanup coordinator resources."""
        _LOGGER.debug("Shutting down coordinator")
        # Cleanup if needed
