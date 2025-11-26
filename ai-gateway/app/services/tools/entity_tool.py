"""Entity tool for comprehensive Home Assistant entity access."""

from __future__ import annotations

import logging
from typing import Any

from app.services.tools.base import BaseTool, ToolResult
from app.services.ha_client import HomeAssistantClient

logger = logging.getLogger(__name__)


class GetEntityTool(BaseTool):
    """Tool for getting state of any Home Assistant entity."""

    def __init__(self, ha_client: HomeAssistantClient) -> None:
        """Initialize entity tool.

        Args:
            ha_client: Home Assistant API client
        """
        self.ha_client = ha_client

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
            # Get entities
            if domain == "all":
                entities = await self.ha_client.get_states()
            elif entity_id:
                entity = await self.ha_client.get_state(entity_id)
                entities = [entity] if entity else []
            else:
                all_states = await self.ha_client.get_states()
                entities = [
                    e for e in all_states
                    if e.get("entity_id", "").startswith(f"{domain}.")
                ]

            if not entities:
                return ToolResult(
                    success=False,
                    content=f"No entities found for domain '{domain}'",
                    metadata={"error": "no_entities", "domain": domain},
                )

            # Format for LLM
            content = self._format_entities(entities, domain)

            # Create display action for dashboard
            display_action = {
                "type": "entity_states",
                "data": {
                    "domain": domain,
                    "entities": entities[:20],  # Limit for display
                    "entity_count": len(entities),
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
