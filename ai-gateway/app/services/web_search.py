"""
Web Search Service using Brave Search API
Provides real-time web search capabilities for the AI Gateway
"""

import logging
import os
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class WebSearchClient:
    """Client for Brave Search API"""

    def __init__(self):
        self.api_key = os.getenv("BRAVE_API_KEY", "")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.results_limit = int(os.getenv("SEARCH_RESULTS_LIMIT", "5"))

        if not self.api_key:
            logger.warning("BRAVE_API_KEY not set - web search disabled")
        else:
            logger.info(f"WebSearchClient initialized (limit: {self.results_limit} results)")

    def is_available(self) -> bool:
        """Check if web search is configured"""
        return bool(self.api_key)

    async def search(self, query: str, count: Optional[int] = None) -> dict:
        """
        Perform web search using Brave Search API

        Args:
            query: Search query string
            count: Number of results to return (default: SEARCH_RESULTS_LIMIT)

        Returns:
            Dictionary with search results and metadata
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Web search not configured (missing BRAVE_API_KEY)",
                "results": []
            }

        if not query or not query.strip():
            return {
                "success": False,
                "error": "Empty search query",
                "results": []
            }

        results_count = count or self.results_limit

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.base_url,
                    params={
                        "q": query,
                        "count": results_count,
                        "safesearch": "moderate"
                    },
                    headers={
                        "X-Subscription-Token": self.api_key,
                        "Accept": "application/json"
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Brave Search API error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Search API error: {response.status_code}",
                        "results": []
                    }

                data = response.json()
                results = self._parse_results(data)

                logger.info(f"Web search completed: '{query}' -> {len(results)} results")

                return {
                    "success": True,
                    "query": query,
                    "results": results,
                    "total_results": len(results)
                }

        except httpx.TimeoutException:
            logger.error(f"Web search timeout for query: {query}")
            return {
                "success": False,
                "error": "Search request timed out",
                "results": []
            }
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    def _parse_results(self, data: dict) -> list:
        """Parse Brave Search API response into simplified format"""
        results = []

        web_results = data.get("web", {}).get("results", [])

        for item in web_results:
            result = {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
                "age": item.get("age", "")  # e.g., "2 days ago"
            }
            results.append(result)

        return results

    def format_for_llm(self, search_result: dict) -> str:
        """
        Format search results as context for LLM

        Args:
            search_result: Result from search() method

        Returns:
            Formatted string for LLM context
        """
        if not search_result.get("success"):
            return f"Search failed: {search_result.get('error', 'Unknown error')}"

        results = search_result.get("results", [])
        if not results:
            return f"No results found for: {search_result.get('query', '')}"

        formatted = f"Web search results for '{search_result.get('query', '')}':\n\n"

        for i, result in enumerate(results, 1):
            formatted += f"{i}. {result['title']}\n"
            formatted += f"   {result['description']}\n"
            if result.get('age'):
                formatted += f"   ({result['age']})\n"
            formatted += f"   URL: {result['url']}\n\n"

        return formatted

    def format_for_display(self, search_result: dict) -> str:
        """
        Format search results for display on Nest Hub

        Args:
            search_result: Result from search() method

        Returns:
            HTML-formatted string for display
        """
        if not search_result.get("success"):
            return f"Search failed: {search_result.get('error', 'Unknown error')}"

        results = search_result.get("results", [])
        if not results:
            return f"No results for: {search_result.get('query', '')}"

        # Simple text format for Nest Hub
        formatted = f"Search: {search_result.get('query', '')}\n\n"

        for i, result in enumerate(results[:3], 1):  # Show top 3 on display
            formatted += f"{i}. {result['title']}\n"
            formatted += f"   {result['description'][:100]}...\n\n"

        return formatted


# Singleton instance
_web_search_client: Optional[WebSearchClient] = None


def get_web_search_client() -> WebSearchClient:
    """Get or create WebSearchClient singleton"""
    global _web_search_client
    if _web_search_client is None:
        _web_search_client = WebSearchClient()
    return _web_search_client
