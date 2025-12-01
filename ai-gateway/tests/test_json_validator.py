"""Tests for JSON validation utilities."""

from __future__ import annotations

import pytest

from app.utils.json_validator import extract_json, parse_ollama_response, validate_ha_action


class TestExtractJson:
    """Tests for extract_json function."""

    def test_extract_simple_json(self) -> None:
        """Test extracting simple JSON object."""
        text = '{"action":"call_service"}'
        result = extract_json(text)
        assert result == '{"action":"call_service"}'

    def test_extract_json_with_prefix(self) -> None:
        """Test extracting JSON with text before it."""
        text = 'Sure, here is the result: {"action":"none"}'
        result = extract_json(text)
        assert result == '{"action":"none"}'

    def test_extract_json_with_suffix(self) -> None:
        """Test extracting JSON with text after it."""
        text = '{"action":"call_service"} - Hope this helps!'
        result = extract_json(text)
        assert result == '{"action":"call_service"}'

    def test_extract_json_embedded(self, json_with_extra_text: str) -> None:
        """Test extracting JSON embedded in text."""
        result = extract_json(json_with_extra_text)
        assert result is not None
        assert '"action":"call_service"' in result

    def test_extract_no_json(self) -> None:
        """Test handling text with no JSON."""
        text = "This is just plain text without any JSON"
        result = extract_json(text)
        assert result is None

    def test_extract_incomplete_json(self) -> None:
        """Test handling incomplete JSON."""
        text = '{"action":"call_service"'
        result = extract_json(text)
        # Should return None because closing brace is missing
        assert result is None


class TestValidateHaAction:
    """Tests for validate_ha_action function."""

    def test_validate_valid_call_service(self, valid_json_response: str) -> None:
        """Test validating valid call_service action."""
        result = validate_ha_action(valid_json_response)
        assert result is not None
        assert result.action == "call_service"
        assert result.service == "light.turn_on"
        assert result.entity_id == "light.living_room_main"

    def test_validate_none_action(self) -> None:
        """Test validating 'none' action."""
        json_str = '{"action":"none"}'
        result = validate_ha_action(json_str)
        assert result is not None
        assert result.action == "none"
        assert result.service is None
        assert result.entity_id is None

    def test_validate_with_brightness(self) -> None:
        """Test validating action with brightness data."""
        json_str = '{"action":"call_service","service":"light.turn_on","entity_id":"light.bedroom","data":{"brightness":128}}'
        result = validate_ha_action(json_str)
        assert result is not None
        assert result.data == {"brightness": 128}

    def test_validate_invalid_json(self, invalid_json_response: str) -> None:
        """Test handling malformed JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            validate_ha_action(invalid_json_response)

    def test_validate_missing_required_fields(self) -> None:
        """Test validation of call_service missing required fields."""
        # Missing service and entity_id for call_service
        json_str = '{"action":"call_service"}'
        result = validate_ha_action(json_str)
        # Should return None due to business logic validation
        assert result is None

    def test_validate_call_service_missing_entity(self) -> None:
        """Test call_service action missing entity_id."""
        json_str = '{"action":"call_service","service":"light.turn_on"}'
        result = validate_ha_action(json_str)
        assert result is None


class TestParseOllamaResponse:
    """Tests for parse_ollama_response function."""

    def test_parse_clean_json(self, valid_json_response: str) -> None:
        """Test parsing clean JSON response."""
        result = parse_ollama_response(valid_json_response)
        assert result is not None
        assert result.action == "call_service"

    def test_parse_json_with_text(self, json_with_extra_text: str) -> None:
        """Test parsing JSON embedded in text."""
        result = parse_ollama_response(json_with_extra_text)
        assert result is not None
        assert result.action == "call_service"
        assert result.entity_id == "light.kitchen"

    def test_parse_no_json(self) -> None:
        """Test parsing response with no JSON."""
        result = parse_ollama_response("Just plain text")
        assert result is None

    def test_parse_invalid_json(self, invalid_json_response: str) -> None:
        """Test parsing invalid JSON."""
        result = parse_ollama_response(invalid_json_response)
        assert result is None

    def test_parse_none_action(self) -> None:
        """Test parsing 'none' action response."""
        response = '{"action":"none"}'
        result = parse_ollama_response(response)
        assert result is not None
        assert result.action == "none"
