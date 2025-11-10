"""Pytest configuration and fixtures for Strava Coach tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance for testing."""
    # This would normally use pytest-homeassistant-custom-component
    # For now, providing a minimal fixture
    return None


@pytest.fixture
def sample_activity_data() -> dict[str, str | int | float]:
    """Sample Strava activity data for testing."""
    return {
        "id": 123456789,
        "athlete_id": 987654,
        "name": "Morning Ride",
        "sport_type": "Ride",
        "start_date": "2025-01-15T07:00:00Z",
        "start_date_local": "2025-01-15T08:00:00",
        "timezone": "Europe/Warsaw",
        "moving_time": 3600,
        "elapsed_time": 3900,
        "distance": 30000.0,
        "total_elevation_gain": 500.0,
        "average_heartrate": 155.0,
        "max_heartrate": 178.0,
        "average_watts": 245.0,
        "weighted_average_watts": 255.0,
        "kilojoules": 920.0,
    }


@pytest.fixture
def sample_metrics() -> dict[str, str | int | float]:
    """Sample aggregated metrics for testing."""
    return {
        "readiness": 72.0,
        "tsb": 3.5,
        "atl": 78.0,
        "ctl": 81.5,
        "monotony": 3.2,
        "rest_days": 1,
        "recent_load_7d": 525.0,
        "date": "2025-01-15",
        "day_of_week": "Wednesday",
    }
