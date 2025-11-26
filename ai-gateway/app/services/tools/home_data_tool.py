"""Home data tool for querying sensor information."""

from __future__ import annotations

import logging
from typing import Any

from app.services.tools.base import BaseTool, ToolResult
from app.services.ha_client import HomeAssistantClient
from app.services.entities import SENSOR_ENTITIES

logger = logging.getLogger(__name__)


class GetHomeDataTool(BaseTool):
    """Tool for getting sensor data from smart home."""

    def __init__(self, ha_client: HomeAssistantClient) -> None:
        """Initialize home data tool.

        Args:
            ha_client: Home Assistant API client
        """
        self.ha_client = ha_client

    @property
    def name(self) -> str:
        """Tool name."""
        return "get_home_data"

    @property
    def schema(self) -> dict[str, Any]:
        """OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": "get_home_data",
                "description": (
                    "Get current sensor data from smart home - temperature, humidity, "
                    "weather conditions, energy usage, etc. Use this when user asks about "
                    "home conditions like 'what's the temperature?', 'how warm is it outside?', "
                    "'what's the weather at home?'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sensor_type": {
                            "type": "string",
                            "description": "Type of sensor data to retrieve",
                            "enum": list(SENSOR_ENTITIES.keys()) + ["all"],
                        }
                    },
                    "required": ["sensor_type"],
                },
            },
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        room_id: str | None = None,
        session_id: str | None = None,
    ) -> ToolResult:
        """Get sensor data from Home Assistant.

        Args:
            arguments: Must contain 'sensor_type' key
            room_id: Not used
            session_id: Not used

        Returns:
            ToolResult with sensor data
        """
        sensor_type = arguments.get("sensor_type", "")

        if not sensor_type:
            return ToolResult(
                success=False,
                content="No sensor type provided",
                metadata={"error": "missing_sensor_type"},
            )

        try:
            if sensor_type == "all":
                # Get all sensor data
                results = {}
                for s_type in SENSOR_ENTITIES.keys():
                    data = await self._get_sensor_data(s_type)
                    if data:
                        results[s_type] = data

                if not results:
                    return ToolResult(
                        success=False,
                        content="No sensor data available",
                        metadata={"error": "no_data"},
                    )

                content = self._format_all_sensors(results)
                return ToolResult(
                    success=True,
                    content=content,
                    metadata={"sensors": results},
                )

            else:
                data = await self._get_sensor_data(sensor_type)
                if not data:
                    return ToolResult(
                        success=False,
                        content=f"No data available for {sensor_type}",
                        metadata={"error": "no_data", "sensor_type": sensor_type},
                    )

                content = self._format_sensor_data(sensor_type, data)
                return ToolResult(
                    success=True,
                    content=content,
                    metadata={"sensor_type": sensor_type, "data": data},
                )

        except Exception as e:
            logger.error(f"Error getting home data: {e}", exc_info=True)
            return ToolResult(
                success=False,
                content=f"Error retrieving sensor data: {str(e)}",
                metadata={"error": "exception", "exception": str(e)},
            )

    async def _get_sensor_data(self, sensor_type: str) -> dict[str, Any] | None:
        """Get data for a specific sensor type.

        Args:
            sensor_type: Type of sensor to query

        Returns:
            Sensor data dict or None if not available
        """
        entity_ids = SENSOR_ENTITIES.get(sensor_type, [])
        if not entity_ids:
            return None

        # Try each entity until we find one that exists
        for entity_id in entity_ids:
            state = await self.ha_client.get_state(entity_id)
            if state:
                return state

        return None

    def _format_sensor_data(self, sensor_type: str, data: dict[str, Any]) -> str:
        """Format sensor data for LLM response.

        Args:
            sensor_type: Type of sensor
            data: Sensor state data

        Returns:
            Formatted string
        """
        state = data.get("state", "unknown")
        attributes = data.get("attributes", {})
        unit = attributes.get("unit_of_measurement", "")

        if sensor_type == "weather":
            condition = state
            temp = attributes.get("temperature", "?")
            return f"Pogoda: {condition}, temperatura: {temp}°C"
        elif "temperature" in sensor_type:
            return f"Temperatura: {state}{unit}"
        elif sensor_type == "humidity":
            return f"Wilgotność: {state}{unit}"
        else:
            return f"{sensor_type}: {state}{unit}"

    def _format_all_sensors(self, results: dict[str, dict[str, Any]]) -> str:
        """Format multiple sensor results.

        Args:
            results: Dict of sensor_type -> data

        Returns:
            Formatted string with all sensor data
        """
        lines = []
        for sensor_type, data in results.items():
            formatted = self._format_sensor_data(sensor_type, data)
            lines.append(formatted)

        return "\n".join(lines)
