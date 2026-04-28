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
    Build a PDF using ReportLab with professional styling.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        doc = SimpleDocTemplate(
            str(path), pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72
        )

        styles = getSampleStyleSheet()
        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=24,
            textColor=colors.HexColor("#1e3a8a"),  # Deep blue
            spaceAfter=20,
        )
        h2_style = ParagraphStyle(
            "CustomH2",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#0f172a"),
            borderPadding=(0, 0, 4, 0),
            borderColor=colors.HexColor("#cbd5e1"),
            borderWidth=1,
            spaceAfter=10,
        )
        normal_style = styles["Normal"]
        cell_style = ParagraphStyle("CellStyle", parent=styles["Normal"], fontSize=9)

        story = []

        # Title Page
        story.append(Paragraph(f"NCA ECC Compliance Report", title_style))
        story.append(Paragraph(f"<b>Client:</b> {client_id}", styles["Heading3"]))
        story.append(Paragraph(f"<b>Target:</b> {target}", styles["Heading3"]))
        story.append(Spacer(1, 30))

        # Narrative Sections
        for section_title, text in [
            ("Executive Summary", narrative.executive_summary),
            ("Risk Overview", narrative.risk_overview),
            ("Remediation Roadmap", narrative.remediation_roadmap),
            ("Conclusion", narrative.conclusion),
        ]:
            story.append(Paragraph(section_title, h2_style))
            story.append(Paragraph(text, normal_style))
            story.append(Spacer(1, 15))

        # Findings Table
        if findings:
            story.append(Paragraph("Detailed Findings", h2_style))
            story.append(Spacer(1, 10))

            # Header
            table_data = [
                [
                    Paragraph("<b>Severity</b>", cell_style),
                    Paragraph("<b>Title</b>", cell_style),
                    Paragraph("<b>CVSS</b>", cell_style),
                    Paragraph("<b>NCA Controls</b>", cell_style),
                ]
            ]

            for f in findings:
                sev = str(f.get("severity", "UNKNOWN")).upper()
                sev_color = (
                    "#ef4444"
                    if sev == "CRITICAL"
                    else "#f97316" if sev == "HIGH" else "#eab308" if sev == "MEDIUM" else "#3b82f6"
                )

                table_data.append(
                    [
                        Paragraph(f'<font color="{sev_color}"><b>{sev}</b></font>', cell_style),
                        Paragraph(f.get("title", ""), cell_style),
                        Paragraph(str(f.get("cvss_score", "")), cell_style),
                        Paragraph(", ".join(f.get("nca_control_ids", [])), cell_style),
                    ]
                )

            col_widths = [0.8 * inch, 3.0 * inch, 0.6 * inch, 1.8 * inch]
            table = Table(table_data, colWidths=col_widths, repeatRows=1)

            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                        ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("TOPPADDING", (0, 0), (-1, 0), 12),
                    ]
                )
            )

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
