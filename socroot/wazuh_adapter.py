"""
Wazuh Adapter — mock skeleton.

Replace with real Wazuh REST API calls using httpx in production.
API docs: https://documentation.wazuh.com/current/user-manual/api/
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_WAZUH_URL: str = os.environ.get("WAZUH_API_URL", "https://wazuh.local:55000")
_WAZUH_USER: str = os.environ.get("WAZUH_API_USER", "wazuh-api")
_WAZUH_PASS: str = os.environ.get("WAZUH_API_PASSWORD", "")


async def wazuh_query(query: str, limit: int = 100) -> dict[str, Any]:
    """
    Query Wazuh SIEM for alerts matching *query*.

    Args:
        query: Free-text or structured query string.
        limit: Maximum number of alerts to return.

    Returns:
        Dict with keys: alerts (list), total_count (int), status (str).
    """
    logger.info("Wazuh query (MOCK): %s", query[:80])

    # TODO: Replace with real implementation:
    # async with httpx.AsyncClient(verify=False) as client:
    #     token_resp = await client.post(
    #         f"{_WAZUH_URL}/security/user/authenticate",
    #         auth=(_WAZUH_USER, _WAZUH_PASS),
    #     )
    #     token = token_resp.json()["data"]["token"]
    #     headers = {"Authorization": f"Bearer {token}"}
    #     resp = await client.get(
    #         f"{_WAZUH_URL}/alerts",
    #         headers=headers,
    #         params={"q": query, "limit": limit},
    #     )
    #     return resp.json()

    return {
        "alerts": [
            {
                "id": "mock-001",
                "rule": {"level": 12, "description": "Mock high-severity alert"},
                "agent": {"name": "target-host", "ip": "192.168.1.10"},
                "timestamp": "2025-04-28T10:00:00Z",
            }
        ],
        "total_count": 1,
        "status": "mock",
        "query": query,
    }


async def get_agent_inventory(agent_id: str) -> dict[str, Any]:
    """Return hardware/software inventory for a Wazuh agent. (MOCK)"""
    logger.info("Wazuh agent inventory (MOCK): %s", agent_id)
    return {
        "agent_id": agent_id,
        "os": "Ubuntu 22.04",
        "packages": ["nginx/1.24", "openssl/3.0.2"],
        "status": "mock",
    }
