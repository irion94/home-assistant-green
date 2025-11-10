"""OpenAI LLM adapter with aggregates-only guardrails."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI, OpenAIError

from .schema import (
    SUGGESTION_SCHEMA,
    SYSTEM_PROMPT,
    build_user_prompt,
    validate_suggestion_response,
)

_LOGGER = logging.getLogger(__name__)

# Fields that are ALLOWED to be sent to LLM (aggregates only)
ALLOWED_FIELDS = {
    "readiness",
    "tsb",
    "atl",
    "ctl",
    "monotony",
    "rest_days",
    "recent_load_7d",
    "date",
    "day_of_week",
}

# Fields that are FORBIDDEN (raw Strava data)
FORBIDDEN_FIELDS = {
    "id",
    "athlete_id",
    "name",
    "sport_type",
    "start_date",
    "start_date_local",
    "timezone",
    "moving_time",
    "elapsed_time",
    "distance",
    "total_elevation_gain",
    "average_heartrate",
    "max_heartrate",
    "average_watts",
    "weighted_average_watts",
    "kilojoules",
    "training_load",
    "intensity_factor",
    "summary_data",
    "lat",
    "lng",
    "polyline",
    "stream",
}


class LLMAdapter:
    """OpenAI adapter for generating training suggestions."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        aggregates_only: bool = True,
    ) -> None:
        """Initialize the LLM adapter.

        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4-turbo-preview)
            aggregates_only: If True, enforce strict filtering of raw Strava fields
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.aggregates_only = aggregates_only
        _LOGGER.info("LLM adapter initialized: model=%s, aggregates_only=%s", model, aggregates_only)

    def _filter_metrics(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Filter metrics to ensure only aggregates are included.

        Args:
            metrics: Input metrics dictionary

        Returns:
            Filtered metrics with only allowed fields

        Raises:
            ValueError: If aggregates_only=True and forbidden fields are present
        """
        filtered = {}

        for key, value in metrics.items():
            if key in FORBIDDEN_FIELDS:
                if self.aggregates_only:
                    _LOGGER.error("Forbidden field '%s' found in metrics", key)
                    raise ValueError(
                        f"Forbidden field '{key}' detected. "
                        "LLM adapter is configured for aggregates_only=True."
                    )
                else:
                    _LOGGER.warning("Forbidden field '%s' skipped (aggregates_only=False)", key)
                    continue

            if key in ALLOWED_FIELDS:
                filtered[key] = value
            else:
                _LOGGER.debug("Unknown field '%s' skipped", key)

        return filtered

    async def generate_suggestion(
        self,
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a training suggestion using OpenAI.

        Args:
            metrics: Aggregated metrics (readiness, tsb, atl, ctl, etc.)

        Returns:
            Suggestion dict with keys: command, params, rationale_short

        Raises:
            ValueError: If metrics contain forbidden fields (when aggregates_only=True)
            LLMError: If LLM request fails
        """
        # Filter metrics to ensure compliance
        filtered_metrics = self._filter_metrics(metrics)

        _LOGGER.debug("Filtered metrics for LLM: %s", filtered_metrics)

        # Build prompt
        user_prompt = build_user_prompt(filtered_metrics)

        try:
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=200,
            )

            # Parse response
            content = response.choices[0].message.content
            if not content:
                raise LLMError("Empty response from LLM")

            suggestion = json.loads(content)

            # Validate response
            if not validate_suggestion_response(suggestion):
                _LOGGER.warning("LLM response failed validation: %s", suggestion)
                raise LLMError("Invalid suggestion format from LLM")

            _LOGGER.info(
                "LLM suggestion generated: command=%s, rationale=%s",
                suggestion.get("command"),
                suggestion.get("rationale_short"),
            )

            return suggestion

        except OpenAIError as err:
            _LOGGER.error("OpenAI API error: %s", err)
            raise LLMError(f"OpenAI API error: {err}") from err
        except json.JSONDecodeError as err:
            _LOGGER.error("Failed to parse LLM response as JSON: %s", err)
            raise LLMError("Invalid JSON response from LLM") from err
        except Exception as err:
            _LOGGER.error("Unexpected error in LLM adapter: %s", err)
            raise LLMError(f"LLM adapter error: {err}") from err


class LLMError(Exception):
    """Exception raised for LLM adapter errors."""

    pass
