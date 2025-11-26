"""Time tool for getting current time."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.services.tools.base import BaseTool, ToolResult


class GetTimeTool(BaseTool):
    """Tool for getting the current time."""

    @property
    def name(self) -> str:
        """Tool name."""
        return "get_time"

    @property
    def schema(self) -> dict[str, Any]:
        """OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "Get the current time. Use when user asks about the time.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        room_id: str | None = None,
        session_id: str | None = None,
    ) -> ToolResult:
        """Get current time in Warsaw timezone.

        Args:
            arguments: No arguments required
            room_id: Not used
            session_id: Not used

        Returns:
            ToolResult with current time
        """
        try:
            warsaw_tz = ZoneInfo("Europe/Warsaw")
            now = datetime.now(warsaw_tz)
            time_str = now.strftime("%H:%M")
            date_str = now.strftime("%Y-%m-%d")
            day_name = now.strftime("%A")

            content = f"Teraz jest godzina {time_str}, {day_name}, {date_str}"

            return ToolResult(
                success=True,
                content=content,
                metadata={
                    "time": time_str,
                    "date": date_str,
                    "day": day_name,
                    "timezone": "Europe/Warsaw",
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                content=f"Error getting time: {str(e)}",
                metadata={"error": "exception", "exception": str(e)},
            )
