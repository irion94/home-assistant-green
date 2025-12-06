"""Base classes for AI Gateway tools.

Defines the abstract base class and result model for all tools.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Standardized result format for all tools.

    Attributes:
        success: Whether the tool execution succeeded
        content: Text content for LLM response
        display_action: Optional display action data for dashboard
        metadata: Additional metadata about execution
    """

    success: bool = Field(..., description="Whether execution succeeded")
    content: str = Field(..., description="Text content for LLM")
    display_action: dict[str, Any] | None = Field(
        None,
        description="Display action for React Dashboard (type, data, timestamp)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional execution metadata"
    )


class BaseTool(ABC):
    """Abstract base class for all AI tools.

    All tools must implement:
    - name: Tool identifier (used in OpenAI function calls)
    - schema: OpenAI function calling schema
    - execute: Tool execution logic
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier for function calling.

        Returns:
            Unique tool name (e.g., 'web_search', 'control_light')
        """
        pass

    @property
    @abstractmethod
    def schema(self) -> dict[str, Any]:
        """OpenAI function calling schema.

        Returns:
            Schema dict with type='function' and function definition
        """
        pass

    @abstractmethod
    async def execute(
        self,
        arguments: dict[str, Any],
        room_id: str | None = None,
        session_id: str | None = None,
    ) -> ToolResult:
        """Execute the tool with given arguments.

        Args:
            arguments: Tool-specific arguments from LLM
            room_id: Optional room context for multi-room support
            session_id: Optional session ID for conversation tracking

        Returns:
            ToolResult with execution outcome
        """
        pass

    def __repr__(self) -> str:
        """String representation."""
        return f"<{self.__class__.__name__}(name='{self.name}')>"
