from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.compliance_agent import (
    ComplianceAnalysisResult,
    NCAControlMapping,
    run_compliance_analysis,
)
from agents.report_agent import ReportNarrative, generate_report
from agents.triage_agent import TriageResult, classify_task


@pytest.mark.asyncio
async def test_compliance_agent_success():
    # Mock LLMManager
    with patch("engine.llm_manager.LLMManager") as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.call_structured = AsyncMock()

        # Setup mock response
        mock_analysis = ComplianceAnalysisResult(
            client_id="test_client",
            total_findings=1,
            critical_count=1,
            high_count=0,
            nca_compliance_score=50.0,
            mappings=[
                NCAControlMapping(
                    finding_id="F1",
                    title="Test Finding",
                    severity="critical",
                    cvss_score=9.0,
                    nca_control_ids=["ECC-1-1"],
                    remediation_summary="Fix it",
                    remediation_priority=1,
                    attack_vector="Network",
                )
            ],
            executive_summary="Summary",
        )
        mock_llm_instance.call_structured.return_value = mock_analysis

        # Mock EvidenceStore
        with patch("socroot.evidence_store.EvidenceStore") as MockStore:
            mock_store_instance = MockStore.return_value
            mock_store_instance.add_record = MagicMock(return_value={"id": "record_1"})

            scan_results = {"tool1": "vulnerability detected"}
            findings, evidence = await run_compliance_analysis("test_client", scan_results)

            assert len(findings) == 1
            assert findings[0]["title"] == "Test Finding"
            assert len(evidence) == 1
            assert evidence[0]["id"] == "record_1"
            mock_store_instance.add_record.assert_called_once()


@pytest.mark.asyncio
async def test_triage_agent_llm_success():
    with patch("engine.llm_manager.LLMManager") as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.call_structured = AsyncMock()

        mock_result = TriageResult(
            task_type="compliance", confidence=0.95, reasoning="Mentions NCA ECC"
        )
        mock_llm_instance.call_structured.return_value = mock_result

        result = await classify_task("Help me with NCA ECC mapping")
        assert result.task_type == "compliance"
        assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_triage_agent_fallback():
    with patch("engine.llm_manager.LLMManager") as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.call_structured = AsyncMock(side_effect=Exception("LLM Down"))

        # Heuristic for "pdf" should be "report_gen"
        result = await classify_task("Generate a PDF report")
        assert result.task_type == "report_gen"
        assert result.reasoning == "heuristic fallback"


@pytest.mark.asyncio
async def test_report_agent_success():
    with patch("engine.llm_manager.LLMManager") as MockLLM:
        mock_llm_instance = MockLLM.return_value
        mock_llm_instance.call_structured = AsyncMock()

        mock_narrative = ReportNarrative(
            executive_summary="Exec",
            risk_overview="Risk",
            remediation_roadmap="Roadmap",
            conclusion="End",
        )
        mock_llm_instance.call_structured.return_value = mock_narrative

        # Mock PDF building to avoid disk writes in tests
        with patch("agents.report_agent._build_pdf") as mock_build:
            path = await generate_report("client1", "target1", [], [])
            assert "client1_compliance_report.pdf" in path
            mock_build.assert_called_once()
