import asyncio
import subprocess

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("terminal_server")


@mcp.tool()
async def run_command(command: str, cwd: str = ".", prune_lines: int = 100) -> str:
    """
    Run a terminal command.
    If output is too long, it prunes the middle to save tokens.
    """
    try:
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd
        )
        stdout, stderr = await process.communicate()

        output = stdout.decode()
        error = stderr.decode()

        full_output = ""
        if output:
            full_output += f"STDOUT:\n{output}\n"
        if error:
            full_output += f"STDERR:\n{error}\n"

        # Pruning logic for Phase 0 (Token Optimizer preview)
        lines = full_output.splitlines()
        if len(lines) > prune_lines:
            half = prune_lines // 2
            pruned_output = "\n".join(lines[:half])
            pruned_output += f"\n... [{len(lines) - prune_lines} lines omitted] ...\n"
            pruned_output += "\n".join(lines[-half:])
            return pruned_output

        return full_output
    except Exception as e:
        return f"Failed to execute command: {e}"


if __name__ == "__main__":
    mcp.run()
