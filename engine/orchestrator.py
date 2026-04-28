"""
LangGraph Orchestrator — the cognitive loop of ide-agentic-engine.

State machine:
    START → triage → ┬→ simple   → END
                     ├→ execute  → END
                     ├→ compliance → report → END
                     └→ report   → END

Triage uses keyword heuristics (free) before escalating to a lightweight
LLM call.  Heavy Sonnet calls only happen for code_generation / compliance.
"""

from __future__ import annotations

import logging
import operator
from typing import Annotated, Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from engine.llm_manager import LLMManager
from engine.mcp_gateway import BatchRequest, MCPGateway, ToolInvocation
from engine.token_optimizer import TokenOptimizer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared state definition
# ---------------------------------------------------------------------------


class AgentState(TypedDict, total=False):
    """Full mutable state passed between graph nodes."""

    client_id: str
    target: str
    task_type: str          # "simple_qa" | "code_task" | "compliance" | "report_gen"
    task_description: str

    # Accumulated lists — operator.add means new items are appended, not replaced
    messages: Annotated[list[dict[str, Any]], operator.add]
    batch_results: Annotated[list[dict[str, Any]], operator.add]
    compliance_findings: Annotated[list[dict[str, Any]], operator.add]
    evidence_records: Annotated[list[dict[str, Any]], operator.add]

    scan_results: dict[str, Any]
    final_report_path: str
    error: str
    iteration_count: int


# ---------------------------------------------------------------------------
# Keyword-based triage heuristics (zero API cost)
# ---------------------------------------------------------------------------

_TASK_KEYWORDS: dict[str, list[str]] = {
    "compliance": [
        "nca", "ecc", "compliance", "audit", "control",
        "iso 27001", "policy", "regulatory", "framework",
    ],
    "report_gen": [
        "report", "pdf", "generate", "document", "summary", "executive",
    ],
    "code_generation": [
        "code", "write", "implement", "fix", "debug", "refactor",
        "function", "class", "script", "tests",
    ],
    "simple_qa": [
        "what", "how", "explain", "list", "show", "tell", "describe",
    ],
}


def _heuristic_triage(description: str) -> str:
    """Return task_type based on keyword frequency — free, instant."""
    text = description.lower()
    scores: dict[str, int] = {}
    for task_type, keywords in _TASK_KEYWORDS.items():
        scores[task_type] = sum(1 for kw in keywords if kw in text)

    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return "code_generation"  # safe default
    return best


# ---------------------------------------------------------------------------
# Node functions — each returns a partial state update (dict)
# ---------------------------------------------------------------------------


