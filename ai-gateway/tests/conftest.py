"""Pytest configuration and shared fixtures for AI Gateway tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.models import Config, HAAction
from app.main import app


@pytest.fixture
def mock_config() -> Config:
    """Fixture providing mock configuration.

    Returns:
        Mock Config instance with test values
    """
    return Config(
        ha_token="test_token_123",
        ha_base_url="http://test-ha:8123",
        ollama_base_url="http://test-ollama:11434",
        ollama_model="test-model",
        openai_api_key="test-openai-key",
        ollama_timeout=90.0,
        openai_timeout=30.0,
        ha_timeout=10.0,
        conversation_timeout=30.0,
        intent_confidence_threshold=0.8,
        log_level="DEBUG",
    )


@pytest.fixture
def sample_turn_on_action() -> HAAction:
    """Fixture providing sample 'turn on' action.

    Returns:
        HAAction for turning on living room lights
    """
    return HAAction(
        action="call_service",
        service="light.turn_on",
        entity_id="light.living_room_main",
        data={},
    )


@pytest.fixture
def sample_turn_off_action() -> HAAction:
    """Fixture providing sample 'turn off' action.

    Returns:
        HAAction for turning off kitchen lights
    """
    return HAAction(
        action="call_service",
        service="light.turn_off",
        entity_id="light.kitchen",
        data={},
    )


@pytest.fixture
def sample_brightness_action() -> HAAction:
    """Fixture providing sample brightness adjustment action.

    Returns:
        HAAction for setting bedroom brightness
    """
    return HAAction(
        action="call_service",
        service="light.turn_on",
        entity_id="light.bedroom",
        data={"brightness": 128},
    )


@pytest.fixture
def sample_none_action() -> HAAction:
    """Fixture providing sample 'none' action.

    Returns:
        HAAction indicating no action available
    """
    return HAAction(action="none")


@pytest.fixture
def valid_json_response() -> str:
    """Fixture providing valid JSON response string.

    Returns:
        JSON string representing a valid action
    """
    return '{"action":"call_service","service":"light.turn_on","entity_id":"light.living_room_main","data":{}}'


@pytest.fixture
def invalid_json_response() -> str:
    """Fixture providing invalid JSON response string.

    Returns:
        Malformed JSON string
    """
    return '{"action":"call_service","service":"light.turn_on", INVALID'


@pytest.fixture
def json_with_extra_text() -> str:
    """Fixture providing JSON embedded in extra text.

    Returns:
        JSON string surrounded by additional text
    """
    return 'Sure, here is the action: {"action":"call_service","service":"light.turn_on","entity_id":"light.kitchen","data":{}} - Hope this helps!'


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_ha_states():
    """Mock Home Assistant states."""
    return [
        {
            "entity_id": "light.living_room",
            "state": "off",
            "attributes": {
                "friendly_name": "Living Room Light",
                "supported_features": 63,
            },
        },
        {
            "entity_id": "sensor.temperature",
            "state": "22.5",
            "attributes": {
                "unit_of_measurement": "°C",
                "friendly_name": "Temperature",
            },
        },
    ]


@pytest.fixture
def mock_ha_client(mock_ha_states):
    """Mock HomeAssistantClient."""
    client = MagicMock()
    client.get_states = AsyncMock(return_value=mock_ha_states)
    client.call_service = AsyncMock(return_value={"success": True})
    return client


@pytest.fixture
def mock_mqtt_client():
    """Mock MQTT client."""
    client = MagicMock()
    client.publish = MagicMock()
    client.publish_display_action = MagicMock()
    client.publish_transcript = MagicMock()
    return client
