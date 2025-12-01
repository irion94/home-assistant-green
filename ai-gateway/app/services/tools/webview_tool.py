"""WebView tool for displaying websites in the React Dashboard."""

from __future__ import annotations

import logging
from typing import Any

from app.services.tools.base import BaseTool, ToolResult
from app.security.url_validator import get_url_validator

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
        """Execute the webview tool with URL validation.

        Args:
            arguments: Tool arguments with 'url' and optional 'title'
            room_id: Room identifier for MQTT publishing
            session_id: Session identifier for MQTT publishing

        Returns:
            ToolResult with display_action for rendering iframe
        """
        url = arguments.get("url", "")
        title = arguments.get("title", "Web View")

        # Validate URL with security checks (Phase 1)
        validator = get_url_validator()
        is_valid, normalized_url, error = validator.validate(url)

        if not is_valid:
            logger.warning(f"WebView URL validation failed: {error} (url={url})")
            return ToolResult(
                success=False,
                content=f"Cannot open URL: {error}",
                metadata={"error": "url_validation_failed", "details": error, "url": url},
            )

        # Use normalized URL (with https:// prefix added if missing)
        url = normalized_url

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
