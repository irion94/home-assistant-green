"""API router for tool management and metrics endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class ToolMetricsResponse(BaseModel):
    """Response schema for tool metrics."""

    metrics: list[dict[str, Any]] | dict[str, Any] = Field(
        ..., description="Tool execution metrics"
    )


class MetricsResetResponse(BaseModel):
    """Response schema for metrics reset."""

    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")


@router.get("/tools/metrics", response_model=ToolMetricsResponse)
async def get_tool_metrics(tool_name: str | None = None) -> ToolMetricsResponse:
    """Get execution metrics for all tools or specific tool.

    Args:
        tool_name: Optional tool name. If omitted, returns metrics for all tools.

    Returns:
        ToolMetricsResponse with execution metrics including:
        - total_executions: Number of times tool was called
        - successful_executions: Number of successful executions
        - failed_executions: Number of failed executions
        - success_rate: Success rate as percentage
        - avg_latency_ms: Average execution time in milliseconds
        - min_latency_ms: Minimum execution time
        - max_latency_ms: Maximum execution time
        - last_execution_time: Unix timestamp of last execution
        - error_counts: Breakdown of error types

    Example:
        GET /tools/metrics
        GET /tools/metrics?tool_name=web_search
    """
    try:
        from app.services.tools.registry import tool_registry

        metrics = tool_registry.get_metrics(tool_name)

        return ToolMetricsResponse(metrics=metrics)

    except Exception as e:
        logger.error(f"Error retrieving tool metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics: {e}")


@router.post("/tools/metrics/reset", response_model=MetricsResetResponse)
async def reset_tool_metrics(tool_name: str | None = None) -> MetricsResetResponse:
    """Reset execution metrics for all tools or specific tool.

    Args:
        tool_name: Optional tool name. If omitted, resets all tool metrics.

    Returns:
        MetricsResetResponse with operation status

    Example:
        POST /tools/metrics/reset
        POST /tools/metrics/reset?tool_name=web_search
    """
    try:
        from app.services.tools.registry import tool_registry

        tool_registry.reset_metrics(tool_name)

        if tool_name:
            message = f"Metrics reset for tool: {tool_name}"
        else:
            message = "Metrics reset for all tools"

        return MetricsResetResponse(status="success", message=message)

    except Exception as e:
        logger.error(f"Error resetting tool metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset metrics: {e}")


@router.get("/tools")
async def list_tools() -> dict[str, Any]:
    """Get list of all registered tools with their schemas.

    Returns:
        Dictionary with:
        - count: Number of registered tools
        - tools: List of tool names
        - schemas: Full OpenAI function calling schemas

    Example:
        GET /tools
    """
    try:
        from app.services.tools.registry import tool_registry

        return {
            "count": len(tool_registry),
            "tools": tool_registry.list_tools(),
            "schemas": tool_registry.get_schemas(),
        }

    except Exception as e:
        logger.error(f"Error listing tools: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {e}")
