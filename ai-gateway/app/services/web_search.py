"""
Web Search Service using Brave Search API
Provides real-time web search capabilities for the AI Gateway

Phase 7: Added circuit breaker pattern to prevent cascading failures.
"""

from __future__ import annotations

import logging
import os

import httpx

from app.services.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class WebSearchClient:
    """Client for Brave Search API.

    Phase 7: Includes circuit breaker (5 failures -> 60s timeout).
    """

    def __init__(self):
        self.api_key = os.getenv("BRAVE_API_KEY", "")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.results_limit = int(os.getenv("SEARCH_RESULTS_LIMIT", "5"))

        # Phase 7: Circuit breaker for Brave Search API
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            name="brave_search"
        )

        if not self.api_key:
            logger.warning("BRAVE_API_KEY not set - web search disabled")
        else:
            logger.info(f"WebSearchClient initialized (limit: {self.results_limit} results, circuit breaker enabled)")

    def is_available(self) -> bool:
        """Check if web search is configured"""
        return bool(self.api_key)

    async def search(self, query: str, count: int | None = None) -> dict:
        """
        Perform web search using Brave Search API.

        Phase 7: Protected by circuit breaker to prevent API overload.

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

        # Phase 7: Use circuit breaker for API call
        try:
            return await self.circuit_breaker.call(
                self._do_search,
                query,
                results_count
            )
        except Exception as e:
            # Circuit breaker or search failure
            logger.error(f"Web search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    async def _do_search(self, query: str, results_count: int) -> dict:
        """
        Internal search method wrapped by circuit breaker.

        Args:
            query: Search query string
            results_count: Number of results to return

        Returns:
            Dictionary with search results and metadata

        Raises:
            Exception: On search failure (triggers circuit breaker)
        """
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

                response.raise_for_status()  # Phase 7: Raise on error (triggers circuit breaker)

                data = response.json()
                results = self._parse_results(data)

                logger.info(f"Web search completed: '{query}' -> {len(results)} results")

                return {
                    "success": True,
                    "query": query,
                    "results": results,
                    "total_results": len(results)
                }

        except httpx.TimeoutException as e:
            logger.error(f"Web search timeout for query: {query}")
            raise  # Phase 7: Let circuit breaker handle timeout
        except httpx.HTTPStatusError as e:
            logger.error(f"Brave Search API error: {e.response.status_code} - {e.response.text}")
            raise  # Phase 7: Let circuit breaker handle HTTP errors
        except Exception as e:
            logger.error(f"Web search error: {e}")
            raise  # Phase 7: Let circuit breaker handle all errors

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
_web_search_client: WebSearchClient | None = None


def get_web_search_client() -> WebSearchClient:
    """Get or create WebSearchClient singleton"""
    global _web_search_client
    if _web_search_client is None:
        _web_search_client = WebSearchClient()
    return _web_search_client
