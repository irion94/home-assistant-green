"""Tests for ControlLightTool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.tools.control_light_tool import ControlLightTool
from app.models import HAAction


@pytest.fixture
def control_light_tool(mock_ha_client):
    """Fixture providing ControlLightTool instance."""
    with patch("app.services.tools.control_light_tool.get_mqtt_client"):
        return ControlLightTool(ha_client=mock_ha_client)


class TestControlLightTool:
    """Test suite for ControlLightTool."""

    def test_tool_name(self, control_light_tool):
        """Test tool name is correct."""
        assert control_light_tool.name == "control_light"

    def test_schema_structure(self, control_light_tool):
        """Test schema has required OpenAI structure."""
        schema = control_light_tool.schema
        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "control_light"
        assert "parameters" in schema["function"]

    def test_schema_required_params(self, control_light_tool):
        """Test schema requires 'room' and 'action' parameters."""
        schema = control_light_tool.schema
        params = schema["function"]["parameters"]
        assert "room" in params["properties"]
        assert "action" in params["properties"]
        assert "room" in params["required"]
        assert "action" in params["required"]

    @pytest.mark.asyncio
    async def test_missing_room_parameter(self, control_light_tool):
        """Test missing room parameter fails."""
        result = await control_light_tool.execute(
            arguments={"action": "on"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "Missing room or action" in result.content
        assert result.metadata["error"] == "missing_parameters"

    @pytest.mark.asyncio
    async def test_missing_action_parameter(self, control_light_tool):
        """Test missing action parameter fails."""
        result = await control_light_tool.execute(
            arguments={"room": "salon"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert result.metadata["error"] == "missing_parameters"

    @pytest.mark.asyncio
    async def test_unknown_room(self, control_light_tool):
        """Test unknown room name fails."""
        result = await control_light_tool.execute(
            arguments={"room": "garage", "action": "on"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "Unknown room" in result.content
        assert result.metadata["error"] == "unknown_room"

    @pytest.mark.asyncio
    @patch("app.services.tools.control_light_tool.ensure_mqtt_connected")
    async def test_successful_light_on(self, mock_mqtt, control_light_tool, mock_ha_client):
        """Test turning on lights successfully."""
        mock_ha_client.call_service = AsyncMock(return_value={"success": True})
        mock_ha_client.get_state = AsyncMock(return_value={
            "state": "on",
            "attributes": {
                "friendly_name": "Living Room Light",
                "brightness": 255
            }
        })

        result = await control_light_tool.execute(
            arguments={"room": "salon", "action": "on"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert "światło" in result.content.lower()
        assert result.metadata["room"] == "salon"
        assert result.metadata["action"] == "on"

    @pytest.mark.asyncio
    @patch("app.services.tools.control_light_tool.ensure_mqtt_connected")
    async def test_successful_light_off(self, mock_mqtt, control_light_tool, mock_ha_client):
        """Test turning off lights successfully."""
        mock_ha_client.call_service = AsyncMock(return_value={"success": True})
        mock_ha_client.get_state = AsyncMock(return_value={
            "state": "off",
            "attributes": {"friendly_name": "Kitchen Light"}
        })

        result = await control_light_tool.execute(
            arguments={"room": "kuchnia", "action": "off"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert result.metadata["action"] == "off"

    @pytest.mark.asyncio
    @patch("app.services.tools.control_light_tool.ensure_mqtt_connected")
    async def test_all_lights_control(self, mock_mqtt, control_light_tool, mock_ha_client):
        """Test controlling all lights at once."""
        mock_ha_client.call_service = AsyncMock(return_value={"success": True})
        mock_ha_client.get_state = AsyncMock(return_value={
            "state": "on",
            "attributes": {"friendly_name": "Light", "brightness": 200}
        })

        result = await control_light_tool.execute(
            arguments={"room": "all", "action": "on"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        # Should control 7 lights (as per tool implementation)
        assert mock_ha_client.get_state.call_count == 7

    @pytest.mark.asyncio
    async def test_ha_call_failure(self, control_light_tool, mock_ha_client):
        """Test handling HA service call failure."""
        mock_ha_client.call_service = AsyncMock(return_value=None)

        result = await control_light_tool.execute(
            arguments={"room": "salon", "action": "on"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "Failed to turn" in result.content
        assert result.metadata["error"] == "ha_call_failed"

    @pytest.mark.asyncio
    @patch("app.services.tools.control_light_tool.ensure_mqtt_connected")
    async def test_display_action_structure(self, mock_mqtt, control_light_tool, mock_ha_client):
        """Test display action is correctly formatted."""
        mock_ha_client.call_service = AsyncMock(return_value={"success": True})
        mock_ha_client.get_state = AsyncMock(return_value={
            "state": "on",
            "attributes": {
                "friendly_name": "Test Light",
                "brightness": 128,
                "color_temp": 370
            }
        })

        result = await control_light_tool.execute(
            arguments={"room": "salon", "action": "on"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.display_action is not None
        assert result.display_action["type"] == "light_control_detailed"
        data = result.display_action["data"]
        assert data["room"] == "salon"
        assert "entities" in data
        assert data["action_performed"] == "on"
        assert data["supports_interaction"] is True

    @pytest.mark.asyncio
    @patch("app.services.tools.control_light_tool.ensure_mqtt_connected")
    async def test_entity_details_include_brightness(self, mock_mqtt, control_light_tool, mock_ha_client):
        """Test entity details include brightness percentage."""
        mock_ha_client.call_service = AsyncMock(return_value={"success": True})
        mock_ha_client.get_state = AsyncMock(return_value={
            "state": "on",
            "attributes": {
                "friendly_name": "Bright Light",
                "brightness": 255  # 100%
            }
        })

        result = await control_light_tool.execute(
            arguments={"room": "salon", "action": "on"},
            room_id="test_room",
            session_id="test_session"
        )

        entities = result.display_action["data"]["entities"]
        assert len(entities) > 0
        assert entities[0]["brightness"] == 255
        assert entities[0]["brightness_pct"] == 100

    @pytest.mark.asyncio
    @patch("app.services.tools.control_light_tool.ensure_mqtt_connected")
    async def test_entity_state_fetch_failure_fallback(self, mock_mqtt, control_light_tool, mock_ha_client):
        """Test fallback when entity state fetch fails."""
        mock_ha_client.call_service = AsyncMock(return_value={"success": True})
        mock_ha_client.get_state = AsyncMock(side_effect=Exception("Connection error"))

        result = await control_light_tool.execute(
            arguments={"room": "salon", "action": "on"},
            room_id="test_room",
            session_id="test_session"
        )

        # Should still succeed with fallback entity details
        assert result.success is True
        assert result.display_action is not None
        entities = result.display_action["data"]["entities"]
        assert len(entities) > 0
