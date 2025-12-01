"""Tool registry for dynamic tool management.

Provides centralized registration and execution of tools.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.services.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class ToolMetrics:
    """Metrics for a single tool."""

    tool_name: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0
    last_execution_time: float | None = None
    error_counts: dict[str, int] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_executions == 0:
            return 0.0
        return (self.successful_executions / self.total_executions) * 100

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if self.total_executions == 0:
            return 0.0
        return self.total_latency_ms / self.total_executions

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            "tool_name": self.tool_name,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": round(self.success_rate, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "min_latency_ms": self.min_latency_ms if self.min_latency_ms != float("inf") else 0,
            "max_latency_ms": round(self.max_latency_ms, 2),
            "last_execution_time": self.last_execution_time,
            "error_counts": self.error_counts,
        }


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
        self._metrics: dict[str, ToolMetrics] = {}

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
        self._metrics[tool.name] = ToolMetrics(tool_name=tool.name)
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
        """Execute tool by name and track metrics.

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

        # Start timing
        start_time = time.time()
        metrics = self._metrics.get(tool_name)

        try:
            logger.info(
                f"Executing tool '{tool_name}' with arguments: {arguments}"
            )
            result = await tool.execute(arguments, room_id, session_id)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Update metrics
            if metrics:
                metrics.total_executions += 1
                metrics.last_execution_time = time.time()
                metrics.total_latency_ms += latency_ms
                metrics.min_latency_ms = min(metrics.min_latency_ms, latency_ms)
                metrics.max_latency_ms = max(metrics.max_latency_ms, latency_ms)

                if result.success:
                    metrics.successful_executions += 1
                else:
                    metrics.failed_executions += 1
                    # Track error type from metadata
                    error_type = result.metadata.get("error", "unknown_error")
                    metrics.error_counts[error_type] = metrics.error_counts.get(error_type, 0) + 1

            logger.info(
                f"Tool '{tool_name}' completed: success={result.success}, latency={latency_ms:.2f}ms"
            )

            # Publish tool execution event to MQTT for history panel
            if room_id and session_id:
                try:
                    from app.services.mqtt_client import get_mqtt_client
                    from app.config.mqtt_topics import get_mqtt_config
                    import json

                    mqtt = get_mqtt_client()
                    topics = get_mqtt_config()
                    topic = topics.tool_executed(room_id, session_id)
                    payload = {
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "success": result.success,
                        "latency_ms": round(latency_ms, 2),
                        "timestamp": time.time(),
                        "content": result.content[:100] if result.content else None,  # Truncate for brevity
                    }
                    mqtt.client.publish(topic, json.dumps(payload), qos=1)
                    logger.debug(f"Published tool_executed event to MQTT: {tool_name}")
                except Exception as mqtt_error:
                    logger.warning(f"Failed to publish tool_executed to MQTT: {mqtt_error}")

            return result

        except Exception as e:
            # Calculate latency even for exceptions
            latency_ms = (time.time() - start_time) * 1000

            # Update metrics for exception
            if metrics:
                metrics.total_executions += 1
                metrics.failed_executions += 1
                metrics.last_execution_time = time.time()
                metrics.total_latency_ms += latency_ms
                metrics.min_latency_ms = min(metrics.min_latency_ms, latency_ms)
                metrics.max_latency_ms = max(metrics.max_latency_ms, latency_ms)
                # Track exception type
                exception_type = type(e).__name__
                metrics.error_counts[exception_type] = metrics.error_counts.get(exception_type, 0) + 1

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

    def get_metrics(self, tool_name: str | None = None) -> dict[str, Any] | list[dict[str, Any]]:
        """Get metrics for specific tool or all tools.

        Args:
            tool_name: Optional tool name. If None, returns all metrics.

        Returns:
            Metrics dictionary for specific tool, or list of all metrics
        """
        if tool_name:
            metrics = self._metrics.get(tool_name)
            if not metrics:
                return {"error": f"Tool '{tool_name}' not found"}
            return metrics.to_dict()

        # Return all metrics
        return [metrics.to_dict() for metrics in self._metrics.values()]

    def reset_metrics(self, tool_name: str | None = None) -> None:
        """Reset metrics for specific tool or all tools.

        Args:
            tool_name: Optional tool name. If None, resets all metrics.
        """
        if tool_name:
            if tool_name in self._metrics:
                self._metrics[tool_name] = ToolMetrics(tool_name=tool_name)
                logger.info(f"Reset metrics for tool: {tool_name}")
        else:
            # Reset all metrics
            for name in self._metrics:
                self._metrics[name] = ToolMetrics(tool_name=name)
            logger.info("Reset metrics for all tools")

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)

    def __repr__(self) -> str:
        """String representation."""
        tools = ", ".join(self.list_tools())
        return f"<ToolRegistry({len(self)} tools: {tools})>"


# Global singleton registry
tool_registry = ToolRegistry()
