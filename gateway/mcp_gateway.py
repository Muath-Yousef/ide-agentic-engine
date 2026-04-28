from typing import Any, Dict, List, Optional
from servers.filesystem_server import read_file
from servers.terminal_server import run_command
from servers.cyber_tools_server import virustotal_scan
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
            "virus_total_scan": self.virus_total_scan_tool,
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
                "description": "Perform a VirusTotal reputation check for an IP, domain, or file hash.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "resource": {"type": "string"}
                    },
                    "required": ["resource"]
                }
            }
        ]

    async def virus_total_scan_tool(self, resource: str) -> str:
        """Wrapper for virustotal_scan that handles key rotation."""
        if not self.key_pool:
            return "Error: No Key Pool configured."
            
        max_retries = 3
        for attempt in range(max_retries):
            current_key = self.key_pool.get_key("virustotal")
            if not current_key:
                return "Error: No VirusTotal keys available in pool."
            
            try:
                return await virustotal_scan(resource, current_key)
            except Exception as e:
                error_str = str(e)
                if ("429" in error_str or "403" in error_str):
                    is_rate_limit = "429" in error_str
                    self.key_pool.mark_exhausted("virustotal", current_key, is_rate_limit=is_rate_limit)
                    print(f"Key Rotation: VirusTotal key failed ({error_str}). Rotating...")
                    continue
                else:
                    return f"VirusTotal Error: {e}"
        
        return "Error: All VirusTotal keys exhausted."

    async def execute_tool(self, tool_name: str, kwargs: Dict[str, Any]) -> str:
        if tool_name not in self.tool_map:
            return f"Error: Tool {tool_name} not found in gateway."
        
        func = self.tool_map[tool_name]
        try:
            result = await func(**kwargs)
            return str(result)
        except Exception as e:
            return f"Error executing {tool_name}: {e}"
