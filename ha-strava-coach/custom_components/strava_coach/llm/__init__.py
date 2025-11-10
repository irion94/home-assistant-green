"""LLM package for Strava Coach."""

from __future__ import annotations

from .adapter import LLMAdapter, LLMError
from .schema import (
    SUGGESTION_SCHEMA,
    SYSTEM_PROMPT,
    build_user_prompt,
    validate_suggestion_response,
)

__all__ = [
    "LLMAdapter",
    "LLMError",
    "SUGGESTION_SCHEMA",
    "SYSTEM_PROMPT",
    "build_user_prompt",
    "validate_suggestion_response",
]
