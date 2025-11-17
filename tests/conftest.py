"""Test fixtures for Home Assistant custom components."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

# Mark all tests as async by default
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_hass() -> Generator[HomeAssistant, None, None]:
    """Create a mock Home Assistant instance for testing.

    Returns:
        A mocked HomeAssistant instance with basic functionality.
    """
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.states = MagicMock()
    hass.services = MagicMock()
    hass.config_entries = MagicMock()
    hass.bus = MagicMock()
    hass.loop = MagicMock()

    # Mock async methods
    hass.async_add_executor_job = AsyncMock()
    hass.async_create_task = MagicMock()
    hass.async_block_till_done = AsyncMock()

    yield hass


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Create a mock ConfigEntry for testing.

    Returns:
        A ConfigEntry with test data for Strava integrations.
    """
    return ConfigEntry(
        version=1,
        minor_version=0,
        domain="test_integration",
        title="Test Integration",
        data={
            CONF_CLIENT_ID: "test_client_id",
            CONF_CLIENT_SECRET: "test_client_secret",
        },
        source="user",
        unique_id="test_unique_id",
    )


@pytest.fixture
def mock_config() -> ConfigType:
    """Create a mock configuration dict for testing.

    Returns:
        A dictionary with test configuration data.
    """
    return {
        "test_integration": {
            CONF_CLIENT_ID: "test_client_id",
            CONF_CLIENT_SECRET: "test_client_secret",
        }
    }


@pytest.fixture
def mock_aiohttp_session() -> Generator[AsyncMock, None, None]:
    """Create a mock aiohttp ClientSession.

    Returns:
        A mocked aiohttp.ClientSession for API calls.
    """
    with patch("aiohttp.ClientSession") as mock_session:
        session = AsyncMock()
        mock_session.return_value = session

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        mock_response.text = AsyncMock(return_value='{"status": "ok"}')

        session.get = AsyncMock(return_value=mock_response)
        session.post = AsyncMock(return_value=mock_response)
        session.close = AsyncMock()

        yield session


@pytest.fixture
def mock_entity_registry() -> MagicMock:
    """Create a mock entity registry.

    Returns:
        A mocked entity registry with common operations.
    """
    registry = MagicMock()
    registry.entities = {}
    registry.async_get = MagicMock(return_value=None)
    registry.async_get_entity_id = MagicMock(return_value=None)
    return registry


@pytest.fixture
def mock_device_registry() -> MagicMock:
    """Create a mock device registry.

    Returns:
        A mocked device registry with common operations.
    """
    registry = MagicMock()
    registry.devices = {}
    registry.async_get = MagicMock(return_value=None)
    registry.async_get_device = MagicMock(return_value=None)
    return registry


@pytest.fixture
def sample_strava_activity() -> dict[str, Any]:
    """Create sample Strava activity data for testing.

    Returns:
        A dictionary representing a Strava activity response.
    """
    return {
        "id": 12345678,
        "name": "Morning Run",
        "type": "Run",
        "distance": 5000.0,  # meters
        "moving_time": 1800,  # seconds
        "elapsed_time": 1900,  # seconds
        "total_elevation_gain": 50.0,  # meters
        "start_date": "2024-01-15T06:00:00Z",
        "average_speed": 2.78,  # m/s
        "max_speed": 3.5,  # m/s
        "average_heartrate": 145.0,
        "max_heartrate": 165.0,
        "suffer_score": 42,
    }


@pytest.fixture
def sample_strava_athlete() -> dict[str, Any]:
    """Create sample Strava athlete data for testing.

    Returns:
        A dictionary representing a Strava athlete response.
    """
    return {
        "id": 123456,
        "username": "test_athlete",
        "firstname": "Test",
        "lastname": "Athlete",
        "city": "Test City",
        "state": "Test State",
        "country": "Test Country",
        "sex": "M",
        "weight": 70.0,
    }


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> None:
    """Enable custom integrations for all tests.

    This fixture is autouse=True, so it runs for every test automatically.
    It uses the pytest-homeassistant-custom-component fixture.
    """
    # This fixture is provided by pytest-homeassistant-custom-component
    # and automatically enables custom integrations during tests
    pass


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Mock successful setup of a config entry.

    Returns:
        An AsyncMock that returns True for setup operations.
    """
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_setup", return_value=True
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_unload_entry() -> Generator[AsyncMock, None, None]:
    """Mock successful unload of a config entry.

    Returns:
        An AsyncMock that returns True for unload operations.
    """
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload", return_value=True
    ) as mock_unload:
        yield mock_unload
