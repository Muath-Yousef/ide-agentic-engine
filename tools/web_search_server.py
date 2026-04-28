"""
Web Search Tool Server — mock skeleton.

Replace with a real search provider (Serper, Brave, Tavily) in production.
Results are cached in Redis by the LLMManager to avoid duplicate API calls.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_SEARCH_API_KEY: str = os.environ.get("SEARCH_API_KEY", "")
_SEARCH_PROVIDER: str = os.environ.get("SEARCH_PROVIDER", "serper")


async def search_web(
    query: str,
    num_results: int = 5,
    site_filter: str | None = None,
) -> dict[str, Any]:
    """
    Search the web for *query* and return structured results. (MOCK)

    Args:
        query: Search query string.
        num_results: Maximum results to return.
        site_filter: Restrict results to a specific domain.

    Returns:
        Dict with results (list of {title, url, snippet}), query, total.
    """
    logger.info("web_search (MOCK): query=%s", query[:80])

    # TODO: Replace with real implementation, e.g. Serper:
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     resp = await client.post(
    #         "https://google.serper.dev/search",
    #         headers={"X-API-KEY": _SEARCH_API_KEY},
    #         json={"q": query, "num": num_results},
    #     )
    #     data = resp.json()
    #     return {
    #         "results": [
    #             {"title": r["title"], "url": r["link"], "snippet": r["snippet"]}
    #             for r in data.get("organic", [])
    #         ],
    #         "query": query,
    #         "total": len(data.get("organic", [])),
    #     }

    return {
        "results": [
            {
                "title": f"Mock result for: {query}",
                "url": "https://example.com/mock",
                "snippet": "This is a mock search result. Configure SEARCH_API_KEY to enable real search.",
            }
        ],
        "query": query,
        "total": 1,
        "status": "mock",
    }
