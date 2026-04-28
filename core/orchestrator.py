import operator
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from servers.terminal_server import TerminalExecutor

# Define Agent State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_action: str

class AgentOrchestrator:
    """
    Core orchestrator handling the Plan -> Execute Tool -> Observe Output -> Refine loop.
    Currently a minimal scaffolding using LangGraph.
    """
    def __init__(self):
        self.terminal = TerminalExecutor()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", self._run_agent)
        workflow.add_node("action", self._execute_action)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "action",
                "end": END
            }
        )
        
        workflow.add_edge("action", "agent")
        
        return workflow.compile()

    def _run_agent(self, state: AgentState):
        """
        Mock agent node. In a real scenario, this calls the LLM (e.g., Gemini)
        and parses its output to determine if a tool call is needed.
        """
        messages = state["messages"]
        last_message = messages[-1].content
        
        # Very rudimentary mock logic for demonstration
        if "terminal:" in last_message.lower():
            # Extract command (e.g., "terminal: ls -la")
            cmd = last_message.split("terminal:")[1].strip()
            return {
                "messages": [AIMessage(content=f"I will run the command: {cmd}")],
                "next_action": "execute_terminal",
                "command": cmd
            }
        
        # If no tool call, we assume we are done
        return {
            "messages": [AIMessage(content="I have completed my reasoning and have no more actions.")],
            "next_action": "end"
        }

    def _execute_action(self, state: AgentState):
        """
        Executes the tool requested by the agent and appends the result to the state.
        """
        messages = state["messages"]
        # In a real setup, we'd extract the tool call from the AIMessage tool_calls
        # For this scaffolding, we pass the command in the state dictionary (injected in _run_agent mock)
        
        # Note: the mock state dict doesn't actually persist non-TypedDict keys unless we define them,
        # so for this scaffolding, we'll just extract from the AIMessage content.
        last_ai_msg = messages[-1].content
        if "I will run the command: " in last_ai_msg:
            cmd = last_ai_msg.replace("I will run the command: ", "").strip()
            output = self.terminal.run_as_tool(cmd)
            return {"messages": [HumanMessage(content=f"Tool Output:\n{output}")]}
            
        return {"messages": [HumanMessage(content="Action failed: Unknown tool.")]}

    def _should_continue(self, state: AgentState):
        """Determines whether to continue to tools or end the loop."""
        if state.get("next_action") == "end":
            return "end"
        return "continue"

    def run(self, prompt: str):
        """Main entry point to trigger the orchestrator."""
        initial_state = {"messages": [HumanMessage(content=prompt)], "next_action": "start"}
        
        # Stream events from the graph
        for event in self.graph.stream(initial_state):
            for node_name, node_state in event.items():
                print(f"\n--- Node: {node_name} ---")
                if "messages" in node_state and node_state["messages"]:
                    print(node_state["messages"][-1].content)
