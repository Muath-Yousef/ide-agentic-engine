import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("filesystem_server")


@mcp.tool()
async def read_file(path: str) -> str:
    """Read the contents of a file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


@mcp.tool()
async def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        # Create directories if they don't exist
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


@mcp.tool()
async def list_dir(path: str) -> str:
    """List contents of a directory."""
    try:
        items = os.listdir(path)
        return "\n".join(items)
    except Exception as e:
        return f"Error listing directory: {e}"


if __name__ == "__main__":
    mcp.run()
