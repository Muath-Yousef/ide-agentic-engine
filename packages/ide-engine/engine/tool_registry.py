from typing import Any, Dict, List, Optional


class ToolRegistry:
    """
    Maintains a catalog of all available tools across all MCP servers.
    Provides routing information for the BatchExecutor.
    """

    def __init__(self):
        # tool_name -> server_name
        self._tool_to_server: Dict[str, str] = {}
        # tool_name -> JSON Schema
        self._tool_schemas: Dict[str, Dict[str, Any]] = {}

    def register_tool(self, server_name: str, tool_schema: Dict[str, Any]):
        """Register a tool and its source server."""
        tool_name = tool_schema.get("name")
        if not tool_name:
            raise ValueError("Tool schema must contain a 'name'")

        self._tool_to_server[tool_name] = server_name
        self._tool_schemas[tool_name] = tool_schema

    def get_server_for_tool(self, tool_name: str) -> Optional[str]:
        """Find which server owns a specific tool."""
        return self._tool_to_server.get(tool_name)

    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all registered tools."""
        return list(self._tool_schemas.values())

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific tool."""
        return self._tool_schemas.get(tool_name)
