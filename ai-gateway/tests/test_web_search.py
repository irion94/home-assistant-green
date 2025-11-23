"""Tests for WebSearchClient."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.web_search import WebSearchClient, get_web_search_client


class TestWebSearchClient:
    """Tests for WebSearchClient."""

    def test_init_without_api_key(self) -> None:
        """Test initialization without API key disables search."""
        with patch.dict("os.environ", {}, clear=True):
            client = WebSearchClient()
            assert not client.is_available()

    def test_init_with_api_key(self) -> None:
        """Test initialization with API key enables search."""
        with patch.dict("os.environ", {"BRAVE_API_KEY": "test-key"}):
            client = WebSearchClient()
            assert client.is_available()
            assert client.api_key == "test-key"

    def test_default_results_limit(self) -> None:
        """Test default results limit is 5."""
        with patch.dict("os.environ", {"BRAVE_API_KEY": "test-key"}, clear=True):
            client = WebSearchClient()
            assert client.results_limit == 5

    def test_custom_results_limit(self) -> None:
        """Test custom results limit from environment."""
        with patch.dict("os.environ", {"BRAVE_API_KEY": "test-key", "SEARCH_RESULTS_LIMIT": "10"}):
            client = WebSearchClient()
            assert client.results_limit == 10

    @pytest.mark.asyncio
    async def test_search_without_api_key(self) -> None:
        """Test search fails gracefully without API key."""
        with patch.dict("os.environ", {}, clear=True):
            client = WebSearchClient()
            result = await client.search("test query")

            assert result["success"] is False
            assert "not configured" in result["error"]
            assert result["results"] == []

    @pytest.mark.asyncio
    async def test_search_empty_query(self) -> None:
        """Test search fails with empty query."""
        with patch.dict("os.environ", {"BRAVE_API_KEY": "test-key"}):
            client = WebSearchClient()
            result = await client.search("")

            assert result["success"] is False
            assert "Empty" in result["error"]

    @pytest.mark.asyncio
    async def test_search_success(self) -> None:
        """Test successful search response parsing."""
        with patch.dict("os.environ", {"BRAVE_API_KEY": "test-key"}):
            client = WebSearchClient()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "web": {
                    "results": [
                        {
                            "title": "Test Result",
                            "url": "https://example.com",
                            "description": "Test description",
                            "age": "1 day ago"
                        }
                    ]
                }
            }

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                result = await client.search("test query")

                assert result["success"] is True
                assert result["query"] == "test query"
                assert len(result["results"]) == 1
                assert result["results"][0]["title"] == "Test Result"

    def test_parse_results(self) -> None:
        """Test result parsing from Brave API response."""
        with patch.dict("os.environ", {"BRAVE_API_KEY": "test-key"}):
            client = WebSearchClient()

            data = {
                "web": {
                    "results": [
                        {
                            "title": "Result 1",
                            "url": "https://example1.com",
                            "description": "Description 1",
                            "age": "2 hours ago"
                        },
                        {
                            "title": "Result 2",
                            "url": "https://example2.com",
                            "description": "Description 2"
                        }
                    ]
                }
            }

            results = client._parse_results(data)

            assert len(results) == 2
            assert results[0]["title"] == "Result 1"
            assert results[0]["age"] == "2 hours ago"
            assert results[1]["age"] == ""  # Missing age

    def test_format_for_llm(self) -> None:
        """Test formatting search results for LLM context."""
        with patch.dict("os.environ", {"BRAVE_API_KEY": "test-key"}):
            client = WebSearchClient()

            search_result = {
                "success": True,
                "query": "test",
                "results": [
                    {
                        "title": "Test Title",
                        "url": "https://example.com",
                        "description": "Test description",
                        "age": "1 day ago"
                    }
                ]
            }

            formatted = client.format_for_llm(search_result)

            assert "test" in formatted
            assert "Test Title" in formatted
            assert "https://example.com" in formatted

    def test_format_for_llm_failure(self) -> None:
        """Test formatting failed search results."""
        with patch.dict("os.environ", {"BRAVE_API_KEY": "test-key"}):
            client = WebSearchClient()

            search_result = {
                "success": False,
                "error": "API error"
            }

            formatted = client.format_for_llm(search_result)
            assert "API error" in formatted

    def test_format_for_display(self) -> None:
        """Test formatting for Nest Hub display."""
        with patch.dict("os.environ", {"BRAVE_API_KEY": "test-key"}):
            client = WebSearchClient()

            search_result = {
                "success": True,
                "query": "weather",
                "results": [
                    {
                        "title": "Weather Report",
                        "url": "https://weather.com",
                        "description": "Current weather conditions for your location today and tomorrow",
                        "age": ""
                    }
                ]
            }

            formatted = client.format_for_display(search_result)

            assert "weather" in formatted
            assert "Weather Report" in formatted
            # Description should be truncated
            assert "..." in formatted or len(formatted) < 200

    def test_get_web_search_client_singleton(self) -> None:
        """Test that get_web_search_client returns singleton."""
        client1 = get_web_search_client()
        client2 = get_web_search_client()
        assert client1 is client2
