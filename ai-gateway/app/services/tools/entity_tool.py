"""Entity tool for comprehensive Home Assistant entity access."""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from app.services.tools.base import BaseTool, ToolResult
from app.services.ha_client import HomeAssistantClient

logger = logging.getLogger(__name__)


@runtime_checkable
class BackendProtocol(Protocol):
    """Protocol for backend abstraction layer."""

    async def get_entity_state(self, entity_id: str) -> Any: ...
    async def get_all_states(self) -> list[Any]: ...
    async def get_entities(self, domain: str | None = None) -> list[Any]: ...


class GetEntityTool(BaseTool):
    """Tool for getting state of any Home Assistant entity."""

    def __init__(
        self,
        ha_client: HomeAssistantClient | None = None,
        backend: BackendProtocol | None = None,
    ) -> None:
        """Initialize entity tool.

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
        self._use_backend = backend is not None

    @property
    def name(self) -> str:
        """Tool name."""
        return "get_entity_state"

    @property
    def schema(self) -> dict[str, Any]:
        """OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": "get_entity_state",
                "description": (
                    "Get current state and attributes of Home Assistant entities. "
                    "Use this to query any device state (lights, switches, sensors, climate, "
                    "media players, etc.)"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "enum": [
                                "light",
                                "sensor",
                                "climate",
                                "switch",
                                "media_player",
                                "weather",
                                "all",
                            ],
                            "description": "Entity domain to query",
                        },
                        "entity_id": {
                            "type": "string",
                            "description": (
                                "Optional specific entity ID (e.g., 'light.living_room'). "
                                "If omitted, returns all entities in the domain."
                            ),
                        },
                    },
                    "required": ["domain"],
                },
            },
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        room_id: str | None = None,
        session_id: str | None = None,
    ) -> ToolResult:
        """Get entity state from Home Assistant.

        Args:
            arguments: Must contain 'domain', optionally 'entity_id'
            room_id: Optional room context for display actions
            session_id: Optional session ID for display actions

        Returns:
            ToolResult with entity states
        """
        domain = arguments.get("domain")
        entity_id = arguments.get("entity_id")

        if not domain:
            return ToolResult(
                success=False,
                content="No domain specified",
                metadata={"error": "missing_domain"},
            )

        try:
            # Get entities based on mode
            if self._use_backend:
                entities = await self._get_entities_via_backend(domain, entity_id)
            else:
                entities = await self._get_entities_via_ha_client(domain, entity_id)

            if not entities:
                return ToolResult(
                    success=False,
                    content=f"No entities found for domain '{domain}'",
                    metadata={"error": "no_entities", "domain": domain},
                )

            # Format for LLM
            content = self._format_entities(entities, domain)

            # Create display action for dashboard (Phase 4: unified data_display)
            # For single entity, use entity mode; for multiple, use first entity as representative
            if entity_id and len(entities) == 1:
                entity = entities[0]
                display_action = {
                    "type": "data_display",
                    "data": {
                        "mode": "entity",
                        "content": {
                            "entity_id": entity.get("entity_id", ""),
                            "state": entity.get("state", "unknown"),
                            "friendly_name": entity.get("attributes", {}).get("friendly_name", entity.get("entity_id", "")),
                            "attributes": entity.get("attributes", {}),
                            "domain": domain,
                        },
                    },
                }
            else:
                # Multiple entities - show first one with count in attributes
                entity = entities[0]
                display_action = {
                    "type": "data_display",
                    "data": {
                        "mode": "entity",
                        "content": {
                            "entity_id": f"{domain} (showing 1 of {len(entities)})",
                            "state": entity.get("state", "unknown"),
                            "friendly_name": entity.get("attributes", {}).get("friendly_name", entity.get("entity_id", "")),
                            "attributes": {
                                "total_entities": len(entities),
                                **entity.get("attributes", {}),
                            },
                            "domain": domain,
                        },
                    },
                }

            return ToolResult(
                success=True,
                content=content,
                display_action=display_action,
                metadata={"entity_count": len(entities), "domain": domain},
            )

        except Exception as e:
            logger.error(f"Error getting entity state: {e}", exc_info=True)
            return ToolResult(
                success=False,
                content=f"Error retrieving entity state: {str(e)}",
                metadata={"error": "exception", "exception": str(e)},
            )

    def _format_entities(
        self, entities: list[dict[str, Any]], domain: str
    ) -> str:
        """Format entities for LLM response.

        Args:
            entities: List of entity state dicts
            domain: Entity domain

        Returns:
            Formatted string
        """
        if not entities:
            return f"No {domain} entities found"

        lines = [f"Found {len(entities)} {domain} entities:"]

        for entity in entities[:10]:  # Limit to 10 for readability
            entity_id = entity.get("entity_id", "unknown")
            state = entity.get("state", "unknown")
            attributes = entity.get("attributes", {})
            friendly_name = attributes.get("friendly_name", entity_id)

            # Format based on domain
            if domain == "light":
                brightness = attributes.get("brightness", "")
                if brightness:
                    brightness_pct = int((int(brightness) / 255) * 100)
                    lines.append(
                        f"- {friendly_name}: {state} ({brightness_pct}%)"
                    )
                else:
                    lines.append(f"- {friendly_name}: {state}")

            elif domain == "sensor":
                unit = attributes.get("unit_of_measurement", "")
                lines.append(f"- {friendly_name}: {state} {unit}")

            elif domain == "climate":
                current_temp = attributes.get("current_temperature", "?")
                target_temp = attributes.get("temperature", "?")
                lines.append(
                    f"- {friendly_name}: {state}, "
                    f"current: {current_temp}°C, target: {target_temp}°C"
                )

            else:
                lines.append(f"- {friendly_name}: {state}")

        if len(entities) > 10:
            lines.append(f"... and {len(entities) - 10} more")

        return "\n".join(lines)

    async def _get_entities_via_backend(
        self, domain: str, entity_id: str | None
    ) -> list[dict[str, Any]]:
        """Get entities via backend abstraction.

        Args:
            domain: Entity domain or 'all'
            entity_id: Optional specific entity ID

        Returns:
            List of entity state dicts
        """
        if domain == "all":
            states = await self.backend.get_all_states()  # type: ignore
        elif entity_id:
            state = await self.backend.get_entity_state(entity_id)  # type: ignore
            states = [state] if state else []
        else:
            states = await self.backend.get_all_states()  # type: ignore
            states = [s for s in states if s.entity_id.startswith(f"{domain}.")]

        # Convert EntityState objects to dicts for compatibility
        result = []
        for state in states:
            if hasattr(state, "entity_id"):
                # EntityState object
                result.append({
                    "entity_id": state.entity_id,
                    "state": state.state,
                    "attributes": state.attributes or {},
                })
            else:
                # Already a dict
                result.append(state)

        return result

    async def _get_entities_via_ha_client(
        self, domain: str, entity_id: str | None
    ) -> list[dict[str, Any]]:
        """Get entities via legacy HA client.

        Args:
            domain: Entity domain or 'all'
            entity_id: Optional specific entity ID

        Returns:
            List of entity state dicts
        """
        if domain == "all":
            return await self.ha_client.get_states()  # type: ignore
        elif entity_id:
            entity = await self.ha_client.get_state(entity_id)  # type: ignore
            return [entity] if entity else []
        else:
            all_states = await self.ha_client.get_states()  # type: ignore
            return [
                e for e in all_states
                if e.get("entity_id", "").startswith(f"{domain}.")
            ]
