import pytest

from core.orchestrator import AgentAction, AgentOrchestrator
from core.state import AgentState
from engine.batch_executor import BatchExecutor
from engine.connection_pool import ConnectionPool
from engine.providers.base_provider import BaseProvider
from engine.providers.router import ProviderRouter
from engine.tool_registry import ToolRegistry


class DummyStructuredProvider(BaseProvider):
    async def generate_response(self, messages, model="dummy", **kwargs):
        return "dummy"

    async def get_structured_output(self, messages, response_model, model="dummy", **kwargs):
        # Determine if it's the first or second iteration based on the number of messages
        has_results = any("Tool Results" in str(msg) for msg in messages)

        if not has_results:
            return response_model(
                thought="I need to check the files.",
                plan="Run echo command.",
                tool_calls=[
                    {
                        "tool": "batch_execute",
                        "args": {
                            "operations": [
                                {
                                    "id": "1",
                                    "tool": "run_command",
                                    "args": {"command": "echo 'dummy'"},
                                }
                            ]
                        },
                    }
                ],
                final_answer="",
            )
        else:
            return response_model(
                thought="I have the results.",
                plan="Done.",
                tool_calls=[],
                final_answer="The execution was successful.",
            )


@pytest.fixture
def setup_orchestrator():
    registry = ToolRegistry()
    registry.register_tool("terminal_server", {"name": "run_command"})

    pool = ConnectionPool()
    executor = BatchExecutor(pool, registry)

    router = ProviderRouter(default_provider="dummy")
    dummy_provider = DummyStructuredProvider()
    router.register_provider("dummy", dummy_provider)

    return AgentOrchestrator(executor, router), pool


@pytest.mark.asyncio
async def test_agent_orchestrator_flow(setup_orchestrator):
    orchestrator, pool = setup_orchestrator
    await pool.connect_all()

    import uuid

    session_id = str(uuid.uuid4())
    state = await orchestrator.run(session_id, "Can you echo dummy?")

    # Simulate HITL approval
    if state.get("pending_approval"):
        state = await orchestrator.resume(session_id, approved=True)

    # In test, DummyStructuredProvider returns "successful" final_answer
    assert "successful" in state.get("final_response", "")
