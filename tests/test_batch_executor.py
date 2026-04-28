import pytest
import asyncio
from gateway.tool_registry import ToolRegistry
from gateway.connection_pool import ConnectionPool
from gateway.batch_executor import BatchExecutor

@pytest.fixture
def setup_gateway():
    registry = ToolRegistry()
    registry.register_tool("filesystem_server", {"name": "read_file"})
    registry.register_tool("terminal_server", {"name": "run_command"})
    
    pool = ConnectionPool()
    executor = BatchExecutor(pool, registry)
    return executor, pool

@pytest.mark.asyncio
async def test_batch_execution(setup_gateway):
    executor, pool = setup_gateway
    await pool.connect_all()
    
    operations = [
        {"id": "op1", "tool": "run_command", "args": {"command": "echo 'batch1'"}},
        {"id": "op2", "tool": "run_command", "args": {"command": "echo 'batch2'"}}
    ]
    
    result = await executor.execute_batch(operations, parallel=True)
    
    assert "results" in result
    assert len(result["results"]) == 2
    
    outputs = [r["output"] for r in result["results"]]
    assert any("batch1" in out for out in outputs)
    assert any("batch2" in out for out in outputs)

@pytest.mark.asyncio
async def test_invalid_tool(setup_gateway):
    executor, pool = setup_gateway
    await pool.connect_all()
    
    operations = [
        {"id": "op1", "tool": "unknown_tool", "args": {}}
    ]
    
    result = await executor.execute_batch(operations)
    assert "error" in result
    assert "not found in registry" in result["error"]
