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
_NUCLEI_TEMPLATES: str = os.environ.get("NUCLEI_TEMPLATES", "/root/nuclei-templates")


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
    logger.info("Nuclei scan (REAL): target=%s severity=%s", target, severity)

    import asyncio
    import json
    import tempfile

    # We use a temporary file for the JSON output because reading a large JSON stream
    # from stdout directly can sometimes be tricky or exceed buffers if Nuclei outputs a lot.
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        out_file = tmp.name

    cmd = [
        _NUCLEI_BIN,
        "-target",
        target,
        "-severity",
        severity,
        "-json-export",
        out_file,
        "-silent",
    ]

    if templates:
        cmd.extend(["-t", templates])
    elif _NUCLEI_TEMPLATES and os.path.exists(_NUCLEI_TEMPLATES):
        cmd.extend(["-t", _NUCLEI_TEMPLATES])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        findings = []
        if os.path.exists(out_file) and os.path.getsize(out_file) > 0:
            with open(out_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                        # Keep only essential fields to save LLM context tokens
                        findings.append(
                            {
                                "template-id": raw.get("template-id", "unknown"),
                                "severity": raw.get("info", {}).get("severity", "unknown"),
                                "name": raw.get("info", {}).get("name", ""),
                                "host": raw.get("host", target),
                                "matched-at": raw.get("matched-at", ""),
                                "description": raw.get("info", {}).get("description", "")[
                                    :500
                                ],  # truncate long descriptions
                                "cvss-score": raw.get("info", {})
                                .get("classification", {})
                                .get("cvss-score", 0.0),
                            }
                        )
                    except json.JSONDecodeError:
                        continue

        if os.path.exists(out_file):
            os.remove(out_file)

        # Truncate findings if there are too many to save tokens (e.g., limit to top 50)
        max_findings = 50
        truncated = len(findings) > max_findings

        return {
            "findings": findings[:max_findings],
            "total": len(findings),
            "status": "ok",
            "target": target,
            "truncated": truncated,
        }

    except FileNotFoundError:
        logger.error("Nuclei binary not found at %s. Ensure it is installed.", _NUCLEI_BIN)
        if os.path.exists(out_file):
            os.remove(out_file)
        return {"findings": [], "total": 0, "status": "error: binary not found", "target": target}
    except Exception as e:
        logger.exception("Error executing Nuclei")
        if os.path.exists(out_file):
            os.remove(out_file)
        return {"findings": [], "total": 0, "status": f"error: {str(e)}", "target": target}
