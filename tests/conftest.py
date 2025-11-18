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


# ============================================================================
# Test Data Factories
# ============================================================================


@pytest.fixture
def automation_factory() -> type[AutomationFactory]:
    """Provide AutomationFactory class for creating test automations.

    Returns:
        AutomationFactory class
    """
    return AutomationFactory


@pytest.fixture
def service_call_factory() -> type[ServiceCallFactory]:
    """Provide ServiceCallFactory class for creating test service calls.

    Returns:
        ServiceCallFactory class
    """
    return ServiceCallFactory


class AutomationFactory:
    """Factory for creating test automation configurations."""

    @staticmethod
    def create_simple_automation(
        automation_id: str = "test_auto",
        alias: str = "Test Automation",
        trigger_platform: str = "state",
        action_service: str = "light.turn_on",
    ) -> dict[str, Any]:
        """Create a simple automation configuration.

        Args:
            automation_id: Unique ID for the automation
            alias: Human-readable alias
            trigger_platform: Trigger platform (state, time, etc.)
            action_service: Service to call in action

        Returns:
            Dictionary representing an automation
        """
        return {
            "id": automation_id,
            "alias": alias,
            "description": f"Test automation: {alias}",
            "trigger": {
                "platform": trigger_platform,
                "entity_id": "sensor.test",
            },
            "action": {
                "service": action_service,
                "entity_id": "light.test",
            },
        }

    @staticmethod
    def create_automation_with_condition(
        automation_id: str = "test_auto_cond",
        condition_type: str = "state",
    ) -> dict[str, Any]:
        """Create an automation with conditions.

        Args:
            automation_id: Unique ID for the automation
            condition_type: Type of condition (state, numeric_state, etc.)

        Returns:
            Dictionary representing an automation with conditions
        """
        return {
            "id": automation_id,
            "alias": "Automation with Condition",
            "trigger": {
                "platform": "state",
                "entity_id": "sensor.test",
            },
            "condition": {
                "condition": condition_type,
                "entity_id": "binary_sensor.test",
                "state": "on",
            },
            "action": {
                "service": "notify.notify",
                "data": {
                    "message": "Condition met",
                },
            },
        }

    @staticmethod
    def create_automation_with_multiple_triggers(
        automation_id: str = "test_multi_trigger",
    ) -> dict[str, Any]:
        """Create an automation with multiple triggers.

        Args:
            automation_id: Unique ID for the automation

        Returns:
            Dictionary representing an automation with multiple triggers
        """
        return {
            "id": automation_id,
            "alias": "Multi-trigger Automation",
            "trigger": [
                {
                    "platform": "state",
                    "entity_id": "sensor.temperature",
                },
                {
                    "platform": "time",
                    "at": "12:00:00",
                },
                {
                    "platform": "numeric_state",
                    "entity_id": "sensor.humidity",
                    "above": 70,
                },
            ],
            "action": {
                "service": "script.handle_trigger",
            },
        }


class ServiceCallFactory:
    """Factory for creating test service call data."""

    @staticmethod
    def create_light_service_call(
        service: str = "turn_on",
        entity_id: str = "light.test",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a light service call.

        Args:
            service: Service name (turn_on, turn_off, toggle)
            entity_id: Entity ID to target
            **kwargs: Additional service data (brightness, color, etc.)

        Returns:
            Dictionary representing a service call
        """
        data: dict[str, Any] = {"entity_id": entity_id}
        data.update(kwargs)

        return {
            "domain": "light",
            "service": service,
            "service_data": data,
        }

    @staticmethod
    def create_climate_service_call(
        temperature: float = 22.0,
        entity_id: str = "climate.test",
    ) -> dict[str, Any]:
        """Create a climate service call.

        Args:
            temperature: Target temperature
            entity_id: Entity ID to target

        Returns:
            Dictionary representing a climate service call
        """
        return {
            "domain": "climate",
            "service": "set_temperature",
            "service_data": {
                "entity_id": entity_id,
                "temperature": temperature,
            },
        }

    @staticmethod
    def create_notify_service_call(
        message: str = "Test notification",
        title: str | None = None,
    ) -> dict[str, Any]:
        """Create a notification service call.

        Args:
            message: Notification message
            title: Optional notification title

        Returns:
            Dictionary representing a notification service call
        """
        data: dict[str, Any] = {"message": message}
        if title:
            data["title"] = title

        return {
            "domain": "notify",
            "service": "notify",
            "service_data": data,
        }


# ============================================================================
# Mock State Factories
# ============================================================================


@pytest.fixture
def state_factory() -> type[StateFactory]:
    """Provide StateFactory class for creating test entity states.

    Returns:
        StateFactory class
    """
    return StateFactory


class StateFactory:
    """Factory for creating test entity states."""

    @staticmethod
    def create_sensor_state(
        entity_id: str = "sensor.test",
        state: str = "10",
        unit: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a sensor state.

        Args:
            entity_id: Entity ID
            state: State value
            unit: Unit of measurement
            attributes: Additional attributes

        Returns:
            Dictionary representing an entity state
        """
        attrs = attributes or {}
        if unit:
            attrs["unit_of_measurement"] = unit

        return {
            "entity_id": entity_id,
            "state": state,
            "attributes": attrs,
        }

    @staticmethod
    def create_binary_sensor_state(
        entity_id: str = "binary_sensor.test",
        state: str = "on",
        device_class: str | None = None,
    ) -> dict[str, Any]:
        """Create a binary sensor state.

        Args:
            entity_id: Entity ID
            state: State ("on" or "off")
            device_class: Device class (motion, door, etc.)

        Returns:
            Dictionary representing a binary sensor state
        """
        attrs: dict[str, Any] = {}
        if device_class:
            attrs["device_class"] = device_class

        return {
            "entity_id": entity_id,
            "state": state,
            "attributes": attrs,
        }

    @staticmethod
    def create_climate_state(
        entity_id: str = "climate.test",
        temperature: float = 22.0,
        target_temperature: float = 21.0,
        hvac_mode: str = "heat",
    ) -> dict[str, Any]:
        """Create a climate entity state.

        Args:
            entity_id: Entity ID
            temperature: Current temperature
            target_temperature: Target temperature
            hvac_mode: HVAC mode (heat, cool, auto, off)

        Returns:
            Dictionary representing a climate state
        """
        return {
            "entity_id": entity_id,
            "state": hvac_mode,
            "attributes": {
                "current_temperature": temperature,
                "temperature": target_temperature,
                "hvac_mode": hvac_mode,
            },
        }
