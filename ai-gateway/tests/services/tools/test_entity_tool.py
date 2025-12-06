"""Tests for GetEntityTool."""

import pytest
from unittest.mock import AsyncMock
from app.services.tools.entity_tool import GetEntityTool


@pytest.fixture
def entity_tool(mock_ha_client):
    """Fixture providing GetEntityTool instance."""
    return GetEntityTool(ha_client=mock_ha_client)


class TestGetEntityTool:
    """Test suite for GetEntityTool."""

    def test_tool_name(self, entity_tool):
        """Test tool name is correct."""
        assert entity_tool.name == "get_entity_state"

    def test_schema_structure(self, entity_tool):
        """Test schema has required OpenAI structure."""
        schema = entity_tool.schema
        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "get_entity_state"
        assert "parameters" in schema["function"]

    def test_schema_required_params(self, entity_tool):
        """Test schema requires 'domain' parameter."""
        schema = entity_tool.schema
        params = schema["function"]["parameters"]
        assert "domain" in params["properties"]
        assert "domain" in params["required"]
        assert "entity_id" in params["properties"]
        assert "entity_id" not in params["required"]  # Optional

    @pytest.mark.asyncio
    async def test_missing_domain(self, entity_tool):
        """Test missing domain argument fails."""
        result = await entity_tool.execute(
            arguments={},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "No domain specified" in result.content
        assert result.metadata["error"] == "missing_domain"

    @pytest.mark.asyncio
    async def test_get_single_entity(self, entity_tool, mock_ha_client):
        """Test retrieving specific entity by ID."""
        mock_ha_client.get_state = AsyncMock(return_value={
            "entity_id": "light.living_room",
            "state": "on",
            "attributes": {
                "friendly_name": "Living Room Light",
                "brightness": 200
            }
        })

        result = await entity_tool.execute(
            arguments={"domain": "light", "entity_id": "light.living_room"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert "Living Room Light" in result.content
        assert result.metadata["entity_count"] == 1

    @pytest.mark.asyncio
    async def test_get_all_domain_entities(self, entity_tool, mock_ha_client):
        """Test retrieving all entities in a domain."""
        mock_ha_client.get_states = AsyncMock(return_value=[
            {
                "entity_id": "light.living_room",
                "state": "on",
                "attributes": {"friendly_name": "Living Room"}
            },
            {
                "entity_id": "light.bedroom",
                "state": "off",
                "attributes": {"friendly_name": "Bedroom"}
            },
            {
                "entity_id": "sensor.temperature",
                "state": "22",
                "attributes": {"friendly_name": "Temperature"}
            }
        ])

        result = await entity_tool.execute(
            arguments={"domain": "light"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert result.metadata["entity_count"] == 2  # Only lights
        assert "Living Room" in result.content
        assert "Bedroom" in result.content
        assert "Temperature" not in result.content  # Sensor filtered out

    @pytest.mark.asyncio
    async def test_get_all_entities(self, entity_tool, mock_ha_client):
        """Test retrieving all entities across all domains."""
        mock_ha_client.get_states = AsyncMock(return_value=[
            {"entity_id": "light.living_room", "state": "on", "attributes": {}},
            {"entity_id": "sensor.temperature", "state": "22", "attributes": {}},
            {"entity_id": "switch.fan", "state": "off", "attributes": {}}
        ])

        result = await entity_tool.execute(
            arguments={"domain": "all"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert result.metadata["entity_count"] == 3

    @pytest.mark.asyncio
    async def test_no_entities_found(self, entity_tool, mock_ha_client):
        """Test handling when no entities match domain."""
        mock_ha_client.get_states = AsyncMock(return_value=[
            {"entity_id": "light.living_room", "state": "on", "attributes": {}}
        ])

        result = await entity_tool.execute(
            arguments={"domain": "climate"},  # No climate entities
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "No entities found" in result.content
        assert result.metadata["error"] == "no_entities"

    @pytest.mark.asyncio
    async def test_display_action_structure(self, entity_tool, mock_ha_client):
        """Test display action is correctly formatted."""
        mock_ha_client.get_state = AsyncMock(return_value={
            "entity_id": "light.bedroom",
            "state": "on",
            "attributes": {"friendly_name": "Bedroom Light"}
        })

        result = await entity_tool.execute(
            arguments={"domain": "light", "entity_id": "light.bedroom"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.display_action is not None
        assert result.display_action["type"] == "get_entity"
        data = result.display_action["data"]
        assert data["domain"] == "light"
        assert data["entity_id"] == "light.bedroom"
        assert "entities" in data
        assert data["entity_count"] == 1

    @pytest.mark.asyncio
    async def test_light_brightness_formatting(self, entity_tool, mock_ha_client):
        """Test light brightness is formatted as percentage."""
        mock_ha_client.get_states = AsyncMock(return_value=[
            {
                "entity_id": "light.living_room",
                "state": "on",
                "attributes": {
                    "friendly_name": "Living Room",
                    "brightness": 128  # 50% of 255
                }
            }
        ])

        result = await entity_tool.execute(
            arguments={"domain": "light"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert "50%" in result.content or "50" in result.content

    @pytest.mark.asyncio
    async def test_sensor_unit_formatting(self, entity_tool, mock_ha_client):
        """Test sensor values include unit of measurement."""
        mock_ha_client.get_states = AsyncMock(return_value=[
            {
                "entity_id": "sensor.temperature",
                "state": "22.5",
                "attributes": {
                    "friendly_name": "Temperature",
                    "unit_of_measurement": "°C"
                }
            }
        ])

        result = await entity_tool.execute(
            arguments={"domain": "sensor"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert "22.5" in result.content
        assert "°C" in result.content

    @pytest.mark.asyncio
    async def test_climate_temperature_formatting(self, entity_tool, mock_ha_client):
        """Test climate entities show current and target temperature."""
        mock_ha_client.get_states = AsyncMock(return_value=[
            {
                "entity_id": "climate.living_room",
                "state": "heat",
                "attributes": {
                    "friendly_name": "Thermostat",
                    "current_temperature": 21.5,
                    "temperature": 22.0
                }
            }
        ])

        result = await entity_tool.execute(
            arguments={"domain": "climate"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert "21.5" in result.content  # Current
        assert "22" in result.content or "22.0" in result.content  # Target

    @pytest.mark.asyncio
    async def test_entity_limit_in_display(self, entity_tool, mock_ha_client):
        """Test display action limits entities to 20."""
        # Create 30 mock entities
        entities = [
            {
                "entity_id": f"light.light_{i}",
                "state": "on",
                "attributes": {"friendly_name": f"Light {i}"}
            }
            for i in range(30)
        ]
        mock_ha_client.get_states = AsyncMock(return_value=entities)

        result = await entity_tool.execute(
            arguments={"domain": "light"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert result.metadata["entity_count"] == 30
        assert len(result.display_action["data"]["entities"]) == 20

    @pytest.mark.asyncio
    async def test_exception_handling(self, entity_tool, mock_ha_client):
        """Test exception during entity query is caught."""
        mock_ha_client.get_states = AsyncMock(side_effect=Exception("Connection error"))

        result = await entity_tool.execute(
            arguments={"domain": "light"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "Error retrieving entity state" in result.content
        assert result.metadata["error"] == "exception"
