from typing import Any, Dict, List, Optional
from servers.filesystem_server import read_file
from servers.terminal_server import run_command
from gateway.key_pool import APIKeyPool

class MCPGateway:
    """
    Gateway to route tool calls to the correct MCP server.
    """
    def __init__(self, key_pool: Optional[APIKeyPool] = None):
        self.key_pool = key_pool
        self.tool_map = {
            "read_file": read_file,
            "run_command": run_command,
            "virus_total_scan": self.virus_total_scan,
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
            },
            {
                "name": "virus_total_scan",
                "description": "Simulate a VirusTotal scan to test key rotation.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "resource": {"type": "string"}
                    },
                    "required": ["resource"]
                }
            }
        ]

    async def virus_total_scan(self, resource: str) -> str:
        """Mock tool that demonstrates key rotation logic."""
        if not self.key_pool:
            return "Error: No Key Pool configured."
            
        current_key = self.key_pool.get_key("virustotal")
        if not current_key:
            return "Error: No VirusTotal keys available in pool."
            
        # Simulate a 429 Rate Limit for 'key_1' to trigger rotation
        if "key_1" in current_key:
            print(f"Mocking 429 Rate Limit for VirusTotal key: {current_key}")
            self.key_pool.mark_exhausted("virustotal", current_key, is_rate_limit=True)
            # Recursively retry after rotation
            return await self.virus_total_scan(resource)
            
        return f"VirusTotal Scan Success for {resource} using key: {current_key}"

    async def execute_tool(self, tool_name: str, kwargs: Dict[str, Any]) -> str:
        if tool_name not in self.tool_map:
            return f"Error: Tool {tool_name} not found in gateway."
        
        func = self.tool_map[tool_name]
        try:
            result = await func(**kwargs)
            return str(result)
        except Exception as e:
            return f"Error executing {tool_name}: {e}"
