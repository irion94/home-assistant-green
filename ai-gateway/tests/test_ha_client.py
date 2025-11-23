"""Tests for Home Assistant client."""

from __future__ import annotations

from app.models import Config
from app.services.ha_client import HomeAssistantClient


class TestHomeAssistantClient:
    """Tests for HomeAssistantClient."""

    def test_get_headers(self, mock_config: Config) -> None:
        """Test that authorization headers are correctly formatted."""
        client = HomeAssistantClient(mock_config)
        headers = client._get_headers()

        assert headers["Authorization"] == "Bearer test_token_123"
        assert headers["Content-Type"] == "application/json"

    def test_client_initialization(self, mock_config: Config) -> None:
        """Test client initialization with config."""
        client = HomeAssistantClient(mock_config)

        assert client.base_url == "http://test-ha:8123"
        assert client.token == "test_token_123"
        assert client.timeout == mock_config.ha_timeout
