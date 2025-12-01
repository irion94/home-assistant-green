"""Tests for GetHomeDataTool."""

import pytest
from unittest.mock import AsyncMock
from app.services.tools.home_data_tool import GetHomeDataTool


@pytest.fixture
def home_data_tool(mock_ha_client):
    """Fixture providing GetHomeDataTool instance."""
    return GetHomeDataTool(ha_client=mock_ha_client)


class TestGetHomeDataTool:
    """Test suite for GetHomeDataTool."""

    def test_tool_name(self, home_data_tool):
        """Test tool name is correct."""
        assert home_data_tool.name == "get_home_data"

    def test_schema_structure(self, home_data_tool):
        """Test schema has required OpenAI structure."""
        schema = home_data_tool.schema
        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "get_home_data"
        assert "parameters" in schema["function"]

    def test_schema_required_params(self, home_data_tool):
        """Test schema requires 'sensor_type' parameter."""
        schema = home_data_tool.schema
        params = schema["function"]["parameters"]
        assert "sensor_type" in params["properties"]
        assert "sensor_type" in params["required"]

    @pytest.mark.asyncio
    async def test_missing_sensor_type(self, home_data_tool):
        """Test missing sensor_type argument fails."""
        result = await home_data_tool.execute(
            arguments={},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "No sensor type provided" in result.content
        assert result.metadata["error"] == "missing_sensor_type"

    @pytest.mark.asyncio
    async def test_single_sensor_success(self, home_data_tool, mock_ha_client):
        """Test retrieving single sensor type."""
        mock_ha_client.get_state = AsyncMock(return_value={
            "state": "22.5",
            "attributes": {
                "unit_of_measurement": "°C",
                "friendly_name": "Temperature"
            }
        })

        result = await home_data_tool.execute(
            arguments={"sensor_type": "temperature"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert "22.5" in result.content
        assert result.metadata["sensor_type"] == "temperature"

    @pytest.mark.asyncio
    async def test_display_action_structure(self, home_data_tool, mock_ha_client):
        """Test display action is correctly formatted."""
        mock_ha_client.get_state = AsyncMock(return_value={
            "state": "60",
            "attributes": {
                "unit_of_measurement": "%",
                "friendly_name": "Humidity"
            }
        })

        result = await home_data_tool.execute(
            arguments={"sensor_type": "humidity"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.display_action is not None
        assert result.display_action["type"] == "get_home_data"
        assert "data" in result.display_action
        data = result.display_action["data"]
        assert data["sensor_type"] == "humidity"
        assert "state" in data
        assert "summary" in data

    @pytest.mark.asyncio
    async def test_all_sensors_query(self, home_data_tool, mock_ha_client):
        """Test querying all sensors."""
        # Mock get_state to return different data for different entities
        async def mock_get_state(entity_id):
            if "temperature" in entity_id:
                return {
                    "state": "22",
                    "attributes": {"unit_of_measurement": "°C"}
                }
            elif "light" in entity_id:
                return {"state": "on"}
            return None

        mock_ha_client.get_state = AsyncMock(side_effect=mock_get_state)

        result = await home_data_tool.execute(
            arguments={"sensor_type": "all"},
            room_id="test_room",
            session_id="test_session"
        )

        # Should succeed if at least lights data is available
        assert result.success is True
        assert "lights" in result.metadata["sensors"].keys()

    @pytest.mark.asyncio
    async def test_lights_count_included(self, home_data_tool, mock_ha_client):
        """Test lights on/off count is included in 'all' query."""
        # Mock some lights as on, some as off
        call_count = [0]

        async def mock_get_state(entity_id):
            if "light" in entity_id:
                call_count[0] += 1
                # First 3 lights on, rest off
                return {"state": "on" if call_count[0] <= 3 else "off"}
            return None

        mock_ha_client.get_state = AsyncMock(side_effect=mock_get_state)

        result = await home_data_tool.execute(
            arguments={"sensor_type": "all"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        lights_data = result.metadata["sensors"]["lights"]
        assert lights_data["on"] == 3
        assert lights_data["total"] == 7  # Total lights defined in tool

    @pytest.mark.asyncio
    async def test_weather_formatting(self, home_data_tool, mock_ha_client):
        """Test weather sensor data is formatted correctly."""
        mock_ha_client.get_state = AsyncMock(return_value={
            "state": "sunny",
            "attributes": {
                "temperature": "25",
                "humidity": "45",
                "friendly_name": "Weather"
            }
        })

        result = await home_data_tool.execute(
            arguments={"sensor_type": "weather"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert "Pogoda" in result.content
        assert "sunny" in result.content
        assert "25" in result.content

    @pytest.mark.asyncio
    async def test_no_data_available(self, home_data_tool, mock_ha_client):
        """Test handling of unavailable sensor data."""
        mock_ha_client.get_state = AsyncMock(return_value=None)

        result = await home_data_tool.execute(
            arguments={"sensor_type": "temperature"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "No data available" in result.content
        assert result.metadata["error"] == "no_data"

    @pytest.mark.asyncio
    async def test_exception_handling(self, home_data_tool, mock_ha_client):
        """Test exception during sensor query is caught."""
        mock_ha_client.get_state = AsyncMock(side_effect=Exception("Connection error"))

        result = await home_data_tool.execute(
            arguments={"sensor_type": "temperature"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "Error retrieving sensor data" in result.content
        assert result.metadata["error"] == "exception"
