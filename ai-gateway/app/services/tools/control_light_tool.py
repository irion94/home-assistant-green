"""Light control tool for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from app.models import HAAction
from app.services.tools.base import BaseTool, ToolResult
from app.services.ha_client import HomeAssistantClient
from app.services.entities import ROOM_ENTITIES, ROOM_NAMES, get_all_light_entities
from app.services.mqtt_client import get_mqtt_client, ensure_mqtt_connected

logger = logging.getLogger(__name__)


@runtime_checkable
class BackendProtocol(Protocol):
    """Protocol for backend abstraction layer."""

    async def execute_action(self, action: Any) -> Any: ...
    async def get_entity_state(self, entity_id: str) -> Any: ...


class ControlLightTool(BaseTool):
    """Tool for controlling lights in different rooms."""

    def __init__(
        self,
        ha_client: HomeAssistantClient | None = None,
        backend: BackendProtocol | None = None,
    ) -> None:
        """Initialize light control tool.

        Args:
            ha_client: Legacy Home Assistant API client (optional)
            backend: New backend abstraction (optional)

        Raises:
            ValueError: If neither ha_client nor backend is provided
        """
        if ha_client is None and backend is None:
            raise ValueError("Either ha_client or backend must be provided")
        self.ha_client = ha_client
        self.backend = backend
        self.mqtt_client = get_mqtt_client()
        self._use_backend = backend is not None

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
            # Build action based on mode
            if entity_id == "all":
                # Control all lights - get from config
                entities = get_all_light_entities()
            else:
                entities = [entity_id]

            # Execute action via appropriate backend
            if self._use_backend:
                result = await self._execute_via_backend(action, entities)
            else:
                result = await self._execute_via_ha_client(action, entity_id, entities)

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

                for eid in entities:
                    state = await self._get_entity_state(eid)
                    if state:
                        # Handle both dict format (legacy) and EntityState format (new)
                        if hasattr(state, "attributes"):
                            # EntityState object
                            attrs = state.attributes or {}
                            state_val = state.state
                        else:
                            # Dict format (legacy)
                            attrs = state.get("attributes", {})
                            state_val = state.get("state", "unknown")

                        entity_details.append({
                            "entity_id": eid,
                            "friendly_name": attrs.get("friendly_name", eid.split(".")[-1]),
                            "state": state_val,
                            "brightness": attrs.get("brightness"),
                            "brightness_pct": int(attrs.get("brightness", 0) / 255 * 100) if attrs.get("brightness") else None,
                            "color_temp": attrs.get("color_temp"),
                            "rgb_color": attrs.get("rgb_color"),
                            "supported_features": [],
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

    async def _execute_via_backend(
        self, action: str, entities: list[str]
    ) -> Any | None:
        """Execute light control via backend abstraction.

        Args:
            action: 'on' or 'off'
            entities: List of entity IDs to control

        Returns:
            Result from backend or None on failure
        """
        from app.core.models import DeviceAction

        action_type = "turn_on" if action == "on" else "turn_off"

        # Execute action for each entity
        results = []
        for entity_id in entities:
            device_action = DeviceAction(
                action_type=action_type,
                entity_id=entity_id,
                domain="light",
                parameters={},
            )
            result = await self.backend.execute_action(device_action)  # type: ignore
            results.append(result)

        # Return combined result (all must succeed)
        return results if all(r.success for r in results) else None

    async def _execute_via_ha_client(
        self, action: str, entity_id: str, entities: list[str]
    ) -> Any | None:
        """Execute light control via legacy HA client.

        Args:
            action: 'on' or 'off'
            entity_id: Original entity ID (may be 'all')
            entities: List of entity IDs to control

        Returns:
            Result from HA client or None on failure
        """
        if entity_id == "all":
            # Control all lights - pass list of entities
            ha_action = HAAction(
                action="call_service",
                service=f"light.turn_{action}",
                entity_id=None,
                data={"entity_id": entities},
            )
        else:
            ha_action = HAAction(
                action="call_service",
                service=f"light.turn_{action}",
                entity_id=entity_id,
                data={},
            )

        return await self.ha_client.call_service(ha_action)  # type: ignore

    async def _get_entity_state(self, entity_id: str) -> Any | None:
        """Get entity state from backend or HA client.

        Args:
            entity_id: Entity ID to query

        Returns:
            Entity state dict or EntityState object
        """
        if self._use_backend:
            return await self.backend.get_entity_state(entity_id)  # type: ignore
        else:
            return await self.ha_client.get_state(entity_id)  # type: ignore
