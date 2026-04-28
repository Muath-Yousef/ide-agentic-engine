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


async def get_wazuh_token() -> str:
    """Authenticate and return the Bearer token."""
    import httpx

    if not _WAZUH_PASS:
        logger.warning("WAZUH_API_PASSWORD is empty. Wazuh API calls may fail if auth is required.")

    async with httpx.AsyncClient(verify=False) as client:
        try:
            resp = await client.post(
                f"{_WAZUH_URL}/security/user/authenticate",
                auth=(_WAZUH_USER, _WAZUH_PASS),
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("token", "")
        except Exception as e:
            logger.error("Failed to authenticate with Wazuh API: %s", e)
            return ""


async def wazuh_query(query: str, limit: int = 100) -> dict[str, Any]:
    """
    Query Wazuh SIEM for alerts matching *query*.

    Args:
        query: Free-text or structured query string.
        limit: Maximum number of alerts to return.

    Returns:
        Dict with keys: alerts (list), total_count (int), status (str).
    """
    logger.info("Wazuh query (REAL): %s", query[:80])
    import httpx

    token = await get_wazuh_token()
    if not token:
        return {
            "alerts": [],
            "total_count": 0,
            "status": "error: authentication failed",
            "query": query,
        }

    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(verify=False) as client:
        try:
            resp = await client.get(
                f"{_WAZUH_URL}/alerts",
                headers=headers,
                params={"q": query, "limit": limit},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            alerts = data.get("affected_items", [])

            # Prune output to keep tokens minimal
            pruned_alerts = []
            for alert in alerts:
                pruned_alerts.append(
                    {
                        "id": alert.get("id"),
                        "rule": {
                            "level": alert.get("rule", {}).get("level"),
                            "description": alert.get("rule", {}).get("description"),
                        },
                        "agent": {
                            "name": alert.get("agent", {}).get("name"),
                            "ip": alert.get("agent", {}).get("ip"),
                        },
                        "timestamp": alert.get("timestamp"),
                    }
                )

            return {
                "alerts": pruned_alerts,
                "total_count": data.get("total_affected_items", len(alerts)),
                "status": "ok",
                "query": query,
            }
        except httpx.HTTPError as e:
            logger.error("Wazuh API request failed: %s", e)
            return {
                "alerts": [],
                "total_count": 0,
                "status": f"error: {str(e)}",
                "query": query,
            }


async def get_agent_inventory(agent_id: str) -> dict[str, Any]:
    """Return hardware/software inventory for a Wazuh agent."""
    logger.info("Wazuh agent inventory (REAL): %s", agent_id)
    import httpx

    token = await get_wazuh_token()
    if not token:
        return {"agent_id": agent_id, "status": "error: auth failed"}

    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(verify=False) as client:
        try:
            # Get agent OS details
            resp_agent = await client.get(
                f"{_WAZUH_URL}/agents",
                headers=headers,
                params={"agents_list": agent_id},
                timeout=15.0,
            )
            resp_agent.raise_for_status()
            agent_data = resp_agent.json().get("data", {}).get("affected_items", [{}])[0]
            os_name = agent_data.get("os", {}).get("name", "Unknown OS")
            os_version = agent_data.get("os", {}).get("version", "")

            # Get agent packages
            resp_pkgs = await client.get(
                f"{_WAZUH_URL}/syscollector/agents/{agent_id}/packages",
                headers=headers,
                params={"limit": 50},  # limit to save context
                timeout=15.0,
            )
            resp_pkgs.raise_for_status()
            pkgs_data = resp_pkgs.json().get("data", {}).get("affected_items", [])

            package_list = [f"{p.get('name')}/{p.get('version')}" for p in pkgs_data]

            return {
                "agent_id": agent_id,
                "os": f"{os_name} {os_version}".strip(),
                "packages": package_list,
                "status": "ok",
            }

        except httpx.HTTPError as e:
            logger.error("Wazuh API inventory request failed: %s", e)
            return {
                "agent_id": agent_id,
                "status": f"error: {str(e)}",
            }
