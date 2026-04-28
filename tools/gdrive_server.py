"""
Google Drive Tool Server — delegates to the connected Google Drive MCP.

In claude.ai the Google Drive MCP is available at:
https://drivemcp.googleapis.com/mcp/v1

For the standalone engine, this mock reads the MCP_SERVERS env var
to locate the Drive MCP and proxies calls through httpx.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_GDRIVE_MCP_URL: str = os.environ.get(
    "GDRIVE_MCP_URL", "https://drivemcp.googleapis.com/mcp/v1"
)
_GDRIVE_TOKEN: str = os.environ.get("GDRIVE_MCP_TOKEN", "")


async def gdrive_read(
    file_id: str | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    """
    Read a file from Google Drive by ID, or search by query. (MOCK)

    Args:
        file_id: Specific Drive file ID.
        query: Full-text search query for Drive files.

    Returns:
        Dict with content (str), name (str), mime_type (str).
    """
    logger.info("gdrive_read (MOCK): file_id=%s query=%s", file_id, query)

    # TODO: Replace with real MCP proxy call:
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     payload = {"file_id": file_id} if file_id else {"query": query}
    #     resp = await client.post(
    #         f"{_GDRIVE_MCP_URL}/read",
    #         headers={"Authorization": f"Bearer {_GDRIVE_TOKEN}"},
    #         json=payload,
    #     )
    #     return resp.json()

    return {
        "content": f"Mock Google Drive content for file_id={file_id} query={query}",
        "name": "mock_document.docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "status": "mock",
    }
