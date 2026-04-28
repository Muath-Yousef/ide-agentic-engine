"""
Report Agent — generate a PDF compliance report from findings and evidence.

Uses ReportLab (or WeasyPrint fallback) to produce a professional PDF.
The LLM generates the narrative sections; layout is handled in Python.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", "reports/output"))
_REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ReportNarrative(BaseModel):
    """LLM-generated narrative sections for the PDF."""

    executive_summary: str = Field(..., max_length=1500)
    risk_overview: str = Field(..., max_length=1000)
    remediation_roadmap: str = Field(..., max_length=1500)
    conclusion: str = Field(..., max_length=500)


_NARRATIVE_SYSTEM = """You are a cybersecurity report writer specialising in NCA ECC compliance
for Saudi organisations. Write in clear, professional English. Be concise but comprehensive.
Avoid jargon where possible. Tailor recommendations to the specific findings provided."""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def generate_report(
    client_id: str,
    target: str,
    findings: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> str:
    """
    Generate a PDF compliance report.

    Returns the absolute path to the generated PDF file.
    """
    from engine.llm_manager import LLMManager

    llm = LLMManager()

    # Generate narrative with LLM
    findings_summary = _summarise_findings(findings)
    user_prompt = (
        f"Client: {client_id}  Target: {target}\n"
        f"Findings summary:\n{findings_summary}\n"
        f"Evidence records: {len(evidence)}\n\n"
        f"Write the report narrative sections."
    )

    try:
        narrative: ReportNarrative = await llm.call_structured(
            task_type="report_gen",
            user_prompt=user_prompt,
            response_model=ReportNarrative,
            system=_NARRATIVE_SYSTEM,
        )
    except Exception as exc:
        logger.error("Report narrative LLM call failed: %s", exc)
        narrative = ReportNarrative(
            executive_summary="Automated narrative generation failed.",
            risk_overview="See findings table.",
            remediation_roadmap="Address critical and high severity findings first.",
            conclusion="Report generated with partial data.",
        )

    # Build PDF
    report_path = _REPORTS_DIR / f"{client_id}_compliance_report.pdf"
    _build_pdf(report_path, client_id, target, findings, narrative)

    logger.info("Report generated: %s", report_path)
    return str(report_path)


def _summarise_findings(findings: list[dict[str, Any]]) -> str:
    """Compact findings summary for LLM context."""
    if not findings:
        return "No findings."
    lines = []
    for f in findings[:20]:  # cap at 20 to stay within tokens
        lines.append(
            f"  [{f.get('severity','?').upper()}] {f.get('title','?')} "
            f"(CVSS: {f.get('cvss_score','?')}) "
            f"Controls: {', '.join(f.get('nca_control_ids', []))}"
        )
    if len(findings) > 20:
        lines.append(f"  ... and {len(findings) - 20} more findings")
    return "\n".join(lines)


def _build_pdf(
    path: Path,
    client_id: str,
    target: str,
    findings: list[dict[str, Any]],
    narrative: ReportNarrative,
) -> None:
    """
    Build a PDF using ReportLab.  Falls back to plain text if unavailable.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

        doc = SimpleDocTemplate(str(path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(f"NCA ECC Compliance Report — {client_id}", styles["Title"]))
        story.append(Paragraph(f"Target: {target}", styles["Normal"]))
        story.append(Spacer(1, 12))

        for section_title, text in [
            ("Executive Summary", narrative.executive_summary),
            ("Risk Overview", narrative.risk_overview),
            ("Remediation Roadmap", narrative.remediation_roadmap),
            ("Conclusion", narrative.conclusion),
        ]:
            story.append(Paragraph(section_title, styles["Heading2"]))
            story.append(Paragraph(text, styles["Normal"]))
            story.append(Spacer(1, 8))

        if findings:
            story.append(Paragraph("Findings", styles["Heading2"]))
            table_data = [["Severity", "Title", "CVSS", "NCA Controls"]]
            for f in findings:
                table_data.append([
                    f.get("severity", ""),
                    f.get("title", "")[:60],
                    str(f.get("cvss_score", "")),
                    ", ".join(f.get("nca_control_ids", [])),
                ])
            table = Table(table_data, hAlign="LEFT")
            story.append(table)

        doc.build(story)

    except ImportError:
        logger.warning("ReportLab not installed — writing plain text report")
        with open(path.with_suffix(".txt"), "w", encoding="utf-8") as fh:
            fh.write(f"NCA ECC Compliance Report — {client_id}\nTarget: {target}\n\n")
            fh.write(f"Executive Summary:\n{narrative.executive_summary}\n\n")
            fh.write(f"Risk Overview:\n{narrative.risk_overview}\n\n")
            for f in findings:
                fh.write(f"[{f.get('severity','?')}] {f.get('title','?')}\n")
