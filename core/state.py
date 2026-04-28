from typing import Annotated, Any, Dict, List, TypedDict


def add_messages(left: list, right: list) -> list:
    """Append new messages to the existing list."""
    return left + right


class AgentState(TypedDict):
    """
    Core state for the LangGraph orchestrator.
    """

    messages: Annotated[list, add_messages]
    current_plan: str
    pending_tool_calls: List[Dict[str, Any]]
    critical_tool_calls: List[Dict[str, Any]]
    pending_approval: bool
    cost_summary: Dict[str, Any]
    iteration: int
    max_iterations: int
    final_response: str

    # IDE Context
    active_file: str
    cursor_line: int
    open_files: List[str]
