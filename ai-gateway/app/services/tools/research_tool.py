"""Research tool for local search queries (bars, restaurants, nearby places)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote_plus

from app.services.tools.base import BaseTool, ToolResult
from app.services.web_search import get_web_search_client
from app.services.mqtt_client import get_mqtt_client, ensure_mqtt_connected

logger = logging.getLogger(__name__)


class ResearchTool(BaseTool):
    """Tool for searching for local places nearby (bars, restaurants, etc.)."""

    def __init__(self) -> None:
        """Initialize research tool."""
        self.web_search = get_web_search_client()
        self.mqtt_client = get_mqtt_client()

    @property
    def name(self) -> str:
        """Tool name."""
        return "research_local"

    @property
    def schema(self) -> dict[str, Any]:
        """OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": "research_local",
                "description": (
                    "Search for local places and businesses nearby (bars, restaurants, cafes, shops, etc.). "
                    "Use this when user asks about nearby locations or wants to find local businesses. "
                    "Examples: 'find bars nearby', 'restaurants in the area', 'coffee shops close to me', "
                    "'where is the closest pharmacy', 'craft beer bars near me'"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for local places (e.g., 'bars', 'pizza restaurants', 'pharmacies')",
                        },
                        "location": {
                            "type": "string",
                            "description": "Optional location context from conversation (city, area, address). If not provided, 'nearby' will be used.",
                        }
                    },
                    "required": ["query"],
                },
            },
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        room_id: str | None = None,
        session_id: str | None = None,
    ) -> ToolResult:
        """Execute local search.

        Args:
            arguments: Must contain 'query' key, optional 'location' key
            room_id: Optional room context for display actions
            session_id: Optional session ID for display actions

        Returns:
            ToolResult with search results and map link
        """
        query = arguments.get("query", "")
        location = arguments.get("location")

        if not query:
            return ToolResult(
                success=False,
                content="No search query provided",
                metadata={"error": "missing_query"},
            )

        if not self.web_search.is_available():
            return ToolResult(
                success=False,
                content="Web search is not configured (missing API key)",
                metadata={"error": "api_key_missing"},
            )

        try:
            # Build search query
            search_query = query
            if "nearby" not in query.lower() and "near me" not in query.lower():
                if location:
                    search_query = f"{query} in {location}"
                else:
                    search_query = f"{query} nearby"

            # Execute search
            result = await self.web_search.search(search_query, count=5)

            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                return ToolResult(
                    success=False,
                    content=f"Search failed: {error_msg}",
                    metadata={"error": "search_failed", "details": error_msg},
                )

            results = result.get("results", [])

            if not results:
                return ToolResult(
                    success=True,
                    content=f"No local results found for: {query}",
                    metadata={"result_count": 0, "query": query},
                )

            # Generate Google Maps search link
            map_query = quote_plus(search_query)
            map_url = f"https://www.google.com/maps/search/{map_query}"

            # Publish display action for React Dashboard
            display_action = None
            if room_id and session_id:
                ensure_mqtt_connected()
                display_action = {
                    "type": "research_results",
                    "data": {
                        "query": query,
                        "location": location,
                        "results": [
                            {
                                "title": r.get("title", ""),
                                "url": r.get("url", ""),
                                "description": r.get("snippet", ""),
                            }
                            for r in results[:5]
                        ],
                        "map_url": map_url,
                    },
                }
                self.mqtt_client.publish_display_action(
                    action_type="research_results",
                    action_data=display_action["data"],
                    room_id=room_id,
                    session_id=session_id,
                )

            # Format results for LLM
            content_parts = [f"Found {len(results)} local results for '{query}':"]
            for idx, r in enumerate(results[:5], 1):
                title = r.get("title", "Unknown")
                snippet = r.get("snippet", "")
                content_parts.append(f"{idx}. {title}")
                if snippet:
                    content_parts.append(f"   {snippet[:150]}...")

            content_parts.append(f"\nView on map: {map_url}")
            content = "\n".join(content_parts)

            return ToolResult(
                success=True,
                content=content,
                display_action=display_action,
                metadata={
                    "result_count": len(results),
                    "query": query,
                    "location": location,
                    "map_url": map_url,
                },
            )

        except Exception as e:
            logger.error(f"Research tool error: {e}", exc_info=True)
            return ToolResult(
                success=False,
                content=f"Error during local search: {str(e)}",
                metadata={"error": "exception", "exception": str(e)},
            )
