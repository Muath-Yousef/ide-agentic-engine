import asyncio
from typing import Any, Dict, List
from pydantic import BaseModel
from gateway.connection_pool import ConnectionPool
from gateway.tool_registry import ToolRegistry

class ToolCall(BaseModel):
    id: str
    tool: str
    args: Dict[str, Any]

class BatchExecutor:
    """
    THE CORE of token optimization in Phase 1.
    Converts N separate tool calls into grouped batch requests.
    """
    def __init__(self, connection_pool: ConnectionPool, tool_registry: ToolRegistry):
        self.pool = connection_pool
        self.registry = tool_registry

    async def execute_batch(self, operations: List[Dict[str, Any]], parallel: bool = True) -> Dict[str, Any]:
        """
        Group operations by MCP server and execute them.
        Parallel execution within the same batch is supported.
        """
        try:
            # Parse into ToolCall objects
            tool_calls = [ToolCall(**op) for op in operations]
        except Exception as e:
            return {"error": f"Invalid operations format: {e}"}
            
        # 1. Group by MCP server
        server_batches: Dict[str, List[ToolCall]] = {}
        for call in tool_calls:
            server_name = self.registry.get_server_for_tool(call.tool)
            if not server_name:
                return {"error": f"Tool '{call.tool}' not found in registry."}
                
            if server_name not in server_batches:
                server_batches[server_name] = []
            server_batches[server_name].append(call)

        # 2. Execute batches
        results = {"results": []}
        
        async def exec_call(server_name: str, call: ToolCall):
            try:
                res = await self.pool.execute_tool(server_name, call.tool, call.args)
                return {"id": call.id, "tool": call.tool, "output": res}
            except Exception as e:
                return {"id": call.id, "tool": call.tool, "error": str(e)}

        if parallel:
            # Execute all calls concurrently across all servers
            tasks = []
            for server_name, calls in server_batches.items():
                for call in calls:
                    tasks.append(exec_call(server_name, call))
            
            completed = await asyncio.gather(*tasks)
            results["results"].extend(completed)
        else:
            # Execute sequentially
            for server_name, calls in server_batches.items():
                for call in calls:
                    res = await exec_call(server_name, call)
                    results["results"].append(res)
                    
        return results

    def get_batch_tool_schema(self) -> Dict[str, Any]:
        """
        Returns the schema for the batch_execute tool to provide to the LLM.
        """
        return {
            "name": "batch_execute",
            "description": "Execute multiple operations in a single call. Always prefer this over calling individual tools separately.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "operations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "Unique ID for this operation"},
                                "tool": {"type": "string"},
                                "args": {"type": "object"}
                            },
                            "required": ["id", "tool", "args"]
                        }
                    },
                    "parallel": {"type": "boolean", "default": True}
                },
                "required": ["operations"]
            }
        }
