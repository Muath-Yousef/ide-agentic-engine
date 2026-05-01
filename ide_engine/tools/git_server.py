import asyncio
import os
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("git_server")


async def _run_git(command: str, cwd: str) -> str:
    """Helper to run git commands."""
    try:
        process = await asyncio.create_subprocess_shell(
            f"git {command}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            return f"Git Error: {stderr.decode()}"
        return stdout.decode() or "Success"
    except Exception as e:
        return f"Execution Error: {e}"


@mcp.tool()
async def git_status(cwd: str = ".") -> str:
    """Get the current git status."""
    return await _run_git("status -s", cwd)


@mcp.tool()
async def git_create_branch(branch_name: str, cwd: str = ".") -> str:
    """Create and checkout a new git branch."""
    return await _run_git(f"checkout -b {branch_name}", cwd)


@mcp.tool()
async def git_commit(message: str, files: Optional[List[str]] = None, cwd: str = ".") -> str:
    """Commit changes to the repository. If files is empty, commits all tracked changes."""
    if not files:
        # Add all and commit
        add_result = await _run_git("add .", cwd)
        if "Error" in add_result:
            return add_result
    else:
        for f in files:
            add_result = await _run_git(f"add {f}", cwd)
            if "Error" in add_result:
                return add_result

    # Escape message quotes
    escaped_msg = message.replace('"', '\\"')
    return await _run_git(f'commit -m "{escaped_msg}"', cwd)


@mcp.tool()
async def git_push(branch_name: str, cwd: str = ".") -> str:
    """Push the current branch to origin."""
    return await _run_git(f"push -u origin {branch_name}", cwd)


@mcp.tool()
async def git_diff(cwd: str = ".") -> str:
    """Get the current working directory diff."""
    return await _run_git("diff", cwd)


if __name__ == "__main__":
    mcp.run()
