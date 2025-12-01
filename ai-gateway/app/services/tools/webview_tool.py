"""WebView tool for displaying websites in the React Dashboard."""

from __future__ import annotations

import logging
from typing import Any

from app.services.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class WebViewTool(BaseTool):
    """Display websites in the React Dashboard WebViewPanel.

    Opens URLs in an iframe on the dashboard, useful for showing
    web content like weather forecasts, news, maps, etc.
    """

    @property
    def name(self) -> str:
        """Tool identifier for LLM function calling."""
        return "open_website"

    @property
    def schema(self) -> dict[str, Any]:
        """OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": "open_website",
                "description": (
                    "Open a website or URL in the dashboard display. "
                    "Use when user wants to see a webpage, check a website, "
                    "view online content, or access web-based information. "
                    "Examples: 'Show me the weather', 'Open YouTube', 'Find nearby restaurants'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to display (e.g., 'https://weather.com' or 'youtube.com'). Protocol optional.",
                        },
                        "title": {
                            "type": "string",
                            "description": "Optional title to show above the webview (defaults to 'Web View')",
                        },
                    },
                    "required": ["url"],
                },
            },
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        room_id: str | None = None,
        session_id: str | None = None,
    ) -> ToolResult:
        """Execute the webview tool.

        Args:
            arguments: Tool arguments with 'url' and optional 'title'
            room_id: Room identifier for MQTT publishing
            session_id: Session identifier for MQTT publishing

        Returns:
            ToolResult with display_action for rendering iframe
        """
        url = arguments.get("url", "")
        title = arguments.get("title", "Web View")

        # Validate URL exists
        if not url or not url.strip():
            return ToolResult(
                success=False,
                content="No URL provided. Please specify a website to open.",
                metadata={"error": "missing_url"},
            )

        # Add protocol if missing
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        logger.info(f"Opening website: {url} (title: {title})")

        # Create display action for React Dashboard
        display_action = {
            "type": "web_view",
            "data": {
                "url": url,
                "title": title,
            },
        }

        # Publish to MQTT for real-time UI update
        if room_id and session_id:
            try:
                from app.services.mqtt_client import get_mqtt_client
                mqtt = get_mqtt_client()
                mqtt.publish_display_action(
                    action_type="web_view",
                    action_data=display_action["data"],
                    room_id=room_id,
                    session_id=session_id,
                )
                logger.debug(f"Published web_view action to MQTT: {room_id}/{session_id}")
            except Exception as e:
                logger.warning(f"Failed to publish web_view to MQTT: {e}")
                # Continue anyway - display_action will still work

        return ToolResult(
            success=True,
            content=f"Opening {url} in the display",
            display_action=display_action,
            metadata={"url": url, "title": title},
        )
