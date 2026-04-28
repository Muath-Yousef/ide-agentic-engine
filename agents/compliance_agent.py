"""
Compliance Agent — maps security findings to NCA ECC controls.

NCA ECC (Essential Cybersecurity Controls) is the Saudi national framework.
Each finding is analysed by the LLM and tagged with the relevant control IDs.
Evidence records are created and stored in the append-only EvidenceStore.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class NCAControlMapping(BaseModel):
    """Mapping of a single finding to NCA ECC controls."""

    finding_id: str
    title: str
    severity: str = Field(..., pattern="^(critical|high|medium|low|info)$")
    cvss_score: float = Field(..., ge=0.0, le=10.0)
    nca_control_ids: list[str] = Field(
        ..., description="e.g. ['ECC-1-1', 'ECC-2-3-1']"
    )
    remediation_summary: str = Field(..., max_length=500)
    remediation_priority: int = Field(..., ge=1, le=5)
    attack_vector: str


class ComplianceAnalysisResult(BaseModel):
    """Full analysis result for all findings from a scan."""

    client_id: str
    total_findings: int
    critical_count: int
    high_count: int
    nca_compliance_score: float = Field(..., ge=0.0, le=100.0)
    mappings: list[NCAControlMapping]
    executive_summary: str = Field(..., max_length=1000)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_COMPLIANCE_SYSTEM = """You are a Saudi NCA ECC cybersecurity compliance expert.
Map security findings to the correct NCA Essential Cybersecurity Controls (ECC-1, ECC-2, etc.).
Be precise with control IDs. CVSS scores must be accurate. Remediation must be actionable.
Return valid JSON matching the exact schema requested."""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def run_compliance_analysis(
    client_id: str,
    scan_results: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Analyse scan results and produce NCA ECC compliance mappings + evidence.

    Returns:
        (findings, evidence_records) — both as lists of plain dicts
        suitable for JSON serialisation and state storage.
    """
    from engine.llm_manager import LLMManager
    from socroot.evidence_store import EvidenceStore

    llm = LLMManager()
    store = EvidenceStore()

    # Prepare context for the LLM
    findings_text = _format_scan_results(scan_results)
    user_prompt = (
        f"Client: {client_id}\n"
        f"Scan results:\n{findings_text}\n\n"
        f"Map ALL findings to NCA ECC controls. Compute a compliance score "
        f"(100 = fully compliant, 0 = no controls met)."
    )

    try:
        analysis: ComplianceAnalysisResult = await llm.call_structured(
            task_type="compliance_map",
            user_prompt=user_prompt,
            response_model=ComplianceAnalysisResult,
            system=_COMPLIANCE_SYSTEM,
        )
    except Exception as exc:
        logger.error("Compliance LLM call failed: %s", exc, exc_info=True)
        return [], []

    # Convert mappings to plain dicts
    findings = [m.model_dump() for m in analysis.mappings]

    # Create evidence records in the append-only store
    evidence_records: list[dict[str, Any]] = []
    for mapping in analysis.mappings:
        record = store.add_record(
            client_id=client_id,
            finding=mapping.model_dump(),
            metadata={
                "nca_control_ids": mapping.nca_control_ids,
                "compliance_score": analysis.nca_compliance_score,
            },
        )
        evidence_records.append(record)

    logger.info(
        "Compliance analysis: client=%s findings=%d score=%.1f%%",
        client_id,
        analysis.total_findings,
        analysis.nca_compliance_score,
    )
    return findings, evidence_records


def _format_scan_results(scan_results: dict[str, Any]) -> str:
    """Convert raw scan results dict to a structured text for LLM context."""
    if not scan_results:
        return "No scan results available. Assume a default SME environment."

    lines: list[str] = []
    for tool, result in scan_results.items():
        lines.append(f"--- {tool.upper()} ---")
        if isinstance(result, str):
            lines.append(result[:2000])  # cap to avoid token explosion
        elif isinstance(result, dict):
            import json
            lines.append(json.dumps(result, indent=2)[:2000])
        else:
            lines.append(str(result)[:500])
    return "\n".join(lines)
