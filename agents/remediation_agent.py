"""
Remediation Agent — analyses security findings and determines the best fix path.
If it's a code issue, it delegates to the Orchestrator to generate diff patches.
If it's a system issue, it delegates to run system commands under HITL.
"""

import logging
import uuid
from typing import Any, Dict

from core.key_pool import APIKeyPool
from core.orchestrator import AgentOrchestrator
from engine.batch_executor import BatchExecutor
from engine.connection_pool import ConnectionPool
from engine.providers.router import ProviderRouter
from engine.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


async def run_auto_remediation(
    finding: Dict[str, Any], cwd: str = "."
) -> tuple[str, Dict[str, Any]]:
    """
    Launch the auto-remediation process for a specific finding.
    Returns the session ID and the initial state dict, which may have pending_approval=True.
    """
    pool = ConnectionPool()
    registry = ToolRegistry()
    batch_executor = BatchExecutor(pool, registry)

    from engine.providers.anthropic_provider import AnthropicProvider
    from engine.providers.deepseek_provider import DeepSeekProvider
    from engine.providers.gemini_provider import GeminiProvider
    from engine.providers.groq_provider import GroqProvider
    from engine.providers.openai_provider import OpenAIProvider

    key_pool = APIKeyPool()
    router = ProviderRouter(key_pool)
    router.register_provider("gemini", GeminiProvider(key_pool=key_pool))
    router.register_provider("anthropic", AnthropicProvider(key_pool=key_pool))
    router.register_provider("openai", OpenAIProvider(key_pool=key_pool))
    router.register_provider("groq", GroqProvider(key_pool=key_pool))
    router.register_provider("deepseek", DeepSeekProvider(key_pool=key_pool))

    orchestrator = AgentOrchestrator(batch_executor, router)

    session_id = str(uuid.uuid4())

    # Formulate the task for the orchestrator
    task_prompt = (
        f"You are tasked with Auto-Remediating the following security finding:\n"
        f"Title: {finding.get('title')}\n"
        f"Severity: {finding.get('severity')}\n"
        f"Details: {finding.get('remediation_summary')}\n\n"
        f"Working Directory: {cwd}\n\n"
        "Follow the AUTO-REMEDIATION PROTOCOL in your system prompt.\n"
        "If it is a code issue, locate the file, create a branch, apply the patch, commit, and push.\n"
        "If it is a system issue, execute the required hardening commands."
    )

    logger.info(f"Starting auto-remediation for: {finding.get('title')} (Session: {session_id})")

    # Run the orchestrator
    state = await orchestrator.run(session_id, task_prompt)

    return session_id, state
