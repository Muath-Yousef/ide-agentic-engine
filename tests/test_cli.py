from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from engine.cli import app

runner = CliRunner()


def test_cli_self_check():
    with patch("engine.cli._run_self_check") as mock_check:
        result = runner.invoke(app, ["self-check"])
        assert result.exit_code == 0
        assert "Running Engine Self-Check" in result.stdout


def test_cli_status():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Engine Status: Nominal" in result.stdout


def test_cli_compliance_no_records():
    with patch("socroot.evidence_store.EvidenceStore.get_records") as mock_get:
        mock_get.return_value = []
        result = runner.invoke(app, ["compliance", "--client", "unknown"])
        assert result.exit_code == 0
        assert "No compliance records found" in result.stdout


def test_cli_scan_smoke():
    # We mock the underlying agent call to avoid real LLM
    with patch("agents.compliance_agent.run_compliance_analysis") as mock_analysis:
        mock_analysis.return_value = ([], [])
        result = runner.invoke(app, ["scan", "--client", "test", "--target", "example.com"])
        assert result.exit_code == 0
        assert "Starting scan for: example.com" in result.stdout
