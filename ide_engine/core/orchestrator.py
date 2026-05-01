import asyncio
from typing import Any, Dict, List

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ConfigDict, Field

from core.ide_context import IDEContext
from core.state import AgentState
from engine.batch_executor import BatchExecutor
from engine.providers.router import ProviderRouter


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: str = Field(..., description="Name of the tool to call.")
    args_json: str = Field(default="{}", description="JSON string of arguments for the tool.")


# Define schema for the LLM output (structured generation)
class AgentAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thought: str = Field(..., description="The reasoning behind the action.")
    plan: str = Field(..., description="Current plan of execution.")
    tool_calls: List[ToolCall] = Field(
        default_factory=list,
        description="List of tools to execute. Must match batch_execute schema if using it.",
    )
    final_answer: str = Field(
        default="", description="The final answer to the user if the task is complete."
    )


class AgentOrchestrator:
    """
    The Brain of the IDE Agentic Engine.
    Uses LangGraph to orchestrate Plan -> Execute -> Observe cycles.
    """

    def __init__(
        self, batch_executor: BatchExecutor, router: ProviderRouter, ide_context: IDEContext = None
    ):
        self.batch_executor = batch_executor
        self.router = router
        self.ide_context = ide_context
        self.skills_content = self._load_shared_skills()
        self.graph = self._build_graph()

    def _load_shared_skills(self) -> str:
        """
        Scans packages/shared_skills/ and returns a formatted string of all markdown skills.
        """
        import os

        skills_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shared_skills")
        if not os.path.exists(skills_root):
            # Try to resolve relative to root if running from root
            skills_root = os.path.join(os.getcwd(), "packages", "shared_skills")
            if not os.path.exists(skills_root):
                return ""

        all_skills = []
        for root, dirs, files in os.walk(skills_root):
            for file in files:
                if file.endswith(".md"):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r") as f:
                            content = f.read()
                            all_skills.append(f"--- SKILL: {file} ---\n{content}")
                    except Exception as e:
                        print(f"DEBUG: Failed to load skill {file}: {e}")

        if not all_skills:
            return ""

        return "\n\nAVAILABLE EXPERT SKILLS:\n" + "\n\n".join(all_skills)

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("plan", self._plan_node)
        workflow.add_node("execute", self._execute_node)

        # Define edges
        workflow.set_entry_point("plan")
        workflow.add_conditional_edges(
            "plan", self._should_continue, {"continue": "execute", "end": END}
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
        print(f"DEBUG: Selected Provider: {getattr(provider, '__class__', {}).__name__}")

        tools = [self.batch_executor.get_batch_tool_schema()]

        system_prompt = (
            "You are an advanced AI Agentic IDE Engine, functioning as an Autonomous SOAR platform. "
            "You must use the 'batch_execute' tool to perform actions in parallel. "
            "Think carefully, plan your steps, and execute.\n\n"
            "AUTO-REMEDIATION PROTOCOL:\n"
            "1. If you find a code vulnerability (e.g., via Nuclei), you MUST generate a fix using the `apply_diff_patch` tool.\n"
            "2. Before fixing code, ALWAYS use `git_create_branch` to create a new branch (e.g., fix/security-vuln).\n"
            "3. After applying the fix, use `git_commit` and `git_push` to save and push your changes.\n"
            "4. If you find a system configuration issue (e.g., open ports), use `run_command` to apply hardening commands (e.g., ufw, systemctl) under HITL supervision.\n\n"
            "IMPORTANT: For tool calls, provide the arguments as a valid JSON string in the 'args_json' field.\n"
        )

        if self.skills_content:
            system_prompt += self.skills_content + "\n\n"

        if self.ide_context:
            system_prompt += self.ide_context.format_context_prompt(
                active_file=state.get("active_file", ""),
                cursor_line=state.get("cursor_line", 0),
                open_files=state.get("open_files", []),
            )

        formatted_messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            # We use structured output to enforce the AgentAction schema
            response: AgentAction = await provider.get_structured_output(
                messages=formatted_messages,
                response_model=AgentAction,
                tools=tools,
            )
            if not response:
                raise ValueError("LLM returned an empty response.")

            print(f"DEBUG: LLM Thought: {response.thought}")
            if response.tool_calls:
                print("\n" + "="*50)
                print("🚀 PROPOSED REMEDIATION PLAN")
                print("="*50)
                for i, call in enumerate(response.tool_calls):
                    print(f"{i+1}. Tool: {call.tool}")
                    print(f"   Arguments: {call.args_json}")
                print("="*50 + "\n")
                
                # Save to a local file for inspection
                import json
                try:
                    with open("remediation_plan.json", "w") as f:
                        json.dump([{"tool": c.tool, "args": c.args_json} for c in response.tool_calls], f, indent=2)
                except Exception as e:
                    print(f"Warning: Could not save plan to file: {e}")
        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            return {
                "iteration": iteration,
                "final_response": f"Error during planning: {e}\n{error_details}",
                "pending_tool_calls": [],
            }

        new_messages = [{"role": "assistant", "content": response.thought}]

        # Intercept critical tools for HITL approval
        CRITICAL_TOOLS = {"apply_diff_patch", "run_command", "git_push"}

        pending_calls = []
        critical_calls = []
        requires_approval = False

        import json

        processed_tool_calls = []
        for tc in response.tool_calls:
            try:
                args = json.loads(tc.args_json)
                processed_tool_calls.append({"tool": tc.tool, "args": args})
            except:
                # Fallback or error
                continue

        for call in processed_tool_calls:
            # Check if any operation in batch_execute is critical
            if call.get("tool") == "batch_execute":
                args = call.get("args", {})
                operations = args.get("operations", [])

                # Check all operations in batch
                batch_critical = any(op.get("tool") in CRITICAL_TOOLS for op in operations)

                # We can also check if run_command has destructive commands
                for op in operations:
                    if op.get("tool") == "run_command":
                        cmd = str(op.get("args", {}).get("command", "")).lower()
                        if any(
                            danger in cmd
                            for danger in ["rm ", "systemctl", "iptables", "chmod", "chown"]
                        ):
                            batch_critical = True

                if batch_critical:
                    critical_calls.append(call)
                    requires_approval = True
                else:
                    pending_calls.append(call)
            else:
                if call.get("tool") in CRITICAL_TOOLS:
                    critical_calls.append(call)
                    requires_approval = True
                else:
                    pending_calls.append(call)

        return {
            "iteration": iteration,
            "current_plan": response.plan,
            "pending_tool_calls": pending_calls,
            "critical_tool_calls": critical_calls,
            "pending_approval": requires_approval,
            "final_response": response.final_answer,
            "messages": new_messages,
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

        return {"messages": [result_msg], "pending_tool_calls": []}

    def _should_continue(self, state: AgentState) -> str:
        """
        Determine if the agent should continue executing or stop.
        """
        if state.get("pending_approval"):
            return "end"  # Pause graph execution for HITL

        if state.get("final_response"):
            return "end"

        if state.get("iteration", 0) >= state.get("max_iterations", 5):
            return "end"

        if not state.get("pending_tool_calls"):
            return "end"

        return "continue"

    async def run(
        self, session_id: str, input_message: str, max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Main entry point for the orchestrator. Returns the final state.
        """
        from core.session_store import SessionStore

        store = SessionStore()

        # Add the assistant turn (thought + tool output)
        messages = [{"role": "user", "content": input_message}]

        initial_state = {
            "messages": messages,
            "current_plan": "",
            "pending_tool_calls": [],
            "critical_tool_calls": [],
            "pending_approval": False,
            "cost_summary": {},
            "iteration": 0,
            "max_iterations": max_iterations,
            "final_response": "",
        }

        final_state = await self.graph.ainvoke(initial_state)

        if final_state.get("pending_approval"):
            store.save_session(session_id, final_state)

        return final_state

    async def resume(self, session_id: str, approved: bool) -> Dict[str, Any]:
        """
        Resume a paused orchestration session.
        """
        from core.session_store import SessionStore

        store = SessionStore()

        state = store.load_session(session_id)
        if not state:
            return {"final_response": "Session not found or expired.", "pending_approval": False}

        # Move state forward based on approval
        if approved:
            state["pending_tool_calls"] = state.get("critical_tool_calls", [])
            state["critical_tool_calls"] = []
            state["pending_approval"] = False

            # Since we paused at 'plan' going to 'end', we need to run 'execute' next manually,
            # or just feed it back to 'ainvoke' but 'ainvoke' starts from entrypoint ('plan').
            # To fix this without checkpointer, we can just execute the critical calls directly,
            # then feedback the result and run ainvoke.
            execute_result = await self._execute_node(state)
            state["messages"].extend(execute_result.get("messages", []))
            state["pending_tool_calls"] = []

            # Now continue graph from plan
            final_state = await self.graph.ainvoke(state)
        else:
            state["critical_tool_calls"] = []
            state["pending_approval"] = False
            state["messages"].append(
                {
                    "role": "user",
                    "content": "Action rejected by user. Please re-evaluate your plan.",
                }
            )
            final_state = await self.graph.ainvoke(state)

        if final_state.get("pending_approval"):
            store.save_session(session_id, final_state)
        else:
            store.delete_session(session_id)

        return final_state
