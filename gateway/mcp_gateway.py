from typing import Any, Dict, List
from servers.filesystem_server import read_file
from servers.terminal_server import run_command

class MCPGateway:
    """
    Gateway to route tool calls to the correct MCP server.
    Phase 0: Directly invokes the local async tools.
    """
    def __init__(self):
        self.tool_map = {
            "read_file": read_file,
            "run_command": run_command,
        }
        
    def get_available_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "read_file",
                "description": "Read the contents of a file.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "run_command",
                "description": "Run a terminal command.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "cwd": {"type": "string", "default": "."}
                    },
                    "required": ["command"]
                }
            }
        ]

    async def execute_tool(self, tool_name: str, kwargs: Dict[str, Any]) -> str:
        if tool_name not in self.tool_map:
            return f"Error: Tool {tool_name} not found in gateway."
        
        func = self.tool_map[tool_name]
        try:
            result = await func(**kwargs)
            return str(result)
        except Exception as e:
            return f"Error executing {tool_name}: {e}"
