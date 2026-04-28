import asyncio
import inspect
import time
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from core.key_pool import APIKeyPool
from engine.optimization.token_optimizer import TokenOptimizer, apply_diff_patch
from tools.cyber_tools_server import virustotal_scan
from tools.filesystem_server import read_file
from tools.git_server import git_commit, git_create_branch, git_push, git_status
from tools.terminal_server import run_command


class ToolInvocation(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None


class BatchRequest(BaseModel):
    invocations: List[ToolInvocation] = Field(..., min_length=1)


class BatchResponse(BaseModel):
    results: List[ToolResult]
    total: int = 0
    successful: int = 0
    failed: int = 0
    total_duration_ms: float = 0.0
    estimated_tokens_saved: int = 0


BATCH_TOOL_DEFINITION = {
    "name": "execute_batch_operations",
    "description": "Execute multiple tools in parallel to save tokens and time.",
    "input_schema": {
        "type": "object",
        "properties": {
            "invocations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "enum": [
                                "read_file",
                                "write_file",
                                "apply_diff_patch",
                                "run_command",
                                "search_web",
                                "get_code_skeleton",
                                "gdrive_read",
                                "wazuh_query",
                                "nuclei_scan",
                                "git_status",
                                "git_create_branch",
                                "git_commit",
                                "git_push",
                            ],
                        },
                        "arguments": {"type": "object"},
                    },
                    "required": ["tool_name", "arguments"],
                },
            }
        },
        "required": ["invocations"],
    },
}


class MCPGateway:
    """
    Gateway to route tool calls to the correct MCP server.
    """

    def __init__(self, key_pool: Optional[APIKeyPool] = None):
        self.key_pool = key_pool
        self._optimizer = TokenOptimizer()
        self._registry: Dict[str, Callable] = {
            "read_file": read_file,
            "run_command": run_command,
            "virus_total_scan": self.virus_total_scan_tool,
            "apply_diff_patch": apply_diff_patch,
            "git_status": git_status,
            "git_create_branch": git_create_branch,
            "git_commit": git_commit,
            "git_push": git_push,
        }

    def register(self, name: str, handler: Callable):
        """Register a new tool handler."""
        self._registry[name] = handler

    @staticmethod
    def get_tool_definition() -> Dict[str, Any]:
        return BATCH_TOOL_DEFINITION

    def get_available_tools(self) -> List[Dict[str, Any]]:
        # Simplified for now, just return the batch tool
        return [BATCH_TOOL_DEFINITION]

    async def execute_batch_operations(self, request: BatchRequest) -> BatchResponse:
        """Execute multiple tools in parallel and return structured response."""
        start_time = time.perf_counter()
        tasks = []
        for inv in request.invocations:
            tasks.append(self._execute_single_invocation(inv))

        results = await asyncio.gather(*tasks)

        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Estimate savings: ~1000 tokens per round-trip saved
        savings = (len(request.invocations) - 1) * 1000 if len(request.invocations) > 1 else 0

        return BatchResponse(
            results=results,
            total=len(results),
            successful=successful,
            failed=failed,
            total_duration_ms=duration_ms,
            estimated_tokens_saved=max(0, savings),
        )

    async def _execute_single_invocation(self, inv: ToolInvocation) -> ToolResult:
        if inv.tool_name not in self._registry:
            return ToolResult(
                tool_name=inv.tool_name, success=False, error=f"Unknown tool: {inv.tool_name}"
            )

        handler = self._registry[inv.tool_name]
        try:
            # Handle both sync and async handlers
            if inspect.iscoroutinefunction(handler):
                output = await handler(**inv.arguments)
            else:
                # Run sync handlers in thread pool to avoid blocking
                output = await asyncio.to_thread(handler, **inv.arguments)

            # Apply pruning for terminal commands
            if inv.tool_name == "run_command":
                output = self._optimizer.prune_terminal_output(str(output))

            return ToolResult(tool_name=inv.tool_name, success=True, result=str(output))
        except Exception as e:
            return ToolResult(tool_name=inv.tool_name, success=False, error=str(e))

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
                if "429" in error_str or "403" in error_str:
                    is_rate_limit = "429" in error_str
                    self.key_pool.mark_exhausted(
                        "virustotal", current_key, is_rate_limit=is_rate_limit
                    )
                    print(f"Key Rotation: VirusTotal key failed ({error_str}). Rotating...")
                    continue
                else:
                    return f"VirusTotal Error: {e}"

        return "Error: All VirusTotal keys exhausted."

    async def execute_tool(self, tool_name: str, kwargs: Dict[str, Any]) -> str:
        # Legacy support
        res = await self._execute_single_invocation(
            ToolInvocation(tool_name=tool_name, arguments=kwargs)
        )
        return res.result if res.success else res.error
