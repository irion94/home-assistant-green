"""Tool registry for dynamic tool management.

Provides centralized registration and execution of tools.
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Dynamic tool registration and management.

    Maintains a registry of available tools and provides:
    - Tool registration
    - Schema generation for OpenAI API
    - Unified tool execution
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool in the registry.

        Args:
            tool: Tool instance to register

        Raises:
            ValueError: If tool with same name already registered
        """
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, replacing")

        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister(self, tool_name: str) -> bool:
        """Unregister a tool by name.

        Args:
            tool_name: Name of tool to remove

        Returns:
            True if tool was removed, False if not found
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
            return True
        return False

    def get_tool(self, name: str) -> BaseTool | None:
        """Get tool by name.

        Args:
            name: Tool name to retrieve

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def get_schemas(self) -> list[dict[str, Any]]:
        """Get all tool schemas for OpenAI API.

        Returns:
            List of tool schemas in OpenAI function calling format
        """
        return [tool.schema for tool in self._tools.values()]

    def list_tools(self) -> list[str]:
        """Get list of registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        room_id: str | None = None,
        session_id: str | None = None,
    ) -> ToolResult:
        """Execute tool by name.

        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments from LLM
            room_id: Optional room context
            session_id: Optional session ID

        Returns:
            ToolResult with execution outcome
        """
        tool = self.get_tool(tool_name)

        if not tool:
            logger.error(f"Tool '{tool_name}' not found in registry")
            return ToolResult(
                success=False,
                content=f"Tool '{tool_name}' not found. Available tools: {', '.join(self.list_tools())}",
                metadata={"error": "unknown_tool", "tool_name": tool_name},
            )

        try:
            logger.info(
                f"Executing tool '{tool_name}' with arguments: {arguments}"
            )
            result = await tool.execute(arguments, room_id, session_id)
            logger.info(
                f"Tool '{tool_name}' completed: success={result.success}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Error executing tool '{tool_name}': {e}", exc_info=True
            )
            return ToolResult(
                success=False,
                content=f"Error executing {tool_name}: {str(e)}",
                metadata={
                    "error": "execution_failed",
                    "tool_name": tool_name,
                    "exception": str(e),
                },
            )

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)

    def __repr__(self) -> str:
        """String representation."""
        tools = ", ".join(self.list_tools())
        return f"<ToolRegistry({len(self)} tools: {tools})>"


# Global singleton registry
tool_registry = ToolRegistry()
