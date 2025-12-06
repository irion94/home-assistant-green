"""Tests for ResearchTool."""

import pytest
from unittest.mock import MagicMock, patch
from app.services.tools.research_tool import ResearchTool


@pytest.fixture
def research_tool():
    """Fixture providing ResearchTool instance."""
    with patch("app.services.tools.research_tool.get_web_search_client"), \
         patch("app.services.tools.research_tool.get_mqtt_client"):
        return ResearchTool()


class TestResearchTool:
    """Test suite for ResearchTool."""

    def test_tool_name(self, research_tool):
        """Test tool name is correct."""
        assert research_tool.name == "research_local"

    def test_schema_structure(self, research_tool):
        """Test schema has required OpenAI structure."""
        schema = research_tool.schema
        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "research_local"
        assert "parameters" in schema["function"]

    def test_schema_required_params(self, research_tool):
        """Test schema requires 'query' parameter."""
        schema = research_tool.schema
        params = schema["function"]["parameters"]
        assert "query" in params["properties"]
        assert "query" in params["required"]
        assert "location" in params["properties"]
        assert "location" not in params["required"]  # Optional

    @pytest.mark.asyncio
    async def test_missing_query_parameter(self, research_tool):
        """Test missing query parameter fails."""
        result = await research_tool.execute(
            arguments={},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "No search query provided" in result.content

    @pytest.mark.asyncio
    async def test_web_search_unavailable(self, research_tool):
        """Test handling when web search is not available."""
        research_tool.web_search.is_available = MagicMock(return_value=False)

        result = await research_tool.execute(
            arguments={"query": "bars"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False

    @pytest.mark.asyncio
    @patch("app.services.tools.research_tool.ensure_mqtt_connected")
    async def test_successful_local_search(self, mock_mqtt, research_tool):
        """Test successful local search."""
        research_tool.web_search.is_available = MagicMock(return_value=True)
        research_tool.web_search.search = MagicMock(return_value=[
            {
                "title": "Bar Name",
                "url": "https://maps.google.com/?q=bar",
                "snippet": "Popular bar in the area"
            }
        ])

        result = await research_tool.execute(
            arguments={"query": "bars"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert "Bar Name" in result.content
        assert result.metadata["result_count"] == 1

    @pytest.mark.asyncio
    @patch("app.services.tools.research_tool.ensure_mqtt_connected")
    async def test_search_with_location(self, mock_mqtt, research_tool):
        """Test local search with specific location."""
        research_tool.web_search.is_available = MagicMock(return_value=True)
        research_tool.web_search.search = MagicMock(return_value=[
            {"title": "Restaurant", "url": "https://example.com", "snippet": "Good food"}
        ])

        result = await research_tool.execute(
            arguments={"query": "restaurants", "location": "Warsaw"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        # Should include location in search query
        research_tool.web_search.search.assert_called_once()
        search_query = research_tool.web_search.search.call_args[0][0]
        assert "Warsaw" in search_query or "restaurants" in search_query

    @pytest.mark.asyncio
    @patch("app.services.tools.research_tool.ensure_mqtt_connected")
    async def test_display_action_structure(self, mock_mqtt, research_tool):
        """Test display action is correctly formatted."""
        research_tool.web_search.is_available = MagicMock(return_value=True)
        research_tool.web_search.search = MagicMock(return_value=[
            {
                "title": "Local Bar",
                "url": "https://example.com",
                "snippet": "Great atmosphere"
            }
        ])

        result = await research_tool.execute(
            arguments={"query": "bars"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.display_action is not None
        assert result.display_action["type"] == "research_results"
        data = result.display_action["data"]
        assert data["query"] == "bars"
        assert "results" in data
        assert "map_link" in data
        assert "google.com/maps" in data["map_link"]

    @pytest.mark.asyncio
    @patch("app.services.tools.research_tool.ensure_mqtt_connected")
    async def test_google_maps_link_generated(self, mock_mqtt, research_tool):
        """Test Google Maps link is generated with query."""
        research_tool.web_search.is_available = MagicMock(return_value=True)
        research_tool.web_search.search = MagicMock(return_value=[
            {"title": "Cafe", "url": "https://example.com", "snippet": "Coffee shop"}
        ])

        result = await research_tool.execute(
            arguments={"query": "coffee shops", "location": "Krakow"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        map_link = result.display_action["data"]["map_link"]
        assert "https://www.google.com/maps/search/" in map_link
        # Should encode query
        assert "coffee" in map_link.lower() or "%20" in map_link

    @pytest.mark.asyncio
    async def test_no_results_found(self, research_tool):
        """Test handling when search returns no results."""
        research_tool.web_search.is_available = MagicMock(return_value=True)
        research_tool.web_search.search = MagicMock(return_value=[])

        result = await research_tool.execute(
            arguments={"query": "obscure place"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "no results" in result.content.lower() or "not found" in result.content.lower()

    @pytest.mark.asyncio
    async def test_search_query_formatting(self, research_tool):
        """Test search query includes 'nearby' when no location specified."""
        research_tool.web_search.is_available = MagicMock(return_value=True)
        research_tool.web_search.search = MagicMock(return_value=[
            {"title": "Place", "url": "https://example.com", "snippet": "Description"}
        ])

        await research_tool.execute(
            arguments={"query": "pizza"},
            room_id="test_room",
            session_id="test_session"
        )

        # Should add "nearby" to query when no location provided
        search_query = research_tool.web_search.search.call_args[0][0]
        assert "nearby" in search_query.lower() or "pizza" in search_query.lower()

    @pytest.mark.asyncio
    @patch("app.services.tools.research_tool.ensure_mqtt_connected")
    async def test_mqtt_publish_called(self, mock_mqtt, research_tool):
        """Test MQTT publish is called with research results."""
        research_tool.web_search.is_available = MagicMock(return_value=True)
        research_tool.web_search.search = MagicMock(return_value=[
            {"title": "Bar", "url": "https://example.com", "snippet": "Nice bar"}
        ])

        result = await research_tool.execute(
            arguments={"query": "bars"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        research_tool.mqtt_client.publish_display_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_handling(self, research_tool):
        """Test exception during search is caught."""
        research_tool.web_search.is_available = MagicMock(return_value=True)
        research_tool.web_search.search = MagicMock(side_effect=Exception("API error"))

        result = await research_tool.execute(
            arguments={"query": "test"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "error" in result.content.lower() or "failed" in result.content.lower()
