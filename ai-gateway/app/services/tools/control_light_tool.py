"""Light control tool for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

from app.models import HAAction
from app.services.tools.base import BaseTool, ToolResult
from app.services.ha_client import HomeAssistantClient
from app.services.entities import ROOM_ENTITIES, ROOM_NAMES
from app.services.mqtt_client import get_mqtt_client, ensure_mqtt_connected

logger = logging.getLogger(__name__)


class ControlLightTool(BaseTool):
    """Tool for controlling lights in different rooms."""

    def __init__(self, ha_client: HomeAssistantClient) -> None:
        """Initialize light control tool.

        Args:
            ha_client: Home Assistant API client
        """
        self.ha_client = ha_client
        self.mqtt_client = get_mqtt_client()

    @property
    def name(self) -> str:
        """Tool name."""
        return "control_light"

    @property
    def schema(self) -> dict[str, Any]:
        """OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": "control_light",
                "description": (
                    "Turn lights on or off in different rooms. "
                    "Use this when the user wants to control lighting."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "room": {
                            "type": "string",
                            "description": (
                                "Room name: salon, kuchnia, sypialnia, biurko, "
                                "all (for all lights)"
                            ),
                            "enum": list(ROOM_ENTITIES.keys()),
                        },
                        "action": {
                            "type": "string",
                            "description": "Action to perform",
                            "enum": ["on", "off"],
                        },
                    },
                    "required": ["room", "action"],
                },
            },
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        room_id: str | None = None,
        session_id: str | None = None,
    ) -> ToolResult:
        """Execute light control command.

        Args:
            arguments: Must contain 'room' and 'action' keys
            room_id: Optional room context for display actions
            session_id: Optional session ID for display actions

        Returns:
            ToolResult with control outcome
        """
        room = arguments.get("room", "")
        action = arguments.get("action", "")

        if not room or not action:
            return ToolResult(
                success=False,
                content="Missing room or action parameter",
                metadata={"error": "missing_parameters"},
            )

        entity_id = ROOM_ENTITIES.get(room)
        if not entity_id:
            return ToolResult(
                success=False,
                content=f"Unknown room: {room}. Available: {', '.join(ROOM_ENTITIES.keys())}",
                metadata={"error": "unknown_room", "room": room},
            )

        try:
            # Build HA action
            if entity_id == "all":
                # Control all lights - pass list of entities
                all_light_entities = [
                    "light.yeelight_color_0x80156a9",  # salon
                    "light.yeelight_color_0x49c27e1",  # kuchnia
                    "light.yeelight_color_0x80147dd",  # sypialnia
                    "light.yeelight_lamp15_0x1b37d19d_ambilight",  # biurko
                    "light.yeelight_lamp15_0x1b37d19d",  # biurko ambient
                    "light.yeelight_color_0x801498b",  # lamp 1
                    "light.yeelight_color_0x8015154",  # lamp 2
                ]

                ha_action = HAAction(
                    action="call_service",
                    service=f"light.turn_{action}",
                    entity_id=None,
                    data={"entity_id": all_light_entities},
                )
                entities = all_light_entities
            else:
                ha_action = HAAction(
                    action="call_service",
                    service=f"light.turn_{action}",
                    entity_id=entity_id,
                    data={},
                )
                entities = [entity_id]

            result = await self.ha_client.call_service(ha_action)

            if result is None:
                return ToolResult(
                    success=False,
                    content=f"Failed to turn {action} lights in {room}",
                    metadata={"error": "ha_call_failed"},
                )

            # Fetch detailed entity states for display panel
            entity_details = []
            try:
                import asyncio
                await asyncio.sleep(0.5)  # Brief delay for state propagation

                for entity_id in entities:
                    state = await self.ha_client.get_state(entity_id)
                    if state:
                        attrs = state.get("attributes", {})
                        entity_details.append({
                            "entity_id": entity_id,
                            "friendly_name": attrs.get("friendly_name", entity_id.split(".")[-1]),
                            "state": state.get("state", "unknown"),
                            "brightness": attrs.get("brightness"),
                            "brightness_pct": int(attrs.get("brightness", 0) / 255 * 100) if attrs.get("brightness") else None,
                            "color_temp": attrs.get("color_temp"),
                            "rgb_color": attrs.get("rgb_color"),
                            "supported_features": [],  # Could parse from attrs.get("supported_features")
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch entity states: {e}")
                # Fall back to simple entity list
                entity_details = [{"entity_id": eid, "friendly_name": eid.split(".")[-1], "state": action} for eid in entities]

            # Ensure we always have entity details, even if all get_state calls failed
            if not entity_details:
                entity_details = [{"entity_id": eid, "friendly_name": eid.split(".")[-1], "state": action} for eid in entities]

            # Always create display action to show the panel
            display_action = {
                "type": "light_control_detailed",
                "data": {
                    "room": room,
                    "entities": entity_details,
                    "action_performed": action,
                    "supports_interaction": True,
                },
            }

            # Publish to MQTT if room_id and session_id are available
            if room_id and session_id:
                ensure_mqtt_connected()
                self.mqtt_client.publish_display_action(
                    action_type="light_control_detailed",
                    action_data=display_action["data"],
                    room_id=room_id,
                    session_id=session_id,
                )

            room_name = ROOM_NAMES.get(room, room)
            content = f"Gotowe, światło {action}e w {room_name}"

            return ToolResult(
                success=True,
                content=content,
                display_action=display_action,
                metadata={
                    "room": room,
                    "action": action,
                    "entity_count": len(entities),
                },
            )

        except Exception as e:
            logger.error(f"Light control error: {e}", exc_info=True)
            return ToolResult(
                success=False,
                content=f"Error controlling lights: {str(e)}",
                metadata={"error": "exception", "exception": str(e)},
            )
