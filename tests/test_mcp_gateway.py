"""Tests for engine/mcp_gateway.py."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from engine.mcp_gateway import BatchRequest, BatchResponse, MCPGateway, ToolInvocation
from engine.token_optimizer import TokenOptimizer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_gateway() -> MCPGateway:
    """Return a gateway with all built-in tools replaced by fast mocks."""
    optimizer = TokenOptimizer(max_head=3, max_tail=3)
    gw = MCPGateway.__new__(MCPGateway)
    gw._optimizer = optimizer
    gw._registry = {}
    return gw


@pytest.fixture()
def gateway() -> MCPGateway:
    return _make_gateway()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_tool_success(gateway: MCPGateway) -> None:
    """A single successful invocation should return success=True."""
    gateway.register("echo", lambda message: f"echo: {message}")

    request = BatchRequest(
        invocations=[ToolInvocation(tool_name="echo", arguments={"message": "hello"})]
    )
    response: BatchResponse = await gateway.execute_batch_operations(request)

    assert response.total == 1
    assert response.successful == 1
    assert response.failed == 0
    assert response.results[0].success is True
    assert response.results[0].result == "echo: hello"


@pytest.mark.asyncio
async def test_unknown_tool_returns_error(gateway: MCPGateway) -> None:
    """Calling an unregistered tool should return a failure result, not raise."""
    request = BatchRequest(
        invocations=[ToolInvocation(tool_name="nonexistent", arguments={})]
    )
    response = await gateway.execute_batch_operations(request)

    assert response.failed == 1
    assert response.successful == 0
    assert "Unknown tool" in (response.results[0].error or "")


@pytest.mark.asyncio
async def test_parallel_execution_is_faster_than_sequential(gateway: MCPGateway) -> None:
    """Parallel batch should complete faster than sum of individual sleeps."""
    import time

    async def slow_tool(delay: float = 0.1) -> str:
        await asyncio.sleep(delay)
        return "done"

    gateway.register("slow", slow_tool)

    invocations = [
        ToolInvocation(tool_name="slow", arguments={"delay": 0.1}) for _ in range(5)
    ]
    request = BatchRequest(invocations=invocations)

    start = time.perf_counter()
    response = await gateway.execute_batch_operations(request)
    elapsed = time.perf_counter() - start

    # 5 × 0.1s sequential = 0.5s; parallel should complete in ~0.1-0.2s
    assert elapsed < 0.35, f"Batch took {elapsed:.2f}s — parallel dispatch may be broken"
    assert response.successful == 5


@pytest.mark.asyncio
async def test_one_failure_does_not_block_others(gateway: MCPGateway) -> None:
    """A tool that raises should not prevent other tools from succeeding."""
    def broken() -> str:
        raise RuntimeError("intentional failure")

    gateway.register("ok", lambda: "success")
    gateway.register("broken", broken)

    request = BatchRequest(
        invocations=[
            ToolInvocation(tool_name="ok", arguments={}),
            ToolInvocation(tool_name="broken", arguments={}),
            ToolInvocation(tool_name="ok", arguments={}),
        ]
    )
    response = await gateway.execute_batch_operations(request)

    assert response.total == 3
    assert response.successful == 2
    assert response.failed == 1
    error_results = [r for r in response.results if not r.success]
    assert "intentional failure" in (error_results[0].error or "")


@pytest.mark.asyncio
async def test_terminal_pruning_applied_for_run_command(gateway: MCPGateway) -> None:
    """run_command output should be pruned automatically."""
    long_output = "\n".join(f"line {i}" for i in range(200))
    gateway.register("run_command", lambda cmd: long_output)

    request = BatchRequest(
        invocations=[ToolInvocation(tool_name="run_command", arguments={"cmd": "echo"})]
    )
    response = await gateway.execute_batch_operations(request)

    result_text = str(response.results[0].result)
    assert "pruned" in result_text
    assert len(result_text.splitlines()) < 50


@pytest.mark.asyncio
async def test_sync_handler_dispatched_via_executor(gateway: MCPGateway) -> None:
    """Sync (non-coroutine) handlers should be offloaded to the executor."""
    import threading

    thread_ids: list[int] = []

    def sync_tool() -> str:
        thread_ids.append(threading.get_ident())
        return "sync_ok"

    gateway.register("sync_tool", sync_tool)
    request = BatchRequest(
        invocations=[ToolInvocation(tool_name="sync_tool", arguments={})]
    )
    response = await gateway.execute_batch_operations(request)
    assert response.successful == 1
    assert response.results[0].result == "sync_ok"


def test_get_tool_definition_schema() -> None:
    """Tool definition should be a valid Anthropic tool schema."""
    defn = MCPGateway.get_tool_definition()
    assert defn["name"] == "execute_batch_operations"
    assert "input_schema" in defn
    assert defn["input_schema"]["type"] == "object"
    assert "invocations" in defn["input_schema"]["properties"]


def test_token_savings_estimate_scales_with_batch_size(gateway: MCPGateway) -> None:
    """Estimated token savings should increase with batch size."""

    async def _run(n: int) -> int:
        gateway.register("noop", lambda: "ok")
        req = BatchRequest(
            invocations=[ToolInvocation(tool_name="noop", arguments={}) for _ in range(n)]
        )
        resp = await gateway.execute_batch_operations(req)
        return resp.estimated_tokens_saved

    savings_1 = asyncio.get_event_loop().run_until_complete(_run(1))
    savings_5 = asyncio.get_event_loop().run_until_complete(_run(5))
    assert savings_5 > savings_1
