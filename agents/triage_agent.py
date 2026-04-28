"""
Triage Agent — optional LLM-based task classification.

The orchestrator uses keyword heuristics by default (zero cost).
This module provides an upgraded LLM-based classifier using Haiku
for cases where heuristics are insufficient.
"""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

TaskType = Literal["simple_qa", "code_generation", "compliance", "report_gen"]


class TriageResult(BaseModel):
    """Structured output from the triage LLM call."""

    task_type: TaskType = Field(..., description="Determined task type")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., max_length=200)


_TRIAGE_SYSTEM = """You are a task classifier for a cybersecurity AI engine.
Classify the user request into exactly one of:
- simple_qa: factual questions, explanations, listings
- code_generation: writing, fixing, or refactoring code / scripts
- compliance: NCA ECC / ISO / regulatory mapping, audit, control analysis
- report_gen: generating PDF reports, executive summaries, documents

Respond with structured JSON only."""


async def classify_task(description: str) -> TriageResult:
    """
    Use Haiku to classify the task description.

    Falls back to heuristics if the LLM call fails.
    """
    from engine.llm_manager import LLMManager

    llm = LLMManager()

    try:
        result = await llm.call_structured(
            task_type="triage",
            user_prompt=f"Classify this request: {description}",
            response_model=TriageResult,
            system=_TRIAGE_SYSTEM,
            use_result_cache=True,
            use_prompt_cache=False,  # triage prompts are short, caching not worthwhile
        )
        logger.info(
            "LLM triage: type=%s confidence=%.2f", result.task_type, result.confidence
        )
        return result

    except Exception as exc:
        logger.warning("LLM triage failed (%s) — falling back to heuristics", exc)
        from engine.orchestrator import _heuristic_triage

        heuristic_type = _heuristic_triage(description)
        return TriageResult(
            task_type=heuristic_type,  # type: ignore[arg-type]
            confidence=0.6,
            reasoning="heuristic fallback",
        )
