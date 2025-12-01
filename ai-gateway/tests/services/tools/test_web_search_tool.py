"""Tests for WebSearchTool."""

import pytest
from unittest.mock import MagicMock, patch
from app.services.tools.web_search_tool import WebSearchTool


@pytest.fixture
def web_search_tool():
    """Fixture providing WebSearchTool instance."""
    with patch("app.services.tools.web_search_tool.get_web_search_client"), \
         patch("app.services.tools.web_search_tool.get_mqtt_client"):
        return WebSearchTool()


class TestWebSearchTool:
    """Test suite for WebSearchTool."""

    def test_tool_name(self, web_search_tool):
        """Test tool name is correct."""
        assert web_search_tool.name == "web_search"

    def test_schema_structure(self, web_search_tool):
        """Test schema has required OpenAI structure."""
        schema = web_search_tool.schema
        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "web_search"
        assert "parameters" in schema["function"]

    def test_schema_required_params(self, web_search_tool):
        """Test schema requires 'query' parameter."""
        schema = web_search_tool.schema
        params = schema["function"]["parameters"]
        assert "query" in params["properties"]
        assert "query" in params["required"]

    @pytest.mark.asyncio
    async def test_missing_query_parameter(self, web_search_tool):
        """Test missing query parameter fails."""
        result = await web_search_tool.execute(
            arguments={},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "No search query provided" in result.content
        assert result.metadata["error"] == "missing_query"

    @pytest.mark.asyncio
    async def test_web_search_unavailable(self, web_search_tool):
        """Test handling when web search is not available."""
        web_search_tool.web_search.is_available = MagicMock(return_value=False)

        result = await web_search_tool.execute(
            arguments={"query": "test query"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False

    @pytest.mark.asyncio
    @patch("app.services.tools.web_search_tool.ensure_mqtt_connected")
    async def test_successful_search(self, mock_mqtt, web_search_tool):
        """Test successful web search."""
        web_search_tool.web_search.is_available = MagicMock(return_value=True)
        web_search_tool.web_search.search = MagicMock(return_value=[
            {
                "title": "Test Result 1",
                "url": "https://example.com/1",
                "snippet": "First result snippet"
            },
            {
                "title": "Test Result 2",
                "url": "https://example.com/2",
                "snippet": "Second result snippet"
            }
        ])

        result = await web_search_tool.execute(
            arguments={"query": "test query"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert "Test Result 1" in result.content
        assert result.metadata["result_count"] == 2

    @pytest.mark.asyncio
    @patch("app.services.tools.web_search_tool.ensure_mqtt_connected")
    async def test_display_action_structure(self, mock_mqtt, web_search_tool):
        """Test display action is correctly formatted."""
        web_search_tool.web_search.is_available = MagicMock(return_value=True)
        web_search_tool.web_search.search = MagicMock(return_value=[
            {
                "title": "Test Result",
                "url": "https://example.com",
                "snippet": "Test snippet"
            }
        ])

        result = await web_search_tool.execute(
            arguments={"query": "test"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.display_action is not None
        assert result.display_action["type"] == "search_results"
        data = result.display_action["data"]
        assert data["query"] == "test"
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["title"] == "Test Result"

    @pytest.mark.asyncio
    async def test_no_results_found(self, web_search_tool):
        """Test handling when search returns no results."""
        web_search_tool.web_search.is_available = MagicMock(return_value=True)
        web_search_tool.web_search.search = MagicMock(return_value=[])

        result = await web_search_tool.execute(
            arguments={"query": "obscure query"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "no results" in result.content.lower() or "not found" in result.content.lower()

    @pytest.mark.asyncio
    async def test_result_limit(self, web_search_tool):
        """Test search results are limited to 5."""
        web_search_tool.web_search.is_available = MagicMock(return_value=True)
        # Return 10 results
        results = [
            {
                "title": f"Result {i}",
                "url": f"https://example.com/{i}",
                "snippet": f"Snippet {i}"
            }
            for i in range(10)
        ]
        web_search_tool.web_search.search = MagicMock(return_value=results)

        result = await web_search_tool.execute(
            arguments={"query": "test"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        # Should limit to 5 results
        assert len(result.display_action["data"]["results"]) == 5

    @pytest.mark.asyncio
    @patch("app.services.tools.web_search_tool.ensure_mqtt_connected")
    async def test_mqtt_publish_called(self, mock_mqtt, web_search_tool):
        """Test MQTT publish is called with search results."""
        web_search_tool.web_search.is_available = MagicMock(return_value=True)
        web_search_tool.web_search.search = MagicMock(return_value=[
            {"title": "Test", "url": "https://example.com", "snippet": "Snippet"}
        ])

        result = await web_search_tool.execute(
            arguments={"query": "test"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        web_search_tool.mqtt_client.publish_display_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_handling(self, web_search_tool):
        """Test exception during search is caught."""
        web_search_tool.web_search.is_available = MagicMock(return_value=True)
        web_search_tool.web_search.search = MagicMock(side_effect=Exception("API error"))

        result = await web_search_tool.execute(
            arguments={"query": "test"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "error" in result.content.lower() or "failed" in result.content.lower()
