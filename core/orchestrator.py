import asyncio
from typing import Any, Dict, List
from langgraph.graph import StateGraph, END
from core.state import AgentState
from gateway.batch_executor import BatchExecutor
from providers.router import ProviderRouter
from pydantic import BaseModel, Field

from core.ide_context import IDEContext

# Define schema for the LLM output (structured generation)
class AgentAction(BaseModel):
    thought: str = Field(..., description="The reasoning behind the action.")
    plan: str = Field(..., description="Current plan of execution.")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="List of tools to execute. Must match batch_execute schema if using it.")
    final_answer: str = Field(default="", description="The final answer to the user if the task is complete.")

class AgentOrchestrator:
    """
    The Brain of the IDE Agentic Engine.
    Uses LangGraph to orchestrate Plan -> Execute -> Observe cycles.
    """
    def __init__(self, batch_executor: BatchExecutor, router: ProviderRouter, ide_context: IDEContext = None):
        self.batch_executor = batch_executor
        self.router = router
        self.ide_context = ide_context
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("execute", self._execute_node)
        
        # Define edges
        workflow.set_entry_point("plan")
        workflow.add_conditional_edges(
            "plan",
            self._should_continue,
            {
                "continue": "execute",
                "end": END
            }
        )
        workflow.add_edge("execute", "plan")
        
        return workflow.compile()

    async def _plan_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Ask the LLM what to do next.
        """
        iteration = state.get("iteration", 0) + 1
        messages = state.get("messages", [])
        
        provider = self.router.route(task_complexity="medium")
        
        tools = [self.batch_executor.get_batch_tool_schema()]
        
        system_prompt = (
            "You are an advanced AI Agentic IDE Engine. "
            "You must use the 'batch_execute' tool to perform actions in parallel. "
            "Think carefully, plan your steps, and execute.\n\n"
        )
        
        if self.ide_context:
            system_prompt += self.ide_context.format_context_prompt(
                active_file=state.get("active_file", ""),
                cursor_line=state.get("cursor_line", 0),
                open_files=state.get("open_files", [])
            )
        
        formatted_messages = [{"role": "system", "content": system_prompt}] + messages
        
        try:
            # We use structured output to enforce the AgentAction schema
            response: AgentAction = await provider.get_structured_output(
                messages=formatted_messages,
                response_model=AgentAction,
                tools=tools
            )
        except Exception as e:
            return {
                "iteration": iteration,
                "final_response": f"Error during planning: {e}",
                "pending_tool_calls": []
            }

        new_messages = [{"role": "assistant", "content": response.thought}]
        
        return {
            "iteration": iteration,
            "current_plan": response.plan,
            "pending_tool_calls": response.tool_calls,
            "final_response": response.final_answer,
            "messages": new_messages
        }

    async def _execute_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute pending tool calls using the BatchExecutor.
        """
        tool_calls = state.get("pending_tool_calls", [])
        if not tool_calls:
            return {}
            
        operations = []
        for call in tool_calls:
            if call.get("tool") == "batch_execute":
                args = call.get("args", {})
                operations.extend(args.get("operations", []))
            else:
                operations.append(call)
                
        results = await self.batch_executor.execute_batch(operations, parallel=True)
        
        result_msg = {"role": "user", "content": f"Tool Results:\n{results}"}
        
        return {
            "messages": [result_msg],
            "pending_tool_calls": []
        }

    def _should_continue(self, state: AgentState) -> str:
        """
        Determine if the agent should continue executing or stop.
        """
        if state.get("final_response"):
            return "end"
            
        if state.get("iteration", 0) >= state.get("max_iterations", 5):
            return "end"
            
        if not state.get("pending_tool_calls"):
            return "end"
            
        return "continue"

    async def run(self, input_message: str, max_iterations: int = 5) -> str:
        """
        Main entry point for the orchestrator.
        """
        initial_state = {
            "messages": [{"role": "user", "content": input_message}],
            "current_plan": "",
            "pending_tool_calls": [],
            "cost_summary": {},
            "iteration": 0,
            "max_iterations": max_iterations,
            "final_response": ""
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        return final_state.get("final_response", "Reached max iterations without a final answer.")