def triage_node(state: AgentState) -> dict[str, Any]:
    """
    Determine task_type from the task_description using keyword heuristics.
    No API call — completely free.  Can be upgraded to a Haiku call if needed.
    """
    description = state.get("task_description", "")
    task_type = _heuristic_triage(description)
    logger.info("Triage: '%s' → task_type=%s", description[:60], task_type)
    return {
        "task_type": task_type,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


async def simple_node(state: AgentState) -> dict[str, Any]:
    """Handle simple QA without tool use — single Haiku call."""
    llm = _get_llm()
    from pydantic import BaseModel

    class SimpleAnswer(BaseModel):
        answer: str
        confidence: float

    try:
        result = await llm.call_structured(
            task_type="simple_qa",
            user_prompt=state.get("task_description", ""),
            response_model=SimpleAnswer,
        )
        return {
            "messages": [{"role": "assistant", "content": result.answer}],
        }
    except Exception as exc:
        logger.error("simple_node failed: %s", exc)
        return {"error": str(exc)}


async def execute_node(state: AgentState) -> dict[str, Any]:
    """
    Code / file execution node.

    Builds a BatchRequest from the task, runs it through the gateway,
    and returns the aggregated results.
    """
    gateway = _get_gateway()
    task = state.get("task_description", "")

    # Build a batch from common code-task operations
    invocations = _build_code_batch(task, state)
    if not invocations:
        return {"error": "execute_node: could not determine required tools from task"}

    try:
        response = await gateway.execute_batch_operations(
            BatchRequest(invocations=invocations)
        )
        results = [r.model_dump() for r in response.results]
        logger.info(
            "execute_node: %d/%d tools succeeded, ~%d tokens saved",
            response.successful,
            response.total,
            response.estimated_tokens_saved,
        )
        return {
            "batch_results": results,
            "scan_results": {r["tool_name"]: r["result"] for r in results if r["success"]},
        }
    except Exception as exc:
        logger.error("execute_node failed: %s", exc, exc_info=True)
        return {"error": str(exc)}


async def compliance_node(state: AgentState) -> dict[str, Any]:
    """
    Run NCA ECC compliance analysis via compliance_agent.

    Reads scan_results from state, maps findings to NCA controls,
    records evidence, and stores compliance_findings in state.
    """
    from agents.compliance_agent import run_compliance_analysis

    scan_results = state.get("scan_results", {})
    client_id = state.get("client_id", "unknown")

    try:
        findings, evidence = await run_compliance_analysis(client_id, scan_results)
        logger.info("compliance_node: %d findings, %d evidence records", len(findings), len(evidence))
        return {
            "compliance_findings": findings,
            "evidence_records": evidence,
        }
    except Exception as exc:
        logger.error("compliance_node failed: %s", exc, exc_info=True)
        return {"error": str(exc)}


async def report_node(state: AgentState) -> dict[str, Any]:
    """
    Generate PDF compliance report via report_agent.

    Returns path to the generated report in final_report_path.
    """
    from agents.report_agent import generate_report

    try:
        report_path = await generate_report(
            client_id=state.get("client_id", "unknown"),
            target=state.get("target", ""),
            findings=state.get("compliance_findings", []),
            evidence=state.get("evidence_records", []),
        )
        logger.info("report_node: report at %s", report_path)
        return {"final_report_path": report_path}
    except Exception as exc:
        logger.error("report_node failed: %s", exc, exc_info=True)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def _route_after_triage(state: AgentState) -> str:
    """Conditional edge: map task_type to next node name."""
    task_type = state.get("task_type", "code_generation")
    routing: dict[str, str] = {
        "compliance": "compliance",
        "report_gen": "report",
        "code_generation": "execute",
        "simple_qa": "simple",
    }
    next_node = routing.get(task_type, "execute")
    logger.debug("Routing: task_type=%s → node=%s", task_type, next_node)
    return next_node


# ---------------------------------------------------------------------------
# Graph factory
# ---------------------------------------------------------------------------


def create_graph() -> Any:
    """
    Compile and return the LangGraph StateGraph.

    Call once at startup; the compiled graph is reusable across requests.
    """
    workflow: StateGraph = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("triage", triage_node)
    workflow.add_node("simple", simple_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("compliance", compliance_node)
    workflow.add_node("report", report_node)

    # Entry point
    workflow.set_entry_point("triage")

    # Edges
    workflow.add_conditional_edges(
        "triage",
        _route_after_triage,
        {
            "simple": "simple",
            "execute": "execute",
            "compliance": "compliance",
            "report": "report",
        },
    )
    workflow.add_edge("simple", END)
    workflow.add_edge("execute", END)
    workflow.add_edge("compliance", "report")
    workflow.add_edge("report", END)

    return workflow.compile()


# ---------------------------------------------------------------------------
# Lazy singletons (avoid circular imports at module level)
# ---------------------------------------------------------------------------

_llm: LLMManager | None = None
_gateway: MCPGateway | None = None


def _get_llm() -> LLMManager:
    global _llm
    if _llm is None:
        _llm = LLMManager(optimizer=TokenOptimizer())
    return _llm


def _get_gateway() -> MCPGateway:
    global _gateway
    if _gateway is None:
        _gateway = MCPGateway(token_optimizer=TokenOptimizer())
    return _gateway


# ---------------------------------------------------------------------------
# Helper: build BatchRequest invocations for code tasks
# ---------------------------------------------------------------------------


def _build_code_batch(
    task: str, state: AgentState
) -> list[ToolInvocation]:
    """
    Heuristically determine which tools to run for a code task.

    For a real engine, the LLM would decide this; here we provide
    a sensible default for bootstrapping / testing.
    """
    target = state.get("target", "")
    invocations: list[ToolInvocation] = []

    if target and ("scan" in task.lower() or "nuclei" in task.lower()):
        invocations.append(
            ToolInvocation(tool_name="nuclei_scan", arguments={"target": target})
        )
    if "wazuh" in task.lower() or "alert" in task.lower():
        invocations.append(
            ToolInvocation(tool_name="wazuh_query", arguments={"query": task})
        )
    if not invocations:
        # Generic: skeleton-read any .py files mentioned in task
        import re
        paths = re.findall(r"[\w/.-]+\.py", task)
        for p in paths[:5]:  # cap at 5 files
            invocations.append(
                ToolInvocation(tool_name="get_code_skeleton", arguments={"path": p})
            )
    if not invocations:
        # Absolute fallback: run a no-op command to confirm environment
        invocations.append(
            ToolInvocation(tool_name="run_command", arguments={"cmd": "echo 'engine ready'"})
        )

    return invocations
