"""Tests for LLM guardrails and aggregates-only enforcement."""

from __future__ import annotations

import pytest

from custom_components.strava_coach.llm.adapter import LLMAdapter


class TestLLMGuardrails:
    """Test LLM guardrails to prevent raw Strava data transmission."""

    def test_aggregates_only_allows_safe_fields(self) -> None:
        """Test that aggregates_only=True allows only safe fields."""
        adapter = LLMAdapter(
            api_key="test_key",
            aggregates_only=True,
        )

        metrics = {
            "readiness": 75.0,
            "tsb": 5.0,
            "atl": 80.0,
            "ctl": 85.0,
            "monotony": 3.0,
            "rest_days": 1,
            "recent_load_7d": 500.0,
            "date": "2025-01-15",
            "day_of_week": "Wednesday",
        }

        # Should not raise
        filtered = adapter._filter_metrics(metrics)

        assert filtered == metrics

    def test_aggregates_only_blocks_raw_fields(self) -> None:
        """Test that aggregates_only=True blocks raw Strava fields."""
        adapter = LLMAdapter(
            api_key="test_key",
            aggregates_only=True,
        )

        metrics = {
            "readiness": 75.0,
            "tsb": 5.0,
            "athlete_id": 12345,  # FORBIDDEN
            "name": "Morning Ride",  # FORBIDDEN
            "average_watts": 250,  # FORBIDDEN
        }

        # Should raise ValueError
        with pytest.raises(ValueError, match="Forbidden field"):
            adapter._filter_metrics(metrics)

    def test_aggregates_only_blocks_activity_id(self) -> None:
        """Test that activity ID is blocked."""
        adapter = LLMAdapter(
            api_key="test_key",
            aggregates_only=True,
        )

        metrics = {
            "readiness": 75.0,
            "id": 987654321,  # FORBIDDEN
        }

        with pytest.raises(ValueError, match="Forbidden field"):
            adapter._filter_metrics(metrics)

    def test_aggregates_only_blocks_location_data(self) -> None:
        """Test that location data is blocked."""
        adapter = LLMAdapter(
            api_key="test_key",
            aggregates_only=True,
        )

        metrics = {
            "readiness": 75.0,
            "lat": 52.5200,  # FORBIDDEN
            "lng": 13.4050,  # FORBIDDEN
        }

        with pytest.raises(ValueError, match="Forbidden field"):
            adapter._filter_metrics(metrics)

    def test_aggregates_only_blocks_heart_rate_data(self) -> None:
        """Test that raw HR data is blocked."""
        adapter = LLMAdapter(
            api_key="test_key",
            aggregates_only=True,
        )

        metrics = {
            "readiness": 75.0,
            "average_heartrate": 150,  # FORBIDDEN
            "max_heartrate": 180,  # FORBIDDEN
        }

        with pytest.raises(ValueError, match="Forbidden field"):
            adapter._filter_metrics(metrics)

    def test_aggregates_only_false_allows_raw_fields(self) -> None:
        """Test that aggregates_only=False allows raw fields (logs warning)."""
        adapter = LLMAdapter(
            api_key="test_key",
            aggregates_only=False,
        )

        metrics = {
            "readiness": 75.0,
            "athlete_id": 12345,  # Would be forbidden if aggregates_only=True
            "average_watts": 250,
        }

        # Should not raise, but filters out forbidden fields with warning
        filtered = adapter._filter_metrics(metrics)

        # Only allowed field should remain
        assert "readiness" in filtered
        assert "athlete_id" not in filtered  # Still filtered even with aggregates_only=False
        assert "average_watts" not in filtered

    def test_empty_metrics(self) -> None:
        """Test with empty metrics dict."""
        adapter = LLMAdapter(
            api_key="test_key",
            aggregates_only=True,
        )

        metrics: dict[str, str | float] = {}

        filtered = adapter._filter_metrics(metrics)

        assert filtered == {}

    def test_only_allowed_fields_returned(self) -> None:
        """Test that only explicitly allowed fields are returned."""
        adapter = LLMAdapter(
            api_key="test_key",
            aggregates_only=True,
        )

        metrics = {
            "readiness": 75.0,
            "tsb": 5.0,
            "atl": 80.0,
            "ctl": 85.0,
            "unknown_field": "value",  # Not in allowed list
        }

        filtered = adapter._filter_metrics(metrics)

        # Only known allowed fields should be present
        assert "readiness" in filtered
        assert "tsb" in filtered
        assert "atl" in filtered
        assert "ctl" in filtered
        assert "unknown_field" not in filtered


class TestLLMResponseValidation:
    """Test LLM response validation."""

    def test_valid_response(self) -> None:
        """Test validation of valid LLM response."""
        from custom_components.strava_coach.llm.schema import validate_suggestion_response

        response = {
            "command": "Z2_RIDE",
            "params": {"duration_min": 60, "zone": 2},
            "rationale_short": "Build aerobic base with Z2 training.",
        }

        assert validate_suggestion_response(response) is True

    def test_missing_required_field(self) -> None:
        """Test that missing required fields fail validation."""
        from custom_components.strava_coach.llm.schema import validate_suggestion_response

        response = {
            "command": "Z2_RIDE",
            # Missing rationale_short
        }

        assert validate_suggestion_response(response) is False

    def test_invalid_command(self) -> None:
        """Test that invalid command fails validation."""
        from custom_components.strava_coach.llm.schema import validate_suggestion_response

        response = {
            "command": "INVALID_COMMAND",
            "rationale_short": "Test rationale",
        }

        assert validate_suggestion_response(response) is False

    def test_rationale_too_long(self) -> None:
        """Test that rationale exceeding max length fails validation."""
        from custom_components.strava_coach.llm.schema import validate_suggestion_response

        response = {
            "command": "Z2_RIDE",
            "rationale_short": "x" * 151,  # Exceeds 150 char limit
        }

        assert validate_suggestion_response(response) is False
