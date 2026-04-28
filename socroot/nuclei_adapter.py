"""
Nuclei Adapter — mock skeleton.

Replace with real subprocess calls to the ``nuclei`` binary in production.
Nuclei docs: https://nuclei.projectdiscovery.io/
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_NUCLEI_BIN: str = os.environ.get("NUCLEI_BIN", "nuclei")
_NUCLEI_TEMPLATES: str = os.environ.get(
    "NUCLEI_TEMPLATES", "/root/nuclei-templates"
)


async def nuclei_scan(
    target: str,
    severity: str = "critical,high,medium",
    templates: str | None = None,
) -> dict[str, Any]:
    """
    Run a Nuclei vulnerability scan against *target*.

    Args:
        target: Domain or IP to scan.
        severity: Comma-separated severity levels.
        templates: Custom template path; defaults to NUCLEI_TEMPLATES env var.

    Returns:
        Dict with keys: findings (list), total (int), status (str).
    """
    logger.info("Nuclei scan (MOCK): target=%s severity=%s", target, severity)

    # TODO: Replace with real implementation:
    # import asyncio, json
    # cmd = [
    #     _NUCLEI_BIN, "-target", target,
    #     "-severity", severity,
    #     "-t", templates or _NUCLEI_TEMPLATES,
    #     "-json-output", "/tmp/nuclei-out.json",
    #     "-silent",
    # ]
    # proc = await asyncio.create_subprocess_exec(
    #     *cmd,
    #     stdout=asyncio.subprocess.PIPE,
    #     stderr=asyncio.subprocess.PIPE,
    # )
    # stdout, stderr = await proc.communicate()
    # findings = [json.loads(line) for line in stdout.decode().splitlines() if line.strip()]
    # return {"findings": findings, "total": len(findings), "status": "ok"}

    return {
        "findings": [
            {
                "template-id": "http-missing-security-headers",
                "severity": "medium",
                "host": target,
                "matched-at": f"https://{target}",
                "description": "Missing security headers",
            }
        ],
        "total": 1,
        "status": "mock",
        "target": target,
    }
