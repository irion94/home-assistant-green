"""JSON validation utilities for Ollama responses.

This module provides utilities for parsing and validating JSON responses
from the Ollama LLM, with robust error handling for malformed output.
"""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from app.models import HAAction

logger = logging.getLogger(__name__)


def extract_json(text: str) -> str | None:
    """Extract JSON from text that may contain additional content.

    Args:
        text: Raw text that should contain JSON

    Returns:
        Extracted JSON string, or None if no valid JSON found
    """
    # Try to find JSON object in the text
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return None

    return text[start : end + 1]


def validate_ha_action(json_str: str) -> HAAction | None:
    """Validate and parse JSON string into HAAction model.

    Args:
        json_str: JSON string to validate

    Returns:
        Validated HAAction model, or None if validation fails

    Raises:
        ValueError: If JSON is malformed or doesn't match schema
    """
    try:
        # Parse JSON
        data = json.loads(json_str)
        logger.debug(f"Parsed JSON: {data}")

        # Validate with Pydantic
        action = HAAction(**data)

        # Additional business logic validation
        if action.action == "call_service":
            if not action.service or not action.entity_id:
                logger.warning(
                    f"call_service action missing required fields: "
                    f"service={action.service}, entity_id={action.entity_id}"
                )
                return None

        return action

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        raise ValueError(f"Invalid JSON: {e}")

    except ValidationError as e:
        logger.error(f"Pydantic validation error: {e}")
        raise ValueError(f"Invalid action schema: {e}")


def parse_ollama_response(response_text: str) -> HAAction | None:
    """Parse and validate Ollama response into HAAction.

    This function handles the full parsing pipeline:
    1. Extract JSON from potentially messy response
    2. Validate JSON structure
    3. Validate business logic

    Args:
        response_text: Raw text response from Ollama

    Returns:
        Validated HAAction, or None if parsing/validation fails
    """
    # Try to extract JSON
    json_str = extract_json(response_text)
    if not json_str:
        logger.warning(f"No JSON found in response: {response_text[:100]}")
        return None

    # Validate and parse
    try:
        return validate_ha_action(json_str)
    except ValueError as e:
        logger.error(f"Failed to validate action: {e}")
        return None
