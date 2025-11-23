"""
LLM Tools Module
Defines tools (functions) that the LLM can call to perform actions.
Supports OpenAI function calling format.
"""

import json
import logging
from typing import Any

from app.services.web_search import get_web_search_client
from app.services.ha_client import HomeAssistantClient
from app.services.entities import ROOM_ENTITIES, ROOM_NAMES, SENSOR_ENTITIES

logger = logging.getLogger(__name__)


# Tool definitions in OpenAI function calling format
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information. ALWAYS use this for: news, current events, what's happening in the world/country/city, sports results, stock prices, recent announcements, or any question requiring up-to-date information from the internet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find information about"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_light",
            "description": "Turn lights on or off in different rooms. Use this when the user wants to control lighting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room": {
                        "type": "string",
                        "description": "Room name: salon, kuchnia, sypialnia, biurko, all (for all lights)",
                        "enum": ["salon", "kuchnia", "sypialnia", "biurko", "all"]
                    },
                    "action": {
                        "type": "string",
                        "description": "Action to perform",
                        "enum": ["on", "off"]
                    }
                },
                "required": ["room", "action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current time. Use when user asks about the time.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_home_data",
            "description": "Get current sensor data from smart home - temperature, humidity, weather conditions, energy usage, etc. Use this when user asks about home conditions like 'what's the temperature?', 'how warm is it outside?', 'what's the weather at home?'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sensor_type": {
                        "type": "string",
                        "description": "Type of sensor data to retrieve",
                        "enum": ["temperature_outside", "temperature_inside", "humidity", "weather", "all"]
                    }
                },
                "required": ["sensor_type"]
            }
        }
    }
]


class ToolExecutor:
    """Executes tools called by the LLM."""

    def __init__(self, ha_client: HomeAssistantClient = None):
        self.ha_client = ha_client
        self.web_search = get_web_search_client()

    async def execute(self, tool_name: str, arguments: dict) -> str:
        """
        Execute a tool and return the result.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Result string to be sent back to the LLM
        """
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")

        try:
            if tool_name == "web_search":
                return await self._execute_web_search(arguments)
            elif tool_name == "control_light":
                return await self._execute_control_light(arguments)
            elif tool_name == "get_time":
                return self._execute_get_time(arguments)
            elif tool_name == "get_home_data":
                return await self._execute_get_home_data(arguments)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return f"Error executing {tool_name}: {str(e)}"

    async def _execute_web_search(self, arguments: dict) -> str:
        """Execute web search and return formatted results."""
        query = arguments.get("query", "")

        if not query:
            return "No search query provided"

        if not self.web_search.is_available():
            return "Web search is not configured (missing API key)"

        result = await self.web_search.search(query)

        if not result.get("success"):
            return f"Search failed: {result.get('error', 'Unknown error')}"

        if not result.get("results"):
            return f"No results found for: {query}"

        # Format results for LLM
        return self.web_search.format_for_llm(result)

    async def _execute_control_light(self, arguments: dict) -> str:
        """Execute light control command."""
        room = arguments.get("room", "")
        action = arguments.get("action", "")

        if not room or not action:
            return "Missing room or action parameter"

        entity_id = ROOM_ENTITIES.get(room)
        if not entity_id:
            return f"Unknown room: {room}"

        if not self.ha_client:
            return "Home Assistant client not available"

        # Build HA action
        from app.models import HAAction

        if entity_id == "all":
            # Control all lights
            ha_action = HAAction(
                action="call_service",
                service=f"light.turn_{action}",
                entity_id="all",
                data={"entity_id": "all"},
            )
        else:
            ha_action = HAAction(
                action="call_service",
                service=f"light.turn_{action}",
                entity_id=entity_id,
                data={},
            )

        result = await self.ha_client.call_service(ha_action)

        # call_service returns None on failure, empty list [] on success
        if result is not None:
            return f"Successfully turned {action} {ROOM_NAMES.get(room, room)}"
        else:
            return f"Failed to control {room} lights"

    def _execute_get_time(self, arguments: dict) -> str:
        """Get current time."""
        from datetime import datetime
        import pytz

        # Warsaw timezone
        tz = pytz.timezone("Europe/Warsaw")
        now = datetime.now(tz)

        return f"Current time is {now.strftime('%H:%M')} on {now.strftime('%A, %B %d, %Y')}"

    async def _execute_get_home_data(self, arguments: dict) -> str:
        """Get sensor data from Home Assistant."""
        sensor_type = arguments.get("sensor_type", "all")

        if not self.ha_client:
            return "Home Assistant client not available"

        results = []

        if sensor_type == "all":
            # Get all sensor types
            for stype in ["temperature_outside", "temperature_inside", "humidity", "weather"]:
                data = await self._get_sensor_data(stype)
                if data:
                    results.append(data)
        else:
            data = await self._get_sensor_data(sensor_type)
            if data:
                results.append(data)

        if not results:
            return f"No sensor data available for: {sensor_type}. Check if sensors are configured in Home Assistant."

        return "\n".join(results)

    async def _get_sensor_data(self, sensor_type: str) -> str | None:
        """Get data for a specific sensor type."""
        entity_ids = SENSOR_ENTITIES.get(sensor_type, [])

        for entity_id in entity_ids:
            state = await self.ha_client.get_state(entity_id)
            if state and state.get("state") not in ["unavailable", "unknown", None]:
                # Format based on entity type
                if entity_id.startswith("weather."):
                    # Weather entity has more attributes
                    attrs = state.get("attributes", {})
                    temp = attrs.get("temperature", "N/A")
                    humidity = attrs.get("humidity", "N/A")
                    condition = state.get("state", "unknown")
                    wind = attrs.get("wind_speed", "N/A")
                    return (
                        f"Weather: {condition}, "
                        f"Temperature: {temp}°C, "
                        f"Humidity: {humidity}%, "
                        f"Wind: {wind} km/h"
                    )
                else:
                    # Regular sensor
                    value = state.get("state")
                    unit = state.get("attributes", {}).get("unit_of_measurement", "")
                    friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
                    return f"{friendly_name}: {value}{unit}"

        return None


def get_tools() -> list:
    """Get list of available tools in OpenAI format."""
    return TOOLS


def get_tool_executor(ha_client: HomeAssistantClient = None) -> ToolExecutor:
    """Get tool executor instance."""
    return ToolExecutor(ha_client)
