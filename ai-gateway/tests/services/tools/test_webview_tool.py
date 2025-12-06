"""Tests for WebViewTool."""

import pytest
from unittest.mock import MagicMock, patch
from app.services.tools.webview_tool import WebViewTool


@pytest.fixture
def webview_tool():
    """Fixture providing WebViewTool instance."""
    return WebViewTool()


class TestWebViewTool:
    """Test suite for WebViewTool."""

    def test_tool_name(self, webview_tool):
        """Test tool name is correct."""
        assert webview_tool.name == "open_website"

    def test_schema_structure(self, webview_tool):
        """Test schema has required OpenAI structure."""
        schema = webview_tool.schema
        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "open_website"
        assert "parameters" in schema["function"]

    def test_schema_required_params(self, webview_tool):
        """Test schema requires 'url' parameter."""
        schema = webview_tool.schema
        params = schema["function"]["parameters"]
        assert "url" in params["properties"]
        assert "url" in params["required"]

    @pytest.mark.asyncio
    @patch("app.services.tools.webview_tool.get_url_validator")
    async def test_successful_execution_with_https(self, mock_validator, webview_tool):
        """Test successful URL opening with https://."""
        # Mock URL validator
        mock_val = MagicMock()
        mock_val.validate.return_value = (True, "https://example.com", None)
        mock_validator.return_value = mock_val

        result = await webview_tool.execute(
            arguments={"url": "https://example.com"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert "example.com" in result.content
        assert result.metadata["url"] == "https://example.com"

    @pytest.mark.asyncio
    @patch("app.services.tools.webview_tool.get_url_validator")
    async def test_url_normalization(self, mock_validator, webview_tool):
        """Test URL normalization adds https:// prefix."""
        mock_val = MagicMock()
        mock_val.validate.return_value = (True, "https://weather.com", None)
        mock_validator.return_value = mock_val

        result = await webview_tool.execute(
            arguments={"url": "weather.com"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert result.metadata["url"] == "https://weather.com"

    @pytest.mark.asyncio
    @patch("app.services.tools.webview_tool.get_url_validator")
    async def test_invalid_url_rejected(self, mock_validator, webview_tool):
        """Test invalid URL is rejected."""
        mock_val = MagicMock()
        mock_val.validate.return_value = (False, None, "Domain not in allowlist")
        mock_validator.return_value = mock_val

        result = await webview_tool.execute(
            arguments={"url": "https://malicious.com"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "Cannot open URL" in result.content
        assert "url_validation_failed" in result.metadata["error"]

    @pytest.mark.asyncio
    @patch("app.services.tools.webview_tool.get_url_validator")
    async def test_missing_url_argument(self, mock_validator, webview_tool):
        """Test missing URL argument fails validation."""
        mock_val = MagicMock()
        mock_val.validate.return_value = (False, None, "Invalid URL")
        mock_validator.return_value = mock_val

        result = await webview_tool.execute(
            arguments={},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False

    @pytest.mark.asyncio
    @patch("app.services.tools.webview_tool.get_url_validator")
    async def test_display_action_published(self, mock_validator, webview_tool):
        """Test display action is correctly formatted."""
        mock_val = MagicMock()
        mock_val.validate.return_value = (True, "https://youtube.com", None)
        mock_validator.return_value = mock_val

        result = await webview_tool.execute(
            arguments={"url": "youtube.com", "title": "YouTube"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.display_action is not None
        assert result.display_action["type"] == "web_view"
        assert "data" in result.display_action
        data = result.display_action["data"]
        assert data["url"] == "https://youtube.com"
        assert data["title"] == "YouTube"

    @pytest.mark.asyncio
    @patch("app.services.tools.webview_tool.get_url_validator")
    async def test_default_title(self, mock_validator, webview_tool):
        """Test default title is 'Web View' when not provided."""
        mock_val = MagicMock()
        mock_val.validate.return_value = (True, "https://example.com", None)
        mock_validator.return_value = mock_val

        result = await webview_tool.execute(
            arguments={"url": "example.com"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.metadata["title"] == "Web View"

    @pytest.mark.asyncio
    @patch("app.services.tools.webview_tool.get_mqtt_client")
    @patch("app.services.tools.webview_tool.get_url_validator")
    async def test_mqtt_publish_called(self, mock_validator, mock_mqtt_getter, webview_tool):
        """Test MQTT publish is called with correct arguments."""
        mock_val = MagicMock()
        mock_val.validate.return_value = (True, "https://example.com", None)
        mock_validator.return_value = mock_val

        mock_mqtt = MagicMock()
        mock_mqtt_getter.return_value = mock_mqtt

        result = await webview_tool.execute(
            arguments={"url": "example.com"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        mock_mqtt.publish_display_action.assert_called_once_with(
            action_type="web_view",
            action_data={"url": "https://example.com", "title": "Web View"},
            room_id="test_room",
            session_id="test_session"
        )

    @pytest.mark.asyncio
    @patch("app.services.tools.webview_tool.get_url_validator")
    async def test_mqtt_failure_does_not_break_execution(self, mock_validator, webview_tool):
        """Test MQTT publish failure doesn't break tool execution."""
        mock_val = MagicMock()
        mock_val.validate.return_value = (True, "https://example.com", None)
        mock_validator.return_value = mock_val

        with patch("app.services.tools.webview_tool.get_mqtt_client", side_effect=Exception("MQTT error")):
            result = await webview_tool.execute(
                arguments={"url": "example.com"},
                room_id="test_room",
                session_id="test_session"
            )

            # Should still succeed even if MQTT fails
            assert result.success is True
