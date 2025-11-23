"""Pytest configuration and shared fixtures for AI Gateway tests."""

from __future__ import annotations

import pytest

from app.models import Config, HAAction


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
