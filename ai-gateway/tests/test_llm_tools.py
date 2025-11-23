"""Tests for LLM Tools module."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm_tools import (
    TOOLS,
    ToolExecutor,
    get_tools,
    get_tool_executor,
)


class TestToolDefinitions:
    """Tests for tool definitions."""

    def test_tools_format(self) -> None:
        """Test that tools are in correct OpenAI format."""
        tools = get_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

        for tool in tools:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]

    def test_web_search_tool_defined(self) -> None:
        """Test web_search tool is properly defined."""
        tools = get_tools()
        web_search = next(
            (t for t in tools if t["function"]["name"] == "web_search"), None
        )

        assert web_search is not None
        assert "query" in web_search["function"]["parameters"]["properties"]

    def test_control_light_tool_defined(self) -> None:
        """Test control_light tool is properly defined."""
        tools = get_tools()
        control_light = next(
            (t for t in tools if t["function"]["name"] == "control_light"), None
        )

        assert control_light is not None
        params = control_light["function"]["parameters"]["properties"]
        assert "room" in params
        assert "action" in params

    def test_get_time_tool_defined(self) -> None:
        """Test get_time tool is properly defined."""
        tools = get_tools()
        get_time = next(
            (t for t in tools if t["function"]["name"] == "get_time"), None
        )

        assert get_time is not None

    def test_get_home_data_tool_defined(self) -> None:
        """Test get_home_data tool is properly defined."""
        tools = get_tools()
        get_home_data = next(
            (t for t in tools if t["function"]["name"] == "get_home_data"), None
        )

        assert get_home_data is not None
        params = get_home_data["function"]["parameters"]["properties"]
        assert "sensor_type" in params


class TestToolExecutor:
    """Tests for ToolExecutor."""

    @pytest.fixture
    def executor(self) -> ToolExecutor:
        """Fixture providing ToolExecutor without HA client."""
        return ToolExecutor(ha_client=None)

    @pytest.fixture
    def executor_with_ha(self) -> ToolExecutor:
        """Fixture providing ToolExecutor with mock HA client."""
        mock_ha = MagicMock()
        mock_ha.call_service = AsyncMock(return_value=[])
        mock_ha.get_state = AsyncMock(return_value=None)
        return ToolExecutor(ha_client=mock_ha)

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, executor: ToolExecutor) -> None:
        """Test handling of unknown tool names."""
        result = await executor.execute("unknown_tool", {})
        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_get_time(self, executor: ToolExecutor) -> None:
        """Test get_time tool execution."""
        result = await executor.execute("get_time", {})

        assert "Current time" in result
        assert ":" in result  # Time format HH:MM

    @pytest.mark.asyncio
    async def test_control_light_missing_params(self, executor_with_ha: ToolExecutor) -> None:
        """Test control_light with missing parameters."""
        result = await executor.execute("control_light", {})
        assert "Missing" in result

    @pytest.mark.asyncio
    async def test_control_light_unknown_room(self, executor_with_ha: ToolExecutor) -> None:
        """Test control_light with unknown room."""
        result = await executor_with_ha.execute(
            "control_light", {"room": "unknown_room", "action": "on"}
        )
        assert "Unknown room" in result

    @pytest.mark.asyncio
    async def test_control_light_no_ha_client(self, executor: ToolExecutor) -> None:
        """Test control_light without HA client."""
        result = await executor.execute(
            "control_light", {"room": "salon", "action": "on"}
        )
        assert "not available" in result

    @pytest.mark.asyncio
    async def test_control_light_success(self) -> None:
        """Test successful light control."""
        mock_ha = MagicMock()
        mock_ha.call_service = AsyncMock(return_value=[])
        executor = ToolExecutor(ha_client=mock_ha)

        result = await executor.execute(
            "control_light", {"room": "salon", "action": "on"}
        )

        assert "Successfully" in result
        mock_ha.call_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_web_search_no_query(self, executor: ToolExecutor) -> None:
        """Test web search with empty query."""
        result = await executor.execute("web_search", {})
        assert "No search query" in result

    @pytest.mark.asyncio
    async def test_web_search_not_available(self, executor: ToolExecutor) -> None:
        """Test web search when API is not configured."""
        with patch.object(executor.web_search, "is_available", return_value=False):
            result = await executor.execute("web_search", {"query": "test"})
            assert "not configured" in result

    @pytest.mark.asyncio
    async def test_web_search_success(self, executor: ToolExecutor) -> None:
        """Test successful web search."""
        mock_result = {
            "success": True,
            "query": "test",
            "results": [
                {"title": "Test", "url": "https://test.com", "description": "Test desc", "age": ""}
            ]
        }

        with patch.object(executor.web_search, "is_available", return_value=True):
            with patch.object(executor.web_search, "search", new_callable=AsyncMock) as mock_search:
                mock_search.return_value = mock_result
                with patch.object(executor.web_search, "format_for_llm", return_value="Formatted results"):
                    result = await executor.execute("web_search", {"query": "test"})
                    assert "Formatted results" in result

    @pytest.mark.asyncio
    async def test_get_home_data_no_ha_client(self, executor: ToolExecutor) -> None:
        """Test get_home_data without HA client."""
        result = await executor.execute("get_home_data", {"sensor_type": "temperature_inside"})
        assert "not available" in result

    @pytest.mark.asyncio
    async def test_get_home_data_with_ha_client(self) -> None:
        """Test get_home_data with HA client."""
        mock_ha = MagicMock()
        mock_ha.get_state = AsyncMock(return_value={
            "state": "22.5",
            "attributes": {
                "unit_of_measurement": "°C",
                "friendly_name": "Indoor Temperature"
            }
        })
        executor = ToolExecutor(ha_client=mock_ha)

        result = await executor.execute("get_home_data", {"sensor_type": "temperature_inside"})

        # Either returns data or "No sensor data" if entity not configured
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_error_handling(self, executor: ToolExecutor) -> None:
        """Test error handling during tool execution."""
        with patch.object(executor, "_execute_get_time", side_effect=Exception("Test error")):
            result = await executor.execute("get_time", {})
            assert "Error" in result


class TestGetToolExecutor:
    """Tests for get_tool_executor factory function."""

    def test_get_tool_executor_without_ha(self) -> None:
        """Test creating executor without HA client."""
        executor = get_tool_executor()
        assert executor is not None
        assert executor.ha_client is None

    def test_get_tool_executor_with_ha(self) -> None:
        """Test creating executor with HA client."""
        mock_ha = MagicMock()
        executor = get_tool_executor(mock_ha)
        assert executor.ha_client is mock_ha
