"""Tests for Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models import AskRequest, AskResponse, Config, HAAction


class TestHAAction:
    """Tests for HAAction model."""

    def test_create_call_service_action(self) -> None:
        """Test creating valid call_service action."""
        action = HAAction(
            action="call_service",
            service="light.turn_on",
            entity_id="light.living_room",
            data={"brightness": 255},
        )
        assert action.action == "call_service"
        assert action.service == "light.turn_on"
        assert action.entity_id == "light.living_room"
        assert action.data == {"brightness": 255}

    def test_create_none_action(self) -> None:
        """Test creating 'none' action."""
        action = HAAction(action="none")
        assert action.action == "none"
        assert action.service is None
        assert action.entity_id is None
        assert action.data == {}

    def test_invalid_action_type(self) -> None:
        """Test that invalid action types are rejected."""
        with pytest.raises(ValidationError):
            HAAction(action="invalid_action")  # type: ignore

    def test_default_empty_data(self) -> None:
        """Test that data defaults to empty dict."""
        action = HAAction(
            action="call_service", service="light.turn_on", entity_id="light.test"
        )
        assert action.data == {}


class TestAskRequest:
    """Tests for AskRequest model."""

    def test_create_valid_request(self) -> None:
        """Test creating valid request."""
        request = AskRequest(text="Turn on the lights")
        assert request.text == "Turn on the lights"

    def test_empty_text_rejected(self) -> None:
        """Test that empty text is rejected."""
        with pytest.raises(ValidationError):
            AskRequest(text="")

    def test_missing_text_rejected(self) -> None:
        """Test that missing text field is rejected."""
        with pytest.raises(ValidationError):
            AskRequest()  # type: ignore


class TestAskResponse:
    """Tests for AskResponse model."""

    def test_create_success_response(self, sample_turn_on_action: HAAction) -> None:
        """Test creating successful response."""
        response = AskResponse(
            status="success",
            plan=sample_turn_on_action,
            message="Action executed",
            ha_response={"state": "on"},
        )
        assert response.status == "success"
        assert response.plan == sample_turn_on_action
        assert response.message == "Action executed"
        assert response.ha_response == {"state": "on"}

    def test_create_error_response(self) -> None:
        """Test creating error response."""
        response = AskResponse(status="error", message="Failed to process")
        assert response.status == "error"
        assert response.plan is None
        assert response.message == "Failed to process"

    def test_invalid_status(self) -> None:
        """Test that invalid status values are rejected."""
        with pytest.raises(ValidationError):
            AskResponse(status="invalid")  # type: ignore


class TestConfig:
    """Tests for Config model."""

    def test_config_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that Config has sensible defaults."""
        monkeypatch.setenv("HA_TOKEN", "test_token")
        config = Config()
        assert config.ha_token == "test_token"
        assert config.ha_base_url == "http://homeassistant:8123"
        assert config.ollama_base_url == "http://host.docker.internal:11434"
        assert config.ollama_model == "llama3.2:3b"
        assert config.log_level == "INFO"

    def test_config_custom_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that Config accepts custom values."""
        monkeypatch.setenv("HA_TOKEN", "custom_token")
        monkeypatch.setenv("HA_BASE_URL", "http://custom:8888")
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom-ollama:11434")
        monkeypatch.setenv("OLLAMA_MODEL", "custom-model")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        config = Config()
        assert config.ha_token == "custom_token"
        assert config.ha_base_url == "http://custom:8888"
        assert config.ollama_base_url == "http://custom-ollama:11434"
        assert config.ollama_model == "custom-model"
        assert config.log_level == "DEBUG"
