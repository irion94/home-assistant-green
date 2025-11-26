"""Web search tool using Brave Search API."""

from __future__ import annotations

import logging
from typing import Any

from app.services.tools.base import BaseTool, ToolResult
from app.services.web_search import get_web_search_client
from app.services.mqtt_client import get_mqtt_client, ensure_mqtt_connected

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """Tool for searching the web for current information."""

    def __init__(self) -> None:
        """Initialize web search tool."""
        self.web_search = get_web_search_client()
        self.mqtt_client = get_mqtt_client()

    @property
    def name(self) -> str:
        """Tool name."""
        return "web_search"

    @property
    def schema(self) -> dict[str, Any]:
        """OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": (
                    "Search the web for current information. ALWAYS use this for: "
                    "news, current events, what's happening in the world/country/city, "
                    "sports results, stock prices, recent announcements, or any question "
                    "requiring up-to-date information from the internet."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find information about",
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
        """Execute web search.

        Args:
            arguments: Must contain 'query' key
            room_id: Optional room context for display actions
            session_id: Optional session ID for display actions

        Returns:
            ToolResult with search results
        """
        query = arguments.get("query", "")

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
            result = await self.web_search.search(query)

            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                return ToolResult(
                    success=False,
                    content=f"Search failed: {error_msg}",
                    metadata={"error": "search_failed", "details": error_msg},
                )

            if not result.get("results"):
                return ToolResult(
                    success=True,
                    content=f"No results found for: {query}",
                    metadata={"result_count": 0, "query": query},
                )

            # Publish display action for React Dashboard
            display_action = None
            if room_id and session_id:
                ensure_mqtt_connected()
                search_results = result.get("results", [])[:5]  # Top 5
                display_action = {
                    "type": "search_results",
                    "data": {
                        "query": query,
                        "results": [
                            {
                                "title": r.get("title", ""),
                                "url": r.get("url", ""),
                                "snippet": r.get("snippet", ""),
                            }
                            for r in search_results
                        ],
                    },
                }
                self.mqtt_client.publish_display_action(
                    action_type="search_results",
                    action_data=display_action["data"],
                    room_id=room_id,
                    session_id=session_id,
                )

            # Format results for LLM
            content = self.web_search.format_for_llm(result)

            return ToolResult(
                success=True,
                content=content,
                display_action=display_action,
                metadata={
                    "result_count": len(result.get("results", [])),
                    "query": query,
                },
            )

        except Exception as e:
            logger.error(f"Web search error: {e}", exc_info=True)
            return ToolResult(
                success=False,
                content=f"Error during search: {str(e)}",
                metadata={"error": "exception", "exception": str(e)},
            )
