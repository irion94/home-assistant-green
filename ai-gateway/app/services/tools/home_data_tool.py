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

                # Always get light states count (even if sensors fail)
                # Use the same complete light list as control_light tool
                all_lights = [
                    "light.yeelight_color_0x80156a9",  # salon
                    "light.yeelight_color_0x49c27e1",  # kuchnia
                    "light.yeelight_color_0x80147dd",  # sypialnia
                    "light.yeelight_lamp15_0x1b37d19d_ambilight",  # biurko
                    "light.yeelight_lamp15_0x1b37d19d",  # biurko ambient
                    "light.yeelight_color_0x801498b",  # lamp 1
                    "light.yeelight_color_0x8015154",  # lamp 2
                ]
                lights_on = 0
                lights_total = len(all_lights)
                for entity_id in all_lights:
                    state = await self.ha_client.get_state(entity_id)
                    if state and state.get("state") == "on":
                        lights_on += 1

                results["lights"] = {"on": lights_on, "total": lights_total}
                logger.info(f"Home data - lights: {lights_on}/{lights_total} on, total results: {len(results)}")

                # Show panel even if only lights data is available
                if not results or (len(results) == 1 and "lights" in results and lights_total == 0):
                    # Only fail if we have no lights AND no sensor data
                    return ToolResult(
                        success=False,
                        content="No home data available",
                        metadata={"error": "no_data"},
                    )

                content = self._format_all_sensors(results)

                # Create display action for left panel
                display_action = {
                    "type": "get_home_data",
                    "data": {
                        "sensor_type": "all",
                        "sensors": results,
                        "summary": content,
                    },
                }

                return ToolResult(
                    success=True,
                    content=content,
                    display_action=display_action,
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

                # Create display action for left panel
                display_action = {
                    "type": "get_home_data",
                    "data": {
                        "sensor_type": sensor_type,
                        "state": data.get("state"),
                        "attributes": data.get("attributes", {}),
                        "summary": content,
                    },
                }

                return ToolResult(
                    success=True,
                    content=content,
                    display_action=display_action,
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
            if sensor_type == "lights":
                # Special formatting for lights
                lines.append(f"Lights: {data['on']}/{data['total']} on")
            else:
                formatted = self._format_sensor_data(sensor_type, data)
                lines.append(formatted)

        return "\n".join(lines)
