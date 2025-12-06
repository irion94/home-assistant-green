"""Tool system for AI Gateway.

This package provides a modular, extensible architecture for AI tools
that can be called by the LLM via OpenAI function calling.
"""

from __future__ import annotations

from app.services.tools.base import BaseTool, ToolResult
from app.services.tools.registry import ToolRegistry, tool_registry

__all__ = ["BaseTool", "ToolResult", "ToolRegistry", "tool_registry"]
