"""
Terminal Tool Server — subprocess execution with output pruning.

Commands run in the workspace root with a configurable timeout.
Output is automatically pruned by the MCPGateway to save context tokens.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
from typing import Any

logger = logging.getLogger(__name__)

_WORKSPACE = os.environ.get("WORKSPACE_ROOT", ".")
_DEFAULT_TIMEOUT: int = int(os.environ.get("CMD_TIMEOUT_SECS", "60"))

# Blocked commands — safety guardrail
_BLOCKED_PREFIXES: tuple[str, ...] = (
    "rm -rf /",
    "dd if=",
    "mkfs",
    ":(){:|:&};:",  # fork bomb
)


async def run_command(
    cmd: str,
    cwd: str | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
    env_override: dict[str, str] | None = None,
) -> str:
    """
    Execute *cmd* in a subprocess and return combined stdout+stderr.

    Output is NOT pruned here — the MCPGateway handles pruning automatically
    for terminal tools.

    Args:
        cmd: Shell command string.
        cwd: Working directory (relative to workspace root).
        timeout: Seconds before the process is killed.
        env_override: Additional environment variables.

    Returns:
        Combined stdout + stderr as a single string.

    Raises:
        PermissionError: If cmd matches a blocked prefix.
        asyncio.TimeoutError: If cmd exceeds *timeout* seconds.
    """
    _check_blocked(cmd)

    work_dir = os.path.join(_WORKSPACE, cwd) if cwd else _WORKSPACE
    env = {**os.environ, **(env_override or {})}

    logger.info("run_command: %s (cwd=%s timeout=%ds)", cmd[:80], work_dir, timeout)

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=work_dir,
            env=env,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            raise asyncio.TimeoutError(
                f"Command timed out after {timeout}s: {cmd[:60]}"
            )

        output = stdout.decode("utf-8", errors="replace")
        exit_code = proc.returncode or 0
        header = f"[exit_code={exit_code}]\n"
        logger.debug("run_command: exit=%d output=%d chars", exit_code, len(output))
        return header + output

    except asyncio.TimeoutError:
        raise
    except Exception as exc:
        logger.error("run_command failed: %s", exc)
        return f"[ERROR] {type(exc).__name__}: {exc}"


def _check_blocked(cmd: str) -> None:
    """Raise PermissionError if *cmd* starts with a blocked prefix."""
    stripped = cmd.strip()
    for blocked in _BLOCKED_PREFIXES:
        if stripped.startswith(blocked):
            raise PermissionError(
                f"Blocked command prefix: '{blocked}'. "
                "This command is disallowed by engine safety policy."
            )


async def run_batch_commands(cmds: list[str], cwd: str | None = None) -> list[str]:
    """
    Run multiple commands in parallel (within one batch).

    Useful when the LLM needs results from several independent commands.
    """
    tasks = [run_command(cmd, cwd=cwd) for cmd in cmds]
    results: list[Any] = await asyncio.gather(*tasks, return_exceptions=True)
    return [
        str(r) if not isinstance(r, Exception) else f"[ERROR] {r}"
        for r in results
    ]
