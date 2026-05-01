"""
n8n Adapter — mock skeleton.

Replace with real n8n REST API calls in production.
n8n docs: https://docs.n8n.io/api/
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_N8N_URL: str = os.environ.get("N8N_URL", "http://localhost:5678")
_N8N_API_KEY: str = os.environ.get("N8N_API_KEY", "")


async def trigger_workflow(
    workflow_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Trigger an n8n workflow by ID with optional payload. (MOCK)

    Args:
        workflow_id: n8n workflow UUID or name.
        payload: Data to pass to the workflow trigger.

    Returns:
        Dict with execution_id and status.
    """
    logger.info("n8n trigger (MOCK): workflow=%s", workflow_id)

    # TODO: Replace with real implementation:
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     resp = await client.post(
    #         f"{_N8N_URL}/api/v1/workflows/{workflow_id}/execute",
    #         headers={"X-N8N-API-KEY": _N8N_API_KEY},
    #         json=payload or {},
    #     )
    #     return resp.json()

    return {
        "execution_id": "mock-exec-001",
        "workflow_id": workflow_id,
        "status": "mock_triggered",
        "payload": payload or {},
    }


async def get_execution_status(execution_id: str) -> dict[str, Any]:
    """Poll execution status by ID. (MOCK)"""
    logger.info("n8n status (MOCK): execution=%s", execution_id)
    return {
        "execution_id": execution_id,
        "status": "success",
        "finished": True,
    }
