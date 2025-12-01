"""Tests for GetTimeTool."""

import pytest
from datetime import datetime
from app.services.tools.time_tool import GetTimeTool


@pytest.fixture
def time_tool():
    """Fixture providing GetTimeTool instance."""
    return GetTimeTool()


class TestGetTimeTool:
    """Test suite for GetTimeTool."""

    def test_tool_name(self, time_tool):
        """Test tool name is correct."""
        assert time_tool.name == "get_time"

    def test_schema_structure(self, time_tool):
        """Test schema has required OpenAI structure."""
        schema = time_tool.schema
        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "get_time"
        assert "parameters" in schema["function"]
        assert schema["function"]["parameters"]["type"] == "object"

    def test_schema_no_required_params(self, time_tool):
        """Test schema has no required parameters."""
        schema = time_tool.schema
        assert schema["function"]["parameters"]["required"] == []

    @pytest.mark.asyncio
    async def test_successful_execution(self, time_tool):
        """Test successful time retrieval."""
        result = await time_tool.execute(
            arguments={},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert result.content is not None
        assert "godzina" in result.content.lower()
        assert result.metadata["timezone"] == "Europe/Warsaw"
        assert "time" in result.metadata
        assert "date" in result.metadata
        assert "day" in result.metadata

    @pytest.mark.asyncio
    async def test_display_action_structure(self, time_tool):
        """Test display action is correctly formatted."""
        result = await time_tool.execute(
            arguments={},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.display_action is not None
        assert result.display_action["type"] == "get_time"
        assert "data" in result.display_action
        data = result.display_action["data"]
        assert "time" in data
        assert "date" in data
        assert "day" in data
        assert data["timezone"] == "Europe/Warsaw"

    @pytest.mark.asyncio
    async def test_time_format(self, time_tool):
        """Test time format is HH:MM."""
        result = await time_tool.execute(arguments={})

        time_str = result.metadata["time"]
        assert ":" in time_str
        parts = time_str.split(":")
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1].isdigit()
        assert 0 <= int(parts[0]) < 24
        assert 0 <= int(parts[1]) < 60

    @pytest.mark.asyncio
    async def test_date_format(self, time_tool):
        """Test date format is YYYY-MM-DD."""
        result = await time_tool.execute(arguments={})

        date_str = result.metadata["date"]
        assert len(date_str) == 10
        assert date_str[4] == "-"
        assert date_str[7] == "-"
        # Validate it's a parseable date
        datetime.strptime(date_str, "%Y-%m-%d")

    @pytest.mark.asyncio
    async def test_no_arguments_required(self, time_tool):
        """Test tool works with empty arguments."""
        result = await time_tool.execute(arguments={})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_works_without_room_session(self, time_tool):
        """Test tool works without room_id and session_id."""
        result = await time_tool.execute(arguments={})
        assert result.success is True
        assert result.content is not None
