"""Media control tool for managing media players via Home Assistant."""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from app.models import HAAction
from app.services.ha_client import HomeAssistantClient
from app.services.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


@runtime_checkable
class BackendProtocol(Protocol):
    """Protocol for backend abstraction layer."""

    async def execute_action(self, action: Any) -> Any: ...
    async def get_entity_state(self, entity_id: str) -> Any: ...


class MediaControlTool(BaseTool):
    """Control media players and display playback status.

    Supports play, pause, next, previous, volume control for
    media players integrated with Home Assistant.
    """

    def __init__(
        self,
        ha_client: HomeAssistantClient | None = None,
        backend: BackendProtocol | None = None,
    ):
        """Initialize with Home Assistant client or backend abstraction.

        Args:
            ha_client: Legacy HomeAssistantClient instance (optional)
            backend: New backend abstraction (optional)

        Raises:
            ValueError: If neither ha_client nor backend is provided
        """
        if ha_client is None and backend is None:
            raise ValueError("Either ha_client or backend must be provided")
        self.ha_client = ha_client
        self.backend = backend
        self._use_backend = backend is not None

    @property
    def name(self) -> str:
        """Tool identifier for LLM function calling."""
        return "control_media"

    @property
    def schema(self) -> dict[str, Any]:
        """OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": "control_media",
                "description": (
                    "Control media players (play, pause, skip, volume). "
                    "Use when user wants to control music, video playback, "
                    "or adjust volume on media devices."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["play", "pause", "toggle", "next", "previous", "volume_up", "volume_down", "volume_set"],
                            "description": "The media control action to perform",
                        },
                        "entity_id": {
                            "type": "string",
                            "description": "Media player entity ID (e.g., 'media_player.spotify')",
                        },
                        "volume_level": {
                            "type": "number",
                            "description": "Volume level (0.0-1.0) - only for volume_set action",
                        },
                    },
                    "required": ["action", "entity_id"],
                },
            },
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        room_id: str | None = None,
        session_id: str | None = None,
    ) -> ToolResult:
        """Execute media control command.

        Args:
            arguments: Tool arguments with 'action', 'entity_id', optional 'volume_level'
            room_id: Room identifier for MQTT publishing
            session_id: Session identifier for MQTT publishing

        Returns:
            ToolResult with display_action showing media state
        """
        action = arguments.get("action", "")
        entity_id = arguments.get("entity_id", "")
        volume_level = arguments.get("volume_level")

        # Validate inputs
        if not action or not entity_id:
            return ToolResult(
                success=False,
                content="Missing required parameters: action and entity_id",
                metadata={"error": "missing_parameters"},
            )

        try:
            # Map action to HA service
            service_map = {
                "play": "media_play",
                "pause": "media_pause",
                "toggle": "media_play_pause",
                "next": "media_next_track",
                "previous": "media_previous_track",
                "volume_up": "volume_up",
                "volume_down": "volume_down",
                "volume_set": "volume_set",
            }

            service = service_map.get(action)
            if not service:
                return ToolResult(
                    success=False,
                    content=f"Unknown media action: {action}",
                    metadata={"error": "unknown_action", "action": action},
                )

            # Build and execute action based on mode
            service_data = {}
            if action == "volume_set" and volume_level is not None:
                service_data["volume_level"] = max(0.0, min(1.0, float(volume_level)))

            if self._use_backend:
                result = await self._execute_via_backend(action, entity_id, service_data)
            else:
                result = await self._execute_via_ha_client(service, entity_id, service_data)

            if result is None:
                return ToolResult(
                    success=False,
                    content=f"Failed to {action} media player {entity_id}",
                    metadata={"error": "ha_call_failed"},
                )

            # Fetch current media player state for display
            import asyncio
            await asyncio.sleep(0.3)  # Brief delay for state propagation

            state = await self._get_entity_state(entity_id)

            media_data = {}
            if state:
                # Handle both dict format (legacy) and EntityState format (new)
                if hasattr(state, "state"):
                    # EntityState object
                    attrs = state.attributes or {}
                    state_val = state.state
                else:
                    # Dict format (legacy)
                    attrs = state
                    state_val = state.get("state", "unknown")

                media_data = {
                    "entity_id": entity_id,
                    "state": state_val,
                    "media_title": attrs.get("media_title"),
                    "media_artist": attrs.get("media_artist"),
                    "media_album": attrs.get("media_album_name"),
                    "media_duration": attrs.get("media_duration"),
                    "media_position": attrs.get("media_position"),
                    "volume_level": attrs.get("volume_level"),
                    "artwork_url": attrs.get("entity_picture"),
                }

            # Publish display action
            display_action = None
            if room_id and session_id:
                try:
                    from app.services.mqtt_client import get_mqtt_client

                    mqtt = get_mqtt_client()
                    display_action = {
                        "type": "media_control",
                        "data": media_data,
                    }
                    mqtt.publish_display_action(
                        action_type="media_control",
                        action_data=media_data,
                        room_id=room_id,
                        session_id=session_id,
                    )
                    logger.debug(f"Published media_control action to MQTT")
                except Exception as e:
                    logger.warning(f"Failed to publish media_control to MQTT: {e}")

            # Build response content
            content = f"Executed {action} on {entity_id}"
            if media_data.get("media_title"):
                content += f" - Now playing: {media_data['media_title']}"
                if media_data.get("media_artist"):
                    content += f" by {media_data['media_artist']}"

            return ToolResult(
                success=True,
                content=content,
                display_action=display_action,
                metadata={
                    "entity_id": entity_id,
                    "action": action,
                    "state": media_data.get("state"),
                },
            )

        except Exception as e:
            logger.error(f"Media control error: {e}", exc_info=True)
            return ToolResult(
                success=False,
                content=f"Error controlling media player: {str(e)}",
                metadata={"error": "execution_failed", "exception": str(e)},
            )

    async def _execute_via_backend(
        self, action: str, entity_id: str, service_data: dict[str, Any]
    ) -> Any | None:
        """Execute media control via backend abstraction.

        Args:
            action: Media action (play, pause, etc.)
            entity_id: Media player entity ID
            service_data: Service call data

        Returns:
            Result from backend or None on failure
        """
        from app.core.models import DeviceAction

        # Map action to DeviceAction action_type
        action_map = {
            "play": "play",
            "pause": "pause",
            "toggle": "toggle",
            "next": "next",
            "previous": "previous",
            "volume_up": "volume_up",
            "volume_down": "volume_down",
            "volume_set": "volume_set",
        }

        action_type = action_map.get(action)
        if not action_type:
            return None

        device_action = DeviceAction(
            action_type=action_type,
            entity_id=entity_id,
            domain="media_player",
            parameters=service_data,
        )

        result = await self.backend.execute_action(device_action)  # type: ignore
        return result if result.success else None

    async def _execute_via_ha_client(
        self, service: str, entity_id: str, service_data: dict[str, Any]
    ) -> Any | None:
        """Execute media control via legacy HA client.

        Args:
            service: HA service name (e.g., 'media_play')
            entity_id: Media player entity ID
            service_data: Service call data

        Returns:
            Result from HA client or None on failure
        """
        ha_action = HAAction(
            action="call_service",
            service=f"media_player.{service}",
            entity_id=entity_id,
            data=service_data,
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
            return await self.ha_client.get_entity_state(entity_id)  # type: ignore
